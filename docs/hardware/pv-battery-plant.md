# PV and Battery Plant (as-built)

Commissioned 2026. Central Slovenia, Elektro Ljubljana distribution area.

This is the as-built record. It corrects an earlier planning description that had
three strings, a WSW roof at 36 degrees, and a 12-panel carport. None of those
survived contact with the install.

## Summary

| Item | Value |
|---|---|
| DC nameplate | 13.65 kWp (30 x 455 W) |
| Panels | Trina Solar TSM-455 NEG9R.28, N-type TOPCon, dual-glass, monofacial |
| Inverter | SOFAR ESI 12K-T1, three-phase hybrid, 12 kW / 13.2 kVA |
| Battery | SOFAR BTS, 4 x BTS-5K, 20.48 kWh nameplate (roughly 18.5 kWh usable) |
| Optimizers | 30 x TIGO TS4-A-O, one per panel |
| Backup | Three-phase island mode (EPS), witnessed at handover |
| Installer | Sol Navitas |

Dual-glass here means glass-glass encapsulation for durability. The panel is
explicitly monofacial, not bifacial.

## Array layout

Two strings of 15. Both deliberately span orientations, which is why every panel
carries an optimizer.

| Surface | Panels | Count | Tilt and orientation |
|---|---|---|---|
| House, east plane | B1-B2 | 2 | 45 degrees east |
| House, west plane (upper row) | B3-B12 | 10 | 45 degrees west |
| House, west plane (lower row) | A9-A15, B13-B15 | 10 | 45 degrees west |
| Carport, flat EPDM | A1-A8 | 8 | 15 degrees south |

String A is 8 south plus 7 west. String B is 2 east plus 13 west.

The house has a north-south ridge with 45 degree planes either side. The carport is
a separate flat roof, laid out two columns by four rows running north to south.

### Known production floors

Four panels sit well below their string-mates in the per-panel view. Both cases are
geometry, not faults. Do not go hunting for failing optimizers.

- **B1 and B2** are the only east-facing panels in a plant that is otherwise west and
  south. Against west-plane peers over an afternoon-weighted window they read around
  40 percent. That is what an east plane looks like in that comparison.
- **A4 and A8** are the southernmost carport row and are partially shaded by the
  house at some times of day. Note this is the opposite of ordinary inter-row
  shading, where each row shadows the row to its north; here the shadow comes from
  the building to the south.

Per-panel production values are not recorded here. They date immediately, and the
TIGO EI app is always the more current source.

### Why mixed-orientation strings are acceptable

TIGO TS4-A-O optimizers on every panel largely remove the MPPT mismatch penalty from
combining orientations on one tracker. This is what resolved the original concern
about running mixed planes through a two-MPPT inverter.

## Mounting

- **House**: clay tile, standard hook mounting on both 45 degree planes.
- **Carport**: ballasted flat EPDM using angled aluminium triangles, concrete
  ballasts, and wind deflectors.
- **Snow guards**: linear snow guards fitted. The house has a modern facade with
  hidden gutters and no eaves, so an ice release would tear out gutters. There are
  also dogs in the yard.
- **DC routing**: down the north-east vent shaft, then horizontally under the vapour
  barrier through a drywall access hole in the utility room ceiling, then down the
  interior wall. The thermal envelope is not pierced.

## Enclosure contents

| Component | Role |
|---|---|
| CHINT DTSU666 | Three-phase smart meter; grid data reaches the inverter over Modbus |
| TIGO CCA gateway | Optimizer telemetry; the GW/TAP port carries it, not RS485-1/2 |
| ABB manual isolator | Manual disconnect |
| Schrack MCBs | Circuit protection |
| Raycap DC SPDs | DC surge protection |
| Delta 24V PSU | DIN-rail 24V supply |
| Unmanaged switch | Local Ethernet, fed by the pre-run hardwired cable |

The enclosure is on a utility room wall that does not back onto a bed, chosen to keep
coil whine away from sleeping space under heavy load.

## Network

| Device | Address | Notes |
|---|---|---|
| SOFAR LSW-3 Wi-Fi logger stick | `192.168.1.6` | Static lease in the Innbox DHCP table. Cloud uplink only, serves nothing locally |
| TIGO CCA gateway | unknown | To be recorded when the RS485 tap is built |
| Elfin EE11A (inverter bridge) | unallocated | Ordered 2026-08-07 |
| Elfin EE11A (TIGO CCA tap) | unallocated | Ordered 2026-08-07 |

Firmware as commissioned:

- Logger stick: `LSW3_15_MQTT_270A_1.22`
- Inverter: `V000001_V000003`

The cloud portal is **SofarCloud**, not SolarMan, and the stick firmware is MQTT-based,
consistent with that move. Published guidance about SolarMan stick firmware 1.09 against
1.11, and about inverter firmware thresholds like V110051, is written for a different
versioning scheme and does not map onto these strings.

**The stick is not a local data source.** Port 8899 is open but answers no protocol
that can be spoken to it, so all Home Assistant telemetry will come from the wired
bridges instead. See [`sofar-modbus-findings.md`](sofar-modbus-findings.md) for the
evidence and ADR 0008 for the decision. Until those bridges are installed, production
history exists only in SofarCloud.

For how the plant is integrated into Home Assistant, see
[`sofar-inverter-ha-integration.md`](sofar-inverter-ha-integration.md).

## Standing constraints

These bind future work. They are settled, not open questions.

- **Local control only.** No virtual power plant enrollment, no net-metering scheme
  that hands battery discharge scheduling to a third party. Any proposal that moves
  discharge control off the local Home Assistant server is out.
- **No cloud dependency for automation.** SofarCloud stays connected for warranty
  diagnostics and as a backup view, but nothing automated may depend on it.
- **Hardwired for control.** Monitoring over Wi-Fi is accepted. Control is not. See
  ADR 0007 for the reasoning, which is about write observability rather than link
  reliability.
- **Self-supply arrangement.** Individual samooskrba under ZSROVE, surplus credited
  and carried forward indefinitely, no lock-in and no exit penalty. Conversion to
  community self-supply remains possible later.

## Sizing rationale

The battery is sized to carry a winter evening and night, roughly 16:00 to 08:00,
running a three-phase Mitsubishi Ecodan heat pump without importing during the
expensive network-fee blocks. The inverter is sized at 12 kW so the heat pump and a
future 11 kW EV charger do not bottleneck each other.

## Contract state

Closed. All contracted items were delivered before sign-off:

- All four BTS-5K battery modules installed
- Linear snow guard fitted
- Three-phase island mode tested and witnessed
- Written lightning protection opinion delivered
- Module layout drawing delivered
- Primopredajni zapisnik signed and final payment released

Withholding the handover record and the final payment was the mechanism that got the
first two items delivered. That leverage is now spent. Anything surfacing from here
runs through warranty and service, which is a slower channel, and is a reason to keep
SofarCloud reachable for remote diagnostics.

## Adjacent systems

- **Heat pump**: Mitsubishi Ecodan, three-phase, on a Carel OEM board. An SG-Ready
  solar dump via a Shelly 1 Gen4 dry contact on the PAC-IF033B-E controller's PV
  input is planned but not installed. See
  [`orca-heatpump-modbus.md`](orca-heatpump-modbus.md).
- **EV charging**: an 11 kW AC charger is anticipated but not installed.
