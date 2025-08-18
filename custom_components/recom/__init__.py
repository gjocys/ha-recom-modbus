import asyncio
import json
import threading
from typing import Optional
from datetime import timedelta

from pymodbus.client import ModbusTcpClient as ModbusClient  # 3.x import
from pymodbus.exceptions import ModbusIOException

from homeassistant import core
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, Platform
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PORT,
    FAN_SPEED_MODES,
    ENTITY_FAN,
    ENTITY_SENSOR,
    MODBUS_INPUT_REGISTER,
    MODBUS_COIL
)

import logging
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.SENSOR,
]

def _decode_s16_from_registers(instance, divide_by: float = 1.0) -> Optional[float]:
    """Mimic old BinaryPayloadDecoder.decode_16bit_int() on a single register."""
    if hasattr(instance, "isError") and instance.isError():
        _LOGGER.error("The register does not exist, Try again.")
        return None
    if not hasattr(instance, "registers") or not instance.registers:
        _LOGGER.error("Empty register response.")
        return None
    val = int(instance.registers[0])
    # interpret as signed 16-bit
    if val >= 0x8000:
        val -= 0x10000
    try:
        return float(val / divide_by)
    except Exception as e:
        _LOGGER.error("Division error in validator: %s", e)
        return None


async def async_setup(hass, config):
    """Set up the recom component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up recom modbus."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    name = entry.data[CONF_NAME]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    hub = RecomModbusHub(
        hass, name, host, port, scan_interval
    )

    """Register the hub."""
    hass.data[DOMAIN][name] = {"hub": hub}

    await hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    )

    return True

class RecomModbusHub:
    """Thread safe wrapper class for pymodbus."""

    def __init__(
        self,
        hass,
        name,
        host,
        port,
        scan_interval
    ):
        """Initialize the Modbus hub."""
        self._hass = hass
        self._client = ModbusClient(host=host, port=port)
        self._lock = threading.Lock()
        self._name = name
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._unsub_interval_method_entity = None
        self._fans = []
        self._entities = []
        self.data = {}

    @callback
    def async_add_entity(self, entity, update_callback):
        """Listen for data updates."""
        if not self._entities:
            self.connect()
            self._unsub_interval_method_entity = async_track_time_interval(
                self._hass, self.async_refresh_modbus_data_entity, self._scan_interval
            )
        self._entities.append(entity)
        return True

    def read_input_registers(self, address, divide_value_by):
        with self._lock:
            try:
                # keyword-only in 3.9.x
                res = self._client.read_input_registers(address=address, count=1, slave=1)
                return _decode_s16_from_registers(res, divide_value_by)
            except ModbusIOException as e:
                _LOGGER.error(e)
                return None

    def read_holding_registers(self, address, divide_value_by = 1):
        with self._lock:
            try:
                # keyword-only in 3.9.x
                res = self._client.read_holding_registers(address=address, count=1, slave=1)
                return _decode_s16_from_registers(res, divide_value_by)
            except ModbusIOException as e:
                _LOGGER.error(e)
                return None

    def read_coils(self, address):
        with self._lock:
            try:
                # keyword-only in 3.9.x
                res = self._client.read_coils(address=address, count=1, slave=1)
                if hasattr(res, 'bits') and res.bits:
                    return res.bits[0]
            except ModbusIOException as e:
                _LOGGER.error(e)
                return None

    def refresh_sensor(self):
        entities = filter(lambda x: x.entity_type == ENTITY_SENSOR, self._entities)
        for entity in entities:
            update_result = None
            if entity.modbus_type == MODBUS_INPUT_REGISTER:
                divide_value_by = 1
                if hasattr(entity, 'divide_value_by'):
                    divide_value_by = entity.divide_value_by
                update_result = self.read_input_registers(entity.address, divide_value_by)

            elif entity.modbus_type == MODBUS_COIL:
                update_result = self.read_coils(entity.address)

            if update_result == False:
                update_result = 0

            if entity.name not in self.data or self.data[entity.name] != update_result:
                self.data[entity.name] = update_result
                entity.update_callback()

    def refresh_fan(self):
        entities = filter(lambda x: x.entity_type == ENTITY_FAN, self._entities)
        for entity in entities:
            self.data[entity.name] = {}

            """ On/Off """
            on_off = self.read_coils(entity.on_off_address)
            self.data[entity.name]["on_off"] = on_off

            """ Speed mode """
            speed_mode = self.read_holding_registers(entity.speed_mode_address)
            if speed_mode is not None:
                speed_mode = FAN_SPEED_MODES[speed_mode]
                self.data[entity.name]["speed_mode"] = speed_mode

            """ Manual speed percentage """
            manual_speed = self.read_holding_registers(entity.manual_speed_address)
            if manual_speed == False:
                manual_speed = 0
            self.data[entity.name]["manual_speed"] = manual_speed
            entity.update_callback()

    async def async_refresh_modbus_data_entity(self, _now: Optional[int] = None) -> None:
        """Time to update."""
        if not self._entities:
            return

        self.refresh_sensor()
        self.refresh_fan()

    def fan_speed_change_mode(self, entity, new_mode: str):
        """ find speed mode number by ENUM """
        for key, value in FAN_SPEED_MODES.items():
            if value == new_mode:
                mode = key

        if mode is not None:
            _ = self._client.write_register(2, mode, slave=1)
            self.data[entity.name]['speed_mode'] = new_mode
            return entity.update_callback()
        return

    def fan_set_percentage(self, entity, percentage):
        self._client.write_register(entity.manual_speed_address, percentage, slave=1)
        self.data[entity.name]["manual_speed"] = percentage
        return entity.update_callback()

    def fan_turn_on(self, entity):
        _ = self._client.write_coil(entity.on_off_address, 1, slave=1)
        self.data[entity.name]["on_off"] = 1
        return entity.update_callback()

    def fan_turn_off(self, entity):
        _ = self._client.write_coil(entity.on_off_address, 0, slave=1)
        self.data[entity.name]["on_off"] = 0
        return entity.update_callback()

    def connect(self):
        """Connect client."""
        with self._lock:
            self._client.connect()

    def close(self):
        """Disconnect client."""
        with self._lock:
            self._client.close()
