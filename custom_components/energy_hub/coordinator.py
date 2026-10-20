"""Push-based coordinator feeding the calculation engine."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BATTERY_POWER,
    CONF_BATTERY_POWER_SIGN,
    CONF_BOILER_EFFICIENCY,
    CONF_CHEAP_NOW,
    CONF_CHEAP_PERCENTILE,
    CONF_EXPORT_PRICE,
    CONF_EXPORT_PRICE_FIXED,
    CONF_EXPORT_REVENUE_OVERRIDE,
    CONF_FLAT_REFERENCE_PRICE,
    CONF_FORECAST_ATTRIBUTE,
    CONF_GAS_CALORIFIC_VALUE,
    CONF_GAS_CO2_FACTOR,
    CONF_GAS_CORRECTION_FACTOR,
    CONF_GAS_DHW_VOLUME,
    CONF_GAS_HEATING_VOLUME,
    CONF_GAS_PRICE,
    CONF_GAS_PRICE_ENTITY,
    CONF_GAS_TOTAL_VOLUME,
    CONF_GRID_CO2_INTENSITY,
    CONF_GRID_EXPORT_POWER,
    CONF_GRID_IMPORT_POWER,
    CONF_GRID_POWER,
    CONF_GRID_POWER_SIGN,
    CONF_HDD_BASE_TEMP,
    CONF_IMPORT_COST_OVERRIDE,
    CONF_IMPORT_PRICE,
    CONF_LOAD_ENERGY,
    CONF_OUTSIDE_TEMP,
    CONF_PV_ENERGY,
    CONF_PV_POWER,
    CONF_SOLAR_THERMAL_ENERGY,
    DEFAULT_BOILER_EFFICIENCY,
    DEFAULT_CHEAP_PERCENTILE,
    DEFAULT_FORECAST_ATTRIBUTE,
    DEFAULT_GAS_CALORIFIC_VALUE,
    DEFAULT_GAS_CO2_FACTOR,
    DEFAULT_GAS_CORRECTION_FACTOR,
    DEFAULT_HDD_BASE_TEMP,
    DOMAIN,
    ENTITY_SLOTS,
    SAVE_DELAY_SECONDS,
    SIGN_POSITIVE_IS_DISCHARGING,
    SIGN_POSITIVE_IS_EXPORT,
    SLOT_TO_ENGINE_INPUT,
    SLOT_UNIT_FAMILY,
    STORAGE_VERSION,
    UNIT_ENERGY,
    UNIT_GAS,
    UNIT_INTENSITY,
    UNIT_NONE,
    UNIT_POWER,
    UNIT_TEMPERATURE,
)
from .engine import EnergyEngine, EngineConfig, EngineState
from .price import PriceSlot, current_slot, day_stats, is_cheap, normalise_forecast, slots_for_day

_LOGGER = logging.getLogger(__name__)

POWER_FACTORS = {"W": 1.0, "kW": 1000.0, "MW": 1_000_000.0, "mW": 0.001}
ENERGY_FACTORS = {"kWh": 1.0, "Wh": 0.001, "MWh": 1000.0, "GJ": 277.778, "MJ": 0.277778}
GAS_VOLUME_FACTORS = {"m³": 1.0, "m3": 1.0, "ft³": 0.0283168, "ft3": 0.0283168, "L": 0.001}
INTENSITY_FACTORS = {"gCO2eq/kWh": 1.0, "g/kWh": 1.0, "kgCO2eq/kWh": 1000.0, "kg/kWh": 1000.0}


def _float(state: State | None) -> float | None:
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, "", None):
        return None
    try:
        return float(state.state)
    except TypeError, ValueError:
        return None


def _unit(state: State | None) -> str | None:
    if state is None:
        return None
    return state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)


def convert(value: float | None, family: str, unit: str | None) -> tuple[float | None, bool]:
    """Convert to the engine's unit for the family.

    Returns (value, in_kwh_flag) where the flag only matters for gas slots.
    """
    if value is None:
        return None, False
    if family == UNIT_POWER:
        return value * POWER_FACTORS.get(unit or "W", 1.0), False
    if family == UNIT_ENERGY:
        return value * ENERGY_FACTORS.get(unit or "kWh", 1.0), False
    if family == UNIT_GAS:
        if unit in ENERGY_FACTORS:
            return value * ENERGY_FACTORS[unit], True
        return value * GAS_VOLUME_FACTORS.get(unit or "m³", 1.0), False
    if family == UNIT_TEMPERATURE:
        if unit == "°F":
            return (value - 32.0) * 5.0 / 9.0, False
        if unit == "K":
            return value - 273.15, False
        return value, False
    if family == UNIT_INTENSITY:
        return value * INTENSITY_FACTORS.get(unit or "gCO2eq/kWh", 1.0), False
    return value, False


def build_engine_config(options: dict[str, Any]) -> EngineConfig:
    """Translate config entry options into an EngineConfig."""
    return EngineConfig(
        gas_calorific_value=float(
            options.get(CONF_GAS_CALORIFIC_VALUE, DEFAULT_GAS_CALORIFIC_VALUE)
        ),
        gas_correction_factor=float(
            options.get(CONF_GAS_CORRECTION_FACTOR, DEFAULT_GAS_CORRECTION_FACTOR)
        ),
        gas_price=_opt_float(options.get(CONF_GAS_PRICE)),
        boiler_efficiency=float(options.get(CONF_BOILER_EFFICIENCY, DEFAULT_BOILER_EFFICIENCY)),
        gas_co2_factor=float(options.get(CONF_GAS_CO2_FACTOR, DEFAULT_GAS_CO2_FACTOR)),
        flat_reference_price=_opt_float(options.get(CONF_FLAT_REFERENCE_PRICE)),
        export_price_fixed=_opt_float(options.get(CONF_EXPORT_PRICE_FIXED)),
        hdd_base_temp=float(options.get(CONF_HDD_BASE_TEMP, DEFAULT_HDD_BASE_TEMP)),
        has_load_energy_slot=bool(options.get(CONF_LOAD_ENERGY)),
    )


def _opt_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


class EnergyHubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Listens to mapped entities, runs the engine, persists its state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}:{entry.entry_id}",
            update_interval=None,
        )
        self.entry = entry
        self.options: dict[str, Any] = {**entry.data, **entry.options}
        self.slots: dict[str, str] = {
            slot: entity_id for slot in ENTITY_SLOTS if (entity_id := self.options.get(slot))
        }
        self.engine = EnergyEngine(build_engine_config(self.options))
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._unsubscribers: list[CALLBACK_TYPE] = []
        self._save_handle: CALLBACK_TYPE | None = None
        self.forecast: list[PriceSlot] = []
        self.price_stats: dict[str, Any] = {}
        self.cheap_now: bool | None = None
        self.raw: dict[str, Any] = {}
        self.data = {}

    # ----------------------------------------------------------- feature flags
    def has_slot(self, *slots: str) -> bool:
        """Whether every named slot is mapped."""
        return all(slot in self.slots for slot in slots)

    def has_any_slot(self, *slots: str) -> bool:
        """Whether at least one named slot is mapped."""
        return any(slot in self.slots for slot in slots)

    @property
    def features(self) -> set[str]:
        """Active feature names derived from the mapping."""
        cfg = self.engine.config
        f: set[str] = {"grid", "load", "self_sufficiency"}
        if self.has_slot(CONF_GRID_POWER) or self.has_slot(
            CONF_GRID_IMPORT_POWER, CONF_GRID_EXPORT_POWER
        ):
            f.add("grid_power")
        if self.has_slot(CONF_PV_ENERGY):
            f.update({"pv", "self_consumption"})
        if self.has_slot(CONF_PV_POWER):
            f.add("pv_power")
        if self.has_slot(CONF_BATTERY_POWER):
            f.add("battery_power")
        import_cost = self.has_any_slot(CONF_IMPORT_PRICE, CONF_IMPORT_COST_OVERRIDE)
        if import_cost:
            f.add("import_cost")
        if (
            self.has_any_slot(CONF_EXPORT_PRICE, CONF_EXPORT_REVENUE_OVERRIDE)
            or cfg.export_price_fixed is not None
        ):
            f.add("export_revenue")
        if import_cost and cfg.flat_reference_price is not None:
            f.add("flat_tariff")
        if self.has_slot(CONF_GRID_CO2_INTENSITY):
            f.add("carbon_grid")
            if "grid_power" in f:
                f.add("home_intensity")
            if "pv" in f:
                f.add("carbon_pv")
        gas = self.has_any_slot(CONF_GAS_HEATING_VOLUME, CONF_GAS_DHW_VOLUME, CONF_GAS_TOTAL_VOLUME)
        gas_price = self.has_slot(CONF_GAS_PRICE_ENTITY) or cfg.gas_price is not None
        if gas:
            f.add("gas")
            if self.has_slot(CONF_GAS_HEATING_VOLUME):
                f.add("gas_heating")
            if self.has_slot(CONF_GAS_DHW_VOLUME):
                f.add("gas_dhw")
            if gas_price:
                f.add("gas_cost")
        if self.has_slot(CONF_SOLAR_THERMAL_ENERGY):
            f.update({"solar_thermal", "solar_thermal_gas"})
            if gas_price:
                f.add("solar_thermal_cost")
            if self.has_slot(CONF_GAS_DHW_VOLUME):
                f.add("solar_share_dhw")
        if self.has_slot(CONF_OUTSIDE_TEMP):
            f.add("hdd")
            if self.has_slot(CONF_GAS_HEATING_VOLUME):
                f.add("gas_per_hdd")
        if self.has_slot(CONF_IMPORT_PRICE):
            f.update({"price_forecast", "cheap"})
        elif self.has_slot(CONF_CHEAP_NOW):
            f.add("cheap")
        return f

    # ------------------------------------------------------------- lifecycle
    async def async_load(self) -> None:
        """Restore persisted engine state."""
        stored = await self._store.async_load()
        self.engine.state = EngineState.from_dict(stored)
        self.data = self.engine.derive({})

    @callback
    def async_start(self) -> None:
        """Subscribe to source entities and timers."""
        entity_ids = sorted(set(self.slots.values()))
        if entity_ids:
            self._unsubscribers.append(
                async_track_state_change_event(self.hass, entity_ids, self._handle_state_change)
            )
        self._unsubscribers.append(
            async_track_time_change(self.hass, self._handle_tick, hour=0, minute=0, second=10)
        )
        self._unsubscribers.append(
            async_track_time_interval(self.hass, self._handle_tick, timedelta(minutes=5))
        )
        self.recalculate()

    @callback
    def async_stop(self) -> None:
        """Unsubscribe everything."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        if self._save_handle:
            self._save_handle()
            self._save_handle = None

    async def async_save(self) -> None:
        """Persist engine state now."""
        if self._save_handle:
            self._save_handle()
            self._save_handle = None
        await self._store.async_save(self.engine.state.as_dict())

    @callback
    def _schedule_save(self) -> None:
        if self._save_handle:
            return

        async def _save(_now: datetime) -> None:
            self._save_handle = None
            await self._store.async_save(self.engine.state.as_dict())

        self._save_handle = async_call_later(self.hass, SAVE_DELAY_SECONDS, _save)

    # --------------------------------------------------------------- updates
    @callback
    def _handle_state_change(self, _event: Event[EventStateChangedData]) -> None:
        self.recalculate()

    @callback
    def _handle_tick(self, _now: datetime) -> None:
        self.recalculate()

    def _gather(self) -> dict[str, float | None]:
        """Read all mapped entities and normalise them for the engine."""
        values: dict[str, float | None] = {}
        raw: dict[str, Any] = {}
        cfg = self.engine.config
        for slot, entity_id in self.slots.items():
            state = self.hass.states.get(entity_id)
            family = SLOT_UNIT_FAMILY.get(slot, UNIT_NONE)
            if family == UNIT_NONE:
                raw[slot] = None if state is None else state.state == STATE_ON
                continue
            value, in_kwh = convert(_float(state), family, _unit(state))
            raw[slot] = value
            if slot == CONF_GAS_HEATING_VOLUME:
                cfg.gas_heating_in_kwh = in_kwh
            elif slot == CONF_GAS_DHW_VOLUME:
                cfg.gas_dhw_in_kwh = in_kwh
            elif slot == CONF_GAS_TOTAL_VOLUME:
                cfg.gas_total_in_kwh = in_kwh
            values[SLOT_TO_ENGINE_INPUT.get(slot, slot)] = value

        # Sign normalisation.
        if (gp := values.get(CONF_GRID_POWER)) is not None and self.options.get(
            CONF_GRID_POWER_SIGN
        ) == SIGN_POSITIVE_IS_EXPORT:
            values[CONF_GRID_POWER] = -gp
        if (bp := values.get(CONF_BATTERY_POWER)) is not None and self.options.get(
            CONF_BATTERY_POWER_SIGN
        ) == SIGN_POSITIVE_IS_DISCHARGING:
            values[CONF_BATTERY_POWER] = -bp
        self.raw = raw
        return values

    def _update_forecast(self, now: datetime) -> None:
        entity_id = self.slots.get(CONF_IMPORT_PRICE)
        if not entity_id:
            return
        state = self.hass.states.get(entity_id)
        attribute = self.options.get(CONF_FORECAST_ATTRIBUTE, DEFAULT_FORECAST_ATTRIBUTE)
        tz = dt_util.get_default_time_zone()
        raw = state.attributes.get(attribute) if state else None
        self.forecast = normalise_forecast(raw, tz)
        today = now.astimezone(tz).date()
        tomorrow = today + timedelta(days=1)
        self.price_stats = {
            "today": day_stats(slots_for_day(self.forecast, today, tz)),
            "tomorrow": day_stats(slots_for_day(self.forecast, tomorrow, tz)),
        }
        slot = current_slot(self.forecast, now)
        self.price_stats["current_slot_end"] = slot.end.isoformat() if slot else None

    def _update_cheap(self, now: datetime, values: dict[str, float | None]) -> None:
        if CONF_CHEAP_NOW in self.slots:
            self.cheap_now = self.raw.get(CONF_CHEAP_NOW)
            return
        if not self.forecast:
            self.cheap_now = None
            return
        pct = float(self.options.get(CONF_CHEAP_PERCENTILE, DEFAULT_CHEAP_PERCENTILE))
        self.cheap_now = is_cheap(
            self.forecast, now, dt_util.get_default_time_zone(), pct, values.get(CONF_IMPORT_PRICE)
        )

    @callback
    def recalculate(self) -> None:
        """Run one engine update from current states."""
        now = dt_util.now()
        values = self._gather()
        self._update_forecast(now)
        self._update_cheap(now, values)
        data = self.engine.update(values, now)
        data["cheap_now"] = self.cheap_now
        data["battery_soc"] = self.raw.get("battery_soc")
        self.async_set_updated_data(data)
        self._schedule_save()
