"""Platform for Scenario Covers."""

import logging
import time
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
from pyscenario.ifsei import IFSEI
from pyscenario.manager import Cover

from . import ScenarioUpdatableEntity
from .const import CONTROLLER_ENTRY, COVERS_ENTRY, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_TRAVEL_TIME = 30.0
RELAY_ACTIVE = 100
POSITION_MIN = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Scenario lights from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    covers = entry_data[COVERS_ENTRY]
    ifsei = entry_data[CONTROLLER_ENTRY]

    async_add_entities(ScenarioCover(cover, ifsei) for cover in covers)


class ScenarioCover(ScenarioUpdatableEntity, CoverEntity):
    """Scenario Cover Entity."""

    _attr_device_class = CoverDeviceClass.SHADE

    def __init__(
        self, cover: Cover, ifsei: IFSEI, travel_time: float = DEFAULT_TRAVEL_TIME
    ) -> None:
        """Initialize a scenario cover."""
        super().__init__(cover, ifsei)
        self.up = cover.up
        self.stop = cover.stop
        self.down = cover.down
        self._travel_time = travel_time
        self._attr_available = ifsei.is_connected

        self._has_relay_feedback = (
            cover.module is not None
            and cover.open_channel is not None
            and cover.close_channel is not None
        )

        self._current_position: int = 50
        self._is_opening: bool = False
        self._is_closing: bool = False
        self._last_relay_on_time: float | None = None

        if not self._has_relay_feedback:
            self.assumed_state = True
            self._attr_is_closed = None

        self._device.add_subscriber(self.async_update_callback)

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Return supported features."""
        features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )
        if self._has_relay_feedback:
            features |= CoverEntityFeature.SET_POSITION
        return features

    @property
    def ifsei(self) -> IFSEI:
        """Return the IFSEI controller."""
        return self._ifsei

    @property
    def current_cover_position(self) -> int | None:
        """Return current position. 0=closed, 100=open."""
        if self._has_relay_feedback:
            return self._current_position
        return None

    @property
    def is_opening(self) -> bool:
        """Return true if cover is opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return true if cover is closing."""
        return self._is_closing

    @property
    def is_closed(self) -> bool | None:
        """Return true if cover is fully closed."""
        if self._has_relay_feedback:
            return self._current_position == 0
        return self._attr_is_closed

    async def _send_cover_command(self, address: str, action: str) -> None:
        """Send a cover command to the IFSEI controller."""
        if self.unique_id is not None:
            _LOGGER.debug("%s cover %s", action, self.name)
            await self._ifsei.async_update_cover_state(self.unique_id, int(address))
        else:
            _LOGGER.warning("Missing device unique id")

    async def async_open_cover(self) -> None:
        """Open the cover."""
        await self._send_cover_command(self.up, "Opening")

    async def async_close_cover(self) -> None:
        """Close the cover."""
        await self._send_cover_command(self.down, "Closing")

    async def async_stop_cover(self) -> None:
        """Stop the cover."""
        await self._send_cover_command(self.stop, "Stopping")

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move cover to a target position."""
        target = kwargs[ATTR_POSITION]
        diff = target - self._current_position
        if diff == 0:
            return
        travel_duration = abs(diff) / 100.0 * self._travel_time
        if diff > 0:
            await self.async_open_cover()
        else:
            await self.async_close_cover()

        def _schedule_stop() -> None:
            self.hass.async_create_task(self.async_stop_cover())

        self.hass.loop.call_later(travel_duration, _schedule_stop)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callbacks."""
        self._device.remove_subscriber()

    def _handle_relay(self, value: int, now: float, *, opening: bool) -> None:
        """Process a relay state change for either open or close direction."""
        is_active_flag = self._is_opening if opening else self._is_closing
        direction_label = "Open" if opening else "Close"
        move_label = "up" if opening else "down"
        sign = 1 if opening else -1

        if value == RELAY_ACTIVE:
            _LOGGER.debug("%s: %s relay energised", self.name, direction_label)
            self._is_opening = opening
            self._is_closing = not opening
            self._last_relay_on_time = now
        else:
            _LOGGER.debug("%s: %s relay de-energised", self.name, direction_label)
            if is_active_flag and self._last_relay_on_time is not None:
                elapsed = now - self._last_relay_on_time
                delta = (elapsed / self._travel_time) * 100
                self._current_position = max(
                    POSITION_MIN,
                    min(RELAY_ACTIVE, int(self._current_position + sign * delta)),
                )
                _LOGGER.info(
                    "%s: Moved %s %.2fs (%+d%%). Position: %d%%",
                    self.name,
                    move_label,
                    elapsed,
                    sign * delta,
                    self._current_position,
                )
            self._is_opening = False
            self._is_closing = False
            self._last_relay_on_time = None

    def _handle_open_relay(self, value: int, now: float) -> None:
        """Process open relay state change."""
        self._handle_relay(value, now, opening=True)

    def _handle_close_relay(self, value: int, now: float) -> None:
        """Process close relay state change."""
        self._handle_relay(value, now, opening=False)

    def _handle_scene_command(self, command: str, state: str) -> None:
        """Process legacy scene command (covers without relay feedback)."""
        _LOGGER.debug(
            "Cover %s received command=%s, state=%s", self.name, command, state
        )
        if self._has_relay_feedback:
            return
        if command == IFSEI_COVER_DOWN and state == IFSEI_ATTR_SCENE_ACTIVE:
            self._attr_is_closed = True
        elif command == IFSEI_COVER_UP and state == IFSEI_ATTR_SCENE_ACTIVE:
            self._attr_is_closed = False
        elif command == IFSEI_COVER_STOP and state in (
            IFSEI_ATTR_SCENE_ACTIVE,
            IFSEI_ATTR_SCENE_INACTIVE,
        ):
            self._attr_is_closing = False
            self._attr_is_opening = False

    def async_update_callback(self, **kwargs: Any) -> None:
        """Update callback."""
        available = kwargs.pop(IFSEI_ATTR_AVAILABLE, None)
        open_relay = kwargs.pop("open_relay", None)
        close_relay = kwargs.pop("close_relay", None)
        command = kwargs.pop(IFSEI_ATTR_COMMAND, None)
        state = kwargs.pop(IFSEI_ATTR_STATE, None)
        now = time.time()
        state_changed = False

        if available is not None:
            self._attr_available = available
            _LOGGER.debug("Set cover %s availability to %s", self.name, available)
            state_changed = True

        if open_relay is not None:
            self._handle_open_relay(open_relay, now)
            state_changed = True

        if close_relay is not None:
            self._handle_close_relay(close_relay, now)
            state_changed = True

        if command is not None and state is not None:
            self._handle_scene_command(command, state)
            state_changed = True

        if state_changed:
            self.async_write_ha_state()
