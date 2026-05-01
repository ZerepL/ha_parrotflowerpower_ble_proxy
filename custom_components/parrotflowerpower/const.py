import logging

DOMAIN = "parrotflowerpower"
LOGGER = logging.getLogger(__name__)

# Parrot Flower Power GATT handles
HANDLES = {
    "battery":          0x004C,
    "light":            0x0025,
    "conductivity":     0x0029,
    "soil_temperature": 0x002D,
    "air_temperature":  0x0031,
    "moisture":         0x0035,
}

# Known MAC prefixes for Parrot Flower Power devices
DEVICE_MAC_PREFIXES = ("A0:14:3D", "90:03:B7")

POLL_INTERVAL = 1800  # seconds (30 minutes)
