"""The Light State Restoration integration."""
from __future__ import annotations

import logging
import asyncio
from datetime import datetime, time
from typing import Any, Dict

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_START,
    EVENT_STATE_CHANGED,
    STATE_ON,
    STATE_OFF,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers import entity_registry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_state_change_event,
)
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_AREA,
    CONF_LIGHTS,
    CONF_MOTION_SENSORS,
    CONF_ILLUMINANCE_SENSORS,
    CONF_TIME_SLOTS,
    CONF_START_TIME,
    CONF_END_TIME,
    CONF_ILLUMINANCE_THRESHOLD,
    CONF_DELAY,
    CONF_TRANSITION,
    DEFAULT_DELAY,
    DEFAULT_TRANSITION,
    DEFAULT_ILLUMINANCE_THRESHOLD,
    SERVICE_ADD_TIME_SLOT,
    SERVICE_REMOVE_TIME_SLOT,
    SERVICE_ENABLE,
    SERVICE_DISABLE,
    ATTR_ENABLED,
    EVENT_RESTORATION_TRIGGERED,
    EVENT_RESTORATION_CANCELLED,
    EVENT_TIME_SLOT_ADDED,
    EVENT_TIME_SLOT_REMOVED,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

TIME_SLOT_SERVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_START_TIME): str,
    vol.Required(CONF_END_TIME): str,
})

ENABLE_DISABLE_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_AREA): str,
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Light State Restoration from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    
    manager = LightStateRestorationManager(hass, entry)
    domain_data[entry.entry_id] = manager
    
    await manager.async_setup()
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := True:
        manager = hass.data[DOMAIN].pop(entry.entry_id)
        await manager.async_unload()

    return unload_ok

