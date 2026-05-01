# Parrot Flower Power BLE Proxy — Home Assistant Integration

A custom Home Assistant integration for the **Parrot Flower Power** plant sensor using the HA Bluetooth stack with ESPHome BLE proxy support.

> This project is heavily based on [mbrentini/homeassistant_parrotflowerpower](https://github.com/mbrentini/homeassistant_parrotflowerpower) and is essentially an update to make it work with the modern HA Bluetooth proxy architecture instead of requiring a direct Bluetooth adapter on the HA host.

## Sensors

Each device exposes 6 entities:

| Sensor | Unit |
|---|---|
| Air Temperature | °C |
| Soil Temperature | °C |
| Light Intensity | lx |
| Moisture | % |
| Conductivity | µS/cm |
| Battery | % |

## Requirements

### Hardware
- Parrot Flower Power plant sensor (MAC prefix `A0:14:3D` or `90:03:B7`)
- An [ESPHome BLE proxy](https://esphome.io/components/bluetooth_proxy.html) (e.g. ESP32) on the same network as Home Assistant

### ESPHome Proxy Configuration

Your ESP32 must have active BLE proxy enabled:

```yaml
bluetooth_proxy:
  active: true
```

Without `active: true` the proxy only does passive scanning and cannot connect to the sensor to read data.

### Home Assistant
- Home Assistant 2023.6 or newer
- ESPHome integration configured and connected to your proxy device

## Installation

Copy the `custom_components/parrotflowerpower` folder into your HA `config/custom_components/` directory and restart Home Assistant.

## Adding a Device

1. Power on the Flower Power sensor — it advertises for ~30 seconds after boot (LED blinks).
2. Go to **Settings → Devices & Services → Add Integration** and search for **Parrot Flower Power BLE Proxy**.
3. Select the device from the dropdown, or enter the MAC address manually (`A0:14:3D:XX:XX:XX`).

Entities are created immediately and will show as unavailable until the first poll (every 30 minutes).

## Troubleshooting

**No data after adding**
- Confirm the ESPHome proxy is connected in HA and has `active: true` in its config.
- If the ESP32 was recently restarted, power-cycle it — it sometimes needs a reboot to resume BLE scanning.

**Two entries for the same device**
- Can happen if the device was added both via auto-discovery and manually. Remove the duplicate that shows no data.
