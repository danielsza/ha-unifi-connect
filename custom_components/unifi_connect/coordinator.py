import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UnifiConnectAPI, UnifiConnectAPIError
from .const import (
    DOMAIN,
    DEFAULT_REFRESH_INTERVAL,
    EV_DEVICE_PLATFORMS,
    EV_ACTION_POWER_STATS_SINGLE,
)

_LOGGER = logging.getLogger(__name__)


def _is_ev_device(device: dict) -> bool:
    """Check if a device is an EV Station (by platform or supported actions)."""
    platform = device.get("type", {}).get("platform", "")
    if platform in EV_DEVICE_PLATFORMS:
        return True
    # Also detect by supported actions for unknown platform IDs
    actions = device.get("supportedActions", [])
    action_names = [a.get("name", "") if isinstance(a, dict) else "" for a in actions]
    return EV_ACTION_POWER_STATS_SINGLE in action_names


def _get_action_id(device: dict, action_name: str) -> str | None:
    """Find the action ID for a named action from the device's supportedActions."""
    for action in device.get("supportedActions", []):
        if isinstance(action, dict) and action.get("name") == action_name:
            return action.get("id")
    return None


class UnifiConnectCoordinator(DataUpdateCoordinator):
    """Class to manage fetching UniFi Connect data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: UnifiConnectAPI,
        update_interval: int = DEFAULT_REFRESH_INTERVAL,
    ):
        self.api = api
        self.charge_history: dict[str, list] = {}
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from UniFi Connect API."""
        try:
            devices = await self.api.get_devices()

            # For EV devices, trigger power_stats_single to get fresh readings
            # and fetch charge history
            for device in devices or []:
                if not _is_ev_device(device):
                    continue

                device_id = device.get("id")
                if not device_id:
                    continue

                # Log full shadow on first discovery to help map field names
                shadow = device.get("shadow", {})
                _LOGGER.debug(
                    "EV device %s (%s) shadow: %s",
                    device.get("name"),
                    device_id,
                    shadow,
                )
                _LOGGER.debug(
                    "EV device %s supportedActions: %s",
                    device.get("name"),
                    device.get("supportedActions", []),
                )

                # Trigger power_stats_single to refresh real-time data
                action_id = _get_action_id(device, EV_ACTION_POWER_STATS_SINGLE)
                if action_id:
                    await self.api.request_power_stats(device_id, action_id)

                # Fetch charge history
                try:
                    history = await self.api.get_charge_history(device_id)
                    self.charge_history[device_id] = history
                    _LOGGER.debug(
                        "EV device %s charge history entries: %d",
                        device.get("name"),
                        len(history),
                    )
                except Exception as err:
                    _LOGGER.debug(
                        "Could not fetch charge history for %s: %s",
                        device.get("name"),
                        err,
                    )

            return devices
        except UnifiConnectAPIError as err:
            raise UpdateFailed(f"Error fetching UniFi Connect data: {err}") from err
