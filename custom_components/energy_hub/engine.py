"""Pure calculation engine for Energy Hub.

This module has no Home Assistant imports so the formulas can be unit tested
in isolation. The Home Assistant layer feeds it normalised numbers (W, kWh, m³,
currency/kWh, gCO2eq/kWh, °C) and reads derived values back.

Sign conventions inside the engine:
- grid power: positive = import, negative = export
- battery power: positive = charging, negative = discharging
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Keys of counter-type inputs (monotonic within a cycle, may reset).
COUNTER_INPUTS: tuple[str, ...] = (
    "grid_import_energy",
    "grid_export_energy",
    "pv_energy",
    "battery_charge_energy",
    "battery_discharge_energy",
    "load_energy",
    "gas_heating_volume",
    "gas_dhw_volume",
    "gas_total_volume",
    "solar_thermal_energy",
    "boiler_electricity_energy",
    "import_cost_override",
    "export_revenue_override",
)

# Lifetime accumulators the engine maintains.
ACCUMULATORS: tuple[str, ...] = (
    "grid_import_energy",
    "grid_export_energy",
    "pv_energy",
    "battery_charge_energy",
    "battery_discharge_energy",
    "load_energy",
    "pv_self_consumed_energy",
    "import_cost",
    "export_revenue",
    "flat_tariff_cost",
    "grid_import_co2",
    "avoided_co2_pv",
    "gas_energy_heating",
    "gas_energy_dhw",
    "gas_energy_total",
    "gas_cost",
    "gas_co2",
    "solar_thermal_energy",
    "solar_thermal_avoided_co2",
    "solar_thermal_gas_avoided_volume",
    "solar_thermal_gas_avoided_cost",
    "boiler_electricity_energy",
)


@dataclass(slots=True)
class EngineConfig:
    """Numeric options and feature switches."""

    gas_calorific_value: float = 11.0  # kWh per m³
    gas_correction_factor: float = 0.95
    gas_price: float | None = None  # currency per kWh
    boiler_efficiency: float = 0.95
    gas_co2_factor: float = 0.201  # kg CO2 per kWh
    flat_reference_price: float | None = None  # currency per kWh
    export_price_fixed: float | None = None  # currency per kWh
    hdd_base_temp: float = 15.0  # °C
    gas_heating_in_kwh: bool = False  # slot already delivers kWh
    gas_dhw_in_kwh: bool = False
    gas_total_in_kwh: bool = False
    has_load_energy_slot: bool = False

    @property
    def gas_kwh_per_m3(self) -> float:
        """Energy content of one cubic metre of gas."""
        return self.gas_calorific_value * self.gas_correction_factor


@dataclass(slots=True)
class EngineState:
    """Persisted engine state."""

    last: dict[str, float] = field(default_factory=dict)
    lifetime: dict[str, float] = field(default_factory=dict)
    today: dict[str, float] = field(default_factory=dict)
    day: str | None = None  # ISO date of the current daily window
    temp_weight_sum: float = 0.0  # sum of temp * seconds, for HDD
    temp_seconds: float = 0.0
    last_temp_ts: float | None = None
    last_temp: float | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serialise for storage."""
        return {
            "last": dict(self.last),
            "lifetime": dict(self.lifetime),
            "today": dict(self.today),
            "day": self.day,
            "temp_weight_sum": self.temp_weight_sum,
            "temp_seconds": self.temp_seconds,
            "last_temp_ts": self.last_temp_ts,
            "last_temp": self.last_temp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> EngineState:
        """Deserialise from storage, tolerating missing keys."""
        if not data:
            return cls()
        return cls(
            last={k: float(v) for k, v in (data.get("last") or {}).items()},
            lifetime={k: float(v) for k, v in (data.get("lifetime") or {}).items()},
            today={k: float(v) for k, v in (data.get("today") or {}).items()},
            day=data.get("day"),
            temp_weight_sum=float(data.get("temp_weight_sum") or 0.0),
            temp_seconds=float(data.get("temp_seconds") or 0.0),
            last_temp_ts=data.get("last_temp_ts"),
            last_temp=data.get("last_temp"),
        )


def counter_delta(last: float | None, new: float | None) -> float:
    """Delta between two counter readings, treating a drop as a reset."""
    if new is None or last is None:
        return 0.0
    if new >= last:
        return new - last
    # Drop: the counter reset (daily or otherwise); what is there now was
    # accumulated since the reset.
    return new


class EnergyEngine:
    """Stateful calculator producing all derived values."""

    def __init__(self, config: EngineConfig, state: EngineState | None = None) -> None:
        self.config = config
        self.state = state or EngineState()

    # ------------------------------------------------------------------ helpers
    def _add(self, key: str, delta: float) -> None:
        if delta == 0.0:
            return
        self.state.lifetime[key] = self.state.lifetime.get(key, 0.0) + delta
        self.state.today[key] = self.state.today.get(key, 0.0) + delta

    def _roll_day(self, now: datetime) -> bool:
        day = now.date().isoformat()
        if self.state.day == day:
            return False
        self.state.day = day
        self.state.today = {}
        self.state.temp_weight_sum = 0.0
        self.state.temp_seconds = 0.0
        # Keep last_temp so the new day starts weighting immediately.
        self.state.last_temp_ts = now.timestamp() if self.state.last_temp is not None else None
        return True

    def _track_temperature(self, temp: float | None, now: datetime) -> None:
        """Time-weighted mean: the previous reading holds until it changes."""
        st = self.state
        ts = now.timestamp()
        if st.last_temp is not None and st.last_temp_ts is not None:
            dt = max(0.0, ts - st.last_temp_ts)
            st.temp_weight_sum += st.last_temp * dt
            st.temp_seconds += dt
            st.last_temp_ts = ts
        if temp is not None:
            st.last_temp = temp
            st.last_temp_ts = ts

    # --------------------------------------------------------------------- main
    def update(self, values: dict[str, float | None], now: datetime) -> dict[str, Any]:
        """Feed the current input values and return derived values.

        ``values`` holds normalised numbers keyed by slot name; ``None`` means
        unknown or unavailable. Signed powers must already follow the engine's
        sign conventions.
        """
        cfg = self.config
        st = self.state
        self._roll_day(now)

        # ---- counter deltas --------------------------------------------------
        deltas: dict[str, float] = {}
        for key in COUNTER_INPUTS:
            new = values.get(key)
            if new is None:
                continue
            last = st.last.get(key)
            deltas[key] = counter_delta(last, new)
            st.last[key] = new

        d_import = deltas.get("grid_import_energy", 0.0)
        d_export = deltas.get("grid_export_energy", 0.0)
        d_pv = deltas.get("pv_energy", 0.0)
        d_charge = deltas.get("battery_charge_energy", 0.0)
        d_discharge = deltas.get("battery_discharge_energy", 0.0)
        d_solar = deltas.get("solar_thermal_energy", 0.0)
        d_boiler_el = deltas.get("boiler_electricity_energy", 0.0)

        if cfg.has_load_energy_slot:
            d_load = deltas.get("load_energy", 0.0)
        else:
            d_load = max(0.0, d_pv + d_import - d_export - d_charge + d_discharge)

        # Gas volumes to kWh.
        def gas_kwh(key: str, in_kwh: bool) -> float:
            d = deltas.get(key, 0.0)
            return d if in_kwh else d * cfg.gas_kwh_per_m3

        d_gas_heating = gas_kwh("gas_heating_volume", cfg.gas_heating_in_kwh)
        d_gas_dhw = gas_kwh("gas_dhw_volume", cfg.gas_dhw_in_kwh)
        if "gas_total_volume" in deltas:
            d_gas_total = gas_kwh("gas_total_volume", cfg.gas_total_in_kwh)
        else:
            d_gas_total = d_gas_heating + d_gas_dhw

        # ---- rates -------------------------------------------------------------
        import_price = values.get("import_price")
        export_price = values.get("export_price")
        if export_price is None:
            export_price = cfg.export_price_fixed
        gas_price = values.get("gas_price")
        if gas_price is None:
            gas_price = cfg.gas_price
        intensity = values.get("grid_co2_intensity")  # gCO2eq/kWh

        # ---- accumulate ----------------------------------------------------------
        self._add("grid_import_energy", d_import)
        self._add("grid_export_energy", d_export)
        self._add("pv_energy", d_pv)
        self._add("battery_charge_energy", d_charge)
        self._add("battery_discharge_energy", d_discharge)
        self._add("load_energy", d_load)
        self._add("pv_self_consumed_energy", max(0.0, d_pv - d_export))
        self._add("solar_thermal_energy", d_solar)
        self._add("boiler_electricity_energy", d_boiler_el)
        self._add("gas_energy_heating", d_gas_heating)
        self._add("gas_energy_dhw", d_gas_dhw)
        self._add("gas_energy_total", d_gas_total)

        if "import_cost_override" in deltas:
            self._add("import_cost", deltas["import_cost_override"])
        elif import_price is not None:
            self._add("import_cost", d_import * import_price)

        if "export_revenue_override" in deltas:
            self._add("export_revenue", deltas["export_revenue_override"])
        elif export_price is not None:
            self._add("export_revenue", d_export * export_price)

        if cfg.flat_reference_price is not None:
            self._add("flat_tariff_cost", d_import * cfg.flat_reference_price)

        if intensity is not None:
            self._add("grid_import_co2", d_import * intensity / 1000.0)
            self._add("avoided_co2_pv", d_pv * intensity / 1000.0)

        if gas_price is not None:
            self._add("gas_cost", d_gas_total * gas_price)
        self._add("gas_co2", d_gas_total * cfg.gas_co2_factor)

        if d_solar:
            heat_as_gas_kwh = d_solar / cfg.boiler_efficiency
            self._add("solar_thermal_avoided_co2", heat_as_gas_kwh * cfg.gas_co2_factor)
            self._add(
                "solar_thermal_gas_avoided_volume",
                heat_as_gas_kwh / cfg.gas_kwh_per_m3,
            )
            if gas_price is not None:
                self._add("solar_thermal_gas_avoided_cost", heat_as_gas_kwh * gas_price)

        self._track_temperature(values.get("outside_temp"), now)

        return self.derive(values)

    # ------------------------------------------------------------------ derive
    def derive(self, values: dict[str, float | None]) -> dict[str, Any]:
        """Compute the output dictionary from state and instantaneous values."""
        cfg = self.config
        life = self.state.lifetime
        today = self.state.today
        out: dict[str, Any] = {}

        # Instantaneous powers.
        grid_power = values.get("grid_power")
        import_power = values.get("grid_import_power")
        export_power = values.get("grid_export_power")
        if grid_power is not None:
            import_power = max(0.0, grid_power)
            export_power = max(0.0, -grid_power)
        battery_power = values.get("battery_power")
        charge_power = discharge_power = None
        if battery_power is not None:
            charge_power = max(0.0, battery_power)
            discharge_power = max(0.0, -battery_power)
        pv_power = values.get("pv_power")
        load_power = values.get("load_power")
        if load_power is None and import_power is not None:
            load_power = (
                (pv_power or 0.0)
                + import_power
                - (export_power or 0.0)
                - (charge_power or 0.0)
                + (discharge_power or 0.0)
            )
            load_power = max(0.0, load_power)

        out["grid_import_power"] = import_power
        out["grid_export_power"] = export_power
        out["battery_charge_power"] = charge_power
        out["battery_discharge_power"] = discharge_power
        out["load_power"] = load_power
        out["pv_power"] = pv_power

        # Lifetime accumulators.
        for key in ACCUMULATORS:
            out[key] = life.get(key, 0.0)
            out[f"today_{key}"] = today.get(key, 0.0)

        out["net_electricity_cost"] = out["import_cost"] - out["export_revenue"]
        out["today_net_electricity_cost"] = out["today_import_cost"] - out["today_export_revenue"]
        out["total_energy_cost"] = out["net_electricity_cost"] + out["gas_cost"]
        out["today_total_energy_cost"] = out["today_net_electricity_cost"] + out["today_gas_cost"]
        out["total_co2"] = out["grid_import_co2"] + out["gas_co2"]
        out["today_total_co2"] = out["today_grid_import_co2"] + out["today_gas_co2"]

        if cfg.flat_reference_price is not None:
            out["dynamic_tariff_savings"] = out["flat_tariff_cost"] - out["import_cost"]
            out["today_dynamic_tariff_savings"] = (
                out["today_flat_tariff_cost"] - out["today_import_cost"]
            )
        else:
            out["dynamic_tariff_savings"] = None
            out["today_dynamic_tariff_savings"] = None

        # Daily ratios.
        t_import = today.get("grid_import_energy", 0.0)
        t_load = today.get("load_energy", 0.0)
        t_pv = today.get("pv_energy", 0.0)
        t_export = today.get("grid_export_energy", 0.0)
        out["self_sufficiency"] = (
            _clamp_pct(100.0 * (1.0 - t_import / t_load)) if t_load > 0 else None
        )
        out["self_consumption_rate"] = (
            _clamp_pct(100.0 * (t_pv - t_export) / t_pv) if t_pv > 0 else None
        )
        out["avg_import_price_paid"] = (
            today.get("import_cost", 0.0) / t_import if t_import > 0 else None
        )

        t_solar = today.get("solar_thermal_energy", 0.0)
        t_dhw_heat_gas = today.get("gas_energy_dhw", 0.0) * cfg.boiler_efficiency
        dhw_heat_total = t_solar + t_dhw_heat_gas
        out["solar_share_of_dhw"] = (
            _clamp_pct(100.0 * t_solar / dhw_heat_total) if dhw_heat_total > 0 else None
        )

        # Carbon intensity of what the house consumes right now.
        intensity = values.get("grid_co2_intensity")
        if intensity is not None and load_power is not None and load_power > 0:
            grid_share = min(1.0, (import_power or 0.0) / load_power)
            out["home_co2_intensity"] = intensity * grid_share
        else:
            out["home_co2_intensity"] = None

        # Heating degree days.
        if self.state.temp_seconds > 0:
            mean_temp = self.state.temp_weight_sum / self.state.temp_seconds
            hdd = max(0.0, cfg.hdd_base_temp - mean_temp)
            out["heating_degree_days"] = hdd
            out["gas_per_hdd"] = today.get("gas_energy_heating", 0.0) / hdd if hdd > 0.5 else None
        else:
            out["heating_degree_days"] = None
            out["gas_per_hdd"] = None

        out["flow_state"] = _flow_state(import_power, export_power, charge_power, discharge_power)
        return out


def _clamp_pct(value: float) -> float:
    return max(0.0, min(100.0, value))


def _flow_state(
    import_power: float | None,
    export_power: float | None,
    charge_power: float | None,
    discharge_power: float | None,
    threshold: float = 50.0,
) -> str | None:
    """Summarise the current energy flow for the flow card."""
    if import_power is None and export_power is None:
        return None
    if (export_power or 0.0) > threshold:
        return "exporting"
    if (import_power or 0.0) > threshold:
        return "importing"
    if (charge_power or 0.0) > threshold:
        return "charging"
    if (discharge_power or 0.0) > threshold:
        return "discharging"
    return "self_powered"
