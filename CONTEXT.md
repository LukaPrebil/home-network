# Home Network (Homelab + Home Assistant)

Single-operator homelab: Ansible-managed infrastructure plus a Home Assistant estate (automations, dashboards) managed via `ha-mcp` tools. This context captures the domain language that recurs across HA automation design.

## Language

### WiFi estate

**House AP**:
The primary indoor access point serving the living space; the only tri-band (6 GHz) unit in
the fleet. Resolved 2026-09-16: the EAP772 (BE9300 EU, ~€185, 2.5G port, 802.3at), mounted
on the top-floor ceiling of a wood-frame house with screed floors.
_Avoid_: "wifi 7 AP" (the requirement is the 6 GHz band for the ~4-5 capable personal
clients; Omada's EU lineup has no 6E ceiling AP, so 6 GHz arrives only via WiFi 7 hardware)
_Avoid_: the EAP723 - it is dual-band WiFi 7 with no 6 GHz radio, so it cannot decongest 5 GHz

**Utility AP**:
The relocated EAP650 (indoor, AX3000) in the utility room, serving the driveway and shed
through the exterior walls. No purchase; it changes coverage zones, not hardware.

**Balcony AP**:
The EAP610-Outdoor (AX1800, IP68, ~€85) wall-mounted ~3 m above the balcony, serving the
20x20 m yard: phones/laptops outdoors, the Luba mower (2.4 GHz), and future outdoor IoT.
Resolved 2026-09-16: 160 MHz on 5 GHz was judged worthless outdoors, so the EAP650-Outdoor
was dropped for the cheaper model with an identical 2.4 GHz radio.
_Avoid_: "outdoor AP" for the Utility AP - it stays indoors and radiates through walls.
Note: the sheet-metal porch roof RF-shadows the porch itself; the AP's pattern should point
outward over the yard, not down into the metal sheet.

**Access switch**:
The single collapsed switch (ES228GP, 24x1G PoE+ / 26 RJ45 / 2x1G SFP, ~€230) that absorbs
both the CSS326 and the YuanLey. Every wired thing lands here; no second switch remains.
_Avoid_: "core switch" (there is no distribution below it to be the core of) and "the 10G
backbone" (retired with the YuanLey - n5p runs 1G, same as today, and 10G returns only as a
separate SFP+ switch if it is ever wanted)

### Mammotion Luba (mower)

**Device-level entity**:
An HA entity bound to the mower device itself (e.g. `lawn_mower.vrt_luba`, `sensor.vrt_luba_progress`); stable across map and task changes.
_Avoid_: "static entity"

**Map-derived entity**:
An HA entity generated from the mower's cloud map/task objects (area switches, saved-task buttons, task-area sensors); appears, renames, or disappears whenever maps, zones, or tasks change on the mower side.
_Avoid_: "zone entity" (too narrow - saved-task buttons and task-area sensors churn too)

**Job**:
One mowing task execution, from start command to task end; survives recharge, rain pauses, and overnight waits without ending.
_Avoid_: "session", "run"

**Job end**:
The moment the mower's task ends for any reason; observable as `sensor.vrt_luba_progress` resetting to 0 (and `lawn_mower.vrt_luba` returning to `docked`).

