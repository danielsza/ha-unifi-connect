import logging
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import UnifiConnectHub

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up UniFi Connect select entities from config entry."""
    hub: UnifiConnectHub = hass.data[DOMAIN][entry.entry_id]
    devices = hub.coordinator.data

    selects = []

    for device in devices:
        if device.get("type", {}).get("platform") == "UC-Display-SE-21":
            features = device.get("featureFlags", {})

            if "mode" in features:
                selects.append(DisplayModeSelect(hub, device))

            mode = device.get("shadow", {}).get("mode")
            if "appList" in device.get("shadow", {}):
                _LOGGER.debug("AppSelect eligibility for %s: mode=%s, appList=%s",
                    device.get("name"),
                    mode,
                    device.get("shadow", {}).get("appList"))
                selects.append(AppSelect(hub, device))

    async_add_entities(selects)


class DisplayModeSelect(CoordinatorEntity, SelectEntity):
    """Mode selector for SE 21."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Mode"
        self._attr_unique_id = f"{device['id']}_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])} ,
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._action_id = "cc9396fc-fa01-4e23-b4f1-f7d031bb0bd3"  # switch
        self._attr_options = device.get("featureFlags", {}).get("mode", {}).get("enum", [])

    @property
    def current_option(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("mode", "web")
        return "web"

    async def async_select_option(self, option: str):
        _LOGGER.debug("Setting mode to %s on %s", option, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "switch",
            {"mode": option}
        )
        await self._hub.coordinator.async_request_refresh()


class AppSelect(CoordinatorEntity, SelectEntity):
    """Dropdown to launch an app in app mode."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} App Selector"
        self._attr_unique_id = f"{device['id']}_app_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])} ,
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._app_list = device.get("shadow", {}).get("appList", [])
        self._apps = [app.get("packageName") for app in self._app_list if app.get("packageName")]
        self._attr_options = self._apps

        self._launch_action_id = "06f76de3-68a0-40ad-a6ab-1c7f352e05b1"

    @property
    def current_option(self):
        for d in self._hub.coordinator.data:
            if d.get("id") == self._device_id:
                apps = d.get("shadow", {}).get("appList", [])
                for app in apps:
                    if app.get("selected"):
                        return app.get("packageName")
        return None

    async def async_select_option(self, option: str):
        _LOGGER.debug("Launching app %s on %s", option, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._launch_action_id,
            "launch_app",
            args={"packageName": option}
        )
        await self._hub.coordinator.async_request_refresh()