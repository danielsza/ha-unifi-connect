from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import UnifiConnectAPI
from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_CONTROLLER_TYPE,
    DEFAULT_PORT,
    CONTROLLER_UDMP,
    CONTROLLER_OTHER,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_CONTROLLER_TYPE, default=CONTROLLER_UDMP): vol.In(
            [CONTROLLER_UDMP, CONTROLLER_OTHER]
        ),
    }
)


class UnifiConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi Connect."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_create_clientsession(self.hass, verify_ssl=False)
            api = UnifiConnectAPI(
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                port=user_input.get(CONF_PORT, DEFAULT_PORT),
                controller_type=user_input.get(CONF_CONTROLLER_TYPE, CONTROLLER_UDMP),
                session=session,
            )
            if await api.login():
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
