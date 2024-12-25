"""Test the Scenario config flow."""

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_DELAY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scenario.const import (
    CONF_CONTROLLER_UNIQUE_ID,
    DOMAIN,
    IFSEI_CONF_RECONNECT,
    IFSEI_CONF_RECONNECT_DELAY,
)


@pytest.mark.asyncio
async def test_form_invalid_ip(hass: HomeAssistant) -> None:
    """Test we handle invalid IP."""
    _result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        {
            "host": "invalid_ip",
            "port": "28000",
            "protocol": "TCP",
        },
    )

    if result.get("errors", {}) != {"base": "invalid_ip"}:
        msg = "Expected invalid IP error."
        raise ValueError(msg)


@pytest.mark.asyncio
async def test_form_invalid_port(hass: HomeAssistant) -> None:
    """Test we handle invalid port."""
    _result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        {
            "host": "192.168.15.20",
            "port": "invalid_port",
            "protocol": "TCP",
        },
    )

    if result.get("errors", {}) != {"base": "invalid_port"}:
        msg = "Expected invalid port error."
        raise ValueError(msg)


@pytest.mark.asyncio
async def test_form(hass: HomeAssistant, config_data: dict[str, str]) -> None:
    """Test we can finish a config flow."""
    _result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        config_data,
    )

    if result.get("type", {}) != "create_entry":
        msg = "Expected create entry."
        raise ValueError(msg)


@pytest.mark.asyncio
async def test_form_port_out_of_range(hass: HomeAssistant) -> None:
    """Test we handle port number out of range."""
    _result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        {
            "host": "192.168.15.20",
            "port": "70000",  # Porta fora do intervalo válido
            "protocol": "TCP",
        },
    )

    if result.get("errors", {}) != {"base": "invalid_port"}:
        msg = "Expected invalid port error."
        raise ValueError(msg)


@pytest.mark.asyncio
async def test_options_flow(hass: HomeAssistant) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "192.168.15.20",
            "port": "28000",
            "protocol": "TCP",
            CONF_CONTROLLER_UNIQUE_ID: "test_id",
        },
        options={
            CONF_DELAY: 0.2,
            IFSEI_CONF_RECONNECT: True,
            IFSEI_CONF_RECONNECT_DELAY: 30.0,
        },
    )
    config_entry.add_to_hass(hass)

    # Test options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    if result.get("type", {}) != FlowResultType.FORM:
        msg = "Expected form."
        raise ValueError(msg)

    if result.get("step_id", {}) != "init":
        msg = "Expected init step."
        raise ValueError(msg)

    # Test updating options flow
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_DELAY: 0.3,
            IFSEI_CONF_RECONNECT: False,
            IFSEI_CONF_RECONNECT_DELAY: 15.0,
        },
    )

    if result.get("type", {}) != FlowResultType.CREATE_ENTRY:
        msg = "Expected create entry."
        raise ValueError(msg)

    if config_entry.options != {
        CONF_DELAY: 0.3,
        IFSEI_CONF_RECONNECT: False,
        IFSEI_CONF_RECONNECT_DELAY: 15.0,
    }:
        msg = "Expected options updated."
        raise ValueError(msg)
