"""Config flow for water provider portal."""
from __future__ import annotations

import toutsurmoneau
import logging
from urllib.parse import urlparse
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    USER_INPUT_METER_ID,
    USER_INPUT_USERNAME,
    USER_INPUT_PASSWORD,
    USER_INPUT_URL,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tout sur mon eau."""

    VERSION = 1

    # "user" means: started by user. This is the initial form
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors_for_form: dict[str, str] = {}
        if user_input is not None:
            try:
                # create client to find out default meter id
                client = toutsurmoneau.AsyncClient(
                    username=user_input[USER_INPUT_USERNAME],
                    password=user_input[USER_INPUT_PASSWORD],
                    url=user_input[USER_INPUT_URL],
                    session=async_get_clientsession(self.hass),
                )
                # store for next step
                self.data = {
                    "client": client,
                    "default_meter_id": await client.async_meter_id(),
                    "contrat": (await client.async_contracts())[0],
                }
                _LOGGER.debug("default_meter_id %s",
                              self.data["default_meter_id"])
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors_for_form["base"] = "unknown"
            else:
                # next step
                return await self.async_step_get_identifier()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        USER_INPUT_URL,
                        default=toutsurmoneau.KNOWN_PROVIDER_URLS[0],
                    ): selector(
                        {
                            "select": {
                                "options": toutsurmoneau.KNOWN_PROVIDER_URLS,
                                "custom_value": True,
                                "mode": "dropdown",
                            }
                        }
                    ),
                    vol.Required(USER_INPUT_USERNAME): str,
                    vol.Required(USER_INPUT_PASSWORD): str,
                }
            ),
            errors=errors_for_form,
        )

    async def async_step_get_identifier(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the meter id step."""
        _LOGGER.debug("get_identifier, default = %s",
                      self.data["default_meter_id"])
        errors_for_form: dict[str, str] = {}
        if user_input is not None:
            try:
                _LOGGER.debug("got input %s", user_input)
                client: toutsurmoneau.AsyncClient = self.data["client"]
                client._id = user_input[USER_INPUT_METER_ID]
                # check by getting meter specific data
                await client.async_monthly_recent()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors_for_form["base"] = "unknown"
            else:
                # configuration data to be stored in hass
                final_config_data = {
                    "username": client._username,
                    "password": client._password,
                    "meter_id": client._id,
                    "url": client._base_url,
                }
                water_provider_name = self.data["contrat"]["brandCode"]
                return self.async_create_entry(
                    title=water_provider_name, data=final_config_data
                )
        return self.async_show_form(
            step_id="get_identifier",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        USER_INPUT_METER_ID, default=self.data["default_meter_id"]
                    ): str,
                }
            ),
            errors=errors_for_form,
        )
