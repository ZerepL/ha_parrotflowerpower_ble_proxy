"""Config flow for Parrot Flower Power BLE."""
from __future__ import annotations

import time

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.device_registry import format_mac
import voluptuous as vol

from .const import DEVICE_MAC_PREFIXES, DOMAIN, LOGGER

DISCOVERY_MAX_AGE = 300  # seconds — only show devices seen in the last 5 minutes


class ParrotFlowerPowerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, str] = {}  # address -> name

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle bluetooth discovery."""
        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": discovery_info.name or discovery_info.address}
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            address = user_input["mac"]
            name = user_input.get("name") or self._discovered.get(address, address)
            await self.async_set_unique_id(format_mac(address))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=name, data={"mac": address, "name": name})

        # Collect discovered devices not yet configured
        current_ids = self._async_current_ids()
        for info in async_discovered_service_info(self.hass, connectable=True):
            if (
                format_mac(info.address) not in current_ids
                and info.address.upper().startswith(DEVICE_MAC_PREFIXES)
                and (time.monotonic() - info.time) < DISCOVERY_MAX_AGE
            ):
                self._discovered[info.address] = info.name or info.address

        if not self._discovered:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required("mac"): str,
                    vol.Optional("name"): str,
                }),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("mac"): vol.In(
                    {**self._discovered, "manual": "Enter MAC manually"}
                ),
                vol.Optional("name"): str,
            }),
        )
