import contextlib
from homeassistant.core import callback
from homeassistant.util.percentage import int_states_in_range, ranged_value_to_percentage, percentage_to_ranged_value
from homeassistant.helpers.entity import ToggleEntity, ToggleEntityDescription
from homeassistant.const import CONF_NAME
from homeassistant.components.fan import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    ATTR_PRESET_MODES,
    FanEntity,
    FanEntityFeature,
)
from typing import Optional

from .const import (
    DOMAIN, 
    FAN_NAME,
    FAN_ON_OFF_ADDRESS,
    FAN_SPEED_MODE_ADDRESS,
    FAN_MANUAL_SPEED_ADDRESS,
    FAN_SPEED_RANGE,
    FAN_SPEED_MODES, 
    ENTITY_FAN
)

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    
    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": "REC Indovent AB",
    }


    

    fan = RecomFanEntity(
        hub_name,
        device_info,
        hub,
        FAN_NAME,
        FAN_ON_OFF_ADDRESS,
        FAN_SPEED_MODE_ADDRESS,
        FAN_MANUAL_SPEED_ADDRESS
    )

    async_add_entities([fan])
    
    return True

class RecomFanEntity(FanEntity):
    def __init__(self, platform_name, device_info, hub, unique_id, on_off_address, speed_mode_address, manual_speed_address):
        self._platform_name = platform_name
        self._attr_device_info = device_info
        self._hub = hub
        self._attr_unique_id = unique_id
        self._name = unique_id
        self._on_off_address = on_off_address
        self._speed_mode_address = speed_mode_address
        self._manual_speed_address = manual_speed_address
        self._current_speed = 0
        self._attr_preset_mode = None
        self._attr_preset_modes = list(FAN_SPEED_MODES.values())
        self._entity_type = ENTITY_FAN
        self._attr_is_on = None
    
    async def async_added_to_hass(self):
        """Add callbacks"""
        self._hub.async_add_entity(self, self.update_callback)

    async def async_turn_on(self, percentage: str = None, preset_mode: str = None, **kwargs):
        await self._hub._hass.async_add_executor_job(self._hub.fan_turn_on, self)

    async def async_turn_off(self):
        await self._hub._hass.async_add_executor_job(self._hub.fan_turn_off, self)

    async def async_set_percentage(self, percentage):
        await self._hub._hass.async_add_executor_job(self._hub.fan_set_percentage, self, percentage)

    async def async_set_preset_mode(self, preset_mode):
        await self._hub._hass.async_add_executor_job(self._hub.fan_speed_change_mode, self, preset_mode)

    @callback
    def update_callback(self):
        with contextlib.suppress(KeyError):
            self._attr_is_on = self._hub.data[self._name]["on_off"]
        with contextlib.suppress(KeyError):
            self._attr_preset_mode = self._hub.data[self._name]["speed_mode"]
        with contextlib.suppress(KeyError):
            if self._hub.data[self._name]["manual_speed"] is not None:
                self._current_speed = int(self._hub.data[self._name]["manual_speed"])
        self.async_write_ha_state()

    @property
    def on_off_address(self):
        return self._on_off_address

    @property
    def manual_speed_address(self):
        return self._manual_speed_address

    @property
    def speed_mode_address(self):
        return self._speed_mode_address

    @property
    def entity_type(self):
        return self._entity_type

    @property
    def is_on(self):
        return self._attr_is_on

    @property
    def name(self):
        return self._name
        
    @property
    def percentage(self):
        """Return the current speed percentage."""
        return ranged_value_to_percentage(FAN_SPEED_RANGE, self._current_speed)

    @property
    def has_entity_name(self):
        return True

    @property
    def supported_features(self) ->int:
        return (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.PRESET_MODE
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False