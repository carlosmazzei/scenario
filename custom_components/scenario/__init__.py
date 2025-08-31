"""The Scenario IFSEI integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.const import (
    CONF_DELAY,
    CONF_HOST,
    CONF_PORT,
    CONF_PROTOCOL,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from pyscenario.const import COVER_DEVICES, IFSEI_ATTR_SEND_DELAY, LIGHT_DEVICES
from pyscenario.ifsei import IFSEI, NetworkConfiguration, Protocol

from .const import (
    CONTROLLER_ENTRY,
    COVERS_ENTRY,
    DEFAULT_RECONNECT,
    DEFAULT_RECONNECT_DELAY,
    DEFAULT_SEND_DELAY,
    DOMAIN,
    IFSEI_CONF_RECONNECT,
    IFSEI_CONF_RECONNECT_DELAY,
    LIGHTS_ENTRY,
    MANUFACTURER,
    YAML_DEVICES,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from pyscenario.manager import Device
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


PLATFORMS: list[Platform] = [Platform.COVER, Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scenario IFSEI from a config entry."""
    entry_id = entry.entry_id
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    protocol = Protocol[entry.data[CONF_PROTOCOL].upper()]

    hass.data.setdefault(DOMAIN, {})
    entry_data = hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # Load options from config entry
    entry_data[CONF_DELAY] = entry.options.get(CONF_DELAY, DEFAULT_SEND_DELAY)
    entry_data[IFSEI_CONF_RECONNECT] = entry.options.get(
        IFSEI_CONF_RECONNECT, DEFAULT_RECONNECT
    )
    entry_data[IFSEI_CONF_RECONNECT_DELAY] = entry.options.get(
        IFSEI_CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY
    )

    network_configuration = NetworkConfiguration(
        host,
        port,
        port,
        protocol,
        entry_data[IFSEI_CONF_RECONNECT],
        entry_data[IFSEI_CONF_RECONNECT_DELAY],
    )
    ifsei = IFSEI(network_config=network_configuration)

    try:
        file_path = Path(hass.config.path(), YAML_DEVICES).absolute().as_posix()
        _LOGGER.info("Load devices from file, config path %s", file_path)
        await hass.async_add_executor_job(ifsei.load_devices, file_path)
        _LOGGER.info("Devices loaded")
        if ifsei.device_manager is None:
            _LOGGER.error("Problem loading devices and creating device manager")
            return False
    except vol.Invalid:
        _LOGGER.exception("Configuration error in %s", YAML_DEVICES)
        return False

    try:
        _LOGGER.debug("Trying to connect to ifsei")
        await ifsei.async_connect()
    except (ConnectionRefusedError, TimeoutError) as e:
        msg = "Timed out while trying to connect to %s, error %s"
        raise ConfigEntryNotReady(msg, host, e) from e

    _LOGGER.debug("Connected to host: %s:%s, protocol: %s", host, port, protocol)
    ifsei.set_send_delay(entry_data[CONF_DELAY])

    if not entry.unique_id:
        hass.config_entries.async_update_entry(entry, unique_id=ifsei.get_device_id())

    _async_register_scenario_device(hass, entry_id, ifsei)

    entry_data[CONTROLLER_ENTRY] = ifsei
    entry_data[LIGHTS_ENTRY] = ifsei.device_manager.get_devices_by_type(LIGHT_DEVICES)
    entry_data[COVERS_ENTRY] = ifsei.device_manager.get_devices_by_type(COVER_DEVICES)

    async def update_listener(
        hass: HomeAssistant,  # noqa: ARG001
        entry: ConfigEntry,
    ) -> None:
        """Handle options update."""
        entry_data[CONF_DELAY] = entry.options.get(CONF_DELAY, IFSEI_ATTR_SEND_DELAY)
        entry_data[IFSEI_CONF_RECONNECT] = entry.options.get(IFSEI_CONF_RECONNECT, True)
        entry_data[IFSEI_CONF_RECONNECT_DELAY] = entry.options.get(
            IFSEI_CONF_RECONNECT_DELAY, 5
        )
        ifsei.set_send_delay(entry_data[CONF_DELAY])
        ifsei.set_reconnect_options(
            reconnect=entry_data[IFSEI_CONF_RECONNECT],
            delay=entry_data[IFSEI_CONF_RECONNECT_DELAY],
        )

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


@callback
def _async_register_scenario_device(
    hass: HomeAssistant, config_entry_id: str, ifsei: IFSEI
) -> None:
    """Register the bridge device in the device registry."""
    device_registry = dr.async_get(hass)
    device_args = DeviceInfo(
        name="Scenario IFSEI",
        manufacturer=MANUFACTURER,
        identifiers={(DOMAIN, ifsei.get_device_id())},
        model="IFSEI Classic",
        via_device=(DOMAIN, ifsei.get_device_id()),
        configuration_url="https://scenario.ind.br",
    )

    device_registry.async_get_or_create(**device_args, config_entry_id=config_entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the bridge from a config entry."""
    entry_data = hass.data[DOMAIN].setdefault(entry.entry_id, {})
    ifsei: IFSEI = entry_data[CONTROLLER_ENTRY]
    await ifsei.async_close()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class ScenarioUpdatableEntity(Entity):
    """Base entity for Scenario."""

    _attr_should_poll = False

    def __init__(self, device: Device, ifsei: IFSEI) -> None:
        """Initialize a Scenario entity."""
        self._ifsei = ifsei
        self._device = device
        self._attr_name = device.name
        self._attr_available = ifsei.is_connected
        self._attr_unique_id = device.unique_id
        self._device_name = ifsei.name
        self._device_manufacturer = MANUFACTURER
        self._device_id = ifsei.get_device_id()
        info = DeviceInfo(
            identifiers={(DOMAIN, str(device.unique_id))},
            manufacturer=MANUFACTURER,
            name=self._attr_name,
            via_device=(DOMAIN, str(device.unique_id)),
            suggested_area=device.zone,
        )
        self._attr_device_info = info

    @property
    def available(self) -> bool:
        """Check availability of the device."""
        return self._ifsei.is_connected
