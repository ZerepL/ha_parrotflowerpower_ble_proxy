"""Parrot Flower Power BLE integration using HA Bluetooth stack (proxy-compatible)."""
from __future__ import annotations

import math
from datetime import timedelta
from struct import unpack

from bleak import BleakClient
from bleak_retry_connector import establish_connection

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval

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


async def _async_poll(hass: HomeAssistant, address: str) -> dict:
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if not ble_device:
        ble_device = async_ble_device_from_address(hass, address, connectable=False)
    if not ble_device:
        raise RuntimeError(f"No BLE device found for {address}")

    result = {}
    client = await establish_connection(BleakClient, ble_device, address)
    try:
        for key, handle in HANDLES.items():
            data = await client.read_gatt_char(handle)
            result[key] = _decode(key, data)
            LOGGER.debug("Read %s = %s", key, result[key])
    except Exception as e:
        LOGGER.error("Poll failed for %s: %s", address, e)
        raise
    finally:
        await client.disconnect()
    return result


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    address = entry.unique_id
    assert address is not None
    address_upper = address.upper()
    address_lower = address.lower()

    device_info = DeviceInfo(
        identifiers={(DOMAIN, address_lower)},
        name=entry.title,
        manufacturer="Parrot",
        model="Flower Power",
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "device_info": device_info,
        "address_lower": address_lower,
        "data": {},
        "listeners": [],
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _do_poll(_now=None) -> None:
        LOGGER.debug("Polling %s", address_upper)
        try:
            data = await _async_poll(hass, address_upper)
        except Exception as err:
            LOGGER.warning("Poll skipped for %s: %s", address_upper, err)
            return
        entry_data = hass.data[DOMAIN][entry.entry_id]
        entry_data["data"].update(data)
        for listener in list(entry_data["listeners"]):
            listener()

    # Poll immediately on setup, then on interval
    hass.async_create_task(_do_poll())
    entry.async_on_unload(
        async_track_time_interval(hass, _do_poll, timedelta(seconds=POLL_INTERVAL))
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
