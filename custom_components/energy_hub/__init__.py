"""Energy Hub: vendor-agnostic energy, cost and carbon calculations."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import EnergyHubCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type EnergyHubConfigEntry = ConfigEntry[EnergyHubCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EnergyHubConfigEntry) -> bool:
    """Set up Energy Hub from a config entry."""
    coordinator = EnergyHubCoordinator(hass, entry)
    await coordinator.async_load()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_on_unload(coordinator.async_stop)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EnergyHubConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_save()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: EnergyHubConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
