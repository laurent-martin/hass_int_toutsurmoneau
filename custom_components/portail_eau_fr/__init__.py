"""The Tout sur mon eau integration."""
from __future__ import annotations

import toutsurmoneau
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, VERSION

# Supported platforms
PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


# called after async_create_entry with data from config_flow
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tout sur mon eau from a config entry."""
    _LOGGER.debug(f"async_setup_entry: version: {
                  VERSION}, config: {entry.data}")

    hass.data.setdefault(DOMAIN, {})
    # TODO 1. Create API instance
    client = toutsurmoneau.AsyncClient(
        username=entry.data["username"],
        password=entry.data["password"],
        meter_id=entry.data["meter_id"],
        url=entry.data["url"],
        session=async_get_clientsession(hass),
    )
    _LOGGER.debug(f"Client created. Checking credentials")
    # TODO 2. Validate the API connection (and authentication)
    if not await client.async_check_credentials():
        return False
    # TODO 3. Store an API object for your platforms to access
    hass.data[DOMAIN][entry.entry_id] = client

    # call async_setup_entry on platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
