"""Config flow for the Bbox integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiobbox import BboxApi

# TODO: adapt these imports to the actual exception classes exposed by
# aiobbox (the package is still alpha, check aiobbox/exceptions.py or
# equivalent). These are plausible names to be confirmed.
try:
    from aiobbox.exceptions import BboxAuthError, BboxConnectionError
except ImportError:  # pragma: no cover - safety net if the API differs
    BboxAuthError = BboxConnectionError = Exception

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input by actually querying the Bbox.

    Raises CannotConnect or InvalidAuth on failure.
    Returns a dict with the title to display and a stable unique
    identifier (router serial number) for the config entry.
    """
    session = async_get_clientsession(hass)

    try:
        async with BboxApi(data[CONF_PASSWORD], session=session) as bbox:
            router_info = await bbox.get_router_info()
    except BboxAuthError as err:
        raise InvalidAuth from err
    except (BboxConnectionError, TimeoutError) as err:
        raise CannotConnect from err

    return {
        "title": f"Bbox {router_info.modelname}",
        "unique_id": router_info.serialnumber,
    }


class BboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Bbox."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the step triggered when the user adds the integration from the UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Prevent the same physical Bbox from being added twice.
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate a connection problem with the Bbox."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate an invalid password."""
