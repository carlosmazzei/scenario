"""Unit tests for init."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyscenario.ifsei import IFSEI

from custom_components.scenario import async_unload_entry
from custom_components.scenario.const import CONTROLLER_ENTRY, DOMAIN


@pytest.fixture
def mock_ifsei() -> MagicMock:
    """Mock IFSEI instance."""
    ifsei = MagicMock(spec=IFSEI)
    ifsei.async_close = AsyncMock()
    return ifsei


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    return entry


@pytest.mark.asyncio
async def test_successful_unload(
    hass: HomeAssistant, mock_ifsei: MagicMock, mock_config_entry: MagicMock
) -> None:
    """Test successful unload of entry."""
    # Arrange
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {CONTROLLER_ENTRY: mock_ifsei}}

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        # Act
        result = await async_unload_entry(hass, mock_config_entry)

        # Assert
        assert result is True
        mock_ifsei.async_close.assert_called_once()
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unsuccessful_unload(
    hass: HomeAssistant, mock_ifsei: MagicMock, mock_config_entry: MagicMock
) -> None:
    """Test unsuccessful unload of entry."""
    # Arrange
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {CONTROLLER_ENTRY: mock_ifsei}}

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=False,
    ):
        # Act
        result = await async_unload_entry(hass, mock_config_entry)

        # Assert
        if result is True:
            msg = "Expected unsuccessful unload."
            raise ValueError(msg)

        mock_ifsei.async_close.assert_called_once()
        assert mock_config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_entry_exception_handling(
    hass: HomeAssistant, mock_ifsei: MagicMock, mock_config_entry: MagicMock
) -> None:
    """Test unload entry handles exceptions properly."""
    # Arrange
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {CONTROLLER_ENTRY: mock_ifsei}}
    mock_ifsei.async_close.side_effect = Exception("Test error")

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        # Act & Assert
        with pytest.raises(Exception, match="Test error"):
            await async_unload_entry(hass, mock_config_entry)

        # Verify data remains
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
