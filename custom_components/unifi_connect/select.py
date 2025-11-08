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
        platform = device.get("type", {}).get("platform", "")
        features = device.get("featureFlags", {})

        # EV Station Lite select entities
        if platform == "EVS-Lite":
            if "evStationMode" in features:
                selects.append(EVStationModeSelect(hub, device))
            if "fallbackSecurity" in features:
                selects.append(EVStationFallbackSecuritySelect(hub, device))

        # Display SE 21 select entities
        elif platform == "UC-Display-SE-21":
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


class EVStationModeSelect(CoordinatorEntity, SelectEntity):
    """EV Station mode selector."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Station Mode"
        self._attr_unique_id = f"{device['id']}_ev_station_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._action_id = "564a0346-079f-4938-8004-1d5d79eda79a"
        self._attr_options = device.get("featureFlags", {}).get("evStationMode", {}).get("enum", [])
        self._attr_icon = "mdi:shield-lock"

    @property
    def current_option(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("evStationMode", "plugAndCharge")
        return "plugAndCharge"

    async def async_select_option(self, option: str):
        _LOGGER.debug("Setting EV station mode to %s on %s", option, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "switch_ev_station_mode",
            {"mode": option}
        )
        await self._hub.coordinator.async_request_refresh()


class EVStationFallbackSecuritySelect(CoordinatorEntity, SelectEntity):
    """EV Station fallback security selector."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Fallback Security"
        self._attr_unique_id = f"{device['id']}_fallback_security"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._action_id = "633270f6-d9f6-4253-b4df-9d06a7f47ad0"
        self._attr_options = device.get("featureFlags", {}).get("fallbackSecurity", {}).get("enum", [])
        self._attr_icon = "mdi:shield-alert"

    @property
    def current_option(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("fallbackSecurity", "noAccess")
        return "noAccess"

    async def async_select_option(self, option: str):
        _LOGGER.debug("Setting fallback security to %s on %s", option, self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            "set_fallback_security",
            {"mode": option}
        )
        await self._hub.coordinator.async_request_refresh()