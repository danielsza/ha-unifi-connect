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
        platform = device.get("type", {}).get("platform", "")

        # EV Station Lite buttons
        if platform == "EVS-Lite":
            buttons.append(EVStationRebootButton(hub, device))

        # Display SE 21 buttons
        elif platform == "UC-Display-SE-21":
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


class EVStationRebootButton(CoordinatorEntity, ButtonEntity):
    """Button to reboot the EV Station."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Reboot"
        self._attr_unique_id = f"{device['id']}_reboot"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )
        self._attr_icon = "mdi:restart"

        self._action_id = "8d2a2b00-e9d8-403e-ae92-c6e933363561"

    async def async_press(self) -> None:
        _LOGGER.debug("Sending reboot to %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "reboot"
        )
        await self._hub.coordinator.async_request_refresh()