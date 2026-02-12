import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UnifiConnectAPI, UnifiConnectAPIError
from .const import DOMAIN, DEFAULT_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)


class UnifiConnectCoordinator(DataUpdateCoordinator):
    """Class to manage fetching UniFi Connect data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: UnifiConnectAPI,
        update_interval: int = DEFAULT_REFRESH_INTERVAL,
    ):
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from UniFi Connect API."""
        try:
            return await self.api.get_devices()
        except UnifiConnectAPIError as err:
            raise UpdateFailed(f"Error fetching UniFi Connect data: {err}") from err
