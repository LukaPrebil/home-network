# SOFAR ESI 12K-T1: Home Assistant Integration

Local Modbus control of the inverter, with no cloud in the automation path.

For the plant itself (array, battery, enclosure, network addresses) see
[`pv-battery-plant.md`](pv-battery-plant.md). For the transport decision and why
control is not allowed over the logger stick, see ADR 0007.

> **Status of the register map below**: inherited research, not yet verified against
> this hardware. Nothing here has been read off the actual inverter. When the first
> poll disagrees with the map, create `sofar-modbus-findings.md` alongside this file,
> following the `orca-modbus-findings.md` precedent, and record what the hardware
> actually says.

## Protocol lineage

The ESI 12K-T1 belongs to the "SOFAR HYD-3PH and SOFAR-G3" protocol family, per the
official SOFAR Modbus User Guide v1.29 (July 2023). That guide covers ESI 2.5-12K-T1,
HYD 5-20KTL-3PH, HYD 3-6K-EP, and the KTL-G3 string inverters. **Register addresses
are identical between the ESI and the HYD three-phase models.** Anything that works
against a HYD 10KTL-3PH works here.

The older "SOFAR HYD 3-6K-ES / ME3000SP" protocol, which `plugin_sofar_old` targets,
is a different register map and does not apply. The correct plugin is `plugin_sofar`,
the G3 and three-phase variant.

No integration lists the ESI 12K-T1 explicitly. Community reports confirm the family
works: a user brought up an ESI 6K-S1 on `homeassistant-solax-modbus` by adding its
serial prefix to `plugin_sofar.py`, and another confirmed `ha-solarman` against an ESI
hybrid using the `sofar_g3hyd.yaml` profile. Neither was a 12K-T1, but the protocol is
shared.

## Transport

Two paths, deliberately used for different things.

| Path | Use | Status |
|---|---|---|
| LSW-3 Wi-Fi logger stick, `192.168.1.6:8899` | Monitoring only | Available now |
| Elfin EE11 on the inverter COM port | Control | Planned, hardware pending |

**Reads over the stick are fine.** A dropped poll costs one sample.

**Writes over the stick are not.** In the stick's default Data Collection mode, write
requests return non-standard response codes, so a write appears to fail even when it
succeeded. The documented workaround is `continue_on_error: true`, which does not fix
the problem, it hides it. For a battery control loop this means a failed Passive Mode
write is indistinguishable from a successful one, and the battery does the wrong thing
at the wrong hour with nothing to signal it. That is the reason control moves to a
wired path, not link reliability.

Transparency mode would give honest write semantics, but it disables the cloud portal
and allows a single TCP client. With the handover signed, SofarCloud is the channel
through which the installer would remote-diagnose a warranty claim, so it stays up.
The EE11 keeps both: clean Modbus on a wired path, cloud untouched.

### Wiring the EE11

Inverter COM port, RS485: pin 1/2 is A+, pin 3/4 is B-, 120 ohm termination,
9600/8-N-1. The EE11 mounts on the DIN rail already in the PV enclosure.

**Check the EE11 input voltage rating against the enclosure's 24V Delta supply before
connecting it.** The Elfin serial servers are commonly specified for a lower DC range.
A step-down may be needed.

## Integration choice

`homeassistant-solax-modbus` (wills106, via HACS), used from day one over the stick,
with writes unused until the wired path exists.

The alternative, `ha-solarman`, works out of the box with `sofar_g3hyd.yaml` and would
be quicker tonight. It was rejected as the starting point because it produces different
entity IDs. Starting there and switching later means either losing accumulated history
or doing entity ID surgery across every dashboard and automation built on top of it.
Starting on `solax-modbus` makes the EE11 arriving a host and port change instead of a
migration.

`ha-solarman` remains the fallback if the serial-prefix patch below turns into a fight.
Accepting the future migration is better than accumulating no local history at all.

### Serial prefix patch

The inverter's serial number prefix must be added to `plugin_sofar.py` with
`HYBRID | X3 | GEN` flags. The single-phase ESI maps its prefix to
`HYBRID | X1 | GEN`; the three-phase model needs `X3`.

This is a one-line edit that HACS will overwrite on every integration update. Report
the prefix upstream in the project's serial-number discussion so it ships in a release
and the patch stops being re-applied.

## Register map

Function code `0x03` for reads, `0x10` for writes. Big endian. Scale factors apply to
raw values.

### Monitoring (read-only)

| Parameter | Hex | Dec | Type | Scale | Unit |
|---|---|---|---|---|---|
| PV1 Voltage | 0x0584 | 1412 | U16 | x0.1 | V |
| PV1 Current | 0x0585 | 1413 | U16 | x0.01 | A |
| PV1 Power | 0x0586 | 1414 | U16 | x10 | W |
| PV2 Voltage | 0x0587 | 1415 | U16 | x0.1 | V |
| PV2 Current | 0x0588 | 1416 | U16 | x0.01 | A |
| PV2 Power | 0x0589 | 1417 | U16 | x10 | W |
| Battery SOC | 0x0210 | 528 | U16 | 1 | % |
| Battery SOH | 0x0211 | 529 | U16 | 1 | % |
| Battery Voltage | 0x0604 | 1540 | U16 | x0.1 | V |
| Battery Current | 0x0605 | 1541 | I16 | x0.01 | A |
| Battery Power | 0x020D | 525 | I16 | x10 | W (+ charge, - discharge) |
| Battery Temperature | 0x0608 | 1544 | I16 | 1 | C |
| Battery Cycles | 0x0212 | 530 | U16 | 1 | cycles |
| Grid Total Power (PCC) | 0x0488 | 1160 | I16 | x10 | W (+ export, - import) |
| Grid Frequency | 0x0484 | 1156 | U16 | x0.01 | Hz |
| Inverter Output Power | 0x0485 | 1157 | I16 | x10 | W |
| L1 / L2 / L3 Voltage | 0x048D / 0x0498 / 0x04A3 | 1165 / 1176 / 1187 | U16 | x0.1 | V |
| L1 / L2 / L3 Grid Power | 0x0493 / 0x049E / 0x04A9 | 1171 / 1182 / 1193 | I16 | x10 | W |
| Inverter Temperature | 0x0418 | 1048 | I16 | 1 | C |
| Operating Status | 0x0404 | 1028 | U16 | - | enum |

