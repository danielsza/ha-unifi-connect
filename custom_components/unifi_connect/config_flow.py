from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_CONTROLLER_TYPE,
    CONTROLLER_UDMP,
    CONTROLLER_OTHER,
)

class UnifiConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi Connect."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_PORT, default=7443): int,
                vol.Required(CONF_CONTROLLER_TYPE, default=CONTROLLER_UDMP): vol.In([
                    CONTROLLER_UDMP,
                    CONTROLLER_OTHER
                ]),
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UnifiConnectOptionsFlowHandler(config_entry)

class UnifiConnectOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle UniFi Connect options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({})  # placeholder
        )
