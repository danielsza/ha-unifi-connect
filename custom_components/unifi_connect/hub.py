from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import UnifiConnectAPI
from .coordinator import UnifiConnectCoordinator
from .const import DEFAULT_PORT, CONTROLLER_UDMP


class UnifiConnectHub:
    """Manages connection and data coordination with UniFi Connect."""

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry

        session = async_create_clientsession(hass, verify_ssl=False)
        self.api = UnifiConnectAPI(
            host=entry.data["host"],
            username=entry.data["username"],
            password=entry.data["password"],
            port=entry.data.get("port", DEFAULT_PORT),
            controller_type=entry.data.get("controller_type", CONTROLLER_UDMP),
            session=session,
        )

        self.coordinator = UnifiConnectCoordinator(hass=hass, api=self.api)

    async def async_initialize(self):
        """Log in and perform initial data fetch."""
        if not await self.api.login():
            raise ConfigEntryNotReady("Unable to log in to UniFi Connect")
        await self.coordinator.async_config_entry_first_refresh()