### Control (read/write)

| Parameter | Hex | Dec | Type | Values / Scale |
|---|---|---|---|---|
| Energy Storage Mode | 0x1110 | 4368 | U16 | 0 Self Use, 1 TOU, 2 Timing, 3 Passive, 4 Peak Shaving |
| Passive: Desired Grid Power | 0x1187-0x1188 | 4487-4488 | I32 | Watts (+ import, - export) |
| Passive: Max Battery Power | 0x1189-0x118A | 4489-4490 | I32 | Watts |
| Passive: Min Battery Power | 0x118B-0x118C | 4491-4492 | I32 | Watts |
| Active Power Export Limit | 0x1106 | 4358 | U16 | x0.1 %Pn (volatile) |
| Power Control Enable | 0x1105 | 4357 | U16 | bitfield (volatile) |
| Export Surplus Limitation | 0x1023-0x1024 | 4131-4132 | U16 | enable plus kW limit |

### Energy counters (read-only, 32-bit)

| Parameter | Hex | Type | Scale |
|---|---|---|---|
| PV Generation Today | 0x0684-0x0685 | U32 | x0.01 kWh |
| PV Generation Total | 0x0686-0x0687 | U32 | x0.1 kWh |
| Grid Import Total | 0x068E-0x068F | U32 | x0.1 kWh |
| Battery Discharge Total | 0x0228-0x0229 | U32 | x0.1 kWh |

## Passive Mode

Writing `3` to `0x1110` enables it. The three I32 pairs at `0x1187` through `0x118C`
then set the grid power target and the battery charge and discharge limits.

Three things matter here:

1. **These are volatile registers**, held in RAM. They are safe to write continuously
   without EEPROM wear. The rest of the register space is not: the EEPROM is rated
   around 100,000 write cycles, so mode changes must be written only when the mode
   actually needs to change, never on a short timer.
2. **They must be written as a block** of six registers starting at `0x1187` using
   function code `0x10`. The native Home Assistant Modbus integration defaults to
   `0x06`, write single register, which will not work. `solax-modbus` handles the
   batching through dedicated update button entities.
3. **There is a two-minute commitment window** after values change.

The upstream documentation recommends driving Passive Mode from Home Assistant rather
than using the inverter's own Time of Use or Timing modes, which are limited.

## Storage modes

| Mode | Behaviour |
|---|---|
| Self Use | Default. Household consumption first, battery absorbs excess PV |
| Time of Use | Up to four schedule rules on time intervals and SOC targets |
| Timing | Fixed times for charge and discharge at set power levels |
| Passive | Full external control. Three parameters, two-minute commitment window |
| Peak Cut | Shaves grid demand peaks |
| Off-Grid (EPS) | Backup during outages |

## Island mode

The ESI 12K-T1 supports three-phase island operation as a hardware feature, and it was
tested and witnessed at handover. The Modbus registers for enabling and disabling it
are not documented in public sources. EPS configuration registers exist in the `0x1000`
range but are normally set from the inverter's LCD menu or the installer app rather
than over Modbus. Treat island mode as out of scope for automation until someone maps
those registers.

## Plan

**Phase 1, monitoring.** Install `homeassistant-solax-modbus` via HACS. Point it at
`192.168.1.6` port 8899. Patch the serial prefix into `plugin_sofar.py`. Confirm
entities enumerate and the energy dashboard populates. Do not write anything.

**Phase 2, control.** When the EE11 arrives, verify its input voltage against the 24V
rail, wire it to the inverter COM port with termination, give it an address, and change
the integration's host and port. Entity IDs and history carry over. Writes become
trustworthy at that point, and Passive Mode automation can start.

**Phase 3, optimizer telemetry.** Passive parallel RS485 tap on the TIGO CCA's GW/TAP
port, with the CCA left powered but blocked from the internet, feeding the
`taptap-mqtt` add-on. This is a separate bus from the inverter and needs its own
bridge. Per-panel visualisation via the Solar Panel Visualizer Lovelace card.

## Gotchas

- Writes over the logger stick report false failures. This is the whole reason for the
  wired path. Do not paper over it with `continue_on_error: true` and call it working.
- The EEPROM has a finite write-cycle budget. Only the Passive Mode registers and the
  two power-control registers marked volatile are safe for frequent writes.
- Passive Mode needs block writes via `0x10`. Single-register writes will not take.
- Transparency mode on the stick kills SofarCloud and allows one client. Not worth it
  while warranty diagnostics matter.
- The serial-prefix patch is overwritten by HACS updates until it is upstreamed.
- Published firmware guidance for these sticks and inverters uses a different
  versioning scheme than the strings this unit reports. Do not assume thresholds like
  V110051 apply.
