import logging
from homeassistant.components.text import TextEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import UnifiConnectHub

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up UniFi Connect text entities from config entry."""
    hub: UnifiConnectHub = hass.data[DOMAIN][entry.entry_id]
    devices = hub.coordinator.data

    texts = []

    for device in devices:
        platform = device.get("type", {}).get("platform", "")

        # EV Station Lite text entities
        if platform == "EVS-Lite":
            if device.get("featureFlags", {}).get("displayLabelSupported"):
                texts.append(EVStationDisplayLabelText(hub, device))
            if device.get("featureFlags", {}).get("adminMessageSupported"):
                texts.append(EVStationAdminMessageText(hub, device))

        # Display SE 21 text entities
        elif platform == "UC-Display-SE-21":
            if device.get("shadow", {}).get("currentHomePage") is not None:
                texts.append(DisplayWebUrlText(hub, device))

    async_add_entities(texts)


class DisplayWebUrlText(CoordinatorEntity, TextEntity):
    """Web URL field for SE 21."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Web URL"
        self._attr_unique_id = f"{device['id']}_web_url"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )
        self._attr_native_min = 0
        self._attr_native_max = 512
        self._action_id = "2d047a97-9882-43f0-b953-88309c0669a8"

    @property
    def native_value(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("currentHomePage", "")
        return ""

    async def async_set_value(self, value: str) -> None:
        _LOGGER.debug("Setting web URL to %s on %s", value, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "load_website",
            {"url": value}
        )
        await self._hub.coordinator.async_request_refresh()


class EVStationDisplayLabelText(CoordinatorEntity, TextEntity):
    """Display label text for EV Station."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Display Label"
        self._attr_unique_id = f"{device['id']}_display_label"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )
        self._attr_native_min = 0
        self._attr_native_max = 128
        self._action_id = "ae1c886a-910c-4395-985b-6f93054c2e9f"

    @property
    def native_value(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("displayLabel", "")
        return ""

    async def async_set_value(self, value: str) -> None:
        _LOGGER.debug("Setting display label to %s on %s", value, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "set_display_label",
            {"label": value}
        )
        await self._hub.coordinator.async_request_refresh()


class EVStationAdminMessageText(CoordinatorEntity, TextEntity):
    """Admin message text for EV Station."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Admin Message"
        self._attr_unique_id = f"{device['id']}_admin_message"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )
        self._attr_native_min = 0
        self._attr_native_max = 256
        self._action_id = "cddf832a-7fcd-4049-981f-281ed4a665f0"

    @property
    def native_value(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("adminMessage", "")
        return ""

    async def async_set_value(self, value: str) -> None:
        _LOGGER.debug("Setting admin message to %s on %s", value, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "set_admin_message",
            {"message": value}
        )
        await self._hub.coordinator.async_request_refresh()
