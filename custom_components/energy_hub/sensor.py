"""Sensors for Energy Hub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    DOMAIN as PLATFORM,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfPower,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import EnergyHubConfigEntry
from .const import ATTR_FORECAST, ATTR_MISSING_FEATURES, DOMAIN
from .coordinator import EnergyHubCoordinator
from .entity import EnergyHubEntity

CO2_INTENSITY_UNIT = "gCO2eq/kWh"
ALL_FEATURES: tuple[str, ...] = (
    "grid_power",
    "pv",
    "pv_power",
    "battery_power",
    "import_cost",
    "export_revenue",
    "flat_tariff",
    "carbon_grid",
    "carbon_pv",
    "home_intensity",
    "gas",
    "gas_heating",
    "gas_dhw",
    "gas_cost",
    "solar_thermal",
    "solar_thermal_cost",
    "solar_share_dhw",
    "hdd",
    "gas_per_hdd",
    "price_forecast",
    "cheap",
)


@dataclass(frozen=True, kw_only=True)
class EnergyHubSensorDescription(SensorEntityDescription):
    """Describes a derived sensor."""

    feature: str
    today: bool = False  # value resets at local midnight
    currency: bool = False  # unit is the HA currency
    currency_per_kwh: bool = False


def _power(key: str, feature: str) -> EnergyHubSensorDescription:
    return EnergyHubSensorDescription(
        key=key,
        feature=feature,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    )


def _energy(key: str, feature: str, *, today: bool = False) -> EnergyHubSensorDescription:
    return EnergyHubSensorDescription(
        key=key,
        feature=feature,
        today=today,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL if today else SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    )


def _money(key: str, feature: str, *, today: bool = False) -> EnergyHubSensorDescription:
    return EnergyHubSensorDescription(
        key=key,
        feature=feature,
        today=today,
        currency=True,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
    )


def _co2(key: str, feature: str, *, today: bool = False) -> EnergyHubSensorDescription:
    return EnergyHubSensorDescription(
        key=key,
        feature=feature,
        today=today,
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        state_class=SensorStateClass.TOTAL if today else SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        icon="mdi:molecule-co2",
    )


def _pct(key: str, feature: str, icon: str) -> EnergyHubSensorDescription:
    return EnergyHubSensorDescription(
        key=key,
        feature=feature,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon=icon,
    )


SENSORS: tuple[EnergyHubSensorDescription, ...] = (
    # Live powers
    _power("grid_import_power", "grid_power"),
    _power("grid_export_power", "grid_power"),
    _power("battery_charge_power", "battery_power"),
    _power("battery_discharge_power", "battery_power"),
    _power("load_power", "grid_power"),
    # Energy counters (lifetime)
    _energy("load_energy", "load"),
    _energy("pv_self_consumed_energy", "pv"),
    _energy("gas_energy_heating", "gas_heating"),
    _energy("gas_energy_dhw", "gas_dhw"),
    _energy("gas_energy_total", "gas"),
    # Energy today
    _energy("today_grid_import_energy", "grid", today=True),
    _energy("today_grid_export_energy", "grid", today=True),
    _energy("today_pv_energy", "pv", today=True),
    _energy("today_load_energy", "load", today=True),
    _energy("today_gas_energy_heating", "gas_heating", today=True),
    _energy("today_gas_energy_dhw", "gas_dhw", today=True),
    _energy("today_gas_energy_total", "gas", today=True),
    _energy("today_solar_thermal_energy", "solar_thermal", today=True),
    # Money
    _money("import_cost", "import_cost"),
    _money("export_revenue", "export_revenue"),
    _money("net_electricity_cost", "import_cost"),
    _money("flat_tariff_cost", "flat_tariff"),
    _money("dynamic_tariff_savings", "flat_tariff"),
    _money("gas_cost", "gas_cost"),
    _money("total_energy_cost", "import_cost"),
    _money("solar_thermal_gas_avoided_cost", "solar_thermal_cost"),
    _money("today_import_cost", "import_cost", today=True),
    _money("today_export_revenue", "export_revenue", today=True),
    _money("today_net_electricity_cost", "import_cost", today=True),
    _money("today_gas_cost", "gas_cost", today=True),
    _money("today_total_energy_cost", "import_cost", today=True),
    _money("today_dynamic_tariff_savings", "flat_tariff", today=True),
    # Carbon
    _co2("grid_import_co2", "carbon_grid"),
    _co2("avoided_co2_pv", "carbon_pv"),
    _co2("gas_co2", "gas"),
    _co2("solar_thermal_avoided_co2", "solar_thermal"),
    _co2("total_co2", "carbon_grid"),
    _co2("today_grid_import_co2", "carbon_grid", today=True),
    _co2("today_avoided_co2_pv", "carbon_pv", today=True),
    _co2("today_gas_co2", "gas", today=True),
    _co2("today_solar_thermal_avoided_co2", "solar_thermal", today=True),
    _co2("today_total_co2", "carbon_grid", today=True),
    # Ratios and rates
    _pct("self_sufficiency", "self_sufficiency", "mdi:home-lightning-bolt"),
    _pct("self_consumption_rate", "pv", "mdi:solar-power-variant"),
    _pct("solar_share_of_dhw", "solar_share_dhw", "mdi:water-boiler"),
    EnergyHubSensorDescription(
        key="avg_import_price_paid",
        feature="import_cost",
        currency_per_kwh=True,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        icon="mdi:cash-multiple",
    ),
    EnergyHubSensorDescription(
        key="home_co2_intensity",
        feature="home_intensity",
        native_unit_of_measurement=CO2_INTENSITY_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:molecule-co2",
    ),
    EnergyHubSensorDescription(
        key="heating_degree_days",
        feature="hdd",
        native_unit_of_measurement="K",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-low",
    ),
    EnergyHubSensorDescription(
        key="gas_per_hdd",
        feature="gas_per_hdd",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:fire",
    ),
    EnergyHubSensorDescription(
        key="solar_thermal_gas_avoided_volume",
        feature="solar_thermal",
        device_class=SensorDeviceClass.GAS,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnergyHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for the active features and prune stale ones."""
    coordinator = entry.runtime_data
    features = coordinator.features
    entities: list[SensorEntity] = [
        EnergyHubSensor(coordinator, description)
        for description in SENSORS
        if description.feature in features
    ]
    entities.append(FlowStateSensor(coordinator))
    entities.append(InactiveFeaturesSensor(coordinator))
    if "price_forecast" in features:
        entities.append(PriceForecastSensor(coordinator))

    wanted = {entity.unique_id for entity in entities}
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.domain == "sensor" and reg_entry.unique_id not in wanted:
            registry.async_remove(reg_entry.entity_id)

    async_add_entities(entities)


