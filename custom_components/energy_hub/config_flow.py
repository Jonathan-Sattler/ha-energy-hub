"""Config and options flow for Energy Hub.

Users map their own entities to named slots in four steps. All values live
in the entry's options so the options flow can edit them later.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
import voluptuous as vol

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_CHARGE_ENERGY,
    CONF_BATTERY_DISCHARGE_ENERGY,
    CONF_BATTERY_POWER,
    CONF_BATTERY_POWER_SIGN,
    CONF_BATTERY_SOC,
    CONF_BOILER_EFFICIENCY,
    CONF_BOILER_ELECTRICITY_ENERGY,
    CONF_BURNER_ACTIVE,
    CONF_BURNER_MODULATION,
    CONF_CHEAP_NOW,
    CONF_CHEAP_PERCENTILE,
    CONF_DHW_STORAGE_TEMP,
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
    CONF_GRID_EXPORT_ENERGY,
    CONF_GRID_EXPORT_POWER,
    CONF_GRID_FOSSIL_SHARE,
    CONF_GRID_IMPORT_ENERGY,
    CONF_GRID_IMPORT_POWER,
    CONF_GRID_POWER,
    CONF_GRID_POWER_SIGN,
    CONF_HDD_BASE_TEMP,
    CONF_IMPORT_COST_OVERRIDE,
    CONF_IMPORT_PRICE,
    CONF_LOAD_ENERGY,
    CONF_LOAD_POWER,
    CONF_NAME,
    CONF_OUTSIDE_TEMP,
    CONF_PV_ENERGY,
    CONF_PV_POWER,
    CONF_SOLAR_COLLECTOR_TEMP,
    CONF_SOLAR_PUMP,
    CONF_SOLAR_STORAGE_TEMP,
    CONF_SOLAR_THERMAL_ENERGY,
    DEFAULT_BOILER_EFFICIENCY,
    DEFAULT_CHEAP_PERCENTILE,
    DEFAULT_FORECAST_ATTRIBUTE,
    DEFAULT_GAS_CALORIFIC_VALUE,
    DEFAULT_GAS_CO2_FACTOR,
    DEFAULT_GAS_CORRECTION_FACTOR,
    DEFAULT_HDD_BASE_TEMP,
    DEFAULT_NAME,
    DOMAIN,
    SIGN_NEGATIVE_IS_EXPORT,
    SIGN_POSITIVE_IS_CHARGING,
    SIGN_POSITIVE_IS_DISCHARGING,
    SIGN_POSITIVE_IS_EXPORT,
)

STEP_ELECTRICITY = "electricity"
STEP_PRICES = "prices"
STEP_GAS_THERMAL = "gas_thermal"
STEP_CARBON = "carbon"
STEP_ORDER = (STEP_ELECTRICITY, STEP_PRICES, STEP_GAS_THERMAL, STEP_CARBON)


def _sensor(
    device_class: SensorDeviceClass | list[SensorDeviceClass] | None = None,
) -> EntitySelector:
    if device_class is None:
        return EntitySelector(EntitySelectorConfig(domain=SENSOR_DOMAIN))
    return EntitySelector(EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class=device_class))


def _binary() -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN))


def _number(
    minimum: float, maximum: float, step: float | str, unit: str | None = None
) -> NumberSelector:
    config = NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=NumberSelectorMode.BOX)
    if unit:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


def _select(options: list[str], translation_key: str) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=options, mode=SelectSelectorMode.DROPDOWN, translation_key=translation_key
        )
    )


POWER = _sensor(SensorDeviceClass.POWER)
ENERGY = _sensor(SensorDeviceClass.ENERGY)
GAS = _sensor([SensorDeviceClass.GAS, SensorDeviceClass.ENERGY])
TEMPERATURE = _sensor(SensorDeviceClass.TEMPERATURE)
MONETARY = _sensor(SensorDeviceClass.MONETARY)
ANY_SENSOR = _sensor()

ELECTRICITY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GRID_IMPORT_ENERGY): ENERGY,
        vol.Required(CONF_GRID_EXPORT_ENERGY): ENERGY,
        vol.Optional(CONF_GRID_POWER): POWER,
        vol.Optional(CONF_GRID_POWER_SIGN, default=SIGN_NEGATIVE_IS_EXPORT): _select(
            [SIGN_NEGATIVE_IS_EXPORT, SIGN_POSITIVE_IS_EXPORT], "grid_power_sign"
        ),
        vol.Optional(CONF_GRID_IMPORT_POWER): POWER,
        vol.Optional(CONF_GRID_EXPORT_POWER): POWER,
        vol.Optional(CONF_PV_POWER): POWER,
        vol.Optional(CONF_PV_ENERGY): ENERGY,
        vol.Optional(CONF_BATTERY_POWER): POWER,
        vol.Optional(CONF_BATTERY_POWER_SIGN, default=SIGN_POSITIVE_IS_CHARGING): _select(
            [SIGN_POSITIVE_IS_CHARGING, SIGN_POSITIVE_IS_DISCHARGING], "battery_power_sign"
        ),
        vol.Optional(CONF_BATTERY_SOC): _sensor(SensorDeviceClass.BATTERY),
        vol.Optional(CONF_BATTERY_CHARGE_ENERGY): ENERGY,
        vol.Optional(CONF_BATTERY_DISCHARGE_ENERGY): ENERGY,
        vol.Optional(CONF_BATTERY_CAPACITY): _number(0, 1000, 0.1, "kWh"),
        vol.Optional(CONF_LOAD_POWER): POWER,
        vol.Optional(CONF_LOAD_ENERGY): ENERGY,
    }
)

PRICES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_IMPORT_PRICE): ANY_SENSOR,
        vol.Optional(CONF_FORECAST_ATTRIBUTE, default=DEFAULT_FORECAST_ATTRIBUTE): TextSelector(),
        vol.Optional(CONF_EXPORT_PRICE): ANY_SENSOR,
        vol.Optional(CONF_EXPORT_PRICE_FIXED): _number(0, 10, "any"),
        vol.Optional(CONF_IMPORT_COST_OVERRIDE): MONETARY,
        vol.Optional(CONF_EXPORT_REVENUE_OVERRIDE): MONETARY,
        vol.Optional(CONF_FLAT_REFERENCE_PRICE): _number(0, 10, "any"),
        vol.Optional(CONF_CHEAP_NOW): _binary(),
        vol.Optional(CONF_CHEAP_PERCENTILE, default=DEFAULT_CHEAP_PERCENTILE): _number(
            1, 99, 1, "%"
        ),
    }
)

GAS_THERMAL_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_GAS_HEATING_VOLUME): GAS,
        vol.Optional(CONF_GAS_DHW_VOLUME): GAS,
        vol.Optional(CONF_GAS_TOTAL_VOLUME): GAS,
        vol.Optional(CONF_GAS_CALORIFIC_VALUE, default=DEFAULT_GAS_CALORIFIC_VALUE): _number(
            5, 15, "any", "kWh/m³"
        ),
        vol.Optional(CONF_GAS_CORRECTION_FACTOR, default=DEFAULT_GAS_CORRECTION_FACTOR): _number(
            0.8, 1.1, "any"
        ),
        vol.Optional(CONF_GAS_PRICE): _number(0, 10, "any"),
        vol.Optional(CONF_GAS_PRICE_ENTITY): ANY_SENSOR,
        vol.Optional(CONF_BOILER_EFFICIENCY, default=DEFAULT_BOILER_EFFICIENCY): _number(
            0.5, 1.1, 0.01
        ),
        vol.Optional(CONF_SOLAR_THERMAL_ENERGY): ENERGY,
        vol.Optional(CONF_SOLAR_COLLECTOR_TEMP): TEMPERATURE,
        vol.Optional(CONF_SOLAR_STORAGE_TEMP): TEMPERATURE,
        vol.Optional(CONF_DHW_STORAGE_TEMP): TEMPERATURE,
        vol.Optional(CONF_SOLAR_PUMP): _binary(),
        vol.Optional(CONF_BOILER_ELECTRICITY_ENERGY): ENERGY,
        vol.Optional(CONF_BURNER_MODULATION): ANY_SENSOR,
        vol.Optional(CONF_BURNER_ACTIVE): _binary(),
        vol.Optional(CONF_OUTSIDE_TEMP): TEMPERATURE,
        vol.Optional(CONF_HDD_BASE_TEMP, default=DEFAULT_HDD_BASE_TEMP): _number(5, 25, 0.5, "°C"),
    }
)

CARBON_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_GRID_CO2_INTENSITY): ANY_SENSOR,
        vol.Optional(CONF_GRID_FOSSIL_SHARE): ANY_SENSOR,
        vol.Optional(CONF_GAS_CO2_FACTOR, default=DEFAULT_GAS_CO2_FACTOR): _number(
            0, 1, "any", "kg/kWh"
        ),
    }
)

STEP_SCHEMAS: dict[str, vol.Schema] = {
    STEP_ELECTRICITY: ELECTRICITY_SCHEMA,
    STEP_PRICES: PRICES_SCHEMA,
    STEP_GAS_THERMAL: GAS_THERMAL_SCHEMA,
    STEP_CARBON: CARBON_SCHEMA,
}


def _validate_electricity(data: Mapping[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    has_pair = bool(data.get(CONF_GRID_IMPORT_POWER)) and bool(data.get(CONF_GRID_EXPORT_POWER))
    one_of_pair = bool(data.get(CONF_GRID_IMPORT_POWER)) != bool(data.get(CONF_GRID_EXPORT_POWER))
    if one_of_pair and not data.get(CONF_GRID_POWER):
        errors["base"] = "grid_power_pair"
    if data.get(CONF_GRID_POWER) and has_pair:
        errors["base"] = "grid_power_both"
    return errors


def _clean(data: Mapping[str, Any]) -> dict[str, Any]:
    """Drop empty strings so cleared selectors do not linger as slots."""
    return {key: value for key, value in data.items() if value not in ("", None)}


class EnergyHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Four-step mapping wizard."""

    VERSION = 1

    def __init__(self) -> None:
        self._collected: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EnergyHubOptionsFlow:
        """Return the options flow."""
        return EnergyHubOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Name the hub."""
        if user_input is not None:
            self._collected[CONF_NAME] = user_input[CONF_NAME]
            return await self.async_step_electricity()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector()}),
        )

    async def async_step_electricity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Grid, PV, battery and load slots."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_electricity(user_input)
            if not errors:
                self._collected.update(_clean(user_input))
                return await self.async_step_prices()
        return self.async_show_form(
            step_id=STEP_ELECTRICITY,
            data_schema=self.add_suggested_values_to_schema(ELECTRICITY_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_prices(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Price and cost slots."""
        if user_input is not None:
            self._collected.update(_clean(user_input))
            return await self.async_step_gas_thermal()
        return self.async_show_form(step_id=STEP_PRICES, data_schema=PRICES_SCHEMA)

    async def async_step_gas_thermal(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Gas, boiler and solar thermal slots."""
        if user_input is not None:
            self._collected.update(_clean(user_input))
            return await self.async_step_carbon()
        return self.async_show_form(step_id=STEP_GAS_THERMAL, data_schema=GAS_THERMAL_SCHEMA)

    async def async_step_carbon(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Carbon slots, then create the entry."""
        if user_input is not None:
            self._collected.update(_clean(user_input))
            name = self._collected.pop(CONF_NAME, DEFAULT_NAME)
            return self.async_create_entry(title=name, data={}, options=self._collected)
        return self.async_show_form(step_id=STEP_CARBON, data_schema=CARBON_SCHEMA)


class EnergyHubOptionsFlow(OptionsFlow):
    """Edit the mapping; the entry reloads on save."""

    def __init__(self) -> None:
        self._collected: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Start with the electricity step."""
        self._collected = dict(self.config_entry.options)
        return await self.async_step_electricity()

    def _form(
        self, step: str, user_input: dict[str, Any] | None, errors: dict[str, str] | None = None
    ):
        schema = STEP_SCHEMAS[step]
        keys = {str(key) for key in schema.schema}
        suggested = {k: v for k, v in self._collected.items() if k in keys}
        if user_input:
            suggested.update(user_input)
        return self.async_show_form(
            step_id=step,
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors or {},
        )

    def _apply(self, step: str, user_input: dict[str, Any]) -> None:
        keys = {str(key) for key in STEP_SCHEMAS[step].schema}
        for key in keys:
            self._collected.pop(key, None)
        self._collected.update(_clean(user_input))

    async def async_step_electricity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Electricity slots."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_electricity(user_input)
            if not errors:
                self._apply(STEP_ELECTRICITY, user_input)
                return await self.async_step_prices()
        return self._form(STEP_ELECTRICITY, user_input, errors)

    async def async_step_prices(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Price slots."""
        if user_input is not None:
            self._apply(STEP_PRICES, user_input)
            return await self.async_step_gas_thermal()
        return self._form(STEP_PRICES, user_input)

    async def async_step_gas_thermal(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Gas and thermal slots."""
        if user_input is not None:
            self._apply(STEP_GAS_THERMAL, user_input)
            return await self.async_step_carbon()
        return self._form(STEP_GAS_THERMAL, user_input)

    async def async_step_carbon(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Carbon slots, then save."""
        if user_input is not None:
            self._apply(STEP_CARBON, user_input)
            return self.async_create_entry(title="", data=self._collected)
        return self._form(STEP_CARBON, user_input)
