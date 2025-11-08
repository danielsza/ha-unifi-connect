import logging
import asyncio
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import UnifiConnectHub

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up UniFi Connect switch entities from config entry."""
    hub: UnifiConnectHub = hass.data[DOMAIN][entry.entry_id]
    devices = hub.coordinator.data

    _LOGGER.debug("Setting up switch platform. Devices: %s", devices)

    switches = []

    for device in devices:
        _LOGGER.debug("Evaluating device: %s", device.get("name", "Unknown"))
        _LOGGER.debug("Model: %s | ID: %s", device.get("type", {}).get("fullName"), device.get("id"))

        platform = device.get("type", {}).get("platform", "")
        shadow = device.get("shadow", {})
        relay_shadow = device.get("relayShadow", {})

        # EV Station Lite switches
        if platform == "EVS-Lite":
            # Charging enabled switch (from relayShadow)
            if "enabledCharging" in relay_shadow:
                switches.append(EVStationChargingSwitch(hub, device))

            # Status light switch
            if "statusLightEnabled" in shadow:
                switches.append(EVStationStatusLightSwitch(hub, device))

            # Locating switch
            switches.append(EVStationLocatingSwitch(hub, device))

        # Display SE 21 switches
        elif platform == "UC-Display-SE-21":
            switches.append(UnifiDisplaySE21Switch(hub, device))

            if "autoRotate" in shadow:
                switches.append(AutoRotateSwitch(hub, device))
            if "autoReload" in shadow:
                switches.append(AutoReloadSwitch(hub, device))
            if "sleepMode" in shadow:
                switches.append(DisplaySleepSwitch(hub, device))
            if "autoSleep" in shadow:
                switches.append(DisplayAutoSleepSwitch(hub, device))

    async_add_entities(switches)


class UnifiDisplaySE21Switch(CoordinatorEntity, SwitchEntity):
    """Switch entity for UniFi Display SE 21 power control."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device

        self._attr_name = device.get("name", f"UniFi Display {device['id']}")
        self._attr_unique_id = device["id"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        shadow = device.get("shadow", {})
        _LOGGER.debug("Device %s shadow: %s", self._attr_name, shadow)

    @property
    def is_on(self):
        """Get latest display state from coordinator data."""
        devices = self._hub.coordinator.data
        for d in devices:
            if d.get("id") == self._device["id"]:
                return d.get("shadow", {}).get("display", False)
        return False

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Turning ON %s", self._attr_name)
        await self._send_command("display_on")

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Turning OFF %s", self._attr_name)
        await self._send_command("display_off")

    async def _send_command(self, command: str):
        device_id = self._device["id"]
        command_map = {
            "display_on": "06ad25d0-b087-46de-8e9b-7b18339e7238",
            "display_off": "ea959362-c56f-4932-ab8b-0f512a93460c",
        }

        action_id = command_map.get(command)
        if not action_id:
            _LOGGER.warning("Unknown command: %s", command)
            return False

        _LOGGER.debug("Sending action: %s (%s) to device %s", command, action_id, device_id)

        success = await self._hub.api.perform_action(device_id, action_id, command)
        if success:
            _LOGGER.debug("Command %s succeeded, waiting 2s before refresh...", command)
            await asyncio.sleep(2)
            await self._hub.coordinator.async_request_refresh()

            devices = self._hub.coordinator.data
            for d in devices:
                if d.get("id") == device_id:
                    _LOGGER.debug("🔍 Post-refresh state for %s: %s", d.get("name"), d.get("shadow", {}))
                    break
        else:
            _LOGGER.warning("Command %s failed", command)

        return success


class AutoRotateSwitch(CoordinatorEntity, SwitchEntity):
    """Auto-rotate toggle switch."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Auto Rotate"
        self._attr_unique_id = f"{device['id']}_auto_rotate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._action_enable_id = "45b05072-edc0-4bd3-a549-41e4e6b66f86"
        self._action_disable_id = "b016c8c9-53d4-4619-8f8e-45d52b361589"

    @property
    def is_on(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("autoRotate", False)
        return False

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Enabling autoRotate for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_enable_id,
            "enable_auto_rotate"
        )
        await self._hub.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Disabling autoRotate for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_disable_id,
            "disable_auto_rotate"
        )
        await self._hub.coordinator.async_request_refresh()

class AutoReloadSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable auto reload in web mode."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Auto Reload"
        self._attr_unique_id = f"{device['id']}_auto_reload"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._action_enable_id = "5e2b821b-af11-4e6f-a408-46bb31ed95b4"
        self._action_disable_id = "9e02c64d-4579-4cc0-9932-26da78bdecdd"

    @property
    def is_on(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("autoReload", False)
        return False

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Enabling autoReload for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_enable_id,
            "enable_auto_reload"
        )
        await self._hub.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Disabling autoReload for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_disable_id,
            "disable_auto_reload"
        )
        await self._hub.coordinator.async_request_refresh()

class DisplaySleepSwitch(CoordinatorEntity, SwitchEntity):
    """Sleep mode toggle switch."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Sleep Mode"
        self._attr_unique_id = f"{device['id']}_sleep_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._action_enable_id = "263e9332-4f5c-4966-95a1-15febb80fb9f"
        self._action_disable_id = "b2c11736-50cc-4aa9-926a-feab64322bfb"

    @property
    def is_on(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("sleepMode", False)
        return False

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Enabling sleepMode for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_enable_id,
            "enable_sleep"
        )
        await self._hub.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Disabling sleepMode for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_disable_id,
            "disable_sleep"
        )
        await self._hub.coordinator.async_request_refresh()


