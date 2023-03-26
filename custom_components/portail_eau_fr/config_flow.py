"""Config flow for water provider portal."""
from __future__ import annotations

import inspect
import toutsurmoneau
import logging
import asyncio
from urllib.parse import urlparse
from typing import Any
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.helpers.selector import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from .const import (
    DOMAIN,
    USER_INPUT_METER_ID,
    USER_INPUT_USERNAME,
    USER_INPUT_PASSWORD,
    USER_INPUT_URL,
    STEP_PREFIX,
    STEP_IMPORT,
    STEP_FINISH
)

_LOGGER = logging.getLogger(__name__)


class MyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tout sur mon eau."""

    VERSION = 1

    # activate the option flow
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get the options flow for this handler."""
        return MyOptionsFlow(config_entry)

    # "user" means: started by user. This is the initial form
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step when new entity is added."""
        # prepare error message for input form, in case there is a problem
        errors_for_form: dict[str, str] = {}
        # input was provided (second call) so try to init
        if user_input is not None:
            # create client with provided credentials
            client = toutsurmoneau.AsyncClient(
                username=user_input[USER_INPUT_USERNAME],
                password=user_input[USER_INPUT_PASSWORD],
                url=user_input[USER_INPUT_URL],
                session=async_get_clientsession(self.hass),
            )
            # ensure we did not keep login from last time
            client.ensure_logout()
            # check login
            if await client.async_check_credentials():
                meter_identifier = None
                try:
                    # getting default meter id may fail ?
                    meter_identifier = await client.async_meter_id()
                    _LOGGER.debug("default_meter_id %s", meter_identifier)
                except toutsurmoneau.ClientError as error:
                    _LOGGER.debug("Error getting meter id: %s", error)
                try:
                    # at least authenticate the user for next step
                    self.data = {
                        "client": client,
                        "default_meter_id": meter_identifier,
                        "contract": (await client.async_contracts())[0],
                    }
                    # no error: go to next step
                    return await self.async_step_get_identifier()
                except Exception as e:  # pylint: disable=broad-except
                    _LOGGER.exception(f"An exception ocurred: {e}")
                    errors_for_form["base"] = "unknown"
            else:
                errors_for_form["base"] = "login_failed"
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
                    # allow autofill in Browser
                    vol.Required(USER_INPUT_USERNAME): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.EMAIL, autocomplete="username")
                    ),
                    vol.Required(USER_INPUT_PASSWORD): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.PASSWORD, autocomplete="current-password"
                        )
                    )}
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
                _LOGGER.debug("Got input %s", user_input)
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
                water_provider_name = self.data["contract"]["brandCode"]
                return self.async_create_entry(
                    title=water_provider_name, data=final_config_data
                )
        elif self.data["default_meter_id"] is None:
            errors_for_form["base"] = "Cannot determine meter id automatically."
            self.data["default_meter_id"] = ""
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


class MyOptionsFlow(OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._import_task = None
        _LOGGER.debug("option flow started")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        _LOGGER.debug("showing menu")
        return self.async_show_menu(
            step_id="options_init",
            menu_options=[
                STEP_IMPORT,
            ],
        )

    # STEP_IMPORT
    async def async_step_import_history(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage import."""
        assert (STEP_PREFIX+STEP_IMPORT == inspect.stack()[0].function)
        _LOGGER.debug(f"in import_history")
        if not self._import_task:
            _LOGGER.debug(f"create task")
            self._import_task = self.hass.async_create_task(
                self._async_import_historical_data()
            )
            _LOGGER.debug(f"start progress ...")
            return self.async_show_progress(
                step_id=STEP_IMPORT,
                progress_action=STEP_IMPORT,
            )

        try:
            _LOGGER.debug("Waiting for task")
            await self._import_task
            _LOGGER.debug("Task finished")
        except asyncio.TimeoutError:
            _LOGGER.debug("Task timeout")
            return self.async_show_progress_done(next_step_id="pairing_timeout")
        finally:
            self._import_task = None

        _LOGGER.debug("Go to finish")
        return self.async_show_progress_done(next_step_id=STEP_FINISH)

    async def async_step_finish(self, user_input=None):
        assert (STEP_PREFIX+STEP_FINISH == inspect.stack()[0].function)
        if not user_input:
            return self.async_show_form(step_id=STEP_FINISH)
        return self.async_create_entry(title="Some title", data={})

    async def _async_import_historical_data(self) -> None:
        """Process advertisements until pairing mode is detected."""
        count = 10

        try:
            while count > 0:
                _LOGGER.debug("Loop %d", count)
                count = count - 1
                await asyncio.sleep(1)
            _LOGGER.debug("Finished Loop")
        finally:
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_configure(flow_id=self.flow_id))
        return
