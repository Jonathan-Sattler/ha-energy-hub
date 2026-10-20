"""Constants for Energy Hub."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "energy_hub"
STORAGE_VERSION: Final = 1
SAVE_DELAY_SECONDS: Final = 30

CONF_NAME: Final = "name"
DEFAULT_NAME: Final = "Energy Hub"

# ---- Electricity slots -------------------------------------------------------
CONF_GRID_POWER: Final = "grid_power"
CONF_GRID_POWER_SIGN: Final = "grid_power_sign"
CONF_GRID_IMPORT_POWER: Final = "grid_import_power"
CONF_GRID_EXPORT_POWER: Final = "grid_export_power"
CONF_GRID_IMPORT_ENERGY: Final = "grid_import_energy"
CONF_GRID_EXPORT_ENERGY: Final = "grid_export_energy"
CONF_PV_POWER: Final = "pv_power"
CONF_PV_ENERGY: Final = "pv_energy"
CONF_BATTERY_POWER: Final = "battery_power"
CONF_BATTERY_POWER_SIGN: Final = "battery_power_sign"
CONF_BATTERY_SOC: Final = "battery_soc"
CONF_BATTERY_CHARGE_ENERGY: Final = "battery_charge_energy"
CONF_BATTERY_DISCHARGE_ENERGY: Final = "battery_discharge_energy"
CONF_BATTERY_CAPACITY: Final = "battery_capacity_kwh"
CONF_LOAD_POWER: Final = "load_power"
CONF_LOAD_ENERGY: Final = "load_energy"

SIGN_NEGATIVE_IS_EXPORT: Final = "negative_is_export"
SIGN_POSITIVE_IS_EXPORT: Final = "positive_is_export"
SIGN_POSITIVE_IS_CHARGING: Final = "positive_is_charging"
SIGN_POSITIVE_IS_DISCHARGING: Final = "positive_is_discharging"

# ---- Price slots ---------------------------------------------------------------
CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_EXPORT_PRICE_FIXED: Final = "export_price_fixed"
CONF_IMPORT_COST_OVERRIDE: Final = "import_cost_override"
CONF_EXPORT_REVENUE_OVERRIDE: Final = "export_revenue_override"
CONF_FLAT_REFERENCE_PRICE: Final = "flat_reference_price"
CONF_CHEAP_NOW: Final = "cheap_now"
CONF_CHEAP_PERCENTILE: Final = "cheap_threshold_percentile"
CONF_FORECAST_ATTRIBUTE: Final = "forecast_attribute"
DEFAULT_CHEAP_PERCENTILE: Final = 25
DEFAULT_FORECAST_ATTRIBUTE: Final = "forecast"

# ---- Gas and thermal slots ----------------------------------------------------
CONF_GAS_HEATING_VOLUME: Final = "gas_heating_volume"
CONF_GAS_DHW_VOLUME: Final = "gas_dhw_volume"
CONF_GAS_TOTAL_VOLUME: Final = "gas_total_volume"
CONF_GAS_CALORIFIC_VALUE: Final = "gas_calorific_value"
CONF_GAS_CORRECTION_FACTOR: Final = "gas_correction_factor"
CONF_GAS_PRICE: Final = "gas_price"
CONF_GAS_PRICE_ENTITY: Final = "gas_price_entity"
CONF_BOILER_EFFICIENCY: Final = "boiler_efficiency"
CONF_SOLAR_THERMAL_ENERGY: Final = "solar_thermal_energy"
CONF_SOLAR_COLLECTOR_TEMP: Final = "solar_collector_temp"
CONF_SOLAR_STORAGE_TEMP: Final = "solar_storage_temp"
CONF_DHW_STORAGE_TEMP: Final = "dhw_storage_temp"
CONF_SOLAR_PUMP: Final = "solar_pump"
CONF_BOILER_ELECTRICITY_ENERGY: Final = "boiler_electricity_energy"
CONF_BURNER_MODULATION: Final = "burner_modulation"
CONF_BURNER_ACTIVE: Final = "burner_active"
CONF_OUTSIDE_TEMP: Final = "outside_temp"
CONF_HDD_BASE_TEMP: Final = "hdd_base_temp"

DEFAULT_GAS_CALORIFIC_VALUE: Final = 11.0
DEFAULT_GAS_CORRECTION_FACTOR: Final = 0.95
DEFAULT_BOILER_EFFICIENCY: Final = 0.95
DEFAULT_HDD_BASE_TEMP: Final = 15.0

# ---- Carbon slots --------------------------------------------------------------
CONF_GRID_CO2_INTENSITY: Final = "grid_co2_intensity"
CONF_GRID_FOSSIL_SHARE: Final = "grid_fossil_share"
CONF_GAS_CO2_FACTOR: Final = "gas_co2_factor"
DEFAULT_GAS_CO2_FACTOR: Final = 0.201

# Slots whose value is an entity id, grouped by the engine input they feed.
ENTITY_SLOTS: Final[tuple[str, ...]] = (
    CONF_GRID_POWER,
    CONF_GRID_IMPORT_POWER,
    CONF_GRID_EXPORT_POWER,
    CONF_GRID_IMPORT_ENERGY,
    CONF_GRID_EXPORT_ENERGY,
    CONF_PV_POWER,
    CONF_PV_ENERGY,
    CONF_BATTERY_POWER,
    CONF_BATTERY_SOC,
    CONF_BATTERY_CHARGE_ENERGY,
    CONF_BATTERY_DISCHARGE_ENERGY,
    CONF_LOAD_POWER,
    CONF_LOAD_ENERGY,
    CONF_IMPORT_PRICE,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_COST_OVERRIDE,
    CONF_EXPORT_REVENUE_OVERRIDE,
    CONF_CHEAP_NOW,
    CONF_GAS_HEATING_VOLUME,
    CONF_GAS_DHW_VOLUME,
    CONF_GAS_TOTAL_VOLUME,
    CONF_GAS_PRICE_ENTITY,
    CONF_SOLAR_THERMAL_ENERGY,
    CONF_SOLAR_COLLECTOR_TEMP,
    CONF_SOLAR_STORAGE_TEMP,
    CONF_DHW_STORAGE_TEMP,
    CONF_SOLAR_PUMP,
    CONF_BOILER_ELECTRICITY_ENERGY,
    CONF_BURNER_MODULATION,
    CONF_BURNER_ACTIVE,
    CONF_OUTSIDE_TEMP,
    CONF_GRID_CO2_INTENSITY,
    CONF_GRID_FOSSIL_SHARE,
)

# Unit families the engine expects per slot. Used for conversion.
UNIT_POWER: Final = "power"  # -> W
UNIT_ENERGY: Final = "energy"  # -> kWh
UNIT_GAS: Final = "gas"  # -> m³ or kWh, flagged
UNIT_TEMPERATURE: Final = "temperature"  # -> °C
UNIT_RATE: Final = "rate"  # currency per kWh, passthrough
UNIT_INTENSITY: Final = "intensity"  # gCO2eq/kWh
UNIT_PERCENT: Final = "percent"
UNIT_MONETARY: Final = "monetary"
UNIT_NONE: Final = "none"

SLOT_UNIT_FAMILY: Final[dict[str, str]] = {
    CONF_GRID_POWER: UNIT_POWER,
    CONF_GRID_IMPORT_POWER: UNIT_POWER,
    CONF_GRID_EXPORT_POWER: UNIT_POWER,
    CONF_PV_POWER: UNIT_POWER,
    CONF_BATTERY_POWER: UNIT_POWER,
    CONF_LOAD_POWER: UNIT_POWER,
    CONF_GRID_IMPORT_ENERGY: UNIT_ENERGY,
    CONF_GRID_EXPORT_ENERGY: UNIT_ENERGY,
    CONF_PV_ENERGY: UNIT_ENERGY,
    CONF_BATTERY_CHARGE_ENERGY: UNIT_ENERGY,
    CONF_BATTERY_DISCHARGE_ENERGY: UNIT_ENERGY,
    CONF_LOAD_ENERGY: UNIT_ENERGY,
    CONF_SOLAR_THERMAL_ENERGY: UNIT_ENERGY,
    CONF_BOILER_ELECTRICITY_ENERGY: UNIT_ENERGY,
    CONF_GAS_HEATING_VOLUME: UNIT_GAS,
    CONF_GAS_DHW_VOLUME: UNIT_GAS,
    CONF_GAS_TOTAL_VOLUME: UNIT_GAS,
    CONF_BATTERY_SOC: UNIT_PERCENT,
    CONF_IMPORT_PRICE: UNIT_RATE,
    CONF_EXPORT_PRICE: UNIT_RATE,
    CONF_GAS_PRICE_ENTITY: UNIT_RATE,
    CONF_IMPORT_COST_OVERRIDE: UNIT_MONETARY,
    CONF_EXPORT_REVENUE_OVERRIDE: UNIT_MONETARY,
    CONF_SOLAR_COLLECTOR_TEMP: UNIT_TEMPERATURE,
    CONF_SOLAR_STORAGE_TEMP: UNIT_TEMPERATURE,
    CONF_DHW_STORAGE_TEMP: UNIT_TEMPERATURE,
    CONF_OUTSIDE_TEMP: UNIT_TEMPERATURE,
    CONF_GRID_CO2_INTENSITY: UNIT_INTENSITY,
    CONF_GRID_FOSSIL_SHARE: UNIT_PERCENT,
    CONF_BURNER_MODULATION: UNIT_PERCENT,
    CONF_CHEAP_NOW: UNIT_NONE,
    CONF_SOLAR_PUMP: UNIT_NONE,
    CONF_BURNER_ACTIVE: UNIT_NONE,
}

# Engine input name per slot (most are identical; the gas price entity maps to
# the engine's ``gas_price`` rate).
SLOT_TO_ENGINE_INPUT: Final[dict[str, str]] = {
    CONF_GAS_PRICE_ENTITY: "gas_price",
}

ATTR_FORECAST: Final = "forecast"
ATTR_MISSING_FEATURES: Final = "inactive_features"
