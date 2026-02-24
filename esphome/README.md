# ESPHome Devices

ESPHome device configurations for the homelab. These are compiled and flashed to microcontrollers — not managed by Ansible.

## Devices

### Air Conditioner (`airconditioner.yaml`)

ESP32-CAM controlling a Mitsubishi air conditioner via the CN105 service port, using [MitsubishiCN105ESPHome](https://github.com/echavet/MitsubishiCN105ESPHome).

#### Components

| Item | Notes |
|:-----|:------|
| ESP32-CAM (AI-Thinker) | Any ESP32-CAM module works |
| JST PA 5-pin connector | CN105 breakout cable — available on AliExpress |
| Dupont jumper wires | For connecting the breakout cable to the ESP32-CAM header |

#### Wiring

The CN105 connector on the Mitsubishi indoor unit has 5 pins. With the clip facing up, pin 1 is on the left.

```
CN105 Pin        ESP32-CAM Header
---------        ----------------
1 (12V)          not connected
2 (GND)    -->   GND
3 (5V)     -->   5V
4 (TX)     -->   IO13 (RX)
5 (RX)     -->   IO14 (TX)
```

The ESP32-CAM is powered directly from the CN105 5V rail. No voltage regulator or level shifter is needed — the 5V supply from the CN105 connector is sufficient and the ESP32 GPIO pins tolerate the 5V logic levels from the heat pump's UART.

**Pin choice:** GPIO14 (TX) and GPIO13 (RX) are used instead of the default GPIO16/GPIO17 because those pins are occupied by PSRAM on the ESP32-CAM. GPIO14/GPIO13 are clean — no strapping pin issues, no conflicts when the SD card slot is unused.

#### Flashing

**First flash (USB):**

```bash
pip install esphome
esphome run airconditioner.yaml
```

The ESP32-CAM requires bridging IO0 to GND (or holding the BOOT button) when powering on to enter flash mode. Release after upload starts.

**Subsequent updates (OTA):**

```bash
esphome run airconditioner.yaml --device <IP_ADDRESS>
```

#### Installation

1. Disconnect the indoor unit from mains power
2. Remove the front panel cover to access the control board
3. Locate the CN105 connector (small white 5-pin connector, usually bottom-left of the board)
4. Plug in the JST connector
5. Route the wires and mount the ESP32-CAM in a safe location inside the unit
6. Restore mains power — the ESP32-CAM boots from the CN105 5V rail

#### Home Assistant Integration

The device auto-discovers in Home Assistant via the ESPHome API. No manual configuration needed — the climate entity appears automatically.

#### Known Issues

- ESPHome 2025.8.0+ has a known UART cold-boot bug with this component. Pin to 2025.7.5 if you hit connection issues after power loss.

#### References

- [MitsubishiCN105ESPHome](https://github.com/echavet/MitsubishiCN105ESPHome) — the ESPHome component
- [Budget Mitsubishi WiFi Controllers](https://houndhillhomestead.com/budget-mitsubishi-hyperheat-wifi-controllers/) — reference build using direct CN105 5V power

## Setup

1. Copy `secrets.yaml.example` to `secrets.yaml` and fill in your values
2. Install ESPHome: `pip install esphome`
3. Flash the device: `esphome run <config>.yaml`
