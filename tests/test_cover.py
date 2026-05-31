"""Tests for Scenario Cover."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.cover import CoverDeviceClass, CoverEntityFeature
from homeassistant.core import HomeAssistant
from pyscenario.const import (
    IFSEI_ATTR_AVAILABLE,
    IFSEI_ATTR_COMMAND,
    IFSEI_ATTR_SCENE_ACTIVE,
    IFSEI_ATTR_SCENE_INACTIVE,
    IFSEI_ATTR_STATE,
    IFSEI_COVER_DOWN,
    IFSEI_COVER_STOP,
    IFSEI_COVER_UP,
)

from custom_components.scenario.const import CONTROLLER_ENTRY, COVERS_ENTRY, DOMAIN
from custom_components.scenario.cover import ScenarioCover, async_setup_entry

# Test constants for cover command values
EXPECTED_UP_VALUE = 2
EXPECTED_DOWN_VALUE = 3
EXPECTED_STOP_VALUE = 4


@pytest.fixture
def mock_cover() -> MagicMock:
    """Create a mock cover fixture."""
    cover = MagicMock()
    cover.unique_id = "test_cover_unique_id"
    cover.up = "0002"
    cover.down = "0003"
    cover.stop = "0004"
    cover.module = None
    cover.open_channel = None
    cover.close_channel = None
    return cover


@pytest.fixture
def mock_ifsei() -> MagicMock:
    """Create a mock IFSEI fixture."""
    ifsei = MagicMock()
    ifsei.async_update_cover_state = AsyncMock()
    ifsei.is_connected = True
    return ifsei


@pytest.fixture
async def scenario_cover(
    hass: HomeAssistant, mock_cover: MagicMock, mock_ifsei: MagicMock
) -> ScenarioCover:
    """Create a ScenarioCover instance for testing."""
    entity = ScenarioCover(mock_cover, mock_ifsei)
    entity.hass = hass
    entity.entity_id = "cover.test_cover"
    await entity.async_added_to_hass()
    return entity


@pytest.mark.asyncio
async def test_async_open_cover(scenario_cover: ScenarioCover) -> None:
    """Test opening the cover with a valid unique_id."""
    await scenario_cover.async_open_cover()
    scenario_cover.ifsei.async_update_cover_state.assert_called_once_with(
        scenario_cover.unique_id, int(scenario_cover.up)
    )
    # Verify the exact values
    call_args = scenario_cover.ifsei.async_update_cover_state.call_args
    assert call_args[0][0] == "test_cover_unique_id"
    assert call_args[0][1] == EXPECTED_UP_VALUE


@pytest.mark.asyncio
async def test_async_close_cover(scenario_cover: ScenarioCover) -> None:
    """Test closing the cover with a valid unique_id."""
    await scenario_cover.async_close_cover()
    scenario_cover.ifsei.async_update_cover_state.assert_called_once_with(
        scenario_cover.unique_id, int(scenario_cover.down)
    )
    # Verify the exact values
    call_args = scenario_cover.ifsei.async_update_cover_state.call_args
    assert call_args[0][0] == "test_cover_unique_id"
    assert call_args[0][1] == EXPECTED_DOWN_VALUE


@pytest.mark.asyncio
async def test_async_stop_cover(scenario_cover: ScenarioCover) -> None:
    """Test stopping the cover with a valid unique_id."""
    await scenario_cover.async_stop_cover()
    scenario_cover.ifsei.async_update_cover_state.assert_called_once_with(
        scenario_cover.unique_id, int(scenario_cover.stop)
    )
    # Verify the exact values
    call_args = scenario_cover.ifsei.async_update_cover_state.call_args
    assert call_args[0][0] == "test_cover_unique_id"
    assert call_args[0][1] == EXPECTED_STOP_VALUE


@pytest.mark.asyncio
async def test_missing_unique_id_for_commands(
    hass: HomeAssistant, mock_cover: MagicMock, mock_ifsei: MagicMock
) -> None:
    """
    Test scenario where unique_id is None.

    Commands should log a warning instead of calling async_update_cover_state.
    """
    mock_cover.unique_id = None
    entity = ScenarioCover(mock_cover, mock_ifsei)
    entity.hass = hass

    with patch("logging.Logger.warning") as mock_log:
        await entity.async_open_cover()
        mock_log.assert_any_call("Missing device unique id")

    with patch("logging.Logger.warning") as mock_log:
        await entity.async_close_cover()
        mock_log.assert_any_call("Missing device unique id")

    with patch("logging.Logger.warning") as mock_log:
        await entity.async_stop_cover()
        mock_log.assert_any_call("Missing device unique id")

    mock_ifsei.async_update_cover_state.assert_not_called()


@pytest.mark.asyncio
async def test_async_will_remove_from_hass(scenario_cover: ScenarioCover) -> None:
    """Test removing the entity from hass."""
    await scenario_cover.async_will_remove_from_hass()
    scenario_cover._device.remove_subscriber.assert_called_once()


def test_properties(scenario_cover: ScenarioCover) -> None:
    """Test entity properties."""
    assert scenario_cover.supported_features == (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )
    assert scenario_cover.device_class == CoverDeviceClass.SHADE
    assert scenario_cover.assumed_state is True
    # No relay feedback: is_closed returns _attr_is_closed (None initially)
    assert scenario_cover.is_closed is None
    # Verify individual properties
    assert scenario_cover.up == "0002"
    assert scenario_cover.down == "0003"
    assert scenario_cover.stop == "0004"
    assert scenario_cover.unique_id == "test_cover_unique_id"


def test_update_callback_down_active(scenario_cover: ScenarioCover) -> None:
    """
    Test update callback.

    Test update callback when the cover command is 'down'
    and state is 'scene active' -> sets _attr_is_closed to True.
    Only applies to covers without relay feedback.
    """
    with patch.object(scenario_cover, "async_write_ha_state") as mock_write_state:
        scenario_cover.async_update_callback(
            **{
                IFSEI_ATTR_AVAILABLE: True,
                IFSEI_ATTR_COMMAND: IFSEI_COVER_DOWN,
                IFSEI_ATTR_STATE: IFSEI_ATTR_SCENE_ACTIVE,
            }
        )
        assert scenario_cover._attr_is_closed is True
        assert scenario_cover.available is True
        mock_write_state.assert_called_once()


def test_update_callback_up_active(scenario_cover: ScenarioCover) -> None:
    """
    Test update callback.

    Test update callback when the cover command is 'up'
    and state is 'scene active' -> sets is_closed to False.
    """
    with patch.object(scenario_cover, "async_write_ha_state") as mock_write_state:
        scenario_cover.async_update_callback(
            **{
                IFSEI_ATTR_AVAILABLE: True,
                IFSEI_ATTR_COMMAND: IFSEI_COVER_UP,
                IFSEI_ATTR_STATE: IFSEI_ATTR_SCENE_ACTIVE,
            }
        )
        assert scenario_cover.is_closed is False
        assert scenario_cover.available is True
        mock_write_state.assert_called_once()


def test_update_callback_stop_active(scenario_cover: ScenarioCover) -> None:
    """
    Test update callback.

    Test update callback when command is 'stop' and state is
    'scene active' or 'scene inactive' -> set _attr_is_closing/_attr_is_opening = False.
    Only applies to covers without relay feedback.
    """
    # Force _attr_is_closing/_attr_is_opening to True for test
    scenario_cover._attr_is_closing = True
    scenario_cover._attr_is_opening = True

    with patch.object(scenario_cover, "async_write_ha_state") as mock_write_state:
        scenario_cover.async_update_callback(
            **{
                IFSEI_ATTR_AVAILABLE: True,
                IFSEI_ATTR_COMMAND: IFSEI_COVER_STOP,
                IFSEI_ATTR_STATE: IFSEI_ATTR_SCENE_ACTIVE,
            }
        )
        assert scenario_cover._attr_is_closing is False
        assert scenario_cover._attr_is_opening is False
        mock_write_state.assert_called_once()

    scenario_cover._attr_is_closing = True
    scenario_cover._attr_is_opening = True

    with patch.object(scenario_cover, "async_write_ha_state") as mock_write_state:
        scenario_cover.async_update_callback(
            **{
                IFSEI_ATTR_AVAILABLE: True,
                IFSEI_ATTR_COMMAND: IFSEI_COVER_STOP,
                IFSEI_ATTR_STATE: IFSEI_ATTR_SCENE_INACTIVE,
            }
        )
        assert scenario_cover._attr_is_closing is False
        assert scenario_cover._attr_is_opening is False
        mock_write_state.assert_called_once()


def test_update_callback_only_availability(scenario_cover: ScenarioCover) -> None:
    """Test update callback when only availability changes."""
    with patch.object(scenario_cover, "async_write_ha_state") as mock_write_state:
        scenario_cover.async_update_callback(**{IFSEI_ATTR_AVAILABLE: False})
        # Note: _attr_available is updated but available property uses _ifsei
        assert scenario_cover._attr_available is False
        mock_write_state.assert_called_once()


def test_update_callback_none_values(scenario_cover: ScenarioCover) -> None:
    """Test update callback with None values doesn't change state or write HA state."""
    initial_closed_state = scenario_cover.is_closed
    with patch.object(scenario_cover, "async_write_ha_state") as mock_write_state:
        scenario_cover.async_update_callback(
            **{
                IFSEI_ATTR_COMMAND: None,
                IFSEI_ATTR_STATE: None,
            }
        )
        assert scenario_cover.is_closed == initial_closed_state
        mock_write_state.assert_not_called()