class EnergyHubSensor(EnergyHubEntity, SensorEntity):
    """A derived value from the engine."""

    entity_description: EnergyHubSensorDescription

    def __init__(
        self, coordinator: EnergyHubCoordinator, description: EnergyHubSensorDescription
    ) -> None:
        super().__init__(coordinator, PLATFORM, description.key)
        self.entity_description = description
        currency = coordinator.hass.config.currency
        if description.currency:
            self._attr_native_unit_of_measurement = currency
        elif description.currency_per_kwh:
            self._attr_native_unit_of_measurement = f"{currency}/kWh"

    @property
    def native_value(self) -> float | None:
        """Return the engine value."""
        value = self.coordinator.data.get(self._key)
        return None if value is None else float(value)

    @property
    def last_reset(self) -> datetime | None:
        """Midnight for today-counters."""
        if not self.entity_description.today:
            return None
        return dt_util.start_of_local_day()


class FlowStateSensor(EnergyHubEntity, SensorEntity):
    """Summary of the current energy flow."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["importing", "exporting", "charging", "discharging", "self_powered"]
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, coordinator: EnergyHubCoordinator) -> None:
        super().__init__(coordinator, PLATFORM, "flow_state")

    @property
    def native_value(self) -> str | None:
        """Return the flow state."""
        return self.coordinator.data.get("flow_state")


class PriceForecastSensor(EnergyHubEntity, SensorEntity):
    """Current import price with a normalised forecast attribute."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-line"
    _attr_suggested_display_precision = 4

    def __init__(self, coordinator: EnergyHubCoordinator) -> None:
        super().__init__(coordinator, PLATFORM, "price_forecast")
        self._attr_native_unit_of_measurement = f"{coordinator.hass.config.currency}/kWh"

    @property
    def native_value(self) -> float | None:
        """Current price as reported by the mapped entity."""
        return self.coordinator.raw.get("import_price")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Normalised forecast and day statistics."""
        return {
            ATTR_FORECAST: [slot.as_dict() for slot in self.coordinator.forecast],
            **self.coordinator.price_stats,
        }


class InactiveFeaturesSensor(EnergyHubEntity, SensorEntity):
    """Diagnostic: which optional features are not active and why."""

    _attr_icon = "mdi:puzzle-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EnergyHubCoordinator) -> None:
        super().__init__(coordinator, PLATFORM, "inactive_features")

    @property
    def native_value(self) -> int:
        """Number of inactive features."""
        return len(self._inactive())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """List the inactive features."""
        return {ATTR_MISSING_FEATURES: self._inactive(), "integration": DOMAIN}

    def _inactive(self) -> list[str]:
        active = self.coordinator.features
        return [feature for feature in ALL_FEATURES if feature not in active]
