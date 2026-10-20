"""Binary sensors for Energy Hub."""

from __future__ import annotations

from homeassistant.components.binary_sensor import DOMAIN as PLATFORM
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EnergyHubConfigEntry
from .coordinator import EnergyHubCoordinator
from .entity import EnergyHubEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnergyHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []
    if "cheap" in coordinator.features:
        entities.append(CheapElectricityBinarySensor(coordinator))
    async_add_entities(entities)


class CheapElectricityBinarySensor(EnergyHubEntity, BinarySensorEntity):
    """On while electricity is cheap, from a provider flag or the forecast."""

    _attr_icon = "mdi:cash-check"

    def __init__(self, coordinator: EnergyHubCoordinator) -> None:
        super().__init__(coordinator, PLATFORM, "cheap_electricity")

    @property
    def is_on(self) -> bool | None:
        """Return the cheap state."""
        return self.coordinator.cheap_now

    @property
    def available(self) -> bool:
        """Unavailable while no price information exists."""
        return super().available and self.coordinator.cheap_now is not None
