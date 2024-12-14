"""Config flow for Light State Restoration integration."""
from __future__ import annotations

import voluptuous as vol
from typing import Any
from datetime import datetime, time

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

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
    DEFAULT_TIME_SLOTS,
)

TIME_SLOT_SCHEMA = vol.Schema({
    vol.Required(CONF_START_TIME): str,  # Format: "HH:MM:SS"
    vol.Required(CONF_END_TIME): str,    # Format: "HH:MM:SS"
})

class LightStateRestorationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Light State Restoration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._time_slots: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_time_slots()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_AREA): str,
                vol.Required(CONF_LIGHTS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light", multiple=True)
                ),
                vol.Required(CONF_MOTION_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                        device_class="motion",
                        multiple=True
                    )
                ),
                vol.Optional(CONF_ILLUMINANCE_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="illuminance",
                        multiple=True
                    )
                ),
                vol.Optional(
                    CONF_ILLUMINANCE_THRESHOLD,
                    default=DEFAULT_ILLUMINANCE_THRESHOLD
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=1000,
                        step=1,
                        unit_of_measurement="lux"
                    )
                ),
                vol.Optional(
                    CONF_DELAY,
                    default=DEFAULT_DELAY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=3600,
                        step=30,
                        unit_of_measurement="seconds"
                    )
                ),
                vol.Optional(
                    CONF_TRANSITION,
                    default=DEFAULT_TRANSITION
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=10,
                        step=0.1,
                        unit_of_measurement="seconds"
                    )
                ),
            })
        )

    async def async_step_time_slots(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the time slots step."""
        if user_input is not None:
            if user_input.get("add_another", False):
                self._time_slots.append({
                    CONF_START_TIME: user_input[CONF_START_TIME],
                    CONF_END_TIME: user_input[CONF_END_TIME],
                })
                return await self.async_step_time_slots()
            
            self._data[CONF_TIME_SLOTS] = self._time_slots
            return self.async_create_entry(
                title=f"Light Restoration - {self._data[CONF_AREA]}",
                data=self._data
            )

        return self.async_show_form(
            step_id="time_slots",
            data_schema=vol.Schema({
                vol.Required(CONF_START_TIME): str,
                vol.Required(CONF_END_TIME): str,
                vol.Optional("add_another", default=False): bool,
            }),
            description_placeholders={
                "existing_slots": "\n".join(
                    f"- {slot[CONF_START_TIME]} to {slot[CONF_END_TIME]}"
                    for slot in self._time_slots
                ) or "No time slots configured"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow changes."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._time_slots = list(config_entry.data.get(CONF_TIME_SLOTS, []))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_LIGHTS,
                    default=self.config_entry.data[CONF_LIGHTS]
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light", multiple=True)
                ),
                vol.Required(
                    CONF_MOTION_SENSORS,
                    default=self.config_entry.data[CONF_MOTION_SENSORS]
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                        device_class="motion",
                        multiple=True
                    )
                ),
                vol.Optional(
                    CONF_ILLUMINANCE_SENSORS,
                    default=self.config_entry.data.get(CONF_ILLUMINANCE_SENSORS, [])
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="illuminance",
                        multiple=True
                    )
                ),
                vol.Optional(
                    CONF_ILLUMINANCE_THRESHOLD,
                    default=self.config_entry.data.get(
                        CONF_ILLUMINANCE_THRESHOLD,
                        DEFAULT_ILLUMINANCE_THRESHOLD
                    )
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=1000,
                        step=1,
                        unit_of_measurement="lux"
                    )
                ),
                vol.Optional(
                    CONF_DELAY,
                    default=self.config_entry.data.get(
                        CONF_DELAY,
                        DEFAULT_DELAY
                    )
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=3600,
                        step=30,
                        unit_of_measurement="seconds"
                    )
                ),
                vol.Optional(
                    CONF_TRANSITION,
                    default=self.config_entry.data.get(
                        CONF_TRANSITION,
                        DEFAULT_TRANSITION
                    )
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=10,
                        step=0.1,
                        unit_of_measurement="seconds"
                    )
                ),
            })
        ) 