def test_update_callback_command_without_state(scenario_cover: ScenarioCover) -> None:
    """Test update callback with command but no state does not write HA state."""
    initial_closed_state = scenario_cover.is_closed
    with patch.object(scenario_cover, "async_write_ha_state") as mock_write_state:
        scenario_cover.async_update_callback(**{IFSEI_ATTR_COMMAND: IFSEI_COVER_DOWN})
        assert scenario_cover.is_closed == initial_closed_state
        mock_write_state.assert_not_called()


@pytest.fixture
def mock_cover_with_relay() -> MagicMock:
    """Create a mock cover fixture with relay feedback configured."""
    cover = MagicMock()
    cover.unique_id = "test_cover_relay_id"
    cover.up = "0008"
    cover.down = "0010"
    cover.stop = "0009"
    cover.module = 0
    cover.open_channel = 5
    cover.close_channel = 6
    return cover


@pytest.fixture
async def scenario_cover_relay(
    hass: HomeAssistant, mock_cover_with_relay: MagicMock, mock_ifsei: MagicMock
) -> ScenarioCover:
    """Create a ScenarioCover with relay feedback for testing."""
    entity = ScenarioCover(mock_cover_with_relay, mock_ifsei)
    entity.hass = hass
    entity.entity_id = "cover.test_cover_relay"
    await entity.async_added_to_hass()
    return entity


