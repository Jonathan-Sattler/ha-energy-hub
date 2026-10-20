"""Config and options flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_hub.const import (
    CONF_GAS_PRICE,
    CONF_GRID_EXPORT_ENERGY,
    CONF_GRID_IMPORT_ENERGY,
    CONF_GRID_IMPORT_POWER,
    CONF_GRID_POWER,
    CONF_IMPORT_PRICE,
    DOMAIN,
)


async def test_full_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "My Hub"})
    assert result["step_id"] == "electricity"

    # Validation: import power without export power is rejected.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GRID_IMPORT_ENERGY: "sensor.import",
            CONF_GRID_EXPORT_ENERGY: "sensor.export",
            CONF_GRID_IMPORT_POWER: "sensor.import_w",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "grid_power_pair"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GRID_IMPORT_ENERGY: "sensor.import",
            CONF_GRID_EXPORT_ENERGY: "sensor.export",
            CONF_GRID_POWER: "sensor.grid_w",
        },
    )
    assert result["step_id"] == "prices"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_IMPORT_PRICE: "sensor.price"}
    )
    assert result["step_id"] == "gas_thermal"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_GAS_PRICE: 0.11}
    )
    assert result["step_id"] == "carbon"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Hub"
    assert result["data"] == {}
    options = result["options"]
    assert options[CONF_GRID_IMPORT_ENERGY] == "sensor.import"
    assert options[CONF_GRID_POWER] == "sensor.grid_w"
    assert options[CONF_IMPORT_PRICE] == "sensor.price"
    assert options[CONF_GAS_PRICE] == 0.11
    assert "name" not in options


async def test_options_flow_replaces_step_keys(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hub",
        data={},
        options={
            CONF_GRID_IMPORT_ENERGY: "sensor.import",
            CONF_GRID_EXPORT_ENERGY: "sensor.export",
            CONF_GRID_POWER: "sensor.grid_w",
            CONF_IMPORT_PRICE: "sensor.price",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "electricity"
    # Clear the grid power slot by omitting it.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_GRID_IMPORT_ENERGY: "sensor.import", CONF_GRID_EXPORT_ENERGY: "sensor.export"},
    )
    assert result["step_id"] == "prices"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["step_id"] == "gas_thermal"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["step_id"] == "carbon"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert CONF_GRID_POWER not in entry.options
    assert CONF_IMPORT_PRICE not in entry.options
    assert entry.options[CONF_GRID_IMPORT_ENERGY] == "sensor.import"