class LightStateRestorationManager:
    """Class to manage light state restoration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        self._area = entry.data[CONF_AREA]
        self._enabled = True
        self._motion_active: Dict[str, bool] = {}
        self._restore_timers: Dict[str, asyncio.Task] = {}
        self._cancel_scan_interval = None

    async def async_setup(self) -> None:
        """Set up the manager."""
        # Register services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_TIME_SLOT,
            self._handle_add_time_slot,
            schema=TIME_SLOT_SERVICE_SCHEMA,
        )
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_TIME_SLOT,
            self._handle_remove_time_slot,
            schema=TIME_SLOT_SERVICE_SCHEMA,
        )
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ENABLE,
            self._handle_enable,
            schema=ENABLE_DISABLE_SERVICE_SCHEMA,
        )
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_DISABLE,
            self._handle_disable,
            schema=ENABLE_DISABLE_SERVICE_SCHEMA,
        )

        # Set up motion sensor monitoring
        for sensor_id in self.entry.data[CONF_MOTION_SENSORS]:
            self._motion_active[sensor_id] = False

        @callback
        def handle_motion(event: Event) -> None:
            """Handle motion sensor state changes."""
            entity_id = event.data["entity_id"]
            if entity_id not in self._motion_active:
                return

            new_state = event.data["new_state"]
            if new_state is None:
                return

            self._motion_active[entity_id] = new_state.state == STATE_ON
            self._handle_motion_change(entity_id)

        self.hass.bus.async_listen(EVENT_STATE_CHANGED, handle_motion)

        # Set up periodic scanning
        self._cancel_scan_interval = async_track_time_interval(
            self.hass,
            self._handle_interval_scan,
            SCAN_INTERVAL
        )

    async def async_unload(self) -> None:
        """Unload the manager."""
        if self._cancel_scan_interval is not None:
            self._cancel_scan_interval()

        # Cancel any pending restore timers
        for timer in self._restore_timers.values():
            timer.cancel()

        self.hass.services.async_remove(DOMAIN, SERVICE_ADD_TIME_SLOT)
        self.hass.services.async_remove(DOMAIN, SERVICE_REMOVE_TIME_SLOT)
        self.hass.services.async_remove(DOMAIN, SERVICE_ENABLE)
        self.hass.services.async_remove(DOMAIN, SERVICE_DISABLE)

    def _is_in_active_time_slot(self) -> bool:
        """Check if current time is within any configured time slot."""
        current_time = dt_util.now().time()
        
        for slot in self.entry.data.get(CONF_TIME_SLOTS, []):
            start = dt_util.parse_time(slot[CONF_START_TIME])
            end = dt_util.parse_time(slot[CONF_END_TIME])
            
            if start <= current_time <= end:
                return True
                
        return False

    def _check_illuminance(self) -> bool:
        """Check if illuminance is below threshold."""
        if not (sensors := self.entry.data.get(CONF_ILLUMINANCE_SENSORS)):
            return True

        threshold = self.entry.data.get(
            CONF_ILLUMINANCE_THRESHOLD,
            DEFAULT_ILLUMINANCE_THRESHOLD
        )

        for sensor_id in sensors:
            state = self.hass.states.get(sensor_id)
            if state is None:
                continue
                
            try:
                if float(state.state) > threshold:
                    return False
            except (ValueError, TypeError):
                continue

        return True

    async def _restore_lights(self) -> None:
        """Restore light states."""
        if not self._enabled or not self._is_in_active_time_slot():
            return

        if not self._check_illuminance():
            return

        # Call light_state_management.restore_state service
        await self.hass.services.async_call(
            "light_state_management",
            "restore_state",
            {
                "entity_id": self.entry.data[CONF_LIGHTS]
            },
            blocking=True,
        )

        self.hass.bus.fire(
            EVENT_RESTORATION_TRIGGERED,
            {"area": self._area}
        )

    def _handle_motion_change(self, motion_sensor_id: str) -> None:
        """Handle changes in motion sensor states."""
        if not self._enabled:
            return

        if self._motion_active[motion_sensor_id]:
            # Cancel any pending restore timer for this motion sensor
            if timer := self._restore_timers.pop(motion_sensor_id, None):
                timer.cancel()

            # Start restoration process
            self.hass.async_create_task(self._restore_lights())
        else:
            # Start delay timer
            delay = self.entry.data.get(CONF_DELAY, DEFAULT_DELAY)
            if delay > 0:
                self._restore_timers[motion_sensor_id] = self.hass.async_create_task(
                    self._handle_delay_timer(motion_sensor_id, delay)
                )

    async def _handle_delay_timer(
        self, motion_sensor_id: str, delay: int
    ) -> None:
        """Handle the delay timer for a motion sensor."""
        try:
            await asyncio.sleep(delay)
            
            # If no motion is active, turn off lights
            if not any(self._motion_active.values()):
                for light_id in self.entry.data[CONF_LIGHTS]:
                    await self.hass.services.async_call(
                        "light",
                        "turn_off",
                        {"entity_id": light_id},
                        blocking=True,
                    )

                self.hass.bus.fire(
                    EVENT_RESTORATION_CANCELLED,
                    {"area": self._area}
                )
        except asyncio.CancelledError:
            pass
        finally:
            self._restore_timers.pop(motion_sensor_id, None)

    async def _handle_interval_scan(self, now: datetime) -> None:
        """Handle periodic scanning."""
        if not self._enabled:
            return

        # Check if we should restore lights based on current conditions
        if (
            self._is_in_active_time_slot()
            and self._check_illuminance()
            and any(self._motion_active.values())
        ):
            await self._restore_lights()

    async def _handle_add_time_slot(self, call: ServiceCall) -> None:
        """Handle adding a time slot."""
        new_slot = {
            CONF_START_TIME: call.data[CONF_START_TIME],
            CONF_END_TIME: call.data[CONF_END_TIME],
        }
        
        time_slots = list(self.entry.data.get(CONF_TIME_SLOTS, []))
        time_slots.append(new_slot)
        
        new_data = dict(self.entry.data)
        new_data[CONF_TIME_SLOTS] = time_slots
        
        self.hass.config_entries.async_update_entry(
            self.entry,
            data=new_data
        )
        
        self.hass.bus.fire(
            EVENT_TIME_SLOT_ADDED,
            {"area": self._area, "slot": new_slot}
        )

    async def _handle_remove_time_slot(self, call: ServiceCall) -> None:
        """Handle removing a time slot."""
        slot_to_remove = {
            CONF_START_TIME: call.data[CONF_START_TIME],
            CONF_END_TIME: call.data[CONF_END_TIME],
        }
        
        time_slots = list(self.entry.data.get(CONF_TIME_SLOTS, []))
        time_slots = [
            slot for slot in time_slots
            if slot != slot_to_remove
        ]
        
        new_data = dict(self.entry.data)
        new_data[CONF_TIME_SLOTS] = time_slots
        
        self.hass.config_entries.async_update_entry(
            self.entry,
            data=new_data
        )
        
        self.hass.bus.fire(
            EVENT_TIME_SLOT_REMOVED,
            {"area": self._area, "slot": slot_to_remove}
        )

    async def _handle_enable(self, call: ServiceCall) -> None:
        """Handle enable service call."""
        if area := call.data.get(CONF_AREA):
            if area != self._area:
                return
        
        self._enabled = True

    async def _handle_disable(self, call: ServiceCall) -> None:
        """Handle disable service call."""
        if area := call.data.get(CONF_AREA):
            if area != self._area:
                return
        
        self._enabled = False
        
        # Cancel any pending restore timers
        for timer in self._restore_timers.values():
            timer.cancel()
        self._restore_timers.clear() 