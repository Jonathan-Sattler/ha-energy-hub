"""Price forecast normalisation (pure Python, no Home Assistant imports).

Tariff integrations expose their forecast in different shapes. This module
accepts the common ones and returns a fixed schema:
``[{"start": datetime, "end": datetime, "price": float}, ...]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo
from typing import Any

START_KEYS = ("start", "start_time", "from", "startsAt", "starts_at", "datetime", "time", "hour")
END_KEYS = ("end", "end_time", "to", "endsAt", "ends_at")
PRICE_KEYS = ("price", "total", "value", "price_per_kwh", "price_ct_per_kwh", "cost")


@dataclass(slots=True)
class PriceSlot:
    """One forecast interval."""

    start: datetime
    end: datetime
    price: float

    def as_dict(self) -> dict[str, Any]:
        """Serialise for entity attributes."""
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "price": self.price}


def _parse_dt(value: Any, tz: tzinfo) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=tz)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=tz)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=tz)
    return None


def _first(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def normalise_forecast(raw: Any, tz: tzinfo, scale: float = 1.0) -> list[PriceSlot]:
    """Turn a vendor forecast attribute into a sorted list of PriceSlot.

    ``scale`` multiplies prices (for example 0.01 for ct/kWh sources).
    Missing end times are filled from the next slot's start, the last one
    assumes the dominant interval length.
    """
    if not isinstance(raw, (list, tuple)):
        return []
    parsed: list[tuple[datetime, datetime | None, float]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        start = _parse_dt(_first(item, START_KEYS), tz)
        price = _first(item, PRICE_KEYS)
        if start is None or price is None:
            continue
        try:
            price_f = float(price) * scale
        except TypeError, ValueError:
            continue
        end = _parse_dt(_first(item, END_KEYS), tz)
        parsed.append((start, end, price_f))
    parsed.sort(key=lambda row: row[0])
    if not parsed:
        return []

    # Dominant interval length for filling missing ends.
    gaps = [
        (parsed[i + 1][0] - parsed[i][0]).total_seconds()
        for i in range(len(parsed) - 1)
        if (parsed[i + 1][0] - parsed[i][0]).total_seconds() > 0
    ]
    default_len = timedelta(seconds=min(gaps)) if gaps else timedelta(hours=1)

    slots: list[PriceSlot] = []
    for i, (start, end, price_f) in enumerate(parsed):
        if end is None:
            end = parsed[i + 1][0] if i + 1 < len(parsed) else start + default_len
        slots.append(PriceSlot(start=start, end=end, price=price_f))
    return slots


def slots_for_day(slots: list[PriceSlot], day: date, tz: tzinfo) -> list[PriceSlot]:
    """Filter slots that start on the given local day."""
    return [s for s in slots if s.start.astimezone(tz).date() == day]


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile; pct in 0..100."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, min(len(ordered), round(pct / 100.0 * len(ordered))))
    return ordered[rank - 1]


def day_stats(slots: list[PriceSlot]) -> dict[str, float | str | None]:
    """Min, max, mean and cheapest slot start for a list of slots."""
    if not slots:
        return {"min": None, "max": None, "mean": None, "cheapest_start": None}
    prices = [s.price for s in slots]
    cheapest = min(slots, key=lambda s: s.price)
    return {
        "min": min(prices),
        "max": max(prices),
        "mean": sum(prices) / len(prices),
        "cheapest_start": cheapest.start.isoformat(),
    }


def current_slot(slots: list[PriceSlot], now: datetime) -> PriceSlot | None:
    """The slot covering ``now``."""
    for s in slots:
        if s.start <= now < s.end:
            return s
    return None


def is_cheap(
    slots: list[PriceSlot], now: datetime, tz: tzinfo, pct: float, current_price: float | None
) -> bool | None:
    """Whether the current price is at or below the day's pct-percentile."""
    today = slots_for_day(slots, now.astimezone(tz).date(), tz)
    threshold = percentile([s.price for s in today], pct)
    if threshold is None:
        return None
    price = current_price
    if price is None:
        slot = current_slot(slots, now)
        price = slot.price if slot else None
    if price is None:
        return None
    return price <= threshold
