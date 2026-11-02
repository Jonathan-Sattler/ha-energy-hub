"""Energy Hub: vendor-agnostic energy, cost and carbon calculations."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import EnergyHubCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

CARD_FILE = Path(__file__).parent / "frontend" / "energy-hub-house-card.js"
CARD_URL = "/energy_hub/energy-hub-house-card.js"

type EnergyHubConfigEntry = ConfigEntry[EnergyHubCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the house card and load it on every dashboard, no resource entry needed."""
    if hass.http is None or "frontend" not in hass.config.components:
        return True
    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    version = await hass.async_add_executor_job(_manifest_version)
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_FILE), cache_headers=True)]
        )
    except RuntimeError:  # already registered after a reload
        _LOGGER.debug("House card path already registered")
    url = f"{CARD_URL}?v={version}"
    # Fast path: the start page imports the card directly.
    add_extra_js_url(hass, url)

    # Robust path: also register a dashboard resource. Clients that keep an
    # older start page cached (notably the companion apps) load resources
    # from the dashboard config instead, so the card is found there too.
    async def _register(_event: Event | None = None) -> None:
        await _async_register_resource(hass, url)

    if hass.is_running:
        hass.async_create_task(_register())
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register)
    return True


async def _async_register_resource(hass: HomeAssistant, url: str) -> None:
    """Add or update the card's Lovelace resource (storage mode only)."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
    except ImportError:
        return
    data = hass.data.get(LOVELACE_DATA)
    if data is None or data.resource_mode != "storage":
        _LOGGER.debug("Lovelace resources in YAML mode; add %s yourself", url)
        return
    resources = data.resources
    await resources.async_get_info()  # loads the collection
    for item in resources.async_items():
        if not item.get("url", "").startswith(CARD_URL):
            continue
        if item["url"] != url:
            await resources.async_update_item(item["id"], {"res_type": "module", "url": url})
            _LOGGER.info("Updated house card resource to %s", url)
        return
    await resources.async_create_item({"res_type": "module", "url": url})
    _LOGGER.info("Registered house card resource %s", url)


def _manifest_version() -> str:
    return json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]


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
