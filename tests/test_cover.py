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


@pytest.fixture
def mock_cover() -> MagicMock:
    """Create a mock cover fixture."""
    cover = MagicMock()
    cover.unique_id = "test_cover_unique_id"
    cover.up = "0002"
    cover.down = "0003"
    cover.stop = "0004"
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


@pytest.mark.asyncio
async def test_async_close_cover(scenario_cover: ScenarioCover) -> None:
    """Test closing the cover with a valid unique_id."""
    await scenario_cover.async_close_cover()
    scenario_cover.ifsei.async_update_cover_state.assert_called_once_with(
        scenario_cover.unique_id, int(scenario_cover.down)
    )


@pytest.mark.asyncio
async def test_async_stop_cover(scenario_cover: ScenarioCover) -> None:
    """Test stopping the cover with a valid unique_id."""
    await scenario_cover.async_stop_cover()
    scenario_cover.ifsei.async_update_cover_state.assert_called_once_with(
        scenario_cover.unique_id, int(scenario_cover.stop)
    )


@pytest.mark.asyncio
async def test_missing_unique_id_for_commands(
    hass: HomeAssistant, mock_cover: MagicMock, mock_ifsei: MagicMock
) -> None:
    """
    Test scenario where unique_id is None.

    Commands should log a debug message instead of calling async_update_cover_state.
    """
    mock_cover.unique_id = None
    entity = ScenarioCover(mock_cover, mock_ifsei)
    entity.hass = hass

    with patch("logging.Logger.debug") as mock_log:
        await entity.async_open_cover()
        mock_log.assert_any_call("Missing device unique id")

    with patch("logging.Logger.debug") as mock_log:
        await entity.async_close_cover()
        mock_log.assert_any_call("Missing device unique id")

    with patch("logging.Logger.debug") as mock_log:
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
    # Initially True, as set in __init__:
    assert scenario_cover.is_closed is True


def test_update_callback_down_active(scenario_cover: ScenarioCover) -> None:
    """
    Test update callback.

    Test update callback when the cover command is 'down'
    and state is 'scene active' -> sets is_closed to True.
    """
    scenario_cover.async_update_callback(
        **{
            IFSEI_ATTR_AVAILABLE: True,
            IFSEI_ATTR_COMMAND: IFSEI_COVER_DOWN,
            IFSEI_ATTR_STATE: IFSEI_ATTR_SCENE_ACTIVE,
        }
    )
    assert scenario_cover.is_closed is True
    assert scenario_cover.available is True


def test_update_callback_up_active(scenario_cover: ScenarioCover) -> None:
    """
    Test update callback.

    Test update callback when the cover command is 'up'
    and state is 'scene active' -> sets is_closed to False.
    """
    scenario_cover.async_update_callback(
        **{
            IFSEI_ATTR_AVAILABLE: True,
            IFSEI_ATTR_COMMAND: IFSEI_COVER_UP,
            IFSEI_ATTR_STATE: IFSEI_ATTR_SCENE_ACTIVE,
        }
    )
    assert scenario_cover.is_closed is False
    assert scenario_cover.available is True


def test_update_callback_stop_active(scenario_cover: ScenarioCover) -> None:
    """
    Test update callback.

    Test update callback when command is 'stop' and state is
    'scene active' or 'scene inactive' -> set is_closing/is_opening = False.
    """
    # Force is_closing/is_opening to True for test
    scenario_cover._attr_is_closing = True
    scenario_cover._attr_is_opening = True

    scenario_cover.async_update_callback(
        **{
            IFSEI_ATTR_AVAILABLE: True,
            IFSEI_ATTR_COMMAND: IFSEI_COVER_STOP,
            IFSEI_ATTR_STATE: IFSEI_ATTR_SCENE_ACTIVE,
        }
    )
    assert scenario_cover._attr_is_closing is False
    assert scenario_cover._attr_is_opening is False

    scenario_cover._attr_is_closing = True
    scenario_cover._attr_is_opening = True

    scenario_cover.async_update_callback(
        **{
            IFSEI_ATTR_AVAILABLE: True,
            IFSEI_ATTR_COMMAND: IFSEI_COVER_STOP,
            IFSEI_ATTR_STATE: IFSEI_ATTR_SCENE_INACTIVE,
        }
    )
    assert scenario_cover._attr_is_closing is False
    assert scenario_cover._attr_is_opening is False


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
