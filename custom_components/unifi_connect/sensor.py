"""Sensor platform for UniFi Connect EV Station devices.

Exposes real-time charging data (power, current, voltage, energy) and
charge session history from the UniFi Connect API.

Shadow field names are discovered dynamically — the integration logs the
full shadow dict at DEBUG level on every poll so users can identify new
fields if the API changes.
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
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EV_DEVICE_PLATFORMS
from .coordinator import _is_ev_device
from .entity import UnifiConnectEntity
from .hub import UnifiConnectHub

_LOGGER = logging.getLogger(__name__)

# Mapping of sensor definitions.
# Each entry tries multiple possible shadow key names (the UniFi API is
# not publicly documented, so we cover likely variations).
EV_SENSOR_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name_suffix": "Charging Power",
        "unique_suffix": "charging_power",
        "shadow_keys": ["currentPower", "power", "chargingPower", "outputPower"],
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
        "icon": "mdi:flash",
    },
    {
        "name_suffix": "Charging Current",
        "unique_suffix": "charging_current",
        "shadow_keys": ["currentAmps", "current", "chargingCurrent", "outputCurrent"],
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "icon": "mdi:current-ac",
    },
    {
        "name_suffix": "Voltage",
        "unique_suffix": "voltage",
        "shadow_keys": ["voltage", "lineVoltage", "inputVoltage"],
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfElectricPotential.VOLT,
        "icon": "mdi:sine-wave",
    },
    {
        "name_suffix": "Session Energy",
        "unique_suffix": "session_energy",
        "shadow_keys": [
            "energyDelivered",
            "sessionEnergy",
            "chargeEnergy",
            "energy",
            "totalEnergy",
        ],
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.WATT_HOUR,
        "icon": "mdi:battery-charging",
    },
    {
        "name_suffix": "Max Current",
        "unique_suffix": "max_current",
        "shadow_keys": ["maxCurrent", "maxAmps", "currentLimit"],
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "icon": "mdi:speedometer",
    },
    {
        "name_suffix": "Charge State",
        "unique_suffix": "charge_state",
        "shadow_keys": [
            "chargeState",
            "chargingState",
            "state",
            "status",
            "evState",
        ],
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:ev-station",
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
            "Setting up EV sensors for %s (platform: %s). Shadow keys: %s",
            device.get("name"),
            device.get("type", {}).get("platform"),
            list(shadow.keys()),
        )

        # Create sensors for each definition where at least one shadow key exists
        for sensor_def in EV_SENSOR_DEFINITIONS:
            matched_key = _find_shadow_key(shadow, sensor_def["shadow_keys"])
            if matched_key is not None:
                entities.append(
                    EVShadowSensor(hub, device, sensor_def, matched_key)
                )
                _LOGGER.debug(
                    "  -> Created sensor '%s' using shadow key '%s'",
                    sensor_def["name_suffix"],
                    matched_key,
                )
            else:
                _LOGGER.debug(
                    "  -> Skipped sensor '%s' (no matching shadow key found from %s)",
                    sensor_def["name_suffix"],
                    sensor_def["shadow_keys"],
                )

        # Charge history sensor (total energy across all sessions)
        entities.append(EVChargeHistoryEnergySensor(hub, device))
        entities.append(EVChargeHistoryCountSensor(hub, device))
        entities.append(EVLastSessionSensor(hub, device))

    if entities:
        _LOGGER.info("Adding %d EV sensor entities", len(entities))
    async_add_entities(entities)


def _find_shadow_key(shadow: dict, candidates: list[str]) -> str | None:
    """Return the first matching key found in the shadow dict."""
    for key in candidates:
        if key in shadow:
            return key
    return None


class EVShadowSensor(UnifiConnectEntity, SensorEntity):
    """Sensor that reads a value from the EV device's shadow state."""

    def __init__(
        self,
        hub: UnifiConnectHub,
        device: dict,
        sensor_def: dict[str, Any],
        shadow_key: str,
    ):
        super().__init__(hub, device, sensor_def["name_suffix"], sensor_def["unique_suffix"])
        self._shadow_key = shadow_key
        self._attr_device_class = sensor_def["device_class"]
        self._attr_state_class = sensor_def["state_class"]
        self._attr_native_unit_of_measurement = sensor_def["unit"]
        self._attr_icon = sensor_def.get("icon")

    @property
    def native_value(self):
        """Return the sensor value from shadow data."""
        value = self._get_shadow().get(self._shadow_key)
        if value is None:
            return None
        # Numeric sensors should return a number
        if self._attr_device_class in (
            SensorDeviceClass.POWER,
            SensorDeviceClass.CURRENT,
            SensorDeviceClass.VOLTAGE,
            SensorDeviceClass.ENERGY,
        ):
            try:
                return round(float(value), 2)
            except (ValueError, TypeError):
                return None
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw shadow key name for debugging."""
        return {"shadow_key": self._shadow_key}


class EVChargeHistoryEnergySensor(UnifiConnectEntity, SensorEntity):
    """Sensor showing total energy delivered across all charge sessions."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub, device, "Total Energy Delivered", "total_energy_delivered")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_icon = "mdi:lightning-bolt-circle"

    @property
    def native_value(self):
        """Sum energy from charge history sessions."""
        history = self.coordinator.charge_history.get(self._device_id, [])
        if not history:
            return None
        total = 0.0
        for session in history:
            # Try common field names for energy per session
            energy = (
                session.get("energyDelivered")
                or session.get("energy")
                or session.get("totalEnergy")
                or session.get("wh")
                or 0
            )
            try:
                total += float(energy)
            except (ValueError, TypeError):
                continue
        return round(total, 2) if total > 0 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose session count and last session info."""
        history = self.coordinator.charge_history.get(self._device_id, [])
        attrs: dict[str, Any] = {"total_sessions": len(history)}
        if history:
            last = history[-1] if isinstance(history[-1], dict) else {}
            attrs["last_session_keys"] = list(last.keys())
        return attrs


class EVChargeHistoryCountSensor(UnifiConnectEntity, SensorEntity):
    """Sensor showing number of charge sessions."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub, device, "Charge Sessions", "charge_sessions")
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self):
        history = self.coordinator.charge_history.get(self._device_id, [])
        return len(history) if history else 0


class EVLastSessionSensor(UnifiConnectEntity, SensorEntity):
    """Sensor showing details of the most recent charge session."""

    def __init__(self, hub: UnifiConnectHub, device: dict):
        super().__init__(hub, device, "Last Charge Session", "last_charge_session")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_icon = "mdi:ev-plug-type2"

    @property
    def native_value(self):
        """Return energy from the most recent session."""
        history = self.coordinator.charge_history.get(self._device_id, [])
        if not history:
            return None
        last = history[-1] if isinstance(history[-1], dict) else {}
        energy = (
            last.get("energyDelivered")
            or last.get("energy")
            or last.get("totalEnergy")
            or last.get("wh")
        )
        if energy is not None:
            try:
                return round(float(energy), 2)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose all fields from the last session for discovery."""
        history = self.coordinator.charge_history.get(self._device_id, [])
        if not history:
            return {}
        last = history[-1] if isinstance(history[-1], dict) else {}
        attrs: dict[str, Any] = {}
        for key, value in last.items():
            # Convert timestamps to readable format
            if isinstance(value, (int, float)) and key.lower().endswith(("time", "at", "timestamp")):
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
