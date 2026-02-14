import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, DEVICE_PLATFORM_SE21, ACTION_MODE_SWITCH, ACTION_LAUNCH_APP,
    EV_ACTION_SWITCH_MODE, EV_ACTION_SET_FALLBACK_SECURITY, EV_ACTION_SET_BREAKER,
)
from .coordinator import _is_ev_device
from .entity import UnifiConnectEntity
from .hub import UnifiConnectHub

_LOGGER = logging.getLogger(__name__)

# EV Station select entities - using actual supportedActions and featureFlags enums
EV_SELECT_ENTITIES = [
    {
        "shadow_key": "evStationMode",
        "feature_key": "evStationMode",
        "name_suffix": "Station Mode",
        "unique_suffix": "station_mode",
        "action_id": EV_ACTION_SWITCH_MODE,
        "action_name": "switch_ev_station_mode",
        "default_options": ["plugAndCharge", "noAccess"],
        "icon": "mdi:ev-station",
    },
    {
        "shadow_key": "fallbackSecurity",
        "feature_key": "fallbackSecurity",
        "name_suffix": "Fallback Security",
        "unique_suffix": "fallback_security",
        "action_id": EV_ACTION_SET_FALLBACK_SECURITY,
        "action_name": "set_fallback_security",
        "default_options": ["plugAndCharge", "noAccess"],
        "icon": "mdi:shield-lock",
    },
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up UniFi Connect select entities from config entry."""
    hub: UnifiConnectHub = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []

    for device in hub.coordinator.data or []:
        platform = device.get("type", {}).get("platform")

        # SE21 Display entities
        if platform == DEVICE_PLATFORM_SE21:
            shadow = device.get("shadow", {})
            if shadow.get("mode") is not None:
                entities.append(DisplayModeSelect(hub, device))
            apps = device.get("featureFlags", {}).get("app", {}).get("enum", [])
            if apps:
                entities.append(DisplayAppSelect(hub, device, apps))

        # EV Station entities
        if _is_ev_device(device):
            shadow = device.get("shadow", {})
            features = device.get("featureFlags", {})
            for config in EV_SELECT_ENTITIES:
                if config["shadow_key"] in shadow:
                    entities.append(EVSelect(hub, device, config, features))
            # Breaker Amperage select (options from breakerLoadLimits)
            breaker_limits = features.get("breakerLoadLimits", [])
            if breaker_limits:
                entities.append(EVBreakerSelect(hub, device, breaker_limits))

    async_add_entities(entities)


class DisplayModeSelect(UnifiConnectEntity, SelectEntity):
    """Mode selector for SE 21 (Web/App)."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub, device, "Mode", "mode")
        mode_enum = device.get("featureFlags", {}).get("mode", {}).get("enum", [])
        self._attr_options = mode_enum if mode_enum else ["Web", "App"]

    @property
    def current_option(self):
        return self._get_shadow().get("mode", "")

    async def async_select_option(self, option: str):
        await self._hub.api.perform_action(
            self._device_id,
            ACTION_MODE_SWITCH,
            "mode_switch",
            {"value": option},
        )
        await self.coordinator.async_request_refresh()


class DisplayAppSelect(UnifiConnectEntity, SelectEntity):
    """App selector for SE 21."""

    def __init__(self, hub: UnifiConnectHub, device: dict, apps: list):
        super().__init__(hub, device, "App Selector", "app_selector")
        self._attr_options = apps

    @property
    def current_option(self):
        return self._get_shadow().get("selectedApp", "")

    async def async_select_option(self, option: str):
        await self._hub.api.perform_action(
            self._device_id,
            ACTION_LAUNCH_APP,
            "launch_app",
            {"value": option},
        )
        await self.coordinator.async_request_refresh()


class EVSelect(UnifiConnectEntity, SelectEntity):
    """Select entity for EV Station settings using perform_action."""

    def __init__(self, hub: UnifiConnectHub, device: dict, config: dict, features: dict):
        super().__init__(hub, device, config["name_suffix"], config["unique_suffix"])
        self._shadow_key = config["shadow_key"]
        self._action_id = config["action_id"]
        self._action_name = config["action_name"]
        self._attr_icon = config.get("icon")

        # Get options from featureFlags enum if available
        feature_def = features.get(config.get("feature_key", ""), {})
        if isinstance(feature_def, dict) and "enum" in feature_def:
            self._attr_options = feature_def["enum"]
        else:
            self._attr_options = config.get("default_options", [])

    @property
    def current_option(self):
        return self._get_shadow().get(self._shadow_key, "")

    async def async_select_option(self, option: str):
        await self._hub.api.perform_action(
            self._device_id,
            self._action_id,
            self._action_name,
            {"value": option},
        )
        await self.coordinator.async_request_refresh()


class EVBreakerSelect(UnifiConnectEntity, SelectEntity):
    """Breaker Amperage selector for EV Station.

    Options derived from featureFlags.breakerLoadLimits.
    The selected breaker determines the maximum output current.
    """

    def __init__(self, hub: UnifiConnectHub, device: dict, breaker_limits: list):
        super().__init__(hub, device, "Breaker Amperage", "breaker_amperage")
        self._attr_icon = "mdi:fuse"
        # Build options like ["15A", "20A", "30A", "40A", "50A", "60A", "70A"]
        self._breaker_map: dict[str, int] = {}
        options = []
        for entry in breaker_limits:
            if isinstance(entry, dict) and "breakerAm" in entry:
                amp = entry["breakerAm"]
                label = f"{amp}A"
                options.append(label)
                self._breaker_map[label] = amp
        self._attr_options = options

    @property
    def current_option(self):
        device = self._get_device()
        if device:
            breaker_am = device.get("extraInfo", {}).get("breakerAm")
            if breaker_am is not None:
                return f"{breaker_am}A"
        return None

    async def async_select_option(self, option: str):
        amp_value = self._breaker_map.get(option)
        if amp_value is not None:
            await self._hub.api.perform_action(
                self._device_id,
                EV_ACTION_SET_BREAKER,
                "set_breaker_amp",
                {"value": amp_value},
            )
            await self.coordinator.async_request_refresh()
