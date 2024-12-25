"""Test the Scenario config flow."""

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.scenario.const import (
    DOMAIN,
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
