"""Sensor platform for UniFi Connect EV Station devices.

Exposes read-only charging status and charge session history.
Writable settings are in their respective control platforms:
  number.py  - Maximum Output, Brightness
  select.py  - Station Mode, Fallback Security
  switch.py  - Status Light, Locating
  text.py    - Display Label, Support Information
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import _is_ev_device
from .entity import UnifiConnectEntity
from .hub import UnifiConnectHub

_LOGGER = logging.getLogger(__name__)

# Read-only sensor definitions from EV Station shadow
EV_SENSOR_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name_suffix": "Charging Status",
        "unique_suffix": "charging_status",
        "shadow_key": "chargingStatus",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:ev-station",
    },
    {
        "name_suffix": "Max Current",
        "unique_suffix": "max_current",
        "shadow_key": "maxCurrent",
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "icon": "mdi:current-ac",
    },
    {
        "name_suffix": "Derating",
        "unique_suffix": "derating",
        "shadow_key": "derating",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:thermometer-alert",
    },
    {
        "name_suffix": "Error Info",
        "unique_suffix": "error_info",
        "shadow_key": "errorInfo",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:alert-circle",
    },
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up UniFi Connect sensor entities from config entry."""
    hub: UnifiConnectHub = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for device in hub.coordinator.data or []:
        if not _is_ev_device(device):
            continue

        shadow = device.get("shadow", {})
        _LOGGER.info(
            "Setting up EV sensors for %s (platform: %s)",
            device.get("name"),
            device.get("type", {}).get("platform"),
        )

        # Create read-only sensors for matching shadow keys
        for sensor_def in EV_SENSOR_DEFINITIONS:
            if sensor_def["shadow_key"] in shadow:
                entities.append(EVShadowSensor(hub, device, sensor_def))

        # Charge history sensors
        entities.append(EVChargeHistoryEnergySensor(hub, device))
        entities.append(EVChargeHistoryCountSensor(hub, device))
        entities.append(EVLastSessionSensor(hub, device))

        # Raw shadow dump sensor for debugging
        entities.append(EVShadowDumpSensor(hub, device))

    if entities:
        _LOGGER.info("Adding %d EV sensor entities", len(entities))
    async_add_entities(entities)


class EVShadowSensor(UnifiConnectEntity, SensorEntity):
    """Sensor that reads a value from the EV device's shadow state."""

    def __init__(
        self,
        hub: UnifiConnectHub,
        device: dict,
        sensor_def: dict[str, Any],
    ):
        super().__init__(hub, device, sensor_def["name_suffix"], sensor_def["unique_suffix"])
        self._shadow_key = sensor_def["shadow_key"]
        self._attr_device_class = sensor_def["device_class"]
        self._attr_state_class = sensor_def["state_class"]
        self._attr_native_unit_of_measurement = sensor_def["unit"]
        self._attr_icon = sensor_def.get("icon")

    @property
    def native_value(self):
        value = self._get_shadow().get(self._shadow_key)
        if value is None:
            return None
        if self._attr_device_class in (
            SensorDeviceClass.POWER,
            SensorDeviceClass.CURRENT,
            SensorDeviceClass.ENERGY,
        ):
            try:
                return round(float(value), 2)
            except (ValueError, TypeError):
                return None
        if isinstance(value, (dict, list)):
            return str(value)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        raw = self._get_shadow().get(self._shadow_key)
        attrs = {"shadow_key": self._shadow_key}
        if isinstance(raw, dict):
            attrs.update(raw)
        return attrs


class EVShadowDumpSensor(UnifiConnectEntity, SensorEntity):
    """Diagnostic sensor that exposes all shadow keys as attributes."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub, device, "Shadow Data", "shadow_dump")
        self._attr_icon = "mdi:bug"
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self):
        return len(self._get_shadow())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        shadow = self._get_shadow()
        attrs: dict[str, Any] = {}
        for key, value in shadow.items():
            if isinstance(value, (dict, list)):
                attrs[key] = str(value)
            else:
                attrs[key] = value
        return attrs


class EVChargeHistoryEnergySensor(UnifiConnectEntity, SensorEntity):
    """Total energy delivered across all charge sessions."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub, device, "Total Energy Delivered", "total_energy_delivered")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_icon = "mdi:lightning-bolt-circle"

    @property
    def native_value(self):
        history = self.coordinator.charge_history.get(self._device_id, [])
        if not history:
            return None
        total = 0.0
        for session in history:
            energy = (
                session.get("energyDelivered")
                or session.get("energy")
                or session.get("totalEnergy")
                or session.get("wh")
                or session.get("kwh")
                or 0
            )
            try:
                total += float(energy)
            except (ValueError, TypeError):
                continue
        return round(total, 2) if total > 0 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        history = self.coordinator.charge_history.get(self._device_id, [])
        attrs: dict[str, Any] = {"total_sessions": len(history)}
        if history:
            last = history[-1] if isinstance(history[-1], dict) else {}
            attrs["last_session_keys"] = list(last.keys())
        return attrs


class EVChargeHistoryCountSensor(UnifiConnectEntity, SensorEntity):
    """Number of charge sessions."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub, device, "Charge Sessions", "charge_sessions")
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self):
        history = self.coordinator.charge_history.get(self._device_id, [])
        return len(history) if history else 0


class EVLastSessionSensor(UnifiConnectEntity, SensorEntity):
    """Most recent charge session details."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub, device, "Last Charge Session", "last_charge_session")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_icon = "mdi:ev-plug-type2"

    @property
    def native_value(self):
        history = self.coordinator.charge_history.get(self._device_id, [])
        if not history:
            return None
        last = history[-1] if isinstance(history[-1], dict) else {}
        energy = (
            last.get("energyDelivered")
            or last.get("energy")
            or last.get("totalEnergy")
            or last.get("wh")
            or last.get("kwh")
        )
        if energy is not None:
            try:
                return round(float(energy), 2)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        history = self.coordinator.charge_history.get(self._device_id, [])
        if not history:
            return {}
        last = history[-1] if isinstance(history[-1], dict) else {}
        attrs: dict[str, Any] = {}
        for key, value in last.items():
            if isinstance(value, (int, float)) and any(
                key.lower().endswith(s) for s in ("time", "at", "timestamp")
            ):
                try:
                    attrs[key] = datetime.fromtimestamp(
                        value / 1000 if value > 1e12 else value,
                        tz=timezone.utc,
                    ).isoformat()
                except (ValueError, OSError):
                    attrs[key] = value
            else:
                attrs[key] = value
        return attrs
