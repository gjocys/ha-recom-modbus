from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, TEMP_CELSIUS, REVOLUTIONS_PER_MINUTE, PERCENTAGE

DOMAIN = "recom"
DEFAULT_NAME = "recom"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 30

VOLT = "V"

MODBUS_INPUT_REGISTER = "input_register"
MODBUS_COIL = "coil"

DONT_DIVIDE_VALUE = 1
DIVIDE_VALUE_BY_10 = 10
DIVIDE_VALUE_BY_1000 = 1000

ENTITY_FAN = "fan"
ENTITY_SENSOR = "sensor"

FAN_NAME = "Ventilation Unit"
FAN_ON_OFF_ADDRESS = 0
FAN_SPEED_MODE_ADDRESS = 2
FAN_MANUAL_SPEED_ADDRESS = 17
FAN_SPEED_RANGE = (0, 100)
FAN_SPEED_MODES = {
    1: "Speed 1",
    2: "Speed 2",
    3: "Speed 3",
    255: "Manual"
}

SENSOR_TYPES = {
    "IR_CurSelTEMP": ["Temperature Setpoint", 0, TEMP_CELSIUS, DIVIDE_VALUE_BY_10, MODBUS_INPUT_REGISTER, "mdi:thermometer"],
    "IR_CurTEMP_SuAirIn": ["Intake Air Temperature",  1, TEMP_CELSIUS, DIVIDE_VALUE_BY_10, MODBUS_INPUT_REGISTER, "mdi:thermometer"],
    "IR_CurTEMP_SuAirOut": ["Supply Air Temperature", 2, TEMP_CELSIUS, DIVIDE_VALUE_BY_10, MODBUS_INPUT_REGISTER, "mdi:thermometer"],
    "IR_CurTEMP_ExAirIn": ["Extract Air Temperature", 3, TEMP_CELSIUS, DIVIDE_VALUE_BY_10, MODBUS_INPUT_REGISTER, "mdi:thermometer"],
    "IR_CurTEMP_ExAirOut": ["Exhaust Air Temperature",4, TEMP_CELSIUS, DIVIDE_VALUE_BY_10, MODBUS_INPUT_REGISTER, "mdi:thermometer"],
    "IR_SuRPM": ["Supply Fan Speed", 23, REVOLUTIONS_PER_MINUTE, DONT_DIVIDE_VALUE, MODBUS_INPUT_REGISTER, "mdi:speedometer"],
    "IR_ExRPM": ["Extract Fan Speed", 24, REVOLUTIONS_PER_MINUTE, DONT_DIVIDE_VALUE, MODBUS_INPUT_REGISTER, "mdi:speedometer"],
    "IR_CurVBAT": ["Internal Battery", 9, VOLT, DIVIDE_VALUE_BY_1000, MODBUS_INPUT_REGISTER, "mdi:battery"],
    "IR_CurRH_Int": ["Humidity", 10, PERCENTAGE, DONT_DIVIDE_VALUE, MODBUS_INPUT_REGISTER, "mdi:cloud-percent"]
    
}
