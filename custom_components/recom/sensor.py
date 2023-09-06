from homeassistant.core import callback
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity

from typing import Optional, Dict, Any
import logging
_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    SENSOR_TYPES,
    ENTITY_SENSOR
)


async def async_setup_entry(hass, entry, async_add_entities):
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    
    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": "REC Indovent AB",
    }


    entities = []
    for key, sensor_info in SENSOR_TYPES.items():
        sensor = RecomSensor(
            hub_name,
            device_info,
            hub,
            sensor_info[0],
            key,
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
            sensor_info[4],
            sensor_info[5]

        )
        entities.append(sensor)
    async_add_entities(entities)
    
    return True

class RecomSensor(Entity):
    def __init__(self, platform_name, device_info, hub, name, key, address, unit_of_measurement, divide_value_by, modbus_type, icon):
        self._platform_name = platform_name
        self._state = None
        self._device_info = device_info
        self._name = name
        self._hub = hub
        self._key = key
        self._address = address
        self._unit_of_measurement = unit_of_measurement
        self._divide_value_by = divide_value_by
        self._modbus_type = modbus_type
        self._entity_type = ENTITY_SENSOR
        self._icon = icon

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_entity(self, self.update_callback)


    @callback
    def update_callback(self):
        self._state = self._hub.data[self._name]
        self.async_write_ha_state()

    @property
    def name(self):
        return self._name

    @property
    def address(self):
        return self._address

    @property
    def entity_type(self):
        return self._entity_type

    @property
    def modbus_type(self):
        return self._modbus_type

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement
        
    @property
    def divide_value_by(self):
        return self._divide_value_by

    @property
    def unique_id(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def has_entity_name(self):
        return True

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info