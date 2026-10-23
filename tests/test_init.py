"""Integration-level tests: setup, entities, live updates, persistence."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_hub.const import (
    CONF_BATTERY_POWER,
    CONF_GAS_HEATING_VOLUME,
    CONF_GAS_PRICE,
    CONF_GRID_CO2_INTENSITY,
    CONF_GRID_EXPORT_ENERGY,
    CONF_GRID_IMPORT_ENERGY,
    CONF_GRID_POWER,
    CONF_IMPORT_PRICE,
    CONF_PV_ENERGY,
    CONF_PV_POWER,
    DOMAIN,
)

OPTIONS = {
    CONF_GRID_IMPORT_ENERGY: "sensor.grid_import",
    CONF_GRID_EXPORT_ENERGY: "sensor.grid_export",
    CONF_GRID_POWER: "sensor.grid_power",
    CONF_PV_POWER: "sensor.pv_power",
    CONF_PV_ENERGY: "sensor.pv_energy",
    CONF_BATTERY_POWER: "sensor.battery_power",
    CONF_IMPORT_PRICE: "sensor.price",
    CONF_GRID_CO2_INTENSITY: "sensor.co2",
    CONF_GAS_HEATING_VOLUME: "sensor.gas_heating",
    CONF_GAS_PRICE: 0.10,
}

KWH = {"unit_of_measurement": "kWh", "device_class": "energy", "state_class": "total_increasing"}
W = {"unit_of_measurement": "W", "device_class": "power"}


def _set_sources(hass: HomeAssistant, import_kwh: float, gas_m3: float, price: float) -> None:
    hass.states.async_set("sensor.grid_import", str(import_kwh), KWH)
    hass.states.async_set("sensor.grid_export", "20.0", KWH)
    hass.states.async_set("sensor.grid_power", "-7500", W)
    hass.states.async_set("sensor.pv_power", "8300", W)
    hass.states.async_set("sensor.pv_energy", "58.0", KWH)
    hass.states.async_set("sensor.battery_power", "400", W)
    hass.states.async_set(
        "sensor.price",
        str(price),
        {
            "unit_of_measurement": "EUR/kWh",
            "forecast": [
                {
                    "start": "2026-10-20T08:00:00+00:00",
                    "end": "2026-10-20T09:00:00+00:00",
                    "price": 0.30,
                },
                {
                    "start": "2026-10-20T09:00:00+00:00",
                    "end": "2026-10-20T10:00:00+00:00",
                    "price": 0.40,
                },
            ],
        },
    )
    hass.states.async_set("sensor.co2", "300", {"unit_of_measurement": "gCO2eq/kWh"})
    hass.states.async_set(
        "sensor.gas_heating", str(gas_m3), {"unit_of_measurement": "m³", "device_class": "gas"}
    )


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Energy Hub", data={}, options=OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entities_follow_features_and_update_live(hass: HomeAssistant) -> None:
    hass.config.currency = "EUR"
    _set_sources(hass, import_kwh=100.0, gas_m3=3.0, price=0.30)
    entry = await _setup(hass)

    # Live powers from the signed grid sensor.
    assert hass.states.get("sensor.energy_hub_grid_export_power").state == "7500.0"
    assert hass.states.get("sensor.energy_hub_grid_import_power").state == "0.0"
    assert hass.states.get("sensor.energy_hub_battery_charge_power").state == "400.0"
    assert hass.states.get("sensor.energy_hub_load_power").state == "400.0"
    assert hass.states.get("sensor.energy_hub_flow_state").state == "exporting"

    # No export price configured: no revenue sensor; no flat price: no savings sensor.
    assert hass.states.get("sensor.energy_hub_export_revenue") is None
    assert hass.states.get("sensor.energy_hub_dynamic_tariff_savings") is None
    # Gas heating mapped, hot water not.
    assert hass.states.get("sensor.energy_hub_gas_energy_heating") is not None
    assert hass.states.get("sensor.energy_hub_gas_energy_dhw") is None

    cost = hass.states.get("sensor.energy_hub_import_cost")
    assert cost.state == "0.0"
    assert cost.attributes["unit_of_measurement"] == "EUR"

    # Consume 2 kWh at 0.30 and 0.5 m³ gas.
    _set_sources(hass, import_kwh=102.0, gas_m3=3.5, price=0.30)
    await hass.async_block_till_done()

    assert float(hass.states.get("sensor.energy_hub_import_cost").state) == 0.6
    assert float(hass.states.get("sensor.energy_hub_today_import_cost").state) == 0.6
    assert float(hass.states.get("sensor.energy_hub_grid_import_co2").state) == 0.6
    # 0.5 m3 * 11.0 * 0.95 default factors.
    assert float(hass.states.get("sensor.energy_hub_gas_energy_heating").state) == 5.225
    assert float(hass.states.get("sensor.energy_hub_gas_cost").state) == 0.5225

    forecast = hass.states.get("sensor.energy_hub_price_forecast")
    assert forecast.state == "0.3"
    assert len(forecast.attributes["forecast"]) == 2

    inactive = hass.states.get("sensor.energy_hub_inactive_features")
    assert "export_revenue" in inactive.attributes["inactive_features"]
    assert "gas_dhw" in inactive.attributes["inactive_features"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_state_survives_reload(hass: HomeAssistant) -> None:
    hass.config.currency = "EUR"
    _set_sources(hass, import_kwh=100.0, gas_m3=3.0, price=0.30)
    entry = await _setup(hass)
    _set_sources(hass, import_kwh=110.0, gas_m3=3.0, price=0.30)
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.energy_hub_import_cost").state) == 3.0

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.energy_hub_import_cost").state) == 3.0

    _set_sources(hass, import_kwh=111.0, gas_m3=3.0, price=0.30)
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.energy_hub_import_cost").state) == 3.3


async def test_flow_state_carries_live_values_for_the_house_card(hass: HomeAssistant) -> None:
    _set_sources(hass, import_kwh=100.0, gas_m3=3.0, price=0.30)
    await _setup(hass)

    attrs = hass.states.get("sensor.energy_hub_flow_state").attributes
    assert attrs["pv_power"] == 8300.0
    assert attrs["grid_export_power"] == 7500.0
    assert attrs["battery_charge_power"] == 400.0
    assert attrs["load_power"] == 400.0
    assert attrs["sources"]["pv_power"] == "sensor.pv_power"
    assert attrs["sources"]["import_price"] == "sensor.price"


def test_card_is_shipped() -> None:
    from custom_components.energy_hub import CARD_FILE

    text = CARD_FILE.read_text()
    assert 'customElements.define("energy-hub-house-card"' in text
    assert "__TEX__" not in text
