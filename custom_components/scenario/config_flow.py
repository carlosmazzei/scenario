"""Config flow for Scenario IFSEI."""

import logging
from ipaddress import AddressValueError, IPv4Address
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_DELAY, CONF_HOST, CONF_PORT, CONF_PROTOCOL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pyscenario.const import IFSEI_ATTR_SEND_DELAY
from pyscenario.ifsei import IFSEI, NetworkConfiguration, Protocol

from .const import (
    CONF_CONTROLLER_UNIQUE_ID,
    DOMAIN,
    IFSEI_CONF_RECONNECT,
    IFSEI_CONF_RECONNECT_DELAY,
)

_LOGGER = logging.getLogger(__name__)

PROTOCOLS = [
    selector.SelectOptionDict(value="TCP", label="TCP"),
    selector.SelectOptionDict(value="UDP", label="UDP"),
]

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT): str,
        vol.Required(CONF_PROTOCOL): selector.SelectSelector(
            selector.SelectSelectorConfig(options=PROTOCOLS),
        ),
    }
)


class ScenarioValidator:
    """Validate Scenario config entries."""

    def __init__(
        self, host: str, port: int, protocol: Protocol, hass: HomeAssistant
    ) -> None:
        """Initialize configuration."""
        self._host = host
        self._port = port
        self._protocol = protocol
        self.hass = hass
        self.ifsei = IFSEI(
            network_config=NetworkConfiguration(
                host, port, port, protocol=Protocol[protocol.upper()]
            )
        )


class ScenarioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Scenario."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            scenario = ScenarioValidator(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_PROTOCOL],
                self.hass,
            )

            # Check if the IP address is a valid IPv4 address.
            try:
                IPv4Address(user_input[CONF_HOST])
            except AddressValueError:
                errors["base"] = "invalid_ip"

            if not errors:
                controller_unique_id = scenario.ifsei.get_device_id()
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=controller_unique_id,
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_PROTOCOL: user_input[CONF_PROTOCOL],
                        CONF_CONTROLLER_UNIQUE_ID: controller_unique_id,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    """Handle a option flow for Scenario."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(
                title="Other options",
                data={
                    CONF_DELAY: user_input[CONF_DELAY],
                    IFSEI_CONF_RECONNECT: user_input[IFSEI_CONF_RECONNECT],
                    IFSEI_CONF_RECONNECT_DELAY: user_input[IFSEI_CONF_RECONNECT_DELAY],
                },
            )

        send_delay_default = self.config_entry.options.get(
            CONF_DELAY, IFSEI_ATTR_SEND_DELAY
        )
        reconnect_default = self.config_entry.options.get(IFSEI_CONF_RECONNECT, True)
        reconnect_delay_default = self.config_entry.options.get(
            IFSEI_CONF_RECONNECT_DELAY, 10
        )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DELAY,
                    default=send_delay_default,
                ): vol.All(cv.positive_float, vol.Clamp(min=0.1, max=0.5)),
                vol.Optional(IFSEI_CONF_RECONNECT, default=reconnect_default): bool,
                vol.Optional(
                    IFSEI_CONF_RECONNECT_DELAY, default=reconnect_delay_default
                ): vol.All(cv.positive_float, vol.Clamp(min=5.0, max=60.0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)


class CannotConnectError(HomeAssistantError):
    """Cannot connect to the device."""
