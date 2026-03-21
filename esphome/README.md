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
4 (TX)     -->   U0R (GPIO3, RX)
5 (RX)     -->   U0T (GPIO1, TX)
```

The ESP32-CAM is powered directly from the CN105 5V rail. No voltage regulator or level shifter is needed — the 5V supply from the CN105 connector is sufficient and the ESP32 GPIO pins tolerate the 5V logic levels from the heat pump's UART.

**Pin choice:** GPIO1 (TX) and GPIO3 (RX) are the dedicated UART0 pins. The hardware serial logger is disabled (`baud_rate: 0`) to free these pins for CN105. GPIO14/GPIO13 were tried first but the on-board SD card slot loads those signal lines, preventing reliable UART communication. GPIO16/GPIO17 are occupied by PSRAM.

#### Flashing

**First flash (USB):**

```bash
brew install esphome
esphome run airconditioner.yaml
```

The ESP32-CAM requires bridging IO0 to GND to enter download mode. Hold the bridge, press RST, then run the upload command. Remove the bridge after flashing completes.

**Subsequent updates (OTA):**

```bash
esphome run airconditioner.yaml --device 192.168.1.99
```

#### Installation

1. Disconnect the indoor unit from mains power
2. Remove the front panel cover to access the control board
3. Locate the CN105 connector (small white 5-pin connector, usually bottom-left of the board)
4. Plug in the JST connector
5. Route the wires and mount the ESP32-CAM in a safe location inside the unit
6. Restore mains power — the ESP32-CAM boots from the CN105 5V rail

#### Home Assistant Integration

The device auto-discovers in Home Assistant via the ESPHome API. No manual configuration needed. Exposed entities:

- **Climate:** heat/cool/auto/dry/fan with dual setpoint support
- **Sensors:** compressor frequency, input power, energy (kWh), outside temperature, stage, sub mode, auto sub mode
- **Binary sensor:** iSee (AI sensing)
- **Selects:** vertical vane, horizontal vane
- **Switches:** night mode, air purifier
- **Diagnostics:** UART connected, complete/total comm cycles

A web server is available at `http://airconditioner.local` (or the device IP) for debugging without Home Assistant.

#### References

- [MitsubishiCN105ESPHome](https://github.com/echavet/MitsubishiCN105ESPHome) — the ESPHome component
- [Budget Mitsubishi WiFi Controllers](https://houndhillhomestead.com/budget-mitsubishi-hyperheat-wifi-controllers/) — reference build using direct CN105 5V power

## Setup

1. Copy `secrets.yaml.example` to `secrets.yaml` and fill in your values
2. Install ESPHome: `brew install esphome`
3. Flash the device: `esphome run <config>.yaml`