class DisplayAutoSleepSwitch(CoordinatorEntity, SwitchEntity):
    """Auto sleep toggle switch."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Auto Sleep"
        self._attr_unique_id = f"{device['id']}_auto_sleep"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )

        self._action_enable_id = "4b723196-e4d7-4b64-935b-07efc34b9b2f"
        self._action_disable_id = "2cd90d8a-edff-4fe8-b941-130d6b0a3f02"

    @property
    def is_on(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("autoSleep", False)
        return False

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Enabling autoSleep for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_enable_id,
            "enable_memorize_playlist"
        )
        await self._hub.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Disabling autoSleep for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_disable_id,
            "disable_memorize_playlist"
        )
        await self._hub.coordinator.async_request_refresh()


class EVStationChargingSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable charging for EV Station."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Charging"
        self._attr_unique_id = f"{device['id']}_charging"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )
        self._attr_icon = "mdi:ev-station"

        self._action_enable_id = "d847c06d-8079-4d70-bb97-84bdc04f6921"
        self._action_disable_id = "ae14879a-4874-4afc-8c70-02594a929e8d"

    @property
    def is_on(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("relayShadow", {}).get("enabledCharging", False)
        return False

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Enabling charging for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_enable_id,
            "enable_charging"
        )
        await self._hub.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Disabling charging for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_disable_id,
            "disable_charging"
        )
        await self._hub.coordinator.async_request_refresh()


class EVStationStatusLightSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable status light for EV Station."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Status Light"
        self._attr_unique_id = f"{device['id']}_status_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )
        self._attr_icon = "mdi:led-on"

        self._action_enable_id = "9ae9ece9-8d31-4177-9b56-f4bbc2f8e533"
        self._action_disable_id = "29034cda-9500-4685-a97a-22c79f1e6b74"

    @property
    def is_on(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("statusLightEnabled", False)
        return False

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Enabling status light for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_enable_id,
            "enable_status_light"
        )
        await self._hub.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Disabling status light for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_disable_id,
            "disable_status_light"
        )
        await self._hub.coordinator.async_request_refresh()


class EVStationLocatingSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable locating mode for EV Station."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device = device
        self._device_id = device["id"]

        self._attr_name = f"{device['name']} Locating"
        self._attr_unique_id = f"{device['id']}_locating"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName", "Unknown"),
        )
        self._attr_icon = "mdi:map-marker-radius"

        self._action_enable_id = "b0ac572e-dc97-49f0-a8c8-2e7f69641a4d"
        self._action_disable_id = "ad45e246-123a-4a13-9a4a-7c1ff87493b6"

    @property
    def is_on(self):
        for d in self._hub.coordinator.data:
            if d["id"] == self._device_id:
                return d.get("shadow", {}).get("locating", False)
        return False

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Starting locating for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_enable_id,
            "start_locating"
        )
        await self._hub.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Stopping locating for %s", self._attr_name)
        await self._hub.api.perform_action(
            self._device_id,
            self._action_disable_id,
            "stop_locating"
        )
        await self._hub.coordinator.async_request_refresh()
