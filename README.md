# ![](https://github.com/gjocys/ha-recom-modbus/blob/main/icon.png) ha-recom-modbus

## Home Assistant integration for REC Indovent Recom ventilation units via Modbus TCP/IP

This component enables communication between Home Assistant and Rec Indovent Recom ventilation units via Modbus TCP/IP.

Features:

- Turn unit on/off
- Select preconfigured fan speed mode
- Manual fan speed adjustment

![](https://github.com/gjocys/ha-recom-modbus/blob/main/fan.png)

Sensors:
| Sensor | Unit of measurement | Note |
| ------------- |:-------------:| :---------------:|
| Intake air temperature | °C | |
| Exhaust air temperature | °C | |
| Supply air temperature | °C | |
| Extract air temperature | °C | |
| Temperature setpoint | °C | |
| Internal battery | V | |
| Humidity | % | requires additional humidity sensor installed |
| Supply fan speed | rpm | |
| Exhaust fan speed | rpm | |

![](https://github.com/gjocys/ha-recom-modbus/blob/main/sensors.png)

# Installation

<B>Recommended</B>

HACS.

<B>Manually</B>

Download the zip / tar.gz from the release page.

- Extract the contents of ha-recom-modbus into to your home assistant config/custom_components folder.

<B>Post Installation</B>

After rebooting Home Assistant, this integration can be enabled via UI (Settings -> Devices & Services -> Add Integration)

![](https://github.com/gjocys/ha-recom-modbus/blob/main/add_integration.png)
