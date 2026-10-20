"""Diagnostics support for Energy Hub."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import EnergyHubConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EnergyHubConfigEntry
) -> dict[str, Any]:
    """Return mapping, active features and engine state."""
    coordinator = entry.runtime_data
    return {
        "options": dict(coordinator.options),
        "slots": dict(coordinator.slots),
        "features": sorted(coordinator.features),
        "engine_state": coordinator.engine.state.as_dict(),
        "data": dict(coordinator.data),
        "price_stats": dict(coordinator.price_stats),
        "forecast_slots": len(coordinator.forecast),
    }
