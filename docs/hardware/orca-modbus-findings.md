# Orca Heat Pump Modbus — Investigation Findings

**Date:** 2026-03-11
**Model:** Orca DUO
**Board:** Custom Carel OEM board, CODE B02563 (labeled "CPP" in schematics)
**Elfin EW11:** IP 192.168.1.160, port 502

## Hardware Findings

### Board Identification

The board is a **custom Carel OEM controller** (not a standard pCO5+). Key differences from a standard pCO5+:

- Part code: **B02563**
- Labeled "CPP" in the Orca electrical schematics (section 26, "Električne sheme naprave DUO")
- No J25/J26 connectors (present on standard pCO5+)
- No DIP microswitches for Fieldbus/BMS port configuration
- Has an **8-pin white BMS expansion slot** (bottom middle of board, labeled "BMS") — currently empty

### Serial Ports

| Port | Label | Purpose | Protocol |
|------|-------|---------|----------|
| **J8** | "Touch zaslon" (touch screen) | pLAN display terminal | Carel pLAN (proprietary, NOT Modbus) |
| **J10** | "Th Tune" | Room thermostat connection | **Modbus RTU** (board is MASTER) |
| **BMS slot** | 8-pin white connector | Supervisor/BMS | Needs add-on card (PCOS004850) |

### J8 — pLAN Port (Dead End)

- Connected Elfin here first — **does not work**
- Board showed "NO_LINK" briefly on first connection attempt
- Tested all baud rate / parity / stop bit combinations — no Modbus response
- This port uses Carel's proprietary **pLAN protocol**, not Modbus RTU
- pLAN is undocumented and impractical to reverse-engineer

### J10 — th-Tune Modbus Port (Partially Useful)

The board acts as **Modbus master** on J10, polling for th-Tune room thermostats.

**Working serial settings:** `19200, 8, 1, NONE`

**Discovery method:** Set Elfin to transparent/None protocol mode, listened for raw RS485 traffic. The board actively sends Modbus RTU frames polling slave addresses 11, 12, and 13.

#### Board Polling Pattern

The board polls 3 slave addresses in a repeating ~5-second cycle:

- **Slave 11** — th-Tune zone 1
- **Slave 12** — th-Tune zone 2
- **Slave 13** — th-Tune zone 3

For each slave, the board:

1. **Reads** coils at addresses 1 and 16 (checking thermostat button states)
2. **Reads** holding registers 140-189, 194, 198 (reading room temp / user setpoint changes from thermostat)
3. **Writes** registers and coils with current state data (see tables below)

#### Registers Written by Board to th-Tune (Slave 11)

Captured 2026-03-11. Display showed: DHW 45.0°C, Outdoor 11.1°C, Room 25.3°C.

| Addr | Raw Value | ÷10 | Notes |
|------|-----------|-----|-------|
| 140 | 5 | — | Mode flag? (possibly heating=5) |
| 141 | 0 | — | Unknown |
| 143 | 0 | — | Unknown |
| 144 | 220 | 22.0°C | Heating setpoint for this zone |
| 145 | 300 | 30.0°C | Max setpoint or secondary setpoint |
| 146 | 80 | 8.0°C | Min setpoint or offset |
| 151-153 | 0,0,0 | — | Unknown (all zero) |
| 157-158 | 0,0 | — | Unknown (all zero) |
| 161 | 1 | — | Mode/season flag (1=winter?) |
| 162 | 2 | — | Mode/season flag (2=heating?) |
| 165 | 495 | 49.5°C | Likely DHW tank temperature (actual, not target) |
| 166 | 31 | 3.1°C | Unknown temp — does NOT match outdoor (11.1°C) |
| 167-169 | 0,0,0 | — | Unknown (all zero) |
| 174-201 | mixed | — | Time band / schedule data (recurring pattern with 24=hour markers) |
| 210-217 | 0,1,0,0,0,1,0,0 | — | Schedule flags |
| 254 | 0 | — | Unknown |

**Key observation:** The values pushed to J10 do NOT directly match the main display values (45.0, 11.1, 25.3°C). The J10 data is a **subset** curated for the room thermostat, not the full internal state.

#### Coils Written by Board to th-Tune

| Coil | State | Possible Meaning |
|------|-------|-----------------|
| 4 | ON | Permission flag (heating allowed?) |
| 7 | ON | Permission flag (DHW allowed?) |
| 16 | ON | Permission flag (schedule active?) |
| 19-20 | OFF | Unknown |
| 25-31 | OFF | Day-of-week schedule flags? |
| 34 | OFF | Unknown |

#### Registers Read by Board from th-Tune

These are the values the board expects the th-Tune to provide:

