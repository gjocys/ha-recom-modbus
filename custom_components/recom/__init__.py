import inspect
import json
import threading
from typing import Optional
from datetime import timedelta

from pymodbus.client import ModbusTcpClient as ModbusClient  # 3.x import
from pymodbus.exceptions import ModbusIOException, ConnectionException

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
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    port = entry.options.get(CONF_PORT, entry.data[CONF_PORT])
    name = entry.data[CONF_NAME]  # keep name from data (unique_id/title)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data[CONF_SCAN_INTERVAL])

    hub = RecomModbusHub(
        hass, name, host, port, scan_interval
    )

    try:
        await hass.async_add_executor_job(hub.connect)
    except Exception as e:
        _LOGGER.warning("Failed to connect to Modbus device %s:%s : %s", host, port, str(e))
        
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
        self._client = ModbusClient(host=host, port=port, timeout=5)
        self._lock = threading.Lock()
        self._name = name
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._unsub_interval_method_entity = None
        self._fans = []
        self._entities = []
        self.data = {}
        self._id_kw = self._detect_device_kw()
        self._id_kwargs = {self._id_kw: 1}

    def _detect_device_kw(self) -> str:
        """Detect whether pymodbus expects device_id= (>=3.10) or slave=/unit= (older)."""
        try:
            sig = inspect.signature(self._client.read_holding_registers)
            params = sig.parameters
            if "device_id" in params:
                return "device_id"
            if "slave" in params:
                return "slave"
        except Exception:
            pass
        return "slave"

    # ---------- connection + retry helpers ----------

    def _ensure_connected(self) -> bool:
        """Ensure socket is connected; call connect() if needed."""
        try:
            return bool(self._client.connect())
        except Exception as e:
            _LOGGER.error("Modbus connect failed: %s", e)
            return False

    def _call_with_retry(self, func, *args, **kwargs):
        """Call a Modbus function; on connection errors reconnect and retry once (no string checks)."""
        with self._lock:
            def _reconnect_and_retry():
                try:
                    self._client.close()
                except Exception:
                    pass
                if not self._ensure_connected():
                    return None
                try:
                    return func(*args, **kwargs)
                except Exception as e2:
                    _LOGGER.error("Modbus retry failed: %s", e2)
                    return None

            try:
                self._ensure_connected()
                return func(*args, **kwargs)

            # Direct low-level socket/connection errors
            except (BrokenPipeError, OSError, ConnectionError, ConnectionException) as e:
                _LOGGER.warning("Modbus connection error: %s. Reconnecting and retrying once...", e)
                return _reconnect_and_retry()

            # ModbusIOException may wrap connection errors
            except ModbusIOException as e:
                inner = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
                disconnected = getattr(self._client, "connected", True) is False
                if isinstance(inner, (BrokenPipeError, OSError, ConnectionError)) or disconnected:
                    _LOGGER.warning("Modbus IO error (connection-related): %s. Reconnecting and retrying once...", e)
                    return _reconnect_and_retry()
                _LOGGER.warning("Modbus IO error (non-connection): %s", e)
                return None

            # Anything else: suppress & log once
            except Exception as e:
                _LOGGER.warning("Unexpected Modbus error (suppressed): %s", e)
                return None

    def _write_and_update(self, entity, write_func, *write_args, write_kwargs=None, update_fn=None):
        write_kwargs = write_kwargs or {}
        res = self._call_with_retry(write_func, *write_args, **write_kwargs)
        if res is None:
            _LOGGER.warning("Modbus write failed for %s", getattr(entity, "name", "<unknown>"))
            return False

        with self._lock:
            data = self.data.setdefault(entity.name, {})
            if callable(update_fn):
                try:
                    update_fn(data)
                except Exception as e:
                    _LOGGER.exception("Error running update_fn for %s: %s", entity.name, e)

        try:
            self._hass.add_job(entity.update_callback)
        except Exception:
            try:
                self._hass.loop.call_soon_threadsafe(entity.update_callback)
            except Exception:
                _LOGGER.exception("Failed to schedule entity update_callback")

        return True

    @callback
    def async_add_entity(self, entity, update_callback):
        """Listen for data updates."""
        if not self._entities:
            self._unsub_interval_method_entity = async_track_time_interval(
                self._hass, self.async_refresh_modbus_data_entity, self._scan_interval
            )
        self._entities.append(entity)
        return True

    def read_input_registers(self, address, divide_value_by):
        res = self._call_with_retry(
            self._client.read_input_registers,
            address=address, count=1, **self._id_kwargs
        )
        if res is None:
            return None
        return _decode_s16_from_registers(res, divide_value_by)

    def read_holding_registers(self, address, divide_value_by = 1):
        res = self._call_with_retry(
            self._client.read_holding_registers,
            address=address, count=1, **self._id_kwargs
        )
        if res is None:
            return None
        return _decode_s16_from_registers(res, divide_value_by)

    def read_coils(self, address):
        res = self._call_with_retry(
            self._client.read_coils,
            address=address, count=1, **self._id_kwargs
        )
        if res is None:
            return None
        if hasattr(res, 'bits') and res.bits:
            return res.bits[0]
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
                try:
                    self._hass.add_job(entity.update_callback)
                except Exception:
                    try:
                        self._hass.loop.call_soon_threadsafe(entity.update_callback)
                    except Exception:
                        _LOGGER.exception("Failed to schedule entity update_callback")

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
                try:
                    speed_mode = FAN_SPEED_MODES[speed_mode]
                    self.data[entity.name]["speed_mode"] = speed_mode
                except Exception:
                    _LOGGER.warning("Unknown speed mode value: %s", speed_mode)

            """ Manual speed percentage """
            manual_speed = self.read_holding_registers(entity.manual_speed_address)
            if manual_speed == False:
                manual_speed = 0
            self.data[entity.name]["manual_speed"] = manual_speed
            try:
                self._hass.add_job(entity.update_callback)
            except Exception:
                try:
                    self._hass.loop.call_soon_threadsafe(entity.update_callback)
                except Exception:
                    _LOGGER.exception("Failed to schedule entity update_callback")

    def _do_refresh(self):
        if not self._entities:
            return

        try:
            self.refresh_sensor()
        except Exception as e:
            _LOGGER.debug("Error in refresh_sensor: %s", e)

        try:
            self.refresh_fan()
        except Exception as e:
            _LOGGER.debug("Error in refresh_fan: %s", e)

    async def async_refresh_modbus_data_entity(self, _now: Optional[int] = None) -> None:
        """Time to update."""
        if not self._entities:
            return
        
        try:
            await self._hass.async_add_executor_job(self._do_refresh)
        except Exception as e:
            _LOGGER.error("Error refreshing Modbus data: %s", e)

    def fan_speed_change_mode(self, entity, new_mode: str):
        """ find speed mode number by ENUM """
        for key, value in FAN_SPEED_MODES.items():
            if value == new_mode:
                mode = key

        if mode is not None:
            _ = self._call_with_retry(self._client.write_register, 2, mode, **self._id_kwargs)
            self.data[entity.name]['speed_mode'] = new_mode
            try:
                self._hass.add_job(entity.update_callback)
            except Exception:
                try:
                    self._hass.loop.call_soon_threadsafe(entity.update_callback)
                except Exception:
                    _LOGGER.exception("Failed to schedule entity update_callback")
            return
        return

    def fan_set_percentage(self, entity, percentage):
        return self._write_and_update(
            entity,
            self._client.write_register,
            entity.manual_speed_address,
            percentage,
            write_kwargs=self._id_kwargs,
            update_fn=lambda d: d.__setitem__("manual_speed", percentage),
        )

    def fan_turn_on(self, entity):
        return self._write_and_update(
            entity,
            self._client.write_coil,
            entity.on_off_address,
            1,
            write_kwargs=self._id_kwargs,
            update_fn=lambda d: d.__setitem__("on_off", 1),
        )

    def fan_turn_off(self, entity):
        return self._write_and_update(
            entity,
            self._client.write_coil,
            entity.on_off_address,
            0,
            write_kwargs=self._id_kwargs,
            update_fn=lambda d: d.__setitem__("on_off", 0),
        )

    def connect(self):
        """Connect client."""
        with self._lock:
            self._ensure_connected()

    def close(self):
        """Disconnect client."""
        with self._lock:
            try:
                self._client.close()
            except Exception as e:
                _LOGGER.debug("Error on close: %s", e)
