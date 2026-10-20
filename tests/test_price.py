"""Tests for price forecast normalisation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.energy_hub.price import (
    day_stats,
    is_cheap,
    normalise_forecast,
    percentile,
    slots_for_day,
)

BERLIN = ZoneInfo("Europe/Berlin")


def test_normalise_start_end_price_shape() -> None:
    raw = [
        {"start": "2026-10-20T08:45:00+00:00", "end": "2026-10-20T09:00:00+00:00", "price": 0.37},
        {"start": "2026-10-20T08:30:00+00:00", "end": "2026-10-20T08:45:00+00:00", "price": 0.36},
    ]
    slots = normalise_forecast(raw, BERLIN)
    assert [s.price for s in slots] == [0.36, 0.37]
    assert slots[0].end == slots[1].start


def test_normalise_fills_missing_end_from_next_start() -> None:
    raw = [
        {"startsAt": "2026-10-20T10:00:00+02:00", "total": 0.30},
        {"startsAt": "2026-10-20T11:00:00+02:00", "total": 0.31},
    ]
    slots = normalise_forecast(raw, BERLIN)
    assert slots[0].end == slots[1].start
    assert slots[1].end - slots[1].start == timedelta(hours=1)


def test_normalise_ignores_garbage() -> None:
    assert normalise_forecast(None, BERLIN) == []
    assert normalise_forecast([{"foo": 1}, "x", {"start": "bad", "price": 1}], BERLIN) == []


def test_percentile_nearest_rank() -> None:
    values = [0.1, 0.2, 0.3, 0.4]
    assert percentile(values, 25) == 0.1
    assert percentile(values, 50) == 0.2
    assert percentile(values, 100) == 0.4
    assert percentile([], 50) is None


def test_day_filter_stats_and_cheap() -> None:
    base = datetime(2026, 10, 20, 0, 0, tzinfo=BERLIN)
    raw = [
        {"start": (base + timedelta(hours=h)).isoformat(), "price": 0.20 + 0.01 * h}
        for h in range(30)
    ]
    slots = normalise_forecast(raw, BERLIN)
    today = slots_for_day(slots, base.date(), BERLIN)
    assert len(today) == 24
    stats = day_stats(today)
    assert stats["min"] == 0.20
    assert stats["cheapest_start"] == base.isoformat()
    now = (base + timedelta(hours=2)).astimezone(UTC)
    assert is_cheap(slots, now, BERLIN, 25, None) is True
    late = (base + timedelta(hours=20)).astimezone(UTC)
    assert is_cheap(slots, late, BERLIN, 25, None) is False