def test_properties_with_relay(scenario_cover_relay: ScenarioCover) -> None:
    """Test properties for a cover with relay feedback."""
    assert scenario_cover_relay.supported_features == (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )
    assert (
        not hasattr(scenario_cover_relay, "assumed_state")
        or not scenario_cover_relay.assumed_state
    )
    assert scenario_cover_relay.current_cover_position == 50  # noqa: PLR2004
    assert scenario_cover_relay.is_opening is False
    assert scenario_cover_relay.is_closing is False
    assert scenario_cover_relay.is_closed is False


def test_open_relay_on(scenario_cover_relay: ScenarioCover) -> None:
    """Test open_relay=100 sets is_opening and records timestamp."""
    with patch.object(scenario_cover_relay, "async_write_ha_state") as mock_write:
        scenario_cover_relay.async_update_callback(open_relay=100)
        assert scenario_cover_relay.is_opening is True
        assert scenario_cover_relay.is_closing is False
        assert scenario_cover_relay._last_relay_on_time is not None
        mock_write.assert_called_once()


def test_open_relay_off_updates_position(scenario_cover_relay: ScenarioCover) -> None:
    """Test open_relay=0 after being active calculates position delta."""
    scenario_cover_relay._current_position = 0
    scenario_cover_relay._is_opening = True
    scenario_cover_relay._last_relay_on_time = (
        scenario_cover_relay._travel_time
    )  # fake start

    with (
        patch("custom_components.scenario.cover.time.time") as mock_time,
        patch.object(scenario_cover_relay, "async_write_ha_state"),
    ):
        mock_time.return_value = scenario_cover_relay._travel_time + 15  # 15s elapsed
        scenario_cover_relay.async_update_callback(open_relay=0)

    # 15s / 30s * 100 = 50%
    assert scenario_cover_relay._current_position == 50  # noqa: PLR2004
    assert scenario_cover_relay.is_opening is False
    assert scenario_cover_relay._last_relay_on_time is None


def test_close_relay_on(scenario_cover_relay: ScenarioCover) -> None:
    """Test close_relay=100 sets is_closing and records timestamp."""
    with patch.object(scenario_cover_relay, "async_write_ha_state") as mock_write:
        scenario_cover_relay.async_update_callback(close_relay=100)
        assert scenario_cover_relay.is_closing is True
        assert scenario_cover_relay.is_opening is False
        assert scenario_cover_relay._last_relay_on_time is not None
        mock_write.assert_called_once()


def test_close_relay_off_updates_position(scenario_cover_relay: ScenarioCover) -> None:
    """Test close_relay=0 after being active calculates position delta."""
    scenario_cover_relay._current_position = 100
    scenario_cover_relay._is_closing = True
    scenario_cover_relay._last_relay_on_time = scenario_cover_relay._travel_time

    with (
        patch("custom_components.scenario.cover.time.time") as mock_time,
        patch.object(scenario_cover_relay, "async_write_ha_state"),
    ):
        mock_time.return_value = (
            scenario_cover_relay._travel_time + 30
        )  # 30s = full close
        scenario_cover_relay.async_update_callback(close_relay=0)

    assert scenario_cover_relay._current_position == 0
    assert scenario_cover_relay.is_closing is False
    assert scenario_cover_relay.is_closed is True


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_ifsei: MagicMock) -> None:
    """Test the async_setup_entry function adds ScenarioCovers to HA."""
    # Arrange
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"

    mock_cover_1 = MagicMock()
    mock_cover_2 = MagicMock()
    covers = [mock_cover_1, mock_cover_2]

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = {
        COVERS_ENTRY: covers,
        CONTROLLER_ENTRY: mock_ifsei,
    }

    mock_add_entities = MagicMock()

    # Act
    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Assert
    # We expect one ScenarioCover entity per cover in 'covers'
    assert mock_add_entities.call_count == 1
    entity_generator = mock_add_entities.call_args[0][0]
    entity_list = list(entity_generator)
    assert len(entity_list) == 2  # noqa: PLR2004

    for cover_entity in entity_list:
        assert isinstance(cover_entity, ScenarioCover)
        assert cover_entity.ifsei == mock_ifsei
        # Each cover entity's _device should be in the covers list
        assert cover_entity._device in covers
