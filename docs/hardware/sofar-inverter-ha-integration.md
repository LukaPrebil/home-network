# Sofar ESI 12K-T1 — Home Assistant Integration

Research date: 2026-03-11

## Summary

The Sofar ESI 12K-T1 (PowerAll) hybrid inverter can be integrated into Home Assistant. **Fully local control is possible via Modbus RS485** — no cloud dependency required. However, the ESI-T1 series is not yet explicitly listed in any major HA integration. It shares the same Modbus protocol family as the HYD series, so existing Sofar plugins should work with some configuration effort.

## Communication Interfaces

The ESI 12K-T1 provides:

| Interface | Details |
|---|---|
| RS485 | RJ45 connector, Modbus RTU, 9600/8/N/1 |
| WiFi | Via LSW-3 stick logger (included) |
| Ethernet | Optional LSE-3 LAN stick logger |

Modbus protocol is Sofar's standard RTU, shared across HYD/G3/ESI families. Sofar publishes a Modbus User Guide covering multiple families including ESI.

## Connection Methods

| Method | Protocol | Cloud-free? | Notes |
|---|---|---|---|
| RS485 USB/Ethernet adapter (e.g. USR-TCP232-304) | Modbus RTU or TCP | Yes | Most reliable. Recommended. Needs 120Ω termination resistor |
| LSW-3 WiFi stick (default mode) | SolarMan protocol | Yes (LAN) | Port 8899. Cloud logging still works in parallel |
| LSW-3 WiFi stick (transparency mode) | Modbus RTU over TCP | Yes | Disables SolarMan cloud. Single client only — use Modbus Proxy for multiple |
| LSE-3 LAN stick | Modbus TCP | Yes | Port 8899. More reliable than WiFi |
| SolarMan cloud API | HTTPS | No | Depends on cloud servers |

**Recommended**: RS485 ethernet adapter directly to the inverter's RS485 port. Doesn't interfere with the WiFi stick's cloud logging, supports both read and write.

## Integration Options

### 1. homeassistant-solax-modbus (HACS) — Best for full control

- **Repo**: https://github.com/wills106/homeassistant-solax-modbus
- **Docs**: https://homeassistant-solax-modbus.readthedocs.io/en/latest/sofar-installation/
- **Connection**: Fully local — RS485 direct, or via LSW-3/LSE-3 on port 8899
- **Explicitly supported Sofar models**: HYDxxKTL-3P (`plugin_sofar`), HYDxxxxES (`plugin_sofar_old`), Azzurro 3.3k-12KTL-V3, Azzurro ZSS
- **ESI-T1 status**: Not explicitly listed. Uses same Modbus protocol as HYD. Try `plugin_sofar` first, adjust registers if needed

Control capabilities (via Passive Mode):
- 6 energy storage modes: Self Use, Time of Use, Timing, Passive, Peak Cut, Off-Grid (EPS)
- Passive Mode gives full external control: desired grid power, max battery charge power, min battery discharge power
- Battery SOC reading, charge/discharge control
- PV production, grid import/export, load consumption
- Anti-reflux control

**Caveat**: Some Sofar registers must be written in batches. The integration handles this with dedicated "Update" buttons (e.g. "Passive: Update Battery Charge/Discharge").

### 2. ha-solarman (HACS) — Monitoring via WiFi stick

- **Repo (active fork)**: https://github.com/davidrapan/ha-solarman
- **Repo (original)**: https://github.com/StephanJoubert/home_assistant_solarman
- **Connection**: Local LAN via SolarMan protocol to LSW-3/LSE-3 stick (port 8899)
- **Sofar profiles**: `sofar_g3.yaml`, `sofar_g3hyd.yaml`, `sofar_hybrid.yaml`, `sofar_string.yaml`
- **ESI-T1 status**: No ESI-specific profile. Use `sofar_hybrid.yaml` or create custom profile
- **Limitation**: Primarily monitoring (read-only). Write support is limited and profile-dependent

### 3. Sofar2mqtt — ESP8266-based MQTT bridge

- **Repo**: https://github.com/cmcgerty/Sofar2mqtt
- **Guide**: https://www.instructables.com/Sofar2mqtt-Remote-Control-for-Sofar-Solar-Inverter/
- **Connection**: ESP8266 + MAX485 module → RS485 → inverter → MQTT
- **Capabilities**: Read + write. Supports passive mode charge/discharge control
- **ESI-T1 status**: Built for ME3000SP/HYD series. ESI compatibility untested

### 4. sofar-inverter-control — ESPHome-based

- **Repo**: https://github.com/rnorth/sofar-inverter-control
- **Connection**: ESPHome on ESP8266 + RS485 → direct HA integration
- **Capabilities**: Monitoring + passive mode control

## Data Available Locally

### Read (monitoring)

- PV production (per MPPT)
- Battery SOC, voltage, current, temperature
- Grid import/export power
- Load/consumption power
- Inverter status, temperature, error codes
- Daily/total energy counters

### Write (control — via Passive Mode)

- Battery charge/discharge rate
- Grid power target (positive = import, negative = export)
- Energy storage mode switching
- Time-of-use schedules
- EPS/off-grid mode

## Energy Storage Modes

The solax-modbus integration supports six modes:

1. **Self Use** — default. Prioritises household consumption, battery absorbs excess PV
2. **Time of Use** — up to 4 schedule rules based on time intervals and SOC targets
3. **Timing Mode** — fixed times for charge/discharge at specific power levels
4. **Passive Mode** — full external control. Three parameters: desired grid power, max battery power, min battery power. 2-minute commitment window after value changes
5. **Peak Cut Mode** — shaves grid demand peaks
6. **Off-Grid (EPS)** — backup power during outages

The docs recommend using **Passive Mode** with HA automations rather than the inverter's built-in Time of Use / Timing modes, which are limited.

## Gotchas

1. **ESI-T1 not explicitly supported yet** — protocol is believed identical to HYD but register offsets may differ. May need to work with the Sofar Modbus User Guide to map registers
2. **Firmware version matters** — versions around V110000 cause RS485 failures after hours of operation. Ensure firmware is V110051+
3. **Single Modbus client** — only one client can talk to the inverter at a time over RTU. If using LSW-3 in transparency mode AND HA, need Modbus Proxy
4. **LSW-3 serial number** — sticks with serial 17xxxxx use SolarMan protocol v5. Newer (23xxxxx) may behave differently
5. **Register batch writes** — some control registers can't be written individually, need batch writes (solax-modbus handles this)
6. **EEPROM write cycles** — ~100,000 write cycle limit. Don't write mode changes every few seconds. Design automations to write only when the mode actually needs to change
7. **LSW-3 transparency mode** — disables cloud logging. Can't use both simultaneously. Hidden config at `http://<ip>/config_hide.html`

## Recommended Setup Path

1. Install `homeassistant-solax-modbus` via HACS
2. Connect via RS485 using an ethernet-to-RS485 adapter (keeps WiFi stick free for SolarMan cloud as backup)
3. Try `plugin_sofar` — if registers don't match, request the ESI-T1 Modbus protocol document from the installer or Sofar directly
4. If custom work is needed, raise an issue on the solax-modbus GitHub — the maintainer is active
5. Once monitoring works, configure Passive Mode for battery control via HA automations
