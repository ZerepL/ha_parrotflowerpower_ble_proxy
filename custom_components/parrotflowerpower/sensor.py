"""Sensor platform for Parrot Flower Power BLE."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LIGHT_LUX, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

SENSOR_DESCRIPTIONS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        key="air_temperature",
        name="Air Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="soil_temperature",
        name="Soil Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="light",
        name="Light Intensity",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="moisture",
        name="Moisture",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:water-percent",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="conductivity",
        name="Conductivity",
        native_unit_of_measurement="µS/cm",
        icon="mdi:flash-circle",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="battery",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entry_data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        FlowerPowerSensor(entry, entry_data, desc)
        for desc in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)
    entry_data["listeners"].extend(e.on_data_update for e in entities)


class FlowerPowerSensor(RestoreEntity, SensorEntity):
    """A Parrot Flower Power BLE sensor entity."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, entry_data: dict, description: SensorEntityDescription) -> None:
        self.entity_description = description
        self._entry_data = entry_data
        address = entry.unique_id.lower()  # type: ignore[union-attr]
        self._attr_unique_id = f"{address}-{description.key}"
        self._attr_device_info = entry_data["device_info"]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Restore last known value so entities don't show unknown after restart
        if (last_state := await self.async_get_last_state()) and last_state.state not in (
            "unknown", "unavailable", "None"
        ):
            try:
                self._entry_data["data"].setdefault(
                    self.entity_description.key, float(last_state.state)
                )
            except ValueError:
                pass

    @callback
    def on_data_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        return self._entry_data["data"].get(self.entity_description.key)
