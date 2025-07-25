import logging
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import UnifiConnectHub

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up UniFi Connect number entities from config entry."""
    hub: UnifiConnectHub = hass.data[DOMAIN][entry.entry_id]
    devices = hub.coordinator.data

    numbers = []

    for device in devices:
        if device.get("type", {}).get("platform") == "UC-Display-SE-21":
            if "brightness" in device.get("featureFlags", {}):
                numbers.append(DisplayBrightnessSlider(hub, device))
            if "volume" in device.get("featureFlags", {}):
                numbers.append(DisplayVolumeSlider(hub, device))

    async_add_entities(numbers)


class DisplayBrightnessSlider(CoordinatorEntity, NumberEntity):
    """Brightness control slider for SE 21."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device

        self._attr_name = f"{device['name']} Brightness"
        self._attr_unique_id = f"{device['id']}_brightness"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])} ,
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        brightness_range = device.get("featureFlags", {}).get("brightness", {})
        self._attr_native_min_value = brightness_range.get("min", 0)
        self._attr_native_max_value = brightness_range.get("max", 255)
        self._attr_native_step = 1
        self._attr_mode = "slider"
        self._attr_unit_of_measurement = "level"

        self._action_id = "521c3110-8f8e-400a-a06f-a529093c7a1c"
        self._device_id = device["id"]

    @property
    def native_value(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("brightness", 0)
        return 0

    async def async_set_native_value(self, value: float):
        _LOGGER.debug("Setting brightness to %s on %s", value, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "brightness",
            {"value": int(value)}
        )
        await self._hub.coordinator.async_request_refresh()


class DisplayVolumeSlider(CoordinatorEntity, NumberEntity):
    """Volume control slider for SE 21."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device

        self._attr_name = f"{device['name']} Volume"
        self._attr_unique_id = f"{device['id']}_volume"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])} ,
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        volume_range = device.get("featureFlags", {}).get("volume", {})
        self._attr_native_min_value = volume_range.get("min", 0)
        self._attr_native_max_value = volume_range.get("max", 40)
        self._attr_native_step = 1
        self._attr_mode = "slider"
        self._attr_unit_of_measurement = "level"

        self._action_id = "26f1b4d8-9fea-4a7c-94a5-daf70e84cd5b"
        self._device_id = device["id"]

    @property
    def native_value(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("volume", 0)
        return 0

    async def async_set_native_value(self, value: float):
        _LOGGER.debug("Setting volume to %s on %s", value, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "volume",
            {"value": int(value)}
        )
        await self._hub.coordinator.async_request_refresh()
