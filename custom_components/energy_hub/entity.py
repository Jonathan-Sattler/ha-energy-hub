"""Base entity for Energy Hub."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import EnergyHubCoordinator


class EnergyHubEntity(CoordinatorEntity[EnergyHubCoordinator]):
    """Common device info and naming.

    Entity ids are suggested as ``<platform>.<hub slug>_<key>`` so they are
    predictable and language independent; users may still rename them.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: EnergyHubCoordinator, platform: str, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self.entity_id = f"{platform}.{slugify(coordinator.entry.title)}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Energy Hub",
            model="Calculated energy data",
            entry_type=DeviceEntryType.SERVICE,
        )
