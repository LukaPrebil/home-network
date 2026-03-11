# Plan: Orca Heat Pump HACS Integration

**Date:** 2026-03-11
**Status:** Blocked on PCOS004850 BMS card arrival (ordered from eBay Italy, ~€53)

## Context

Orca heat pumps (DUO, Energo, etc.) are common in Slovenia/Croatia but have zero public Modbus documentation. The heat pumps use custom Carel OEM boards that require a PCOS004850 BMS card for Modbus slave access. We've reverse-engineered the board layout and communication patterns. Once the BMS card arrives and registers are mapped, we want to publish both the register map and a turnkey Home Assistant integration via HACS, so other Orca owners can plug in an Elfin EW11 + BMS card and get full monitoring with minimal effort.

## Deliverable

A **standalone GitHub repository** (`orca-heatpump`) containing:
1. A HACS-installable HA custom integration
2. Complete hardware documentation (wiring, BMS card installation, Elfin setup)
3. The discovered Modbus register map
4. Reverse-engineering tools (our diff script, slave emulator)

## Repository Structure

```
orca-heatpump/
├── README.md                              # Overview, screenshots, quick start
├── LICENSE                                # MIT
├── hacs.json                              # HACS metadata
├── .github/
│   └── workflows/
│       ├── hassfest.yaml                  # HA manifest validation
│       └── hacs.yaml                      # HACS validation
│
├── custom_components/
│   └── orca_heatpump/
│       ├── __init__.py                    # Integration setup & teardown
│       ├── manifest.json                  # HA integration manifest
│       ├── const.py                       # Domain, defaults, register definitions
│       ├── config_flow.py                 # UI setup: user enters Elfin IP → auto-validates
│       ├── coordinator.py                 # DataUpdateCoordinator — single polling loop
│       ├── entity.py                      # Base entity class with device info
│       ├── sensor.py                      # Temperature sensors (OT, TM1, TM2, TB, LB, etc.)
│       ├── binary_sensor.py              # Status flags (compressor, defrost, pump, alarm)
│       ├── climate.py                     # ClimateEntity for heating/DHW setpoint control
│       ├── select.py                      # Operating mode selector (heating/cooling/DHW/off)
│       ├── number.py                      # Direct setpoint numbers (weather curve offset, etc.)
│       ├── diagnostics.py                 # Debug data download for issue reports
│       ├── strings.json                   # English UI strings
│       └── brand/
│           └── icon.png                   # Orca logo icon (128-256px)
│
├── docs/
│   ├── hardware-setup.md                  # BMS card installation, wiring, photos
│   ├── elfin-configuration.md             # Elfin EW11 WiFi + serial settings
│   ├── register-map.md                    # Full Modbus register table
│   ├── reverse-engineering.md             # How we discovered the registers (methodology)
│   └── images/                            # Wiring photos, board photos, screenshots
│
├── tools/
│   ├── modbus_diff.py                     # Register hunting diff tool
│   └── modbus_slave_emulator.py           # th-Tune emulator (J10 research)
│
└── tests/
    └── test_config_flow.py                # Config flow validation tests
```

## Key Design Decisions

### 1. Data-Driven Register Map (in `const.py`)

All registers defined as dataclasses in one place. Adding support for a new Orca model = adding a new register set. No hardcoded addresses scattered across entity files.

```python
@dataclass
class OrcaRegisterDef:
    key: str                    # e.g. "outdoor_temp"
    address: int                # Modbus register address
    register_type: str          # "holding" | "input" | "coil" | "discrete"
    scale: float = 1.0          # 0.1 for Carel temps
    unit: str | None = None     # "°C", "%", etc.
    device_class: str | None = None
    entity_type: str = "sensor" # "sensor" | "binary_sensor" | "number" | "select"
    writable: bool = False
    min_value: float | None = None
    max_value: float | None = None
    options: list[str] | None = None  # For select entities

ORCA_DUO_REGISTERS: list[OrcaRegisterDef] = [
    OrcaRegisterDef("outdoor_temp", address=XX, register_type="input", scale=0.1, unit="°C", device_class="temperature"),
    OrcaRegisterDef("flow_temp", address=XX, register_type="input", scale=0.1, unit="°C", device_class="temperature"),
    # ... populated after BMS card register hunting
]
```

### 2. Config Flow (user enters IP, integration auto-discovers)

```
Step 1: User enters Elfin IP + port (default 502) + slave ID (default 1)
Step 2: Integration connects via pymodbus AsyncModbusTcpClient
Step 3: Reads a known "identity" register to confirm it's an Orca board
Step 4: Creates config entry → coordinator starts polling
```

If step 3 fails, show a user-friendly error ("Cannot connect" or "Device not recognized").

### 3. Coordinator Pattern

