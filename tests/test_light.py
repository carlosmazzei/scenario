"""Tests for the Scenario Light platform."""

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.components.light import (
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.scenario.const import (
    CONTROLLER_ENTRY,
    DOMAIN,
    LIGHTS_ENTRY,
)
from custom_components.scenario.light import (
    ScenarioLight,
    to_hass_level,
    to_scenario_level,
)


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
    light._attr_unique_id = "test_light_unique_id"  # noqa: SLF001
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
    light_entity._attr_brightness = 0  # noqa: SLF001
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.brightness == 0

    # Test brightness update
    light_entity._attr_brightness = to_hass_level(50)  # Set directly  # noqa: SLF001
    light_entity.async_update_callback(brightness=50)  # This updates state
    await hass.async_block_till_done()
    assert light_entity.brightness == to_hass_level(50)

    # Test availability changes
    mock_ifsei.is_connected = False
    light_entity._attr_available = True  # noqa: SLF001
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()

    light_entity.async_update_callback(available=False)
    await hass.async_block_till_done()
    assert light_entity.available is False

    # Test RGBW update with availability restore
    mock_ifsei.is_connected = True
    light_entity._attr_available = True  # noqa: SLF001

    # Set expected values
    hass_red = to_hass_level(100)
    hass_green = to_hass_level(75)
    hass_blue = to_hass_level(25)
    hass_white = to_hass_level(100)
    expected_rgbw = (hass_red, hass_green, hass_blue, hass_white)

    # Set initial RGBW values
    light_entity._attr_rgbw_color = expected_rgbw  # noqa: SLF001
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
    assert to_hass_level(50) == 127  # noqa: PLR2004


async def test_light_state(hass: HomeAssistant, light_entity: ScenarioLight) -> None:
    """Test light state properties."""
    # Initialize the entity with platform and registry
    light_entity.platform = Mock()
    light_entity.platform.platform_name = "light"

    # Test initial state (should be off)
    light_entity._attr_brightness = 0  # noqa: SLF001
    light_entity._attr_rgbw_color = (0, 0, 0, 0)  # noqa: SLF001
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.is_on is False

    # Set some brightness and test state
    light_entity._attr_brightness = to_hass_level(50)  # noqa: SLF001
    light_entity._attr_available = True  # noqa: SLF001
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.is_on is True

    # Test with RGB values
    light_entity._attr_brightness = 0  # noqa: SLF001
    light_entity._attr_rgbw_color = (0, 0, 0, 0)  # noqa: SLF001
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.is_on is False

    light_entity._attr_rgbw_color = (255, 0, 0, 0)  # noqa: SLF001
    await light_entity.async_update_ha_state(force_refresh=True)
    await hass.async_block_till_done()
    assert light_entity.is_on is True


async def test_remove_from_hass(light_entity: ScenarioLight) -> None:
    """Test removing light from Home Assistant."""
    await light_entity.async_will_remove_from_hass()
    assert light_entity._device.remove_subscriber.called  # noqa: SLF001


async def test_async_setup_entry(hass: HomeAssistant) -> None:
    """Test setting up entities from a config entry."""
    from custom_components.scenario.light import async_setup_entry

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
