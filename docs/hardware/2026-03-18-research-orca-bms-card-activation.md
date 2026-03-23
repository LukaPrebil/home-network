# Research: Activating PCOS004850 BMS Card on Orca DUO Carel pCO Board

**Date:** 2026-03-18
**Status:** Research complete -- findings ready for action
**Board:** Custom Carel OEM (CODE B02563, labeled "CPP")
**Card:** PCOS004850 RS485 BMS serial card (installed in 8-pin BMS slot)
**Problem:** Card installed but not responding to Modbus queries

---

## Executive Summary

The PCOS004850 card is **just a passive RS485 transceiver with opto-isolation**. It does not activate Modbus by itself. The Modbus protocol must be **activated via system variables** that are set by the **application program** (Orca's firmware) running on the pCO controller. Simply inserting the card does nothing until the firmware enables the BMS serial port.

There are two paths forward:
1. **Best case:** Orca's application program already has BMS/Modbus support built in, and it just needs to be enabled via a service menu parameter (likely behind a service/manufacturer password)
2. **Worst case:** Orca's firmware does not set the COM_PROTOCOL_BMS system variable at all, meaning the BMS port is permanently disabled in software, and only Orca (or someone with the 1tool/EasyTool programming environment and the source code) can enable it

---

## Finding 1: Carel System Variables Required for BMS Modbus

Source: Carel document +030221945 "Modbus protocol for pCO controllers" (both rel. 1.0 and 1.1)

### Protocol Activation (Tab. 2)

The protocol is activated by setting system variables. For the **BMS** serial port:

| System variable | Valid values |
|---|---|
| `COM_PROTOCOL_BMS` | **3** (Modbus, small DB), **30** (Modbus Extended, large DB), **33** (Modbus v33) |

- Value **3**: Standard Modbus, 127 Analogue + 127 Integer + 199 Digital variables (with BMS_EXTENSION=0)
- Value **30**: Extended Modbus, 5000A + 5000I + 2048D variables (requires 512KB RAM controller)
- Value **33**: Available only on SuperNodo, pCOCOMPACT, pCO5 with BIOS >= 5.04/5.17

**Recommendation:** Start with `COM_PROTOCOL_BMS = 3` as safest option for a custom OEM board.

### Baud Rate Selection (Tab. 4)

| `COM_BAUDRATE_BMS` value | Baud rate |
|---|---|
| 0 | 1200 |
| 1 | 2400 |
| 2 | 4800 |
| 3 | 9600 |
| 4 | **19200** (most likely for Orca) |
| 5 | 38400 (only SuperNodo, pCOCOMPACT, pCO5, BIOS >= 5.17) |

### Frame Format (Tab. 5) -- COM_CONFIG_BMS bitfield

| Bit | Name | Values |
|---|---|---|
| 0 | Stop | 0 = 2 stop bits, **1 = 1 stop bit** |
| 1-3 | (unused) | 0 |
| 4-5 | Parity | **00 = none**, 01 = even, 10 = odd |
| 6-15 | (unused) | 0 |

Common values:
- `COM_CONFIG_BMS = 1` (decimal) = 1 stop bit, no parity (8N1) -- **most likely setting**
- `COM_CONFIG_BMS = 0` (decimal) = 2 stop bits, no parity (8N2)
- `COM_CONFIG_BMS = 0x11` (d17) = 1 stop bit, even parity (8E1)

### Supervisor Address

| Serial port | Address variable |
|---|---|
| pLAN, BMS, FIELDBUS | `BMS_ADDRESS` |
| BMS2 | `BMS2_ADDRESS` |

**Set `BMS_ADDRESS` to any value 1-247** (standard Modbus slave address range). Typical: 1.

### Database Extension

| `BMS_EXTENSION` | Effect with Protocol 3/5 |
|---|---|
| 0 | 127A, 127I, 199D (Threshold Th=128) |
| 1 | 207A, 207I, 207D (Threshold Th=208) |

---

## Finding 2: System Variables Are Controlled by the Application Program

**Critical insight from Carel documentation:** "Reading/writing of supervisor variables using the implemented Modbus commands during normal controller operation depends on the application software that manages these."

On a Carel pCO controller, system variables like `COM_PROTOCOL_BMS`, `COM_BAUDRATE_BMS`, `COM_CONFIG_BMS`, and `BMS_ADDRESS` are **not user-accessible through a generic menu**. They are set by the **application program** -- in this case, Orca's custom firmware (part code B02563).

This means:
- The Orca firmware must explicitly assign values to these system variables in its code
- If Orca's programmers never wrote code to set `COM_PROTOCOL_BMS`, the BMS port stays dormant forever
- If they did include BMS support, it would likely be exposed as a configurable parameter in their service/installer menu

---

## Finding 3: Orca DUO Service/Installer Menu Access

### Carel Standard Password Levels

Carel applications typically use a 3-tier password system:

| Level | Typical password | Access |
|---|---|---|
| User | (none) | Basic display, temperatures, mode |
| Service/Technician | **22** or manufacturer-defined | Setpoints, differentials, alarm thresholds |
| Manufacturer/Factory | **66** or manufacturer-defined | Full configuration including BMS parameters |

Additionally, Carel has a **universal master password**: **1315** -- this reportedly works across many Carel applications when the original password is lost.

### Other Known Carel Passwords

From forum reports (refrigeration-engineer.com):
- Menu setting: 00000
- Menu service: 00121
- Maintenance range: 0100, 0105, 0110, 0113, 0118, 0120

### Orca-Specific Access

Orca uses a pGD Touch display panel connected via pLAN to the controller. The service menu is likely accessed by:
1. Pressing and holding a specific button combination on the pGD display (commonly holding the ENTER/OK button for 5+ seconds, or pressing UP+DOWN simultaneously)
2. Navigating to a "Service" or "Parameters" menu section
3. Entering a numeric password

**Passwords to try (in order of likelihood):**
1. `22` (Carel standard service)
2. `66` (Carel standard manufacturer)
3. `1315` (Carel universal master)
4. `0121` (reported Carel service)
5. `0100` (reported Carel maintenance)
6. `1234` (common default)
7. `0000` or `00000` (common default)

### What to Look For in the Service Menu

Once in the service/manufacturer menu, look for parameters related to:
- **BMS** / **Supervisione** / **Nadzor** (supervision)
- **Modbus** / **Protocollo** / **Protokol**
- **Seriale** / **Serial** / **Komunikacija**
- **Indirizzo** / **Address** / **Naslov**
- **Baudrate**

The parameters would be:
- Protocol/BMS enable: should be set to `3` (Modbus) or `30` (Modbus Extended)
- Baud rate: should be set to `4` (= 19200 bps)
- Frame format: should be set to `1` (= 8N1)
- BMS address: should be set to `1` (or any 1-247)

---

## Finding 4: Fallback Options If Orca Firmware Has No BMS Support

### Option A: Contact Orca Energija Service

- Phone: 080 23 24 (Slovenia)
- Website: si.orcaenergy.eu/kontakt/
- Ask specifically: "Can you enable the BMS/Modbus serial port on my DUO? I have installed a PCOS004850 card."
- They may need to send a technician with the Carel 1tool/EasyTool programming environment
- They may charge for a firmware update or parameter change

### Option B: Use pCO Manager via the BMS Port Itself

The PCOS004850 documentation mentions the card can be used "to run the commissioning procedure from a personal computer installed with pCO Manager." This suggests:
- pCO Manager software (Windows) can connect through the BMS serial port
- It may be able to read/write system variables directly
- This would require a USB-to-RS485 adapter connected to the PCOS004850 card
- pCO Manager may be downloadable from Carel's website or available to registered users

### Option C: Exploit the th-Tune Modbus Master Port (J10)

Already documented in `orca-modbus-findings.md`. The board acts as Modbus master on J10, polling addresses 11-13. By emulating a th-Tune slave, we can passively receive some data the board pushes. However:
- This is read-only for the data subset the board sends to thermostats
- Cannot read the full internal variable database
- Cannot write setpoints back

### Option D: Orca Cloud API ("Moja Orca")

The HA community thread mentions someone built a Home Assistant integration using the heat pump's web API instead of Modbus. Orca has a cloud platform called "Moja Orca" (si.orcaenergy.eu/moja-orca/). This is cloud-dependent but may provide an interim solution while resolving the BMS card issue.

---

## Finding 5: PCOS004850 Hardware Details

- **Function:** Passive RS485 transceiver with opto-isolation
- **Slot:** 8-pin white BMS connector on the pCO board
- **Max baud:** 19200 (software configurable)
- **Cable:** AWG20/22 twisted pair, shielded, 0.2-2.5mm2
- **Protocols supported:** Carel Slave or Modbus RTU Slave
- **LED indicators:** Should be present on the card -- check for activity LEDs when powered
- **No DIP switches or jumpers** on the card itself -- all configuration is in software (system variables)
- **Compatible with:** All pCO family controllers except pCOB (pCO2, pCO1, pCOXS, pCO3, pCOCOMPACT, SuperNodo, pCO5)

---

## Recommended Action Plan

1. **Power cycle the heat pump** with the PCOS004850 installed -- the firmware may auto-detect the card on boot
2. **Try all passwords** listed above to access the service/manufacturer menu on the pGD display
3. **Look for any BMS/Modbus/Supervision parameters** in the service menu
4. **Check the PCOS004850 card for LEDs** -- if no LEDs are lit, the firmware may not be initializing the port at all
5. **If no BMS parameters exist in any menu**: call Orca Energija and ask them to enable BMS Modbus on the controller
6. **Try pCO Manager** via USB-RS485 adapter connected to the BMS card -- this may bypass the need for Orca's involvement
7. **If all else fails**: investigate the Moja Orca cloud API as a workaround

---

## Key Sources

- Carel +030221945 "Modbus protocol for pCO controllers" rel. 1.0 (2011) and rel. 1.1 (2012) -- **the definitive reference** for system variable values
- Carel PCOS004850 technical leaflet +050003237
- Carel pCO sistema general manual +030220336
- HA Community thread: community.home-assistant.io/t/help-request-using-modbus-to-control-heatpump-thermostats/429451 (confirms Orca DUO uses Carel pCO + pGD Touch)
- refrigeration-engineer.com forums: Carel pCO maintenance passwords
- Domat Control System: Carel-Modbus integration practical guide (domat-int.com/en/carel-modbus-integration)
