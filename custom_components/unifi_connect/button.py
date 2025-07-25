import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import UnifiConnectHub

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up UniFi Connect buttons from config entry."""
    hub: UnifiConnectHub = hass.data[DOMAIN][entry.entry_id]
    devices = hub.coordinator.data

    buttons = []

    for device in devices:
        if device.get("type", {}).get("platform") == "UC-Display-SE-21":
            buttons.append(ReloadWebButton(hub, device))

    async_add_entities(buttons)


class ReloadWebButton(CoordinatorEntity, ButtonEntity):
    """Button to reload the current web page."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Reload Web Page"
        self._attr_unique_id = f"{device['id']}_reload_web"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._action_id = "416cef71-50b4-4983-91cc-e6d8dcb82505"  # refresh_website

    async def async_press(self) -> None:
        _LOGGER.debug("Sending refresh_website to %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "refresh_website"
        )
        await self._hub.coordinator.async_request_refresh()