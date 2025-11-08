"""Sensor platform for UniFi Connect integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UniFi Connect sensors from a config entry."""
    hub = hass.data[DOMAIN][config_entry.entry_id]
    devices = hub.coordinator.data

    entities = []
    for device in devices:
        platform = device.get("type", {}).get("platform", "")

        # EV Station Lite sensors
        if platform == "EVS-Lite":
            shadow = device.get("shadow", {})

            # Charging Status sensor
            if "chargingStatus" in shadow:
                entities.append(EVStationChargingStatusSensor(hub, device))

            # Max Current sensor
            if "maxCurrent" in shadow:
                entities.append(EVStationMaxCurrentSensor(hub, device))

            # Derating sensor
            if "derating" in shadow:
                entities.append(EVStationDeratingBinarySensor(hub, device))

    async_add_entities(entities)


class EVStationChargingStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EV Station charging status."""

    def __init__(self, hub, device):
        """Initialize the sensor."""
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device_id = device["id"]
        self._attr_name = f"{device['name']} Charging Status"
        self._attr_unique_id = f"{device['id']}_charging_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName"),
            sw_version=device.get("firmwareVersion"),
        )

    @property
    def native_value(self) -> str | None:
        """Return the charging status."""
        for device in self._hub.coordinator.data:
            if device["id"] == self._device_id:
                return device.get("shadow", {}).get("chargingStatus")
        return None

    @property
    def icon(self) -> str:
        """Return the icon based on charging status."""
        status = self.native_value
        if status == "Charging":
            return "mdi:ev-station"
        elif status == "Available":
            return "mdi:ev-plug-type1"
        elif status == "Unavailable":
            return "mdi:power-plug-off"
        return "mdi:ev-station"


class EVStationMaxCurrentSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EV Station max current."""

    def __init__(self, hub, device):
        """Initialize the sensor."""
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device_id = device["id"]
        self._attr_name = f"{device['name']} Max Current"
        self._attr_unique_id = f"{device['id']}_max_current"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName"),
            sw_version=device.get("firmwareVersion"),
        )

    @property
    def native_value(self) -> int | None:
        """Return the max current."""
        for device in self._hub.coordinator.data:
            if device["id"] == self._device_id:
                return device.get("shadow", {}).get("maxCurrent")
        return None

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:current-ac"


class EVStationDeratingBinarySensor(CoordinatorEntity, SensorEntity):
    """Binary sensor for EV Station derating status."""

    def __init__(self, hub, device):
        """Initialize the sensor."""
        super().__init__(hub.coordinator)
        self._hub = hub
        self._device_id = device["id"]
        self._attr_name = f"{device['name']} Derating"
        self._attr_unique_id = f"{device['id']}_derating"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device.get("name"),
            manufacturer="Ubiquiti",
            model=device.get("type", {}).get("fullName"),
            sw_version=device.get("firmwareVersion"),
        )

    @property
    def native_value(self) -> str:
        """Return the derating status."""
        for device in self._hub.coordinator.data:
            if device["id"] == self._device_id:
                derating = device.get("shadow", {}).get("derating", False)
                return "Active" if derating else "Inactive"
        return "Inactive"

    @property
    def icon(self) -> str:
        """Return the icon."""
        derating = self.native_value == "Active"
        return "mdi:thermometer-alert" if derating else "mdi:thermometer-check"