| Type | Address | Count | Likely Purpose |
|------|---------|-------|---------------|
| Coil | 1 | 1 | Occupancy / mode button |
| Coil | 16 | 1 | Unknown button state |
| Holding Reg | 140 | 50 | Block read — room temp + user setpoints |
| Holding Reg | 141 | 1 | Room temperature reading |
| Holding Reg | 181 | 1 | User setpoint (time band 1?) |
| Holding Reg | 185 | 1 | User setpoint (time band 2?) |
| Holding Reg | 194 | 1 | User setpoint (time band 3?) |
| Holding Reg | 198 | 1 | User setpoint (time band 4?) |

### BMS Expansion Slot — The Path Forward

The 8-pin white BMS connector accepts the **PCOS004850** RS485 serial card.

- **Part:** PCOS004850 (Carel BMS RS485 serial card)
- **Function:** Turns the board into a Modbus **slave**, exposing the full internal variable database
- **Compatibility:** All pCO family controllers (except pCOB)
- **Max baud rate:** 19200
- **Ordered from:** eBay Italy (~€53 shipped)
- **Protocol doc:** Carel +030221945 "Modbus protocol for pCO controllers"

Once installed, the board will respond as a Modbus slave with:
- All analogue variables (temperatures) mapped to Modbus registers (scaled ×10)
- All integer variables mapped to registers (offset by threshold Th)
- All digital variables mapped to Modbus coils
- Slave address configurable via BMS_ADDRESS system variable

## Elfin EW11 Configuration

### For BMS Card (when it arrives)

```
Baud Rate: 19200
Data Bits: 8
Stop Bits: 1
Parity: None
Protocol: Modbus
Port: 502
```

Connect Elfin to the BMS card's RS485 terminals (A+, B-, GND).

### For J10 Sniffing / th-Tune Emulation (current setup)

```
Baud Rate: 19200
Data Bits: 8
Stop Bits: 1
Parity: None
Protocol: None (transparent)
Port: 502
```

## Tools Created

### `scripts/modbus_diff.py`

Register diff tool for hunting specific registers via the BMS card. Takes two snapshots and shows changes.

```bash
.venv/bin/python3 scripts/modbus_diff.py --type holding --start 0 --count 100
.venv/bin/python3 scripts/modbus_diff.py --type input --start 0 --count 100
.venv/bin/python3 scripts/modbus_diff.py --type coil --start 0 --count 200
```

Uses `pymodbus` 3.12+ API (`device_id=` and `count=` as keyword args).

### `scripts/modbus_slave_emulator.py`

Emulates a th-Tune slave at a given address to capture data the board pushes.

```bash
.venv/bin/python3 scripts/modbus_slave_emulator.py 11
```

## Carel pCO Modbus Protocol Reference

From Carel document +030221945:

### Variable Mapping

| Carel Type | Modbus Type | Address Formula |
|------------|-------------|----------------|
| Analogue A[N] | Register | Register[N] (value ×10) |
| Integer I[N] | Register | Register[Th + N] |
| Digital D[N] | Coil | Coil[N] |

Threshold (Th) depends on protocol activation value and BMS_EXTENSION setting.

### Baud Rate Settings

| COM_BAUDRATE value | Baud |
|-------------------|------|
| 0 | 1200 |
| 1 | 2400 |
| 2 | 4800 |
| 3 | 9600 |
| 4 | 19200 |
| 5 | 38400 (pCO5 only) |

### Frame Format (COM_CONFIG bitfield)

- Bit 0: Stop bits (0=2 stop, 1=1 stop)
- Bits 4-5: Parity (00=none, 01=even, 10=odd)

## BMS Card Installation Results (2026-03-18)

### What was done

1. Installed PCOS004850 into the 8-pin BMS slot
2. Wired Elfin EW11 to BMS card RS485 terminals (-, +, GND)
3. Power cycled heat pump after installation

### Testing performed

- Full slave ID sweep (1-247) at **19200 baud** — no response
- Full slave ID sweep (1-247) at **9600 baud** — no response
- Slave IDs 0-3 at **4800 baud** — no response
- Slave IDs 0-3 at **2400 baud** — no response
- Elfin TCP connection works fine in all tests (issue is RS-485 side)
- Elfin confirmed in Modbus protocol mode (was initially in transparent mode from J10 work)

### Conclusion

The Orca DUO firmware (B02563) does **not** initialize `COM_PROTOCOL_BMS` on the BMS serial port. The PCOS004850 card is physically installed and wired correctly, but the firmware never enables the Modbus slave protocol on it. No combination of baud rate or slave address produces a response.

### Service menu access

- Service password: **0001** (unlocks basic service parameters)
- No BMS/Modbus/Serial parameters found in the service menu
- Manufacturer/factory password unknown — tried 22, 66, 1315, 0121, 0100, 1234, 0000 — none worked

### Next Steps

1. **Call Orca Energija (080 23 24)** — ask if firmware supports BMS Modbus, request manufacturer password or firmware update
2. If Orca can't help: investigate **Moja Orca cloud API** as alternative integration path
3. If BMS gets enabled: set Elfin to 19200/8/1/None/Modbus, use `modbus_diff.py` to hunt registers
