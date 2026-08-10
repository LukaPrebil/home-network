# Utility room cooled through the conditioned space, not by dedicated equipment

Status: accepted (2026-08-10)

The utility room holds the PV enclosure, the four BTS-5K battery modules, the network
cabinet and the laundry. It has always run warm: from February to July 2026 it sat 3 to 5 K
above the bedroom every month, on a baseline of the network cabinet's 67 W around the clock
plus a heat-pump dryer drawing 400 to 590 W for two to four hours most days. That was
tolerable. The plant was energised on Friday 2026-08-07 and it stopped being tolerable.

Two matched pairs either side of the switch-on isolate the plant's contribution from the
weather. With the cooling path open all afternoon, Aug 5 peaked at 26.2 C against a 38.0 C
outdoor high; Aug 7 peaked at 30.1 C against 32.7 C. With the path shut through the
afternoon, Aug 6 peaked at 28.2 C against roughly 36 C; Aug 8 peaked at 31.3 C against
roughly 29 C. Both pairs show the same thing: outdoor 5 to 7 K cooler, room 3 K hotter. A
roughly 9 to 10 K divergence appearing on the day the inverter started, holding across both
door states.

The clearest single measurement was accidental. On Aug 9 both the window and the doors were
shut from 15:35 to 21:20. The sealed room climbed from 30.8 C to 33.2 C and then flattened,
settling 11 K above a 22 C house. That plateau implies the enclosure dissipates somewhere
around 500 to 900 W on a summer afternoon. PVGIS for the actual array geometry (3.64 kWp
south at 15 degrees, 9.10 kWp west at 45, 0.91 kWp east at 45) gives 12,900 kWh a year, 1781
kWh in July against 359 kWh in December. Converting throughput to conversion and battery
losses puts July at roughly 3.3 to 3.6 kWh of heat a day and December at 0.7 to 1.7, which
independently lands on the same afternoon figure. Twenty of the thirty panels face west, so
the heat peaks between 16:00 and 19:00, after the outdoor air peak.

The decision is that this heat is removed through the **cooling path**: Utility -> Vrata
utility -> Vhod -> Notranja vrata -> conditioned space, where the existing MSZ-AY42 split is
the only heat sink in the building. No fan, no duct, no second indoor unit. An advisory
notification keeps the path open when it matters and manages the window, which is the only
opening whose correct state genuinely changes with conditions.

This was tested on 2026-08-10. With the window shut and both doors open, the room fell from
31.7 C at 14:23 to 26.3 C at 16:07 while outdoor climbed to 37 C. At the same hour the
previous day the room was 31.8 C with outdoor 4 K cooler, so the configuration is worth
roughly 9 K. Vhod held between 22.6 and 23.1 C throughout, level with the conditioned
average, confirming it acts as a conduit rather than a buffer when both doors are open. It
had reached 26.5 C on Aug 7 with Notranja vrata shut, which is what a saturating dead end
looks like. The AC's input rose from 486 W to 592 W absorbing the load.

A prediction made before the test is recorded here because it was wrong and a future reader
may otherwise re-derive it. Doorway flow is buoyancy-driven and scales as roughly the 1.5
power of the temperature difference, which implies the required difference grows as the load
to the 2/3. Calibrating on Aug 5's 4.5 K rise at baseline load and tripling the load
predicted 31 to 33 C. The measured result was 26.3 C. Either the plant heat is smaller than
the sealed-room estimate or two doorways in series conduct far better than the model
suggests. The model should not be trusted for sizing.

The reason to care is not the inverter, which will not derate anywhere near these
temperatures, and not comfort, since nobody lives in the room. It is the battery. LFP
calendar ageing roughly doubles per 10 K, so cells held at 30 C rather than 22 C across a 10
to 15 year life is a real capacity cost. The room sensor is a proxy for cell temperature and
will be replaced by the real reading once the Elfin EE11A bridge on the inverter COM port is
installed, per ADR 0007.

## Considered options

- **Extract fan to outside** - rejected: it can only ever clamp the room to outdoor air
  temperature plus whatever the load divided by the flow gives. On the afternoons that
  matter outdoor is 36 to 37 C, so it cannot reach any useful target, and it would discard
  the thermal buffering the room's mass and its coupling to the house currently provide. In
  winter it is worse than useless: the DC routing was deliberately run without piercing the
  thermal envelope, so every watt dissipated in that room already offsets the heat pump, and
  exhausting it outdoors throws away heat that is currently free. Wrong in both seasons, not
  merely seasonally inappropriate.
- **Decentralised HRV unit** - rejected: an HRV's function is to make incoming air resemble
  indoor air, so when both sides are hot it transfers almost no heat. It is an air quality
  device and this is not an air quality problem. The 2026-03-22 decentralised HRV research
  covers a separate whole-house project and should not be conflated with this.
- **Ducted transfer fan, roughly 150 EUR** - rejected for now, and kept as the first
  escalation. Air carries about 0.34 Wh per cubic metre per kelvin, so 300 m3/h of 22 C air
  removes 600 W at 6 K of rise, and that relationship stays linear as load grows rather than
  compounding the way a doorway does. It would also bypass Vhod entirely. It was not needed
  because the measured path already holds the room near its pre-plant delta, but it remains
  the correct answer if a hotter summer, an EV charger, or added IT load in that room pushes
  past what two doorways can carry.
- **Dedicated split in the utility room, 700 to 1200 EUR** - rejected: 2 to 2.5 kW of
  capacity against a load measured in hundreds of watts, and the existing split absorbed the
  entire load for roughly 100 W of extra input. The outdoor unit would also need checking
  first, since Mitsubishi Electric uses MUZ for single-split and MXZ for multi-split, and a
  MUZ-AY42VG cannot take a second head at all. Reconsider only if battery cell temperature,
  once readable over the wired bridge, shows the cells running materially hotter than the
  room implies.
- **Leave it alone** - rejected: the Aug 9 sealed-room plateau at 33.2 C is what happens by
  default, and Aug 4 shows the room holding 28.9 C all night against 18 C outside, starting
  the following day already loaded. Doing nothing has a measurable cost in cell ageing and
  costs nothing to avoid.

## Consequences

The cooling path is now load-bearing infrastructure made of two ordinary doors, which is
fragile in a way a fan would not be. That is what the advisory automation exists to cover.
Notranja vrata is also shut regularly to keep the animals in the living space, so the
automation carries a snooze that suppresses door advice until midnight rather than repeating
guidance already overruled.

Any future load added to that room invalidates the measurement behind this decision. An EV
charger's control gear, more homelab hardware, or a vented dryer would each move the number,
and the escalation path is the transfer fan rather than a rerun of this analysis.