Single `DataUpdateCoordinator` with ~30s polling interval:
- One `_async_update_data()` call reads ALL registers in batched block reads
- Returns a dict keyed by register `key` with parsed values
- All entities extend `CoordinatorEntity` and pull their value from the dict
- Handles connection failures with automatic retry + exponential backoff

### 4. Climate Entity

One `ClimateEntity` per heating zone (and one for DHW) providing:
- `current_temperature` — from flow/room temp register
- `target_temperature` — read/write to setpoint register
- `hvac_mode` — mapped from mode register (HEAT, COOL, OFF, AUTO)
- `hvac_action` — derived from compressor + valve status coils

### 5. pymodbus Version

Pin to whatever version ships with HA at the time of development. Currently HA core pins `pymodbus==3.9.2`. Use async API (`AsyncModbusTcpClient`) throughout.

## Implementation Phases

### Phase A: Register Hunting (blocked on BMS card arrival)

1. Install PCOS004850 into BMS slot
2. Wire Elfin to BMS card RS485 terminals
3. Set Elfin: `19200, 8, 1, NONE, Modbus protocol, port 502`
4. Run `modbus_diff.py` systematically:
   - Input registers 0-500 (live temperatures)
   - Holding registers 0-500 (setpoints, modes)
   - Coils 0-200 (status flags)
5. Cross-reference with display values to map every register
6. Document in `docs/register-map.md`

### Phase B: Scaffold the Integration

1. Create new GitHub repo `orca-heatpump`
2. Set up directory structure as above
3. Implement `manifest.json`:
   ```json
   {
     "domain": "orca_heatpump",
     "name": "Orca Heat Pump",
     "codeowners": ["@lukastevec"],
     "config_flow": true,
     "documentation": "https://github.com/lukastevec/orca-heatpump",
     "issue_tracker": "https://github.com/lukastevec/orca-heatpump/issues",
     "integration_type": "device",
     "iot_class": "local_polling",
     "requirements": ["pymodbus>=3.9.2"],
     "version": "0.1.0"
   }
   ```
4. Implement `const.py` with register dataclasses + register map
5. Implement `config_flow.py` — IP/port/slave input → Modbus connection test
6. Implement `coordinator.py` — DataUpdateCoordinator with batched reads
7. Implement `entity.py` — base class with Orca device info
8. Implement `strings.json` — English UI text

### Phase C: Entity Platforms

1. `sensor.py` — temperature sensors from register map
2. `binary_sensor.py` — compressor, defrost, pump, alarm, valve states
3. `climate.py` — heating zone + DHW climate entities
4. `select.py` — operating mode (if mode register is writable)
5. `number.py` — setpoint controls (DHW target, curve offset)
6. `diagnostics.py` — dump raw register values for debugging

### Phase D: Documentation & Publishing

1. Write `docs/hardware-setup.md` — BMS card installation with photos
2. Write `docs/elfin-configuration.md` — Elfin settings with screenshots
3. Write `docs/register-map.md` — full register table
4. Write `docs/reverse-engineering.md` — methodology for others to contribute
5. Write `README.md` with:
   - What this is / what hardware you need
   - Installation via HACS
   - Supported entities
   - Screenshots of HA dashboard
   - Contributing guide (for other Orca models)
6. Add CI: `hassfest.yaml` + `hacs.yaml` GitHub Actions
7. Create `hacs.json`, tag v0.1.0 release
8. Submit to HACS default repository list

### Phase E: Testing & Polish

1. Test on real hardware (your Orca DUO)
2. Write `test_config_flow.py` with mocked pymodbus
3. Handle edge cases: Elfin offline, register read failures, stale data
4. Options flow: allow changing polling interval, slave ID
5. Solicit beta testers from Slovenian HA community

## Verification

1. HACS validation passes (`hacs/action@main`)
2. hassfest validation passes (`home-assistant/actions/hassfest@master`)
3. Config flow: entering correct Elfin IP creates a working integration
4. Config flow: entering wrong IP shows "Cannot connect" error
5. All sensors show correct values matching the heat pump display
6. Climate entity can change DHW setpoint and it reflects on the heat pump
7. Integration survives Elfin disconnection and reconnects gracefully

## Open Questions

1. **GitHub username** — what username/org to create the repo under?
2. **Orca model coverage** — start with DUO only, or try to support multiple models from day one? (registers may differ between DUO, Energo, etc.)
3. **Climate entity scope** — should it control both heating zones and DHW, or just one?
4. **Register map completeness** — should we block the integration release until we have a "complete" map, or release early with the registers we've confirmed and iterate?

## Related Files

- `docs/hardware/orca-heatpump-modbus.md` — Master hardware guide with wiring, Elfin setup, and AI agent instructions
- `docs/hardware/orca-modbus-findings.md` — Investigation findings (board ID, port analysis, J10 data captures)
- `scripts/modbus_diff.py` — Register diff tool for BMS card register hunting
- `scripts/modbus_slave_emulator.py` — th-Tune slave emulator for J10 research