**Finished**:
A job end with progress-before-reset >= 90 (observed completions peak at 99, never 100).
_Avoid_: "COMPLETE" (the deleted enum's value)

**Cancelled / aborted**:
A job end with progress-before-reset below 90; a fresh fault distinguishes aborted (alert) from a deliberate cancel (silent).

**Fresh fault**:
`sensor.vrt_luba_last_error_time` within a short window of the event being evaluated; the only fault-liveness signal, since `last_error_code` holds the last error ever.

**Transport flap**:
Sub-minute `unavailable` blips affecting all mower entities at once (cloud transport hiccup on v0.6.3); triggers must not fire or clear on these.

### Mammotion Luba (blade wear)

**Blade set**:
The nine blades installed together and replaced together - six on the main disc, three on the side disc.
_Avoid_: "set of 4"

**Blade stage**:
One of four roughly 50 h wear segments of a blade set.
_Avoid_: "hole", "side" (both are physical realizations of a stage, not the unit we track)

**Flip**:
Advance a blade set to the next blade stage, by turning the blades over or moving them to the second hole.
_Avoid_: "rotation", "change the blades"

**Replace**:
Install a fresh blade set and reset the device counter.
_Avoid_: "flip"

### Matter fabric (time)

**Time push**:
Controller-originated delivery of wall-clock time to a Matter device via the SetUTCTime / SetTimeZone / SetDSTOffset commands, sent by matter-server.
_Avoid_: "NTP" (no NTP protocol touches any device on this fleet; the devices cannot be NTP clients)

**Time-capable device**:
A Matter node exposing the Time Synchronization cluster (0x0038); currently only the ALPSTUGA air quality monitor, and only in its TZ-only form.

**Fabric state**:
matter-server's on-disk store (`/srv/docker/matter-server/data` on rpi4) holding the fabric credentials and node table; losing it means re-commissioning every Matter device.
_Avoid_: "matter data dir"

### Thread border routing

**On-link prefix**:
The ULA the Thread border router advertises on the LAN so LAN hosts take an address in it;
derived from the extended PAN ID, and `fd11:1111:1122:2222::/64` for the current network.
_Avoid_: "the fd11 prefix" (names one instance of the concept), "ULA" (the address class, not
this role)

**Backbone link**:
The border router's LAN-facing side, eth0 on `containers`, over which it advertises the on-link
prefix and the off-mesh-routable route.
_Avoid_: "infrastructure link", "infra netif" (the OTBR implementation's wording), "the ethernet
side"

**Border router host**:
The VM that runs the OTBR container; it is the machine that must itself hold an address and
route in the **on-link prefix**, separately from the container's own health.
_Avoid_: "the OTBR" unqualified - the container and the host fail independently

### Solar and tariff

**Passive Mode**:
The inverter storage mode in which Home Assistant sets the grid power target and the
battery charge and discharge limits directly, rather than the inverter deciding. Its
three control register pairs are volatile RAM, so they are safe to write continuously;
every other control register is EEPROM-backed and is not.
_Avoid_: "manual mode"

**Blok**:
A Slovenian network-fee (omrežnina) time band. Blok 1 is the most expensive winter
peak band, and carrying the house through it without importing is what the 20.48 kWh
battery is sized against.
_Avoid_: "peak tariff" (the energy price and the network fee are billed separately, and
it is the network fee that drives the battery schedule)

**Samooskrba**:
The Slovenian self-supply arrangement the metering point is enrolled in. Surplus is
credited and carries forward indefinitely; there is no lock-in and no exit penalty.
Individual samooskrba today, with community samooskrba possible later.

**Viški / manki**:
Energy exported from and taken by the metering point over one **obračunsko obdobje**.
Viški are credited at a much lower rate than manki are charged, which is why
self-consumption beats export.

**Obračunsko obdobje**:
The settlement period for samooskrba, which under the ZSROVE monthly scheme is the
calendar month.
_Avoid_: "billing year" (the annual net settlement belongs to the older EZ-1 scheme)

**Dobroimetje**:
The monetary credit viški earn, netted against the same month's electricity bill and
carried forward against future invoices with no expiry once it exceeds one bill.
_Avoid_: treating it as banked kWh - it is euros at the viški rate, not energy

**Gross-import rule**:
Omrežnina, prispevki and trošarina are billed on the whole quantity taken from the
grid, never on import net of export, so an exported kWh relieves no network charge.

**Logger stick**:
The SOFAR LSW-3 Wi-Fi dongle that talks to SofarCloud. Port 8899 is open but answers no
protocol, so it carries nothing locally and is not a data source.
_Avoid_: conflating it with the **inverter bridge**. Both reach the same inverter; only
the bridge can be read or written.

**Monitoring bus**:
The RS485 pair on the inverter's Link0 (or Link1) COM jack, pins 1 and 2, which the
manual labels "Upper computer RS485A/B". The inverter is a Modbus *slave* here, so
whatever attaches becomes the master. This is where the **inverter bridge** lands.
_Avoid_: "the COM port" - that is a bank of six RJ45 jacks plus a dry-contact block, and
two of those jacks carry RS485 in opposite master/slave roles.

**Meter bus**:
The RS485 pair on the inverter's Meter/CT COM jack, pins 1 and 2, intended for the
DTSU666's terminals A(24) and B(25). The inverter is the *master* here, polling the meter.
Bypassed at commissioning: the pair was run into the cabinet but left unlanded, and the
inverter senses grid power from its own internal CTs instead.
_Avoid_: attaching anything to this pair. A second master on it collides with the inverter.

**Inverter bridge**:
The Elfin EE11A on the SOFAR inverter's COM port, carrying Modbus RTU at 9600 in both
directions; the only path by which **Passive Mode** can be read or written. Needs 120
ohm termination.
_Avoid_: "wired bridge" - both EE11A units are wired, so that name stopped identifying
anything once the second one was installed.

**Tap bridge**:
The Elfin EE11A at `192.168.40.162` on the TIGO CCA's GW/TAP port, serving the bus as a
TCP stream on port 7160. Read-only by construction: it drives the RS485 transmitter
only when a TCP client writes, and nothing ever does. It can also stop feeding a client
it has already accepted without ever closing that socket, and nothing on the bridge side
will say so.
_Avoid_: adding termination to it. It is a passive parallel tap on a bus already
terminated at the CCA and at the furthest TAP; a third resistor degrades the CCA's own
traffic.

**Module**:
One optimizer as taptap-mqtt names it, identified by the barcode serial printed on the
unit (`A-1234567` form) and mapped by hand to a panel position (`A1` to `B15`).
_Avoid_: "node" for this. A **node ID** is the bus-level address the TAP gateway assigns,
it is not stable across gateway restarts, and it is what the raw taptap output carries.
The module serial is the identity that survives.

**TAP gateway**:
A TIGO TAP radio bridging optimizers to the CCA over RF, identified on the bus by a
gateway ID (`4609` and `4610` on this plant).
_Avoid_: reading gateway membership as string membership. The two gateways are not the
two strings - gateway 4609 carries nodes 4, 5, 6 and 9 while 4610 carries 10 to 30.
Gateways are placed for RF coverage; string membership is operator-supplied config.

### EV charging

**Surplus-only charge**:
The default charging policy: the car draws power only while the metering point is exporting
PV surplus, so it never adds to the **Night load** the SOFAR battery carries and never causes
a grid import. The car is a daytime sink for energy that would otherwise leave as
**viški**.
_Avoid_: "solar charging" (the house runs on solar at night too, via the battery - the point is
import timing, not energy color); "eco mode" (vendor UI wording that varies per box)

**Night load**:
The evening-to-morning house consumption the 20.48 kWh battery is sized to carry without
grid import, especially through **Blok** 1. Adding the car to it defeats both the battery's
sizing and the **gross-import rule** economics, so by policy the car stays out of it, with
exactly one standing exception, the **Conditioning draw**.
_Avoid_: "overnight charging" as a routine (it is exactly what the policy forbids; the
sanctioned exception is **Trip recovery**)

**Trip recovery**:
The sanctioned exception to **Surplus-only charge**: a known-ahead trip gets a charge plan
aimed at a departure time and target SoC, scheduled into the daylight of the days before it.
When the window is too short, an en-route DC fast stop is the accepted fallback, not a
failure of the plan.
_Avoid_: "fast charging" (a power level, not a purpose); "top up before the trip" (hides that
the 11 kW ceiling exists for exactly this and nothing else)

**Charge floor**:
The lowest power an EVSE will hold a session at: 6 A per phase, so 4.2 kW across three
phases or 1.4 kW on one. The floor, not the 11 kW ceiling, decides how much marginal spring
and autumn surplus the car can harvest, which is why the charger choice is designed around
it.
_Avoid_: "minimum charging power" (silent about phase count, which changes it threefold)

**Surplus signal**:
The whole-house grid exchange at the point of common coupling, read from the inverter's
internal CTs as register 0x0488 (`active_power_pcc_total`), positive on export. Verified live
on the evening of 2026-10-12: with PV off and the battery carrying the whole house, the
register reads ~0 where a plant-only view would have read the full discharge as export. It
is the control input that **Surplus-only charge** modulates against, and because the entire
**Backed-up panel** sits behind the same CTs, it sees the car with no extra metering.
_Avoid_: "export reading" (the same register reads import; the sign carries direction),
"the DTSU666" (bypassed, and not the source of this value), "CT clamp" (nothing external
is clamped anywhere)

**Backed-up panel**:
The entire main distribution panel, served through the inverter's EPS load path, so every
house circuit - including the carport charging point - sits both behind the internal CTs
and inside the island. Two consequences, one per side of the CTs: every load is visible to
the **Surplus signal**, and every load stays live through an island event, so any big load
carried on it needs its own **Island guard**.
_Avoid_: "backup circuits" (there is no partial backup list to be on or off - the whole
panel is one), "EPS loads" (vendor wording that hides the CT-visibility consequence)

**Battery-first**:
The surplus allocation rule: the SOFAR battery eats all PV surplus until satisfied, and the
EV never preempts it. In the surplus season the battery is full late morning and every
afternoon export is car food; in winter the house and battery take essentially all
production and the EV charges only through **Trip recovery**.
_Avoid_: "battery priority" (sounds like a tunable weight; the rule is absolute), "sharing the
surplus" (there is no sharing - the EV eats only what would otherwise become **viški**)

**Island guard**:
The rule that the EVSE stops charging whenever the inverter runs in island mode, because the
point stays live through the **Backed-up panel** and the surplus loop is structurally blind
in an island (the **Surplus signal** reads ~0 there). Resolved 2026-10-12: hard block, no
surplus-in-island exceptions, a short debounce so ride-through blips do not flap sessions,
automatic resume once the grid status returns, and fail-closed - an unreadable inverter state
blocks charging rather than allowing it. Which register value encodes the island is a
one-time calibration against a real island test, not a guess.
_Avoid_: "outage blocking" (the grid being out is not the trigger - the island being live is),
"the charger turns off in a blackout" (nothing turns off - that is the whole problem), moving
the point to a non-backup spur (it deletes the guard and the **Surplus signal** together)

**Boost**:
The manual override that charges immediately at full current, knowingly importing whatever
PV cannot cover. Session-scoped: on unplug it reverts to **Surplus-only charge** by itself, so
a forgotten Boost never becomes a silent night-long import. It is one of only two standing
paths to deliberate import, the other being a **Charge plan** hitting its deadline.
_Avoid_: "fast charging" (a power level, not consent to import), "manual override" (which of
the several overrides?), leaving the mode sticky after the guest drives off

**Permissionless surplus**:
The rule that any plugged-in car may charge while the point exports, guest or resident, with
no approval step while the **Car gate** is open - the energy was leaving as **viški** anyway.
Only deliberate import (**Boost**, or a **Charge plan** escalating at its deadline) requires
an operator action, and that is what makes helping a guest charge a two-gesture affair: plug
in, and hit Boost only if they need speed.
_Avoid_: adding per-guest approval flows (the gate exists for an empty house, not to judge
who the guest is), treating guest sessions as a different charging policy (the sink's owner
changes nothing about import timing)

**Charge plan**:
A target SoC plus a departure time, handed to evcc, which then runs surplus-first and
escalates to import only as late as the deadline still allows. It is the implementation of
**Trip recovery**, and because it escalates only near the deadline, its import lands in
daylight cheap **Blok** windows instead of the night the raw Boost would burn.
_Avoid_: "scheduled charging" (a wallbox timer starts at a set time regardless of surplus;
the plan is deadline-driven and surplus-first), "overnight Boost for the trip" (the exact
thing the ladder forbids)

**Vehicle feed**:
The car's charging telemetry entering the estate through exactly one BMW CarData client,
owned by evcc. Resolved 2026-10-12, after finding that BMW killed the legacy MyBMW API for
third-party clients (Approov attestation, autumn 2025) and Home Assistant removed its BMW
integration entirely (March 2026): the mature, quota-aware CarData consumer left in this
ecosystem is evcc's `cardata` vehicle, so HA reads the car from evcc's MQTT output, never
from BMW directly.
_Avoid_: "the BMW integration" (none exists in HA anymore), "CarData in HA" (inverts the
data direction), adding a second client for charging data (the quota is spent once, by the
client that manages its own cache)

**Presence feed**:
The second BMW CarData client, separate from the **Vehicle feed**: self-hosted, connected to
BMW's streaming endpoint, publishing only presence-class data (location, doors) over MQTT for
HA. It exists so location-based automations (chiefly the **Car gate**) get live data without
polling a 50-calls-per-day budget, and it is deliberately not the source of any charging
data.
_Avoid_: a hosted relay (no third party may hold the BMW client credentials - same class of
rule as no cloud in the automation path), duplicating SoC (charging telemetry belongs to the
**Vehicle feed** alone)

**Car gate**:
The anti-theft bound on every session: charging is enabled only while the i4 is home or the
operator is home, judged from the **Presence feed** and phone presence, and a stale feed reads
as away. It exists for exactly one scenario - the house empty for days and a neighbour over
the fence with a cable - so it is a default with sanctioned openings, not a lock.
_Avoid_: "presence lock" (which presence?), "the security feature" (the box's disabled
local start surface is the security feature; the gate is the enable policy)

**Token override**:
The registered RFID chip at the box: a possession credential that may open a session while
the **Car gate** is closed, running under **Surplus-only charge** so a leaked token burns
nothing but **viški**. Import still needs the owner's **Boost** or **Guest override**. It is
also the always-works path when both gate signals die at once (phone flat, stream stale),
and the physical fallback when the whole stack is down: the box's default current is set to
6 A, so a brain-dead session is slow, bounded and visible. It does not open the **Island
guard** - nothing does.
_Avoid_: "RFID authentication" (possession of the token is the authorization, the reader is
just the mechanism), plug-and-charge auto-start (the hole the token replaces: plugging in
alone must start nothing)

**Control-loss watchdog**:
The box-side rule that disables charging when the controller stops talking: an idle box
stays off, a mid-session box stops within a few minutes of the last Modbus write. Resolved
2026-10-12 as fail-closed, never fallback current, because a stale setpoint imports
indefinitely with nobody watching - the same silent degradation the tap bridge taught the
house to distrust, now with a 4-11 kW draw attached.
_Avoid_: "fallback to 6 A" (a fallback current keeps charging with no brain), treating it
as optional (it is the **Island guard**'s posture applied to a different dead input)

**Guest override**:
The explicit, session-scoped opening of the **Car gate** from HA for the away-and-friend
case: one session, expiring on unplug, and the only import path while the gate is closed.
_Avoid_: "disabling the gate" (the gate never comes off; one session opens)

**Surplus dump**:
The heat pump converting surplus into stored heat through its SG-Ready PV input, driven by the
Shelly 1 Gen4 dry contact on the PAC-IF033B-E controller. It is a house load inside the loop,
not a loop participant: the battery eats first, the dump takes the deep end of genuine
export, and the car harvests the residual, which lands disproportionately in the **Charge
floor**'s 1p band. Its trigger must clear its own unmodulated compressor draw with margin,
because the signal is binary and an undersized trigger manufactures import.
_Avoid_: "heat pump PV mode" (vendor wording for the same signal), coordinating it with
evcc (no protocol is needed or wanted - the loop follows whatever export remains), firing it
on band-level export (that is the car's food, and the binary dump would overshoot into
import)

**Connection budget**:
The 3x25 A (17.25 kW) house connection that every big load must fit inside simultaneously:
the 12 kW inverter, the winter heat pump, and an EV. Resolved 2026-10-12 to a static Boost
cap of 9-10 kW via the loadpoint maxcurrent, not dynamic headroom trimming; dynamic
downrating stays a revisit option if real load patterns ever demand it.
_Avoid_: "the 16 A circuit" (that is the charging point's feeder, which caps the box, not
the house), "11 kW Boost" (the point allows it, the connection does not, in a winter evening
alongside the heat pump)

**Conditioning draw**:
The one standing exception to the car staying out of the **Night load**: cabin and pack
preconditioning, which is always a deliberate manual start (MyBMW or in-car, since CarData
is read-only and no command path exists), so the grid import it may cost is consented by
the act itself. The EVSE enable that makes wall-powered conditioning possible is
feed-triggered from the climatisation state on the **Presence feed**, with a parked
low-current enable as the fallback; an HA confirmation card with predicted energy and
battery states is an optional nicety, never a gate.
_Avoid_: "preheat scheduling" (nothing in the house can start it - only the car's owner
can), letting it fall on the traction battery (that is the disabled-EVSE failure mode, and
it burns range on the very morning the trip needs it)

### Utility room thermal

**Vhod**:
The vestibule where shoes and slippers are kept. It has three doors: **Vhodna vrata** to
outside, **Vrata utility** to the utility room, and **Notranja vrata** to the living space.
It has no heat source or sink of its own, so it is a corridor rather than a destination.
_Avoid_: "vrata notri" for the living-space door - two of the three doors are interior from
some standpoint, so relative names are ambiguous. Name each door by where it leads.

**Cooling path**:
The route by which utility room heat reaches the air conditioner: Utility -> **Vrata utility**
-> **Vhod** -> **Notranja vrata** -> conditioned space. Open only when *both* doors are open.
With Notranja vrata shut, Vhod is a dead end that saturates (it reached 26.5 C on 2026-08-07),
so opening Vrata utility alone achieves almost nothing.
_Avoid_: "open the door" - naming a single door hides that the path needs both.

**Plant heat**:
The conversion loss from the inverter and battery pack, dissipated into the utility room.
Afternoon-weighted, peaking 16:00 to 19:00 local because 20 of the 30 panels face west at 45
degrees, so it arrives after the outdoor air peak. December throughput is about a fifth of July.
_Avoid_: treating it as the room's only heat source - the network cabinet's 67 W runs around
the clock and exceeds plant heat in winter.

**Free cooling**:
Purging the utility room through Okno instead of through the **cooling path**. Valid only when
outdoor air is both cooler than the room and at a lower dew point, judged with a 1 K deadband so
the disagreement between an airport station and a room sensor is not read as signal. On a
heatwave afternoon it is never valid, and an extract fan to outside would be wrong year-round:
it cannot beat 36 C air in summer, and in winter it discards heat already banked inside the
thermal envelope.
_Avoid_: "ventilation" - the existing humidity automations use that word for whole-house
moisture, which is a different decision with a different trigger.
_Avoid_: comparing absolute humidity in g/m3. It is volumetric, so it shifts as incoming air
warms to room temperature and reports a gradient across an exchange that moves no moisture at
all. Dew point is the invariant the room settles at. Relative humidity is wronger still.

### Indoor climate

**Room-air sensor**:
A temperature or humidity entity measuring air a person breathes in a room of the house.
The only kind that belongs in `sensor.average_temperature` and `sensor.average_humidity`.
Membership is declared by the `indoor_climate` label and is never inferred from
`device_class`, because the useful line is what the sensor measures rather than where its
device sits.
_Avoid_: "indoor sensor" - the SOFAR inverter heatsink is indoors and is not one.

**Apparatus sensor**:
A temperature entity reporting a machine's own temperature rather than room air: an inverter
heatsink, a battery pack, a PV panel, a CPU. Whether the machine is indoors is irrelevant;
what disqualifies it is that nobody breathes it. Roughly 43 of these entered the house
average when TIGO and SOFAR telemetry landed, taking `sensor.average_temperature` to 47 C on
an August afternoon.

**Whole-house ventilation**:
The decision to open house windows to drop indoor moisture, judged by the average room dew
point against a smoothed ARSO dew point. Distinct from **free cooling**, which purges one
room through its own window on its own threshold. The two read the same ARSO feed and answer
different questions.

**Ventilation window**:
A window whose open state counts as the house being aired, declared by the
`ventilation_window` label. `binary_sensor.utility_okno` is deliberately excluded: it is the
**free cooling** purge path, it stood open about 80% of one sample week, and it was open at
07:30 on all 8 sampled mornings, so admitting it would suppress the morning reminder every
day.

**Station wander**:
The 1 to 2 K the ARSO dew point moves inside a single hour, occasionally 3 K, being an
airport reading 25 km away reported at 0.1 K resolution. Larger than any deadband worth
applying, so a rule comparing it against a slow indoor average has to smooth it rather than
widen around it.
_Avoid_: treating it as sensor noise. The station is reporting real air; it is just not
reporting this house's air.

### Guest autostart (n5p)

**Startup order group**:
The set of Proxmox guests sharing one `startup: order=N` value. `startall` releases groups
in ascending order and waits for every guest in a group to finish starting before releasing
the next. Guests within a group start near-simultaneously (3 s apart for VMs, 0 s for LXCs).

**NFS readiness gate**:
The post-start hookscript on the TrueNAS VM that holds `startall` inside order=1 until the
NFS server can actually serve guest disks. It gates only *later* order groups, which is why
the TrueNAS VM must stay alone in order=1.
_Avoid_: "NFS check" - the gate is a blocking hold, not a test that reports a result.

**Storage ready**:
The NFS server can complete an `OPEN` and a write on the exports that back guest disks.
Strictly stronger than "answering": `showmount` replies while the server is still refusing
every open.
_Avoid_: "NFS is up" - that phrase hid the distinction that caused the 2026-08-08 incident.

**Grace period**:
The 90 s window after `nfsd` starts during which the server refuses all non-reclaim `OPEN`
requests with `NFS4ERR_GRACE`, so clients can reclaim prior state first. Per-server, not
per-export. No guest disk can be opened until it ends.

**Start budget**:
The timeout PVE computes per guest for the kvm start phase (`config_aware_timeout`: 30 s
base, plus 5 s per NIC, x4 with PCI passthrough). Not configurable from the guest config,
and unrelated to `startup: up=N`, which is a delay *after* a guest starts.

### Guest state and rebuilds

**Local-rootfs state**:
Service state stored on a guest's own disk rather than on an NFS export, because the
workload is NFS-hostile (SQLite locking, a Postgres or Mongo data directory, a Prometheus
TSDB). It is the state a guest rebuild must carry across by hand; everything else on the
disk is reproducible by converge.
_Avoid_: "local data" - the distinction is not where the bytes are useful, it is which
bytes survive the guest being replaced.

**NFS-backed state**:
Service state on a TrueNAS export, reachable from any guest that mounts it. It survives a
guest rebuild untouched, which is also exactly why two guests must never run the same
service at once - both would write the same files.

**Staged cutover**:
The guest replacement sequence in which the new guest's services are converged only after
the old guest is stopped: copy **local-rootfs state** out, stop the old guest, provision
the replacement on the same IP, converge the base layer, restore state, converge the
service roles. Trades a bounded outage for never having two instances of a service live
against the same **NFS-backed state**.
_Avoid_: "blue-green", "DNS flip" - both imply the two instances run concurrently, which
is the case this pattern exists to prevent.

**Orphaned guest**:
A stopped predecessor left behind by a **staged cutover**, still present on the hypervisor
but no longer declared in `vars/lxc.yml` or `vars/vms.yml`. It is the only rollback on a
fleet where snapshots are structurally impossible, and it is invisible to Ansible's onboot
drift correction, which loops over declared guests only. An orphaned guest left at
`onboot: 1` will be started by the boot-time reconciler on the next power event, colliding
with its replacement on the same IP.

### Fleet SSH access

**Pinned host key**:
An SSH server key recorded in the repo-tracked `ansible/known_hosts`, matched by the IP Ansible connects to. A converge refuses a changed key on a pinned IP and auto-pins a new IP on first contact (`accept-new`); provision playbooks refresh the pin for every guest they (re)build.
_Avoid_: "known_hosts" unqualified - the control node has two: the repo-tracked `ansible/known_hosts` that fleet converges read, and the user's `~/.ssh/known_hosts`, which fleet connections no longer read.

**TOFU**:
Trust on first use - accepting a host key at first contact with no out-of-band check. Every pin starts as one; the fleet accepts it only when the trust event is a deliberate, checkable step (a provision keyscan, the pre-seed fingerprint spot-check), never a silent moment mid-converge.
_Avoid_: "verified" - a TOFU pin detects key change, not imposture at first contact.

### Socket proxy

**Socket proxy**:
The digest-pinned wollomatic/socket-proxy container fronting the raw Docker socket on each Docker runtime host; the only container that touches the socket itself. Serves exactly the method+path pairs its **allowlist** permits, default-deny everything else.
_Avoid_: "docker socket" (that is the raw socket the proxy exists to keep containers away from) and "socket-proxy network" for the container.

**Socket proxy network**:
The isolated Docker network that is the sole access boundary to the **socket proxy**; membership, not source IPs, decides who can call it. Consumers join it (autoheal everywhere, Uptime Kuma on the containers VM) and never mount the raw socket.
_Avoid_: "the Docker network" (there are many) and "socket-proxy container" for the network.

**Allowlist**:
The per-method regex contract of the **socket proxy**, anchored so only the exact pairs listed pass. Deliberately excludes container inspect, which returns every env_file value as `Config.Env`; allowing it once let a Kuma compromise read PDS and Paperless secrets. Retired the Kuma docker-type monitors that required it.
_Avoid_: "GET access" (the allowlist is per method+path, not per method).

### Service health

**Respawned crash**:
A process crash inside a container that the container's own supervisor restarts, so the
container itself never restarts. `RestartCount` stays 0, the Docker healthcheck stays
green, and autoheal never fires. The only trace is a line in the container's log. Named
after the immich ML worker, where gunicorn's master respawned a segfaulting worker 13 times
across four months without a single alert.
_Avoid_: "crash loop" - a crash loop is visible precisely because the container restarts;
this is the opposite case.

**Blind source**:
An Alloy log source that is configured, running and reporting healthy while shipping
nothing, because its target list resolved to empty. `systemctl is-active` says active,
the component logs no error, and the alerts that read its stream simply stay quiet,
which is indistinguishable from the host being fine. The only tell is a zero in the
source's own target-count metric (`loki_source_file_files_active_total`,
`loki_source_docker_target_entries_total`), already scraped and, so far, never watched.
It has now happened four times: docker logs with no `discovery.docker`, host metrics
pushed to a disabled receiver, container logs missing until a second converge, and
n5p plus rpi4 tailing a `/var/log/syslog` that Debian 13 never creates.
_Avoid_: "log shipping is broken" - nothing is broken; the source is doing exactly what
its empty target list asks of it.

### Model residency (n5p)

**On-demand model**:
A model that loads on the first request and unloads after an idle **model TTL**, so it holds no
host RAM between sessions.
_Avoid_: "lazy load" (says nothing about the memory coming back)

**Resident model**:
A model kept loaded continuously; it does not survive memory pressure, because its pages are
**reclaimable weights**, so it degrades into an **on-demand model** exactly when another workload
needs the RAM.
_Avoid_: "pinned", "always-on"

**Model TTL**:
The idle window measured from the last request before a model unloads - 30 minutes for the local
LLM, 300 s (the Immich default) for the ML models.
_Avoid_: "request timeout" (that bounds one call; this bounds idle time)

**Cold start**:
The load paid on the first request after an unload, about one second per GiB on n5p, because local
disk and the TrueNAS share both read near 1 GB/s.
_Avoid_: "warm-up"

**Reclaimable weights**:
Weights held as file-backed mmap pages, which the kernel may drop under pressure, so a model slows
down instead of forcing swap or an OOM kill.
_Avoid_: "shared memory"

**Reclaim order**:
Which pages the kernel drops first when the host is short - reclaimable file-backed pages before
anonymous ones. It is an outcome of reclaimability, not a setting.
_Avoid_: "priority", "preemption" (cgroup v2 offers neither between sibling groups)

**Model artifact**:
A read-only set of weight files. It lives on a TrueNAS share but is not **NFS-backed state**: being
immutable, two guests may read it at once and rollback is deleting a file.
_Avoid_: "model data" (that word collides with the **local-rootfs state** / **NFS-backed state** split)

**ML burst**:
One immich ML residency window: three models loaded, about 4.1 GiB of host RAM and 938 MB of GTT at
peak, then everything freed 300 s after the last request.
_Avoid_: "ML job" (a job is one queue task; the burst is the whole window)

### Hermes agent

**Agent brain**:
The provider and model serving the hermes gateway's main chat loop, wired through
`model.provider` / `model.default` plus one API key in `.env`. Switching brains is a vars edit and
a converge, never an install or a rebuild; the local-model track swaps it in the same way when its
gate clears.
_Avoid_: "the model" (collides with the local-model plan's llama-server and with **model
artifact** - those are weights, this is a subscription), "provider setup" (the interactive
`hermes model` wizard is exactly what the Ansible role exists to bypass)

**Event wake**:
A house event starting an agent turn on its own, through the Home Assistant gateway
platform's WebSocket subscription. Bounded by two things: the entity allowlist in the
role's `hermes_ha_watch_entities`, because upstream forwards nothing without one, and the
per-entity cooldown. Every wake spends brain tokens, so an entry has to pass the
watch-decision gate and gets pruned monthly.
_Avoid_: "trigger" (that is the HA-side concept, not the agent turn), "subscription" (says
nothing about who pays)

**Pull-only**:
Hermes acting on the house because a human asked, over Telegram. This is one of two
initiators, not the whole posture: see **Event wake** for the house-initiated path. The
ha-mcp include whitelist is the HA privilege boundary (approvals gate terminal commands,
not MCP tool calls), and the four built-in Home Assistant REST tools that `HASS_TOKEN`
also enables are suppressed so the whitelist stays the only tool surface.
_Avoid_: "passive" (says nothing about who initiates), "read-only" (service calls still act -
they just need a human to ask first)

### EV hunt

**Hunt monitor**:
The scheduled hermes cron job that watches the damaged-car platforms against the
purchase filters in `.claude/state/ev-purchase/plan.md`. A scheduled turn, so it never
passes the watch-decision gate that bounds **Event wake**.
_Avoid_: "the monitor" (collides with the Prometheus monitoring stack), "the alert" (that
is one message it may send)

**Filter contract**:
The split of the purchase rules into machine-checkable bounds the fetch script enforces
(price, km, model, airbags, drivable) and the judgment rules the brain applies to
survivors (bolt-on zone, pack-untouched, deal-trigger). Bounds are Ansible vars; rule
changes are reviewed diffs.
_Avoid_: "the filters" (silent about who checks what)

**Seen set**:
The script-owned JSON of every listing id the hunt has observed, with first-seen and
price history. "New" means absent from it; a price decrease re-alerts. It is the data
source for the **market digest**, never written by the brain.
_Avoid_: "cache" (it is the dedup record, not a fetch cache), "database"

**Match** vs **near-miss**:
A candidate inside the purchase bounds is a match and always alerts; one within the
+20% band above a bound is a near-miss and alerts only when damage or mileage is
exceptional. Near-misses stay in the **seen set** so a price cut re-alerts into range.
_Avoid_: "hit" (says nothing about which side of the bound)

**Market digest**:
The weekly Sunday summary of the **seen set** - volume, price movement, sold listings,
near-miss inventory - that feeds the week-4 market review (switch-trigger reset
evidence) in the EV purchase plan.
_Avoid_: "report" (every platform has reports; this one exists to reset the switch-trigger)

**Degraded run**:
A hunt run whose fetch script failed, so the brain fell back to web tools for data. Its
alerts are marked degraded and advance no **seen set** state, so a later script run
re-alerts the same listing rather than trusting fallback data.
_Avoid_: "fallback run" (hides that the data is unverified)

### Pi chat remote

**Attach**:
Connecting the phone to a pi session already running in a TUI at the Mac. One transcript, one writer; desk and phone see the same session by construction. v1 supports attach only.
_Avoid_: "sync" (implies two transcripts being reconciled) and "open the session file" (attach targets a running process, not a file)

**Spawn**:
The bridge starting its own headless pi session instead of attaching. A second pi on the same project with a diverged session tree. Goal-state feature, not v1.
_Avoid_: "new session" (ambiguous between a fresh attach and a spawn)

**Bridge**:
The always-on service that pi sessions dial into and the phone talks to. Runs as a Docker container on the containers VM, reachable over the tailnet; serves every host (Mac, dev VM) from one endpoint. Holds the session registry, auth, and notification dispatch.
_Avoid_: "relay" (it owns registry and auth, not a dumb pass-through); "the server" (every component is a server; the name must say what it does)

**Steer**:
A message injected while the session is streaming. Pi delivers it after the current assistant turn's tool calls finish and before the next LLM call, so the agent adjusts course without the turn ending. Mechanism: `pi.sendUserMessage` with `deliverAs: "steer"`.
_Avoid_: "interrupt" (tool calls already running still complete; only the next LLM call changes)

**Follow-up**:
A message delivered only once the agent has no more tool calls. The "when you are done" path for prompts sent mid-turn. Mechanism: `deliverAs: "followUp"`.
_Avoid_: "queue" (pi has no single queue; steer lands at the next LLM call, follow-up lands at the end of the work)

**Abort**:
Ending the running turn from the phone. The session stays attached and keeps everything already in the transcript.
_Avoid_: "kill the session" (abort ends a turn, not the session)

**Dial-in**:
The outbound WebSocket from a session's extension to the bridge, carrying the live event stream up and prompts down. Its presence is the session's online status; a drop while the session was working means an interrupted turn.
_Avoid_: "connection to the session" (the direction is the point: sessions always dial out, nothing listens on the workstation)

**Remote client**:
The phone-side PWA served by the bridge. Installed to the home screen on the Galaxy S24+; compatible with iOS. Talks to the bridge over the tailnet.
_Avoid_: "the app" (reads as a native app; v1 ships no native app)

## Relationships

- A **Job** produces exactly one **Job end**, which is either **Finished** or **Cancelled/aborted**
- **Map-derived entities** must never be referenced by automations or dashboards; only **Device-level entities** may be
- A **Fresh fault** at a low-progress **Job end** means aborted; without it, the same job end is a deliberate cancel
- A **Time push** lands only on a **Time-capable device**; the other 19 Matter nodes have nowhere to store time
- A **Border router host** carries Thread traffic to the LAN only while it holds an address and route in the **on-link prefix**; the OTBR container can be healthy, with every Thread child attached, while the host underneath it has lost both, because those two live on opposite sides of the container boundary
- **Fabric state** loss is re-commission-class, like Thread dataset loss; the two stores back different halves of the same Matter estate
- **Passive Mode** is reachable only over the **inverter bridge**; the **logger stick** answers no local protocol at all, so it can be neither read nor written
- The **inverter bridge** and the **tap bridge** are the same hardware in the same enclosure and are opposite in every property that matters: one is read-write and must be terminated, the other is read-only and must not be
- A **module** is reported under a **node ID** that belongs to one **TAP gateway**, but its panel position comes only from TIGO EI - nothing on the bus carries it
- The **monitoring bus** and the **meter bus** both leave the inverter as RS485 on pins 1 and 2 of an RJ45 jack, so a cable moves between them unchanged; only the jack it is plugged into decides whether the inverter answers or competes
- **Blok** boundaries drive when the battery should discharge; the **viški** / **manki** spread drives why self-consumption is preferred over export
- A **Surplus-only charge** keeps the car out of the **Night load**, so the battery's sizing assumption survives the EV: the car eats only what would otherwise become **viški**, and a **Trip recovery** is the only sanctioned reason it may ever do otherwise
- The **Surplus signal** needs no meter on the **Meter bus** and no clamp anywhere: the internal CTs see the whole house (verified 2026-10-12), so the DTSU666 stays bypassed and 0x0488 remains the loop input
- The charging point lands on the **Backed-up panel**, so the **Surplus signal** sees the car with no extra metering, and charging carries an **Island guard** because the point stays live when the grid is gone
- In island mode the **Surplus signal** still reads ~0, so the surplus loop is structurally blind to the island; the **Island guard** must read the inverter's state directly and can never be inferred from the loop's own balance
- **Battery-first** makes the EV and the battery never compete: whatever the EV takes was already on its way to the grid, so the battery's evening job is untouched by charging
- **Boost** is session-scoped and self-reverting, so the **Night load** policy cannot be violated by a forgotten mode, while **Permissionless surplus** keeps guest charging free of ceremony
- The **Vehicle feed** and the **Presence feed** are two CarData clients with disjoint jobs: charging data flows only through evcc, presence only through the self-hosted bridge, so neither quota is spent twice and neither source is trusted for the other's job
- The **Car gate** ORs signals from different failure domains - phone presence dies with the phone, the **Presence feed** dies with BMW - so one dead signal never locks out a resident car, and the **Token override** covers the both-dead case
- A **Token override** session runs **Surplus-only charge**: possession buys **viški**, never grid import, so the import path stays the owner's alone (**Boost**, **Guest override**)
- Surplus has three sinks in fixed order: the battery eats all it can take, the **Surplus dump** takes the deep end of genuine export, and the EV harvests the residual - so **Battery-first** binds the other two with no protocol between them
- The **Surplus dump** converts some above-floor hours into **Charge floor** band hours: once the compressor runs, the residual export is small, which raises rather than lowers the value of 1p switching
- A **Conditioning draw** spends **Night load** only behind a manual start: no one taps preheat, nothing draws - the exception is bounded by consent, not by a timer
- The **Control-loss watchdog**, the **Island guard** and the **Car gate** are one fail-closed posture applied to three dead inputs: a dead controller, a dead grid and an empty house each de-energize the point rather than improvise
- The **Token override** is the sanctioned physical opening in two of the three: possession at the box starts a 6 A local session through a closed gate or a dead stack, and nothing opens the **Island guard**
- The **Connection budget** bounds **Boost** at 9-10 kW: a winter evening's heat pump plus house load plus full 11 kW would trip a 3x25 A main, and a rare deliberate override gains nothing by living on that edge
- A **Charge plan** is the only scheduled import: it escalates late enough that its import lands in daylight cheap **Blok** windows, which is the (b) rung of the **Trip recovery** ladder
- The **gross-import rule** is what widens that spread: a self-consumed kWh avoids energy, omreznina, prispevki, trosarina and the DDV on all of it, while an exported kWh earns only the viski rate plus DDV
- **Dobroimetje** carries across an **obračunsko obdobje** boundary but never expires, so surplus value is deferred rather than lost
- The **NFS readiness gate** delays only *later* **startup order groups**, so any guest sharing order=1 with the TrueNAS VM starts ungated
- **Storage ready** cannot be true before the **grace period** ends; any probe that goes green earlier is measuring something other than what guests need
- A guest whose **start budget** expires while the **grace period** is still running fails permanently - `startall` never retries a failed guest and still reports `TASK OK`
- The **cooling path** is open only when both **Vrata utility** and **Notranja vrata** are open; with either shut, **free cooling** is the only remaining lever, and it works only while outdoor air is below the room
- **Plant heat** peaks after the outdoor air peak, so the hours of greatest need are hours when **free cooling** is becoming more viable rather than less
- **NFS-backed state** survives a guest rebuild but forbids concurrency; **local-rootfs state** is the opposite on both counts, which is why the two demand different handling in a **staged cutover**
- A guest's rebuild cost is set by its **local-rootfs state**, not by its disk size - the six 26.04 rebuild targets total 43.6 GB on disk but only ~10 GB of state that a converge cannot recreate
- An **orphaned guest** is rollback only while it stays stopped; leaving it at `onboot: 1` converts the safety net into a duplicate-IP incident on the next power event
- A **staged cutover** replaces a guest on the same IP with a fresh host key, so its **pinned host key** is stale until the provision playbook's keyscan hook refreshes it; converging against an un-refreshed pin fails hard rather than trusting the new key
- A **respawned crash** is invisible to the container-restart alert by construction, so detecting one has to start from the container's logs, never from its restart count or health status
- Where a guest's **local-rootfs state** is an index over its **NFS-backed state** - Immich's Postgres over the photo library - a **staged cutover** rollback desynchronises the two: anything written after cutover survives on NFS with no row in the restored index. Rollback value expires at the first write, not on a timer, which makes the **orphaned guest** worth far less here than for a guest whose state is self-contained
- A **blind source** and a **respawned crash** fail identically from the outside: the evidence that would show a problem is absent rather than negative, so every liveness check reads green. Both are found only by asking a component to account for its own throughput - target count for the source, log lines for the supervisor - never by asking whether it is running
- The taptap bridge is a **blind source** by default: if the **tap bridge** or the CCA goes quiet it keeps running and keeps its MQTT connection open, so its LWT never fires and a container-running probe stays green. Neither its heartbeat file nor its MQTT topic accounts for its own throughput: the heartbeat counts loop passes, and the topic is republished on a timer carrying the bridge's own clock, so both stay fresh while the data inside them goes stale. The optimisers' own last-report time inside the payload is the only value that moves with the plant
- A **blind source** silently disables every alert reading its stream, so the alert going quiet is the symptom; on `job="system"` that is Error Log Spike, Service Crash Detected and Authentication Failure Spike at once
- A **room-air sensor** enters the house averages by label; an **apparatus sensor** never does, whatever room its machine stands in
- **Whole-house ventilation** and **free cooling** read the same ARSO dew point and are opposite in stability: opening the utility window pulls that room toward outdoor and deeper inside its deadband, while opening house windows pulls the house average toward outdoor and out of the ventilation condition. Free cooling therefore settles on a bare deadband, and ventilation needs two thresholds
- The **ventilation window** set excludes the one window **free cooling** drives, so the two decisions cannot silence each other
- **Station wander** is why the ventilation comparison smooths ARSO to an hourly mean instead of widening its band: a deadband large enough to cover the wander would be large enough to miss the weather
- A **resident model** buys less than it looks: under the pressure it exists to survive, its **reclaimable weights** are the first pages dropped, so it becomes an **on-demand model** paying a **cold start** at exactly the wrong moment
- A **model TTL** counts idle time from the last request, not the length of a session, so a busy agent loop or an **ML burst** keeps a model loaded well past its nominal TTL
- An **on-demand model** and the **ML burst** collide only if an LLM session is open when the burst starts; reclaim settles it in favour of ML, because the LLM is the side holding **reclaimable weights**
- Weights are a **model artifact**, not **NFS-backed state**, so the ban on two guests sharing an NFS path does not reach them, and a **staged cutover** cannot desynchronise them from an index the way Immich's Postgres can
- A guest's own `memory.high` must sit above its working set, or the cgroup reclaims the very pages a **model artifact** runs from; the soft limit is a floor under the model, never a lever against another workload
- **Reclaim order** falls out of reclaimability rather than priority: **reclaimable weights** yield before the ML workload's anonymous GPU buffers, so ML wins the morning **ML burst** without being configured to win
- A **Pull-only** turn and an **Event wake** are the same agent with different initiators, so the wake list has to be a token budget rather than a mirror of what the house reports

## Example dialogue

> **Dev:** "The mower docked - is the **Job** over?"
> **Domain expert:** "Only if **progress** reset to 0. It pauses on the dock mid-**Job** overnight without ending; interruptions show as `returning`/`paused`, never `docked`."
> **Dev:** "It stopped at 38% and there's a **fresh fault** - notify?"
> **Domain expert:** "Yes, that's aborted. The same stop without a fresh fault is a deliberate cancel - stay silent."

> **Dev:** "Can we point the sensors at our NTP server?"
> **Domain expert:** "No - nothing on the fleet speaks NTP. Time reaches a **Time-capable device** only as a **Time push** from matter-server, and the device forgets on every power cycle unless the push repeats."

> **Dev:** "The OTBR is healthy and every child is attached - why is the border router still the suspect?"
> **Domain expert:** "Because the mesh ends at the container. If the **Border router host** has no route in the **on-link prefix**, the devices' replies reach the **Backbone link** and go nowhere."

## Flagged ambiguities

- "task status sensor" - the deleted `sensor.vrt_luba_task_area_path` looked like a stable device-level status enum but was a **map-derived entity** whose display name was bugged upstream (Mammotion-HA #700). Resolved: job state is reconstructed from device-level entities only.
- "push NTP time to all devices" - resolved: the mechanism is a **Time push** (Matter commands, no NTP protocol), and "all devices" is in practice one device (the ALPSTUGA). NTP appears in this project only as clock hygiene on the hosts, chiefly rpi4.
- "open the door to the utility room" - resolved: the unit is the **cooling path**, not either door on its own. **Vrata utility** alone routes heat into **Vhod**, which has no sink and saturates; only both doors together reach the air conditioner.
- "the wired bridge" - unambiguous while one Elfin EE11A existed, ambiguous the moment the second was installed on the TIGO CCA. Resolved: **inverter bridge** and **tap bridge**, each named for what is on the far end. The distinction is physical, not cosmetic - the inverter link needs 120 ohm termination and the tap must never be terminated.
- "NFS is up" - the 2026-07-22 **NFS readiness gate** treated a `showmount` reply as proof that guests could start. On 2026-08-08 that went green 1 s before `nfsd` had even started and 91 s before the **grace period** ended, and HAOS missed its **start budget** by one second. Resolved: the term is **Storage ready**, and only a completed open-and-write on a real NFS mount proves it.
- "the OTBR" - used for both the `otbr` container and the `containers` VM that runs it, which is how the 2026-09-30 Matter outage read as healthy everywhere while 21 devices were unreachable. Resolved: the container is the OTBR container and the VM is the **Border router host**; they fail independently.
