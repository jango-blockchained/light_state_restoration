"""Constants for the Light State Restoration integration."""
from typing import Final
from datetime import timedelta

DOMAIN: Final = "light_state_restoration"

# Configuration
CONF_AREA = "area"
CONF_LIGHTS = "lights"
CONF_MOTION_SENSORS = "motion_sensors"
CONF_ILLUMINANCE_SENSORS = "illuminance_sensors"
CONF_TIME_SLOTS = "time_slots"
CONF_START_TIME = "start_time"
CONF_END_TIME = "end_time"
CONF_ILLUMINANCE_THRESHOLD = "illuminance_threshold"
CONF_DELAY = "delay"
CONF_TRANSITION = "transition"
CONF_RESTORE_STATES = "restore_states"

# Defaults
DEFAULT_DELAY = 180  # 3 minutes
DEFAULT_TRANSITION = 1.0
DEFAULT_ILLUMINANCE_THRESHOLD = 10  # lux
DEFAULT_TIME_SLOTS = []

# Services
SERVICE_ADD_TIME_SLOT = "add_time_slot"
SERVICE_REMOVE_TIME_SLOT = "remove_time_slot"
SERVICE_ENABLE = "enable"
SERVICE_DISABLE = "disable"

# Attributes
ATTR_ENTITY_ID = "entity_id"
ATTR_ENABLED = "enabled"
ATTR_ACTIVE = "active"
ATTR_LAST_TRIGGERED = "last_triggered"
ATTR_CURRENT_DELAY = "current_delay"
ATTR_TIME_SLOTS = "time_slots"

# Events
EVENT_RESTORATION_TRIGGERED = "light_restoration_triggered"
EVENT_RESTORATION_CANCELLED = "light_restoration_cancelled"
EVENT_TIME_SLOT_ADDED = "time_slot_added"
EVENT_TIME_SLOT_REMOVED = "time_slot_removed"

# Scan interval
SCAN_INTERVAL = timedelta(seconds=30) 