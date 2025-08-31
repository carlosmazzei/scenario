"""Unit tests for the scenario integration init."""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_DELAY
from homeassistant.core import HomeAssistant
from pyscenario.ifsei import IFSEI
from pyscenario.manager import Device, DeviceManager
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scenario import (
    ScenarioUpdatableEntity,
)
from custom_components.scenario.const import (
    CONTROLLER_ENTRY,
    COVERS_ENTRY,
    DEFAULT_SEND_DELAY,
    DOMAIN,
    IFSEI_CONF_RECONNECT,
    IFSEI_CONF_RECONNECT_DELAY,
    LIGHTS_ENTRY,
)


@pytest.fixture
def mock_ifsei() -> MagicMock:
    """Mock IFSEI instance with default behaviors."""
    mock = MagicMock(spec=IFSEI)
    mock.is_connected = True
    mock.name = "Scenario IFSEI"
    mock.async_close = AsyncMock()
    mock.async_connect = AsyncMock()
    mock.load_devices = MagicMock()
    mock.set_send_delay = MagicMock()
    mock.set_reconnect_options = MagicMock()
    mock.get_device_id.return_value = "test_device_id"

    device_manager = MagicMock(spec=DeviceManager)
    device_manager.get_devices_by_type.return_value = ["mock_device_list"]
    mock.device_manager = device_manager
    return mock


@pytest.fixture
def mock_config_entry_missing_id() -> MockConfigEntry:
    """Set MockConfigEntry that starts with no unique_id set."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Scenario Test Entry",
        data={
            "host": "127.0.0.1",
            "port": 1234,
            "protocol": "TCP",
        },
        options={},
        entry_id="test_entry_id",
        unique_id=None,
    )


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Set standard MockConfigEntry with an existing unique_id."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Scenario Test Entry",
        data={
            "host": "127.0.0.1",
            "port": 1234,
            "protocol": "TCP",
        },
        options={},
        entry_id="test_entry_id",
        unique_id="already_has_id",
    )


@pytest.mark.asyncio
async def test_async_setup_entry_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """Test a successful setup entry."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch("custom_components.scenario.IFSEI", return_value=mock_ifsei),
        patch("custom_components.scenario.Path") as mock_path,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=None,
        ) as mock_forward,
    ):
        # Avoid real file usage
        mock_path.return_value.absolute.return_value.as_posix.return_value = (
            "/fake/path"
        )

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
    mock_ifsei.load_devices.assert_called_once_with("/fake/path")
    mock_ifsei.async_connect.assert_called_once()
    mock_ifsei.set_send_delay.assert_called_once_with(DEFAULT_SEND_DELAY)
    connect_index = mock_ifsei.mock_calls.index(call.async_connect())
    delay_index = mock_ifsei.mock_calls.index(call.set_send_delay(DEFAULT_SEND_DELAY))
    assert connect_index < delay_index

    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert CONTROLLER_ENTRY in entry_data
    assert LIGHTS_ENTRY in entry_data
    assert COVERS_ENTRY in entry_data
    mock_forward.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_vol_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """Test Voluptuous error when loading devices."""
    mock_config_entry.add_to_hass(hass)
    mock_ifsei.load_devices.side_effect = vol.Invalid("Invalid config")

    with patch("custom_components.scenario.IFSEI", return_value=mock_ifsei):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # The entry setup should fail
    assert mock_config_entry.state == ConfigEntryState.SETUP_ERROR


