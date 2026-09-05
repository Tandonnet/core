"""The Bbox integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from aiobbox import BboxApi

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]

type BboxConfigEntry = ConfigEntry["BboxCoordinator"]


class BboxCoordinator(DataUpdateCoordinator):
    """Periodically fetch data from the Bbox."""

    def __init__(self, hass: HomeAssistant, entry: BboxConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="bbox",
            update_interval=timedelta(seconds=60),
        )
        self._password = entry.data[CONF_PASSWORD]
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self):
        try:
            async with BboxApi(self._password, session=self._session) as bbox:
                hosts = await bbox.get_hosts()
                router = await bbox.get_router_info()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Bbox: {err}") from err

        return {"hosts": hosts, "router": router}


async def async_setup_entry(hass: HomeAssistant, entry: BboxConfigEntry) -> bool:
    """Set up Bbox from a config entry created via the UI."""
    coordinator = BboxCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BboxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
