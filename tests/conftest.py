"""Fixtures for Scenario integration tests."""

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PROTOCOL


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: bool) -> None:  # noqa: ARG001, FBT001
    """Enable custom integrations defined in the test dir."""
    return


@pytest.fixture
def config_data() -> dict[str, str]:
    """Return a sample config data."""
    return {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: "28000",
        CONF_PROTOCOL: "TCP",
    }
