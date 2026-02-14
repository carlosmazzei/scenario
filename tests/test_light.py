"""Tests for the Scenario Light platform."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.light import (
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyscenario.const import IFSEI_ATTR_RED

from custom_components.scenario.const import (
    CONTROLLER_ENTRY,
    DOMAIN,
    LIGHTS_ENTRY,
)
from custom_components.scenario.light import (
    ScenarioLight,
    async_setup_entry,
    to_hass_level,
    to_scenario_level,
)

# Test constants for RGBW color values
UNCHANGED_GREEN_VALUE = 50
UNCHANGED_BLUE_VALUE = 25


@pytest.fixture
def mock_light() -> Mock:
    """Create a mock Scenario Light."""
    light = Mock()
    light.zone = "Living Room"
    light.address = [{"isDimmeable": True}]
    light.get_is_rgb = Mock(return_value=True)
    light.add_subscriber = Mock()
    light.remove_subscriber = Mock()
    light.unique_id = "test_light_unique_id"
    return light


@pytest.fixture
def mock_ifsei() -> Mock:
    """Create a mock IFSEI controller."""
    ifsei = Mock()
    ifsei.is_connected = True
    ifsei.device_manager = Mock()
    ifsei.async_update_light_state = AsyncMock()
    return ifsei


@pytest.fixture
async def light_entity(
    hass: HomeAssistant, mock_light: Mock, mock_ifsei: Mock
) -> ScenarioLight:
    """Create a light entity fixture."""
    light = ScenarioLight(mock_light, mock_ifsei)
    light.hass = hass
    light.entity_id = "light.test_light"
    light._attr_unique_id = "test_light_unique_id"
    light.platform = Mock()
    light.platform.platform_name = "light"

    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain="light",
        platform="scenario",
        unique_id="test_light_unique_id",
    )

    await light.async_added_to_hass()
    await hass.async_block_till_done()
    return light


async def test_light_setup(light_entity: ScenarioLight) -> None:
    """Test light setup."""
    assert light_entity.available is True
    assert light_entity.color_mode == ColorMode.RGBW
    assert light_entity.supported_color_modes == {ColorMode.RGBW}
    assert light_entity.brightness == 0
    assert light_entity.rgbw_color == (0, 0, 0, 0)


async def test_light_setup_dimmable_non_rgb(
    hass: HomeAssistant, mock_light: Mock, mock_ifsei: Mock
) -> None:
    """Test light setup for dimmable non-RGB light."""
    mock_light.get_is_rgb.return_value = False
    light = ScenarioLight(mock_light, mock_ifsei)
    light.hass = hass
    light.platform = Mock()
    light.platform.platform_name = "light"

    assert light.color_mode == ColorMode.BRIGHTNESS
    assert light.supported_color_modes == {ColorMode.BRIGHTNESS}


async def test_light_setup_non_dimmable(
    hass: HomeAssistant, mock_light: Mock, mock_ifsei: Mock
) -> None:
    """Test light setup for non-dimmable light."""
    mock_light.get_is_rgb.return_value = False
    mock_light.address = [{"isDimmeable": False}]
    light = ScenarioLight(mock_light, mock_ifsei)
    light.hass = hass
    light.platform = Mock()
    light.platform.platform_name = "light"

    assert light.color_mode == ColorMode.ONOFF
    assert light.supported_color_modes == {ColorMode.ONOFF}


async def test_light_turn_on(
    hass: HomeAssistant, light_entity: ScenarioLight, mock_ifsei: Mock
) -> None:
    """Test turning on the light."""
    await light_entity.async_turn_on()
    await hass.async_block_till_done()

    mock_ifsei.async_update_light_state.assert_called_once()
    call_args = mock_ifsei.async_update_light_state.call_args[0][1]
    assert call_args == [0, 0, 0, 100]  # 255 converted to scenario level (100)


async def test_light_turn_on_with_brightness(
    hass: HomeAssistant, light_entity: ScenarioLight, mock_ifsei: Mock
) -> None:
    """Test turning on the light with brightness."""
    await light_entity.async_turn_on(brightness=128)  # Half brightness
    await hass.async_block_till_done()

    mock_ifsei.async_update_light_state.assert_called_once()
    call_args = mock_ifsei.async_update_light_state.call_args[0][1]
    assert call_args == [0, 0, 0, 50]  # 128 converted to scenario level (50)


async def test_light_turn_on_with_rgbw(
    hass: HomeAssistant, light_entity: ScenarioLight, mock_ifsei: Mock
) -> None:
    """Test turning on the light with RGBW color."""
    await light_entity.async_turn_on(brightness=255, rgbw_color=(255, 128, 0, 255))
    await hass.async_block_till_done()

    mock_ifsei.async_update_light_state.assert_called_once()
    call_args = mock_ifsei.async_update_light_state.call_args[0][1]
    assert call_args == [100, 50, 0, 100]  # RGB values converted to scenario levels


async def test_light_turn_off(
    hass: HomeAssistant, light_entity: Mock, mock_ifsei: Mock
) -> None:
    """Test turning off the light."""
    await light_entity.async_turn_off()
    await hass.async_block_till_done()

    mock_ifsei.async_update_light_state.assert_called_once()
    call_args = mock_ifsei.async_update_light_state.call_args[0][1]
    assert call_args == [0, 0, 0, 0]


async def test_update_callback(
    hass: HomeAssistant, light_entity: Mock, mock_ifsei: Mock
) -> None:
    """Test update callback with various attributes."""
    # Set up the entity and platform
    light_entity.platform = Mock()
    light_entity.platform.platform_name = "light"

    # Test initial state - should be available due to ifsei.is_connected = True
    assert light_entity.available is True

    # Set initial brightness to 0
    light_entity._attr_brightness = 0
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.brightness == 0

    # Test brightness update
    light_entity._attr_brightness = to_hass_level(50)  # Set directly
    light_entity.async_update_callback(brightness=50)  # This updates state
    await hass.async_block_till_done()
    assert light_entity.brightness == to_hass_level(50)

    # Test availability changes
    mock_ifsei.is_connected = False
    light_entity._attr_available = True
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()

    light_entity.async_update_callback(available=False)
    await hass.async_block_till_done()
    assert light_entity.available is False

    # Test RGBW update with availability restore
    mock_ifsei.is_connected = True
    light_entity._attr_available = True

    # Set expected values
    hass_red = to_hass_level(100)
    hass_green = to_hass_level(75)
    hass_blue = to_hass_level(25)
    hass_white = to_hass_level(100)
    expected_rgbw = (hass_red, hass_green, hass_blue, hass_white)

    # Set initial RGBW values
    light_entity._attr_rgbw_color = expected_rgbw
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()

    # Update through callback
    light_entity.async_update_callback(
        available=True, red=100, green=75, blue=25, brightness=100
    )
    await hass.async_block_till_done()

    # Verify results
    assert light_entity.available is True
    assert tuple(light_entity.rgbw_color) == expected_rgbw


def test_level_conversion() -> None:
    """Test level conversion functions."""
    # Test Home Assistant to Scenario conversion
    assert to_scenario_level(0) == 0
    assert to_scenario_level(255) == 100  # noqa: PLR2004
    assert to_scenario_level(128) == 50  # noqa: PLR2004

    # Test Scenario to Home Assistant conversion
    assert to_hass_level(0) == 0
    assert to_hass_level(100) == 255  # noqa: PLR2004
    assert to_hass_level(50) == 128  # noqa: PLR2004


async def test_light_state(hass: HomeAssistant, light_entity: ScenarioLight) -> None:
    """Test light state properties."""
    # Initialize the entity with platform and registry
    light_entity.platform = Mock()
    light_entity.platform.platform_name = "light"

    # Test initial state (should be off)
    light_entity._attr_brightness = 0
    light_entity._attr_rgbw_color = (0, 0, 0, 0)
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.is_on is False

    # Set some brightness and test state
    light_entity._attr_brightness = to_hass_level(50)
    light_entity._attr_available = True
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.is_on is True

    # Test with RGB values
    light_entity._attr_brightness = 0
    light_entity._attr_rgbw_color = (0, 0, 0, 0)
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.is_on is False

    light_entity._attr_rgbw_color = (255, 0, 0, 0)
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.is_on is True


async def test_remove_from_hass(light_entity: ScenarioLight) -> None:
    """Test removing light from Home Assistant."""
    await light_entity.async_will_remove_from_hass()
    assert light_entity._device.remove_subscriber.called


async def test_async_setup_entry(hass: HomeAssistant) -> None:
    """Test setting up entities from a config entry."""
    mock_light = Mock()
    mock_ifsei = Mock()
    mock_entry = Mock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {
        mock_entry.entry_id: {LIGHTS_ENTRY: [mock_light], CONTROLLER_ENTRY: mock_ifsei}
    }

    async_add_entities = Mock(spec=AddEntitiesCallback)
    await async_setup_entry(hass, mock_entry, async_add_entities)

    async_add_entities.assert_called_once()


async def test_update_callback_writes_state(light_entity: ScenarioLight) -> None:
    """Test that update callback calls async_write_ha_state."""
    with patch.object(light_entity, "async_write_ha_state") as mock_write:
        light_entity.async_update_callback(brightness=50)
        mock_write.assert_called_once()


async def test_update_callback_brightness_when_unavailable(
    light_entity: ScenarioLight,
) -> None:
    """Test that brightness is not updated when device is unavailable."""
    light_entity._attr_available = False
    initial_brightness = light_entity.brightness

    with patch.object(light_entity, "async_write_ha_state") as mock_write:
        light_entity.async_update_callback(brightness=50)
        # State write still called but brightness should not change
        assert light_entity.brightness == initial_brightness
        mock_write.assert_called_once()


async def test_update_callback_rgbw_partial_colors(
    light_entity: ScenarioLight,
) -> None:
    """Test RGBW update with partial color values."""
    # Ensure entity is available and in RGBW mode
    light_entity._attr_available = True
    light_entity._attr_color_mode = ColorMode.RGBW
    light_entity._attr_rgbw_color = (100, 50, 25, 10)

    with patch.object(light_entity, "async_write_ha_state") as mock_write:
        # Update only red channel - use the correct constant name
        kwargs = {IFSEI_ATTR_RED: 75}
        light_entity.async_update_callback(**kwargs)
        assert light_entity.rgbw_color[0] == to_hass_level(75)
        assert light_entity.rgbw_color[1] == UNCHANGED_GREEN_VALUE
        assert light_entity.rgbw_color[2] == UNCHANGED_BLUE_VALUE
        mock_write.assert_called_once()


async def test_set_brightness_with_no_device_manager(
    light_entity: ScenarioLight, mock_ifsei: Mock
) -> None:
    """Test _async_set_brightness when device_manager is None."""
    mock_ifsei.device_manager = None
    await light_entity._async_set_brightness(50)
    # Should not crash, but also should not call async_update_light_state
    mock_ifsei.async_update_light_state.assert_not_called()


async def test_set_brightness_with_no_unique_id(
    light_entity: ScenarioLight, mock_ifsei: Mock
) -> None:
    """Test _async_set_brightness when unique_id is None."""
    light_entity._attr_unique_id = None
    await light_entity._async_set_brightness(50)
    # Should not crash, but also should not call async_update_light_state
    mock_ifsei.async_update_light_state.assert_not_called()


async def test_turn_on_with_rgbw_but_no_brightness(
    hass: HomeAssistant, light_entity: ScenarioLight, mock_ifsei: Mock
) -> None:
    """Test turning on with RGBW color but no brightness specified."""
    await light_entity.async_turn_on(rgbw_color=(255, 128, 0, 64))
    await hass.async_block_till_done()

    mock_ifsei.async_update_light_state.assert_called_once()
    call_args = mock_ifsei.async_update_light_state.call_args[0][1]
    # Should use rgbw_color values + default brightness (255 -> 100)
    assert call_args[0] == to_scenario_level(255)  # red
    assert call_args[1] == to_scenario_level(128)  # green
    assert call_args[2] == to_scenario_level(0)  # blue
    assert call_args[3] == to_scenario_level(64)  # white


async def test_brightness_property_none_handling(
    mock_light: Mock, mock_ifsei: Mock
) -> None:
    """Test brightness property when _attr_brightness is None."""
    light = ScenarioLight(mock_light, mock_ifsei)
    light._attr_brightness = None
    assert light.brightness == 0


async def test_is_on_with_none_values(mock_light: Mock, mock_ifsei: Mock) -> None:
    """Test is_on property handles None values gracefully."""
    light = ScenarioLight(mock_light, mock_ifsei)
    light._attr_brightness = None
    light._attr_rgbw_color = None
    # Should not crash and should return False
    assert light.is_on is False
