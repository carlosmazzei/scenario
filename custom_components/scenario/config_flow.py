"""Config flow for Scenario IFSEI."""

import logging
from ipaddress import AddressValueError, IPv4Address
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_DELAY, CONF_HOST, CONF_PORT, CONF_PROTOCOL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pyscenario.ifsei import IFSEI, NetworkConfiguration, Protocol

from .const import (
    CONF_CONTROLLER_UNIQUE_ID,
    DEFAULT_RECONNECT,
    DEFAULT_RECONNECT_DELAY,
    DEFAULT_SEND_DELAY,
    DOMAIN,
    IFSEI_CONF_RECONNECT,
    IFSEI_CONF_RECONNECT_DELAY,
    MAX_PORT_NUMBER,
    MIN_PORT_NUMBER,
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


class ScenarioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Scenario."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Check if the IP address is a valid IPv4 address.
            try:
                IPv4Address(user_input[CONF_HOST])
            except AddressValueError:
                errors["base"] = "invalid_ip"

            # Check if is a valid port number
            try:
                input_port = int(user_input[CONF_PORT])
                if not (MIN_PORT_NUMBER <= input_port <= MAX_PORT_NUMBER):
                    errors["base"] = "invalid_port"
            except ValueError:
                errors["base"] = "invalid_port"

            if not errors:
                ifsei = IFSEI(
                    network_config=NetworkConfiguration(
                        host=user_input[CONF_HOST],
                        tcp_port=user_input[CONF_PORT],
                        udp_port=user_input[CONF_PORT],
                        protocol=Protocol[user_input[CONF_PROTOCOL]],
                    )
                )
                controller_unique_id = ifsei.get_device_id()
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
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return ScenarioOptionsFlowHandler(config_entry)


class ScenarioOptionsFlowHandler(OptionsFlow):
    """Handle a option flow for Scenario."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry: ConfigEntry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_DELAY: user_input[CONF_DELAY],
                    IFSEI_CONF_RECONNECT: user_input[IFSEI_CONF_RECONNECT],
                    IFSEI_CONF_RECONNECT_DELAY: user_input[IFSEI_CONF_RECONNECT_DELAY],
                },
            )

        send_delay_default: float = self.config_entry.options.get(
            CONF_DELAY, DEFAULT_SEND_DELAY
        )
        reconnect_default: bool = self.config_entry.options.get(
            IFSEI_CONF_RECONNECT, DEFAULT_RECONNECT
        )
        reconnect_delay_default: float = self.config_entry.options.get(
            IFSEI_CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY
        )

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DELAY,
                    default=send_delay_default,
                ): vol.All(cv.positive_float, vol.Clamp(min=0.1, max=0.5)),
                vol.Required(IFSEI_CONF_RECONNECT, default=reconnect_default): bool,
                vol.Required(
                    IFSEI_CONF_RECONNECT_DELAY,
                    default=reconnect_delay_default,
                ): vol.All(cv.positive_float, vol.Clamp(min=5.0, max=60.0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=options_schema)
