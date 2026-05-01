"""Parrot Flower Power BLE integration using HA Bluetooth stack (proxy-compatible)."""
from __future__ import annotations

import math
from struct import unpack

from bleak import BleakClient
from bleak_retry_connector import establish_connection

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
)
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, HANDLES, LOGGER, POLL_INTERVAL

PLATFORMS = [Platform.SENSOR]


def _decode(key: str, data: bytes) -> float:
    if len(data) <= 2:
        raw = int.from_bytes(data, byteorder="little")
    elif len(data) == 4:
        raw = unpack("<f", data)[0]
    else:
        return float(int.from_bytes(data[:2], byteorder="little"))

    if key == "light":
        return 0.0 if raw == 65535 else round(80000000 * (math.pow(raw, -1.063)), 1)
    if key in ("soil_temperature", "air_temperature"):
        v = 0.00000003044 * raw**3 - 0.00008038 * raw**2 + raw * 0.1149 - 30.45
        return round(max(-10.0, min(55.0, v)), 1)
    if key == "moisture":
        sm = 11.4293 + (1.0698e-9 * raw**4 - 1.52538e-6 * raw**3 + 8.66976e-4 * raw**2 - 0.169422 * raw)
        v = 100.0 * (4.5e-6 * sm**3 - 5.5e-4 * sm**2 + 0.0292 * sm - 0.053)
        return round(max(0.0, min(60.0, v)), 1)
    return round(raw * 1.0, 1)


async def _async_poll(hass: HomeAssistant, service_info: BluetoothServiceInfoBleak) -> dict:
    if service_info.connectable:
        ble_device = service_info.device
    else:
        ble_device = async_ble_device_from_address(hass, service_info.device.address, connectable=True)
        if not ble_device:
            ble_device = async_ble_device_from_address(hass, service_info.device.address, connectable=False)
        if not ble_device:
            raise RuntimeError(f"No device found for {service_info.device.address}")

    result = {}
    client = await establish_connection(BleakClient, ble_device, service_info.device.address)
    try:
        for key, handle in HANDLES.items():
            data = await client.read_gatt_char(handle)
            result[key] = _decode(key, data)
            LOGGER.debug("Read %s = %s", key, result[key])
    except Exception as e:
        LOGGER.error("Poll failed for %s: %s", service_info.device.address, e)
        raise
    finally:
        await client.disconnect()
    return result


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    address = entry.unique_id
    assert address is not None
    address = address.upper()

    last_poll: dict = {}

    def _needs_poll(service_info: BluetoothServiceInfoBleak, seconds_since_last_poll: float | None) -> bool:
        return (
            hass.is_running
            and (seconds_since_last_poll is None or seconds_since_last_poll >= POLL_INTERVAL)
        )

    async def _poll(service_info: BluetoothServiceInfoBleak) -> dict:
        data = await _async_poll(hass, service_info)
        last_poll.update(data)
        return data

    def _update(service_info: BluetoothServiceInfoBleak) -> dict:
        return last_poll.copy()

    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        LOGGER,
        address=address,
        mode=BluetoothScanningMode.ACTIVE,
        update_method=_update,
        needs_poll_method=_needs_poll,
        poll_method=_poll,
        connectable=False,
    )

    device_info = DeviceInfo(
        identifiers={(DOMAIN, address)},
        name=entry.title,
        manufacturer="Parrot",
        model="Flower Power",
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "device_info": device_info,
        "last_poll": last_poll,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
