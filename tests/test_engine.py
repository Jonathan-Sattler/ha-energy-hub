"""Unit tests for the pure calculation engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.energy_hub.engine import (
    EnergyEngine,
    EngineConfig,
    EngineState,
    counter_delta,
)

T0 = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)


def test_counter_delta_handles_reset() -> None:
    assert counter_delta(None, 5.0) == 0.0
    assert counter_delta(5.0, None) == 0.0
    assert counter_delta(5.0, 7.5) == 2.5
    # Daily reset: what is there now was consumed since the reset.
    assert counter_delta(3.5, 0.1) == pytest.approx(0.1)


def test_first_update_sets_baseline_without_accumulating() -> None:
    engine = EnergyEngine(EngineConfig())
    out = engine.update({"grid_import_energy": 100.0, "grid_export_energy": 50.0}, T0)
    assert out["grid_import_energy"] == 0.0
    assert out["today_grid_import_energy"] == 0.0


def test_cost_and_carbon_accumulate_with_rates() -> None:
    engine = EnergyEngine(EngineConfig(flat_reference_price=0.40))
    base = {
        "grid_import_energy": 100.0,
        "grid_export_energy": 50.0,
        "pv_energy": 200.0,
        "import_price": 0.30,
        "export_price": 0.08,
        "grid_co2_intensity": 300.0,
    }
    engine.update(base, T0)
    out = engine.update(
        {
            **base,
            "grid_import_energy": 102.0,
            "grid_export_energy": 51.0,
            "pv_energy": 204.0,
        },
        T0 + timedelta(minutes=15),
    )
    assert out["import_cost"] == pytest.approx(2.0 * 0.30)
    assert out["export_revenue"] == pytest.approx(1.0 * 0.08)
    assert out["net_electricity_cost"] == pytest.approx(0.60 - 0.08)
    assert out["flat_tariff_cost"] == pytest.approx(2.0 * 0.40)
    assert out["dynamic_tariff_savings"] == pytest.approx(0.80 - 0.60)
    assert out["grid_import_co2"] == pytest.approx(2.0 * 300.0 / 1000.0)
    assert out["avoided_co2_pv"] == pytest.approx(4.0 * 300.0 / 1000.0)
    assert out["pv_self_consumed_energy"] == pytest.approx(3.0)
    assert out["self_consumption_rate"] == pytest.approx(75.0)


def test_load_is_computed_when_no_slot() -> None:
    engine = EnergyEngine(EngineConfig())
    base = {
        "grid_import_energy": 0.0,
        "grid_export_energy": 0.0,
        "pv_energy": 0.0,
        "battery_charge_energy": 0.0,
        "battery_discharge_energy": 0.0,
    }
    engine.update(base, T0)
    out = engine.update(
        {
            "grid_import_energy": 1.0,
            "grid_export_energy": 2.0,
            "pv_energy": 5.0,
            "battery_charge_energy": 1.5,
            "battery_discharge_energy": 0.5,
        },
        T0 + timedelta(hours=1),
    )
    # pv + import - export - charge + discharge
    assert out["load_energy"] == pytest.approx(5.0 + 1.0 - 2.0 - 1.5 + 0.5)
    assert out["self_sufficiency"] == pytest.approx(100.0 * (1 - 1.0 / 3.0))


def test_gas_conversion_cost_and_solar_thermal() -> None:
    cfg = EngineConfig(
        gas_calorific_value=10.0,
        gas_correction_factor=0.9,
        gas_price=0.10,
        boiler_efficiency=0.9,
        gas_co2_factor=0.2,
    )
    engine = EnergyEngine(cfg)
    base = {
        "grid_import_energy": 0.0,
        "grid_export_energy": 0.0,
        "gas_heating_volume": 1.0,
        "gas_dhw_volume": 0.0,
        "solar_thermal_energy": 0.0,
    }
    engine.update(base, T0)
    out = engine.update(
        {**base, "gas_heating_volume": 2.0, "gas_dhw_volume": 0.5, "solar_thermal_energy": 1.8},
        T0 + timedelta(hours=2),
    )
    assert out["gas_energy_heating"] == pytest.approx(1.0 * 9.0)
    assert out["gas_energy_dhw"] == pytest.approx(0.5 * 9.0)
    assert out["gas_energy_total"] == pytest.approx(13.5)
    assert out["gas_cost"] == pytest.approx(1.35)
    assert out["gas_co2"] == pytest.approx(13.5 * 0.2)
    # Solar thermal 1.8 kWh heat = 2.0 kWh gas at 90 percent efficiency.
    assert out["solar_thermal_avoided_co2"] == pytest.approx(2.0 * 0.2)
    assert out["solar_thermal_gas_avoided_volume"] == pytest.approx(2.0 / 9.0)
    assert out["solar_thermal_gas_avoided_cost"] == pytest.approx(0.20)
    # DHW heat from gas: 4.5 kWh gas * 0.9 = 4.05 kWh heat; solar 1.8.
    assert out["solar_share_of_dhw"] == pytest.approx(100.0 * 1.8 / (1.8 + 4.05))


def test_gas_slot_already_in_kwh_is_not_converted() -> None:
    cfg = EngineConfig(gas_total_in_kwh=True)
    engine = EnergyEngine(cfg)
    base = {"grid_import_energy": 0.0, "grid_export_energy": 0.0, "gas_total_volume": 10.0}
    engine.update(base, T0)
    out = engine.update({**base, "gas_total_volume": 13.0}, T0 + timedelta(hours=1))
    assert out["gas_energy_total"] == pytest.approx(3.0)


def test_daily_window_resets_at_day_change() -> None:
    engine = EnergyEngine(EngineConfig())
    base = {"grid_import_energy": 0.0, "grid_export_energy": 0.0}
    engine.update(base, T0)
    engine.update({**base, "grid_import_energy": 4.0}, T0 + timedelta(hours=1))
    next_day = T0 + timedelta(days=1)
    out = engine.update({**base, "grid_import_energy": 5.0}, next_day)
    assert out["grid_import_energy"] == pytest.approx(5.0)
    assert out["today_grid_import_energy"] == pytest.approx(1.0)


def test_vendor_daily_counter_reset_is_counted_correctly() -> None:
    engine = EnergyEngine(EngineConfig(gas_calorific_value=10.0, gas_correction_factor=1.0))
    base = {"grid_import_energy": 0.0, "grid_export_energy": 0.0}
    engine.update({**base, "gas_heating_volume": 3.4}, T0)
    engine.update({**base, "gas_heating_volume": 3.5}, T0 + timedelta(hours=1))
    # Midnight reset: vendor reports 0.1 for the new day.
    out = engine.update({**base, "gas_heating_volume": 0.1}, T0 + timedelta(hours=15))
    assert out["gas_energy_heating"] == pytest.approx((0.1 + 0.1) * 10.0)


def test_unavailable_values_do_not_break_deltas() -> None:
    engine = EnergyEngine(EngineConfig())
    base = {"grid_import_energy": 10.0, "grid_export_energy": 0.0}
    engine.update(base, T0)
    engine.update(
        {"grid_import_energy": None, "grid_export_energy": 0.0}, T0 + timedelta(minutes=1)
    )
    out = engine.update({**base, "grid_import_energy": 12.0}, T0 + timedelta(minutes=2))
    assert out["grid_import_energy"] == pytest.approx(2.0)


def test_power_split_and_flow_state() -> None:
    engine = EnergyEngine(EngineConfig())
    out = engine.derive(
        {
            "grid_power": -7500.0,
            "battery_power": 400.0,
            "pv_power": 8300.0,
            "grid_co2_intensity": 280.0,
        }
    )
    assert out["grid_import_power"] == 0.0
    assert out["grid_export_power"] == 7500.0
    assert out["battery_charge_power"] == 400.0
    assert out["battery_discharge_power"] == 0.0
    assert out["load_power"] == pytest.approx(8300.0 - 7500.0 - 400.0)
    assert out["flow_state"] == "exporting"
    assert out["home_co2_intensity"] == 0.0

    out = engine.derive({"grid_power": 1200.0, "pv_power": 0.0, "grid_co2_intensity": 280.0})
    assert out["flow_state"] == "importing"
    assert out["home_co2_intensity"] == pytest.approx(280.0)


def test_override_cost_sensors_replace_internal_integration() -> None:
    engine = EnergyEngine(EngineConfig())
    base = {
        "grid_import_energy": 0.0,
        "grid_export_energy": 0.0,
        "import_price": 0.30,
        "import_cost_override": 10.0,
    }
    engine.update(base, T0)
    out = engine.update(
        {**base, "grid_import_energy": 100.0, "import_cost_override": 10.5},
        T0 + timedelta(hours=1),
    )
    assert out["import_cost"] == pytest.approx(0.5)


def test_heating_degree_days_use_time_weighted_mean() -> None:
    engine = EnergyEngine(EngineConfig(hdd_base_temp=15.0))
    base = {"grid_import_energy": 0.0, "grid_export_energy": 0.0}
    engine.update({**base, "outside_temp": 10.0}, T0)
    engine.update({**base, "outside_temp": 10.0}, T0 + timedelta(hours=1))
    out = engine.update({**base, "outside_temp": 20.0}, T0 + timedelta(hours=2))
    # Weighted: 10 °C for the first hour, 10 °C for the second (value before change).
    assert out["heating_degree_days"] == pytest.approx(5.0)


def test_state_round_trips_through_dict() -> None:
    engine = EnergyEngine(EngineConfig())
    base = {"grid_import_energy": 0.0, "grid_export_energy": 0.0, "import_price": 0.2}
    engine.update(base, T0)
    engine.update({**base, "grid_import_energy": 3.0}, T0 + timedelta(hours=1))
    restored = EnergyEngine(EngineConfig(), EngineState.from_dict(engine.state.as_dict()))
    out = restored.update({**base, "grid_import_energy": 4.0}, T0 + timedelta(hours=2))
    assert out["grid_import_energy"] == pytest.approx(4.0)
    assert out["import_cost"] == pytest.approx(0.8)