@pytest.mark.asyncio
async def test_async_setup_entry_device_manager_none(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """Test setup fails if device_manager is None."""
    mock_config_entry.add_to_hass(hass)
    mock_ifsei.device_manager = None

    with patch("custom_components.scenario.IFSEI", return_value=mock_ifsei):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Should fail setup
    assert mock_config_entry.state == ConfigEntryState.SETUP_ERROR


@pytest.mark.asyncio
async def test_async_setup_entry_connection_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """Test connection error => ConfigEntryNotReady => state=SETUP_RETRY."""
    mock_config_entry.add_to_hass(hass)
    mock_ifsei.async_connect.side_effect = ConnectionRefusedError("Connection refused")

    with patch("custom_components.scenario.IFSEI", return_value=mock_ifsei):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_async_setup_entry_timeout_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """Test timeout => ConfigEntryNotReady => state=SETUP_RETRY."""
    mock_config_entry.add_to_hass(hass)
    mock_ifsei.async_connect.side_effect = TimeoutError("Timeout")

    with patch("custom_components.scenario.IFSEI", return_value=mock_ifsei):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_async_setup_entry_updates_entry_unique_id(
    hass: HomeAssistant,
    mock_config_entry_missing_id: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """
    Test setup config entry.

    Test that if entry.unique_id is not set, it is updated with ifsei.get_device_id().
    """
    cfg_entry = mock_config_entry_missing_id
    cfg_entry.add_to_hass(hass)

    with (
        patch("custom_components.scenario.IFSEI", return_value=mock_ifsei),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=None,
        ),
    ):
        await hass.config_entries.async_setup(cfg_entry.entry_id)
        await hass.async_block_till_done()

    # Should be loaded and unique_id updated
    assert cfg_entry.state == ConfigEntryState.LOADED
    assert cfg_entry.unique_id == "test_device_id"


@pytest.mark.asyncio
async def test_async_setup_entry_update_listener(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """Test that the update_listener updates IFSEI options."""
    mock_config_entry.add_to_hass(hass)

    # 1) Setup entry
    with (
        patch("custom_components.scenario.IFSEI", return_value=mock_ifsei),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=None,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED

    # 2) The integration expects keys: CONF_DELAY, IFSEI_CONF_RECONNECT,
    #    IFSEI_CONF_RECONNECT_DELAY by default (like "delay",
    #    "ifsei_reconnect", "ifsei_reconnect_delay" won't match).
    #    So let's supply the correct keys:
    new_options = {
        CONF_DELAY: 999,
        IFSEI_CONF_RECONNECT: False,
        IFSEI_CONF_RECONNECT_DELAY: 30,
    }

    # Official way to update the entry
    hass.config_entries.async_update_entry(mock_config_entry, options=new_options)
    await hass.async_block_till_done()

    # The update_listener is supposed to set ifsei.set_send_delay(...)
    # and ifsei.set_reconnect_options(...) with the new values.
    mock_ifsei.set_send_delay.assert_called_with(999)
    mock_ifsei.set_reconnect_options.assert_called_with(reconnect=False, delay=30)


@pytest.mark.asyncio
async def test_async_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """Test unloading a config entry via hass.config_entries.async_unload(...)."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch("custom_components.scenario.IFSEI", return_value=mock_ifsei),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=None,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED

    # Unload using official approach
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Now it should be not_loaded
    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
    mock_ifsei.async_close.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_failure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
) -> None:
    """Test an unsuccessful unload (platform unloading fails)."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch("custom_components.scenario.IFSEI", return_value=mock_ifsei),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=None,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED

    # Return False from async_unload_platforms
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=False,
    ):
        await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # The integration function might have returned True,
    # but HA sees partial unload => STILL loaded
    assert mock_config_entry.state == ConfigEntryState.LOADED
    mock_ifsei.async_close.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_exception(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ifsei: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test an unsuccessful unload (exception raised by ifsei.async_close).

    Test that if an exception is raised by ifsei.async_close,
    Home Assistant logs an error and sets the entry to FAILED_UNLOAD.
    It does NOT re-raise the exception to the test.
    """
    mock_config_entry.add_to_hass(hass)

    with (
        patch("custom_components.scenario.IFSEI", return_value=mock_ifsei),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=None,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED

    # Force an exception on close
    mock_ifsei.async_close.side_effect = Exception("Test error")

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        # HA will call async_unload_entry ->
        # which calls ifsei.async_close -> raises "Test error"
        # HA catches it, logs, and sets entry to FAILED_UNLOAD,
        # so the exception won't bubble up here
        await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # The final state should be FAILED_UNLOAD since the exception was caught by HA
    assert mock_config_entry.state == ConfigEntryState.FAILED_UNLOAD
    # We can also confirm the error message was logged
    assert "Test error" in caplog.text


@pytest.mark.asyncio
async def test_scenario_updatable_entity_available() -> None:
    """Test the 'available' property reflects IFSEI connection state."""
    device = MagicMock(spec=Device)
    device.name = "Test Device"
    device.unique_id = "test_device_unique_id"
    device.zone = "Test Zone"

    mock_ifsei = MagicMock(spec=IFSEI)
    mock_ifsei.is_connected = True
    mock_ifsei.name = "Scenario IFSEI"
    mock_ifsei.get_device_id.return_value = "ifsei_device_id"

    entity = ScenarioUpdatableEntity(device, mock_ifsei)
    assert entity.available

    mock_ifsei.is_connected = False
    assert not entity.available


@pytest.mark.asyncio
async def test_scenario_updatable_entity_device_info() -> None:
    """Test that device info is properly assigned."""
    device = MagicMock(spec=Device)
    device.name = "Test Device"
    device.unique_id = "test_device_unique_id"
    device.zone = "Test Zone"

    mock_ifsei = MagicMock(spec=IFSEI)
    mock_ifsei.is_connected = True
    mock_ifsei.name = "Scenario IFSEI"
    mock_ifsei.get_device_id.return_value = "ifsei_device_id"

    entity = ScenarioUpdatableEntity(device, mock_ifsei)
    device_info = entity.device_info
    assert device_info is not None

    assert device_info.get("identifiers") == {("scenario", "test_device_unique_id")}
    assert device_info.get("via_device") == ("scenario", "test_device_unique_id")
    assert device_info.get("name") == "Test Device"
    assert device_info.get("manufacturer") == entity._device_manufacturer
