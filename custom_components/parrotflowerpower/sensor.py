"""Sensor platform for Parrot Flower Power BLE."""
from __future__ import annotations

from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "air_temperature": SensorEntityDescription(
        key="air_temperature",
        name="Air Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "soil_temperature": SensorEntityDescription(
        key="soil_temperature",
        name="Soil Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "light": SensorEntityDescription(
        key="light",
        name="Light Intensity",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "moisture": SensorEntityDescription(
        key="moisture",
        name="Moisture",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:water-percent",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "conductivity": SensorEntityDescription(
        key="conductivity",
        name="Conductivity",
        native_unit_of_measurement="µS/cm",
        icon="mdi:flash-circle",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "battery": SensorEntityDescription(
        key="battery",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


def _to_data_update(data: dict) -> PassiveBluetoothDataUpdate:
    return PassiveBluetoothDataUpdate(
        devices={None: {}},
        entity_descriptions={
            PassiveBluetoothEntityKey(key, None): desc
            for key, desc in SENSOR_DESCRIPTIONS.items()
            if key in data
        },
        entity_names={
            PassiveBluetoothEntityKey(key, None): desc.name
            for key, desc in SENSOR_DESCRIPTIONS.items()
            if key in data
        },
        entity_data={
            PassiveBluetoothEntityKey(key, None): value
            for key, value in data.items()
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ActiveBluetoothProcessorCoordinator = coordinator_data["coordinator"]

    processor = PassiveBluetoothDataProcessor(_to_data_update)
    processor.device_info = coordinator_data["device_info"]  # type: ignore[attr-defined]
    entry.async_on_unload(
        processor.async_add_entities_listener(FlowerPowerSensor, async_add_entities)
    )
    entry.async_on_unload(coordinator.async_register_processor(processor))

    # Eagerly create all entities with None state so they appear even when the
    # device is off and no BLE advertisements have been received yet.
    processor.async_handle_update({key: None for key in SENSOR_DESCRIPTIONS}, True)


class FlowerPowerSensor(PassiveBluetoothProcessorEntity, SensorEntity):
    """A Parrot Flower Power BLE sensor entity."""

    @property
    def device_info(self):
        """Return device info for the sensor."""
        return self.processor.device_info  # type: ignore[attr-defined]

    @property
    def native_value(self) -> float | None:
        return self.processor.entity_data.get(self.entity_key)
