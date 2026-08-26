# Home Network (Homelab + Home Assistant)

Single-operator homelab: Ansible-managed infrastructure plus a Home Assistant estate (automations, dashboards) managed via `ha-mcp` tools. This context captures the domain language that recurs across HA automation design.

## Language

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

### Matter fabric (time)

**Time push**:
Controller-originated delivery of wall-clock time to a Matter device via the SetUTCTime / SetTimeZone / SetDSTOffset commands, sent by matter-server.
_Avoid_: "NTP" (no NTP protocol touches any device on this fleet; the devices cannot be NTP clients)

**Time-capable device**:
A Matter node exposing the Time Synchronization cluster (0x0038); currently only the ALPSTUGA air quality monitor, and only in its TZ-only form.

**Fabric state**:
matter-server's on-disk store (`/srv/docker/matter-server/data` on rpi4) holding the fabric credentials and node table; losing it means re-commissioning every Matter device.
_Avoid_: "matter data dir"

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
Surplus and deficit against the metering point over a settlement period. Viški are
credited at a much lower rate than manki are charged, which is why self-consumption
beats export.

**Logger stick**:
The SOFAR LSW-3 Wi-Fi dongle that talks to SofarCloud. Port 8899 is open but answers no
protocol, so it carries nothing locally and is not a data source.
_Avoid_: conflating it with the **inverter bridge**. Both reach the same inverter; only
the bridge can be read or written.

**Inverter bridge**:
The Elfin EE11A on the SOFAR inverter's COM port, carrying Modbus RTU at 9600 in both
directions; the only path by which **Passive Mode** can be read or written. Needs 120
ohm termination.
_Avoid_: "wired bridge" - both EE11A units are wired, so that name stopped identifying
anything once the second one was installed.

**Tap bridge**:
The Elfin EE11A at `192.168.1.162` on the TIGO CCA's GW/TAP port, serving the bus as a
TCP stream on port 7160. Read-only by construction: it drives the RS485 transmitter
only when a TCP client writes, and nothing ever does.
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

## Relationships

- A **Job** produces exactly one **Job end**, which is either **Finished** or **Cancelled/aborted**
- **Map-derived entities** must never be referenced by automations or dashboards; only **Device-level entities** may be
- A **Fresh fault** at a low-progress **Job end** means aborted; without it, the same job end is a deliberate cancel
- A **Time push** lands only on a **Time-capable device**; the other 19 Matter nodes have nowhere to store time
- **Fabric state** loss is re-commission-class, like Thread dataset loss; the two stores back different halves of the same Matter estate
- **Passive Mode** is reachable only over the **inverter bridge**; the **logger stick** answers no local protocol at all, so it can be neither read nor written
- The **inverter bridge** and the **tap bridge** are the same hardware in the same enclosure and are opposite in every property that matters: one is read-write and must be terminated, the other is read-only and must not be
- A **module** is reported under a **node ID** that belongs to one **TAP gateway**, but its panel position comes only from TIGO EI - nothing on the bus carries it
- **Blok** boundaries drive when the battery should discharge; the **viški** / **manki** spread drives why self-consumption is preferred over export
- The **NFS readiness gate** delays only *later* **startup order groups**, so any guest sharing order=1 with the TrueNAS VM starts ungated
- **Storage ready** cannot be true before the **grace period** ends; any probe that goes green earlier is measuring something other than what guests need
- A guest whose **start budget** expires while the **grace period** is still running fails permanently - `startall` never retries a failed guest and still reports `TASK OK`
- The **cooling path** is open only when both **Vrata utility** and **Notranja vrata** are open; with either shut, **free cooling** is the only remaining lever, and it works only while outdoor air is below the room
- **Plant heat** peaks after the outdoor air peak, so the hours of greatest need are hours when **free cooling** is becoming more viable rather than less
- **NFS-backed state** survives a guest rebuild but forbids concurrency; **local-rootfs state** is the opposite on both counts, which is why the two demand different handling in a **staged cutover**
- A guest's rebuild cost is set by its **local-rootfs state**, not by its disk size - the six 26.04 rebuild targets total 43.6 GB on disk but only ~10 GB of state that a converge cannot recreate
- An **orphaned guest** is rollback only while it stays stopped; leaving it at `onboot: 1` converts the safety net into a duplicate-IP incident on the next power event
- A **respawned crash** is invisible to the container-restart alert by construction, so detecting one has to start from the container's logs, never from its restart count or health status
- Where a guest's **local-rootfs state** is an index over its **NFS-backed state** - Immich's Postgres over the photo library - a **staged cutover** rollback desynchronises the two: anything written after cutover survives on NFS with no row in the restored index. Rollback value expires at the first write, not on a timer, which makes the **orphaned guest** worth far less here than for a guest whose state is self-contained
- A **blind source** and a **respawned crash** fail identically from the outside: the evidence that would show a problem is absent rather than negative, so every liveness check reads green. Both are found only by asking a component to account for its own throughput - target count for the source, log lines for the supervisor - never by asking whether it is running
- The taptap bridge is a **blind source** by default: if the **tap bridge** or the CCA goes quiet it keeps running and keeps its MQTT connection open, so its LWT never fires and a container-running probe stays green. Its heartbeat file is the only thing that accounts for its own throughput
- A **blind source** silently disables every alert reading its stream, so the alert going quiet is the symptom; on `job="system"` that is Error Log Spike, Service Crash Detected and Authentication Failure Spike at once

## Example dialogue

> **Dev:** "The mower docked - is the **Job** over?"
> **Domain expert:** "Only if **progress** reset to 0. It pauses on the dock mid-**Job** overnight without ending; interruptions show as `returning`/`paused`, never `docked`."
> **Dev:** "It stopped at 38% and there's a **fresh fault** - notify?"
> **Domain expert:** "Yes, that's aborted. The same stop without a fresh fault is a deliberate cancel - stay silent."

> **Dev:** "Can we point the sensors at our NTP server?"
> **Domain expert:** "No - nothing on the fleet speaks NTP. Time reaches a **Time-capable device** only as a **Time push** from matter-server, and the device forgets on every power cycle unless the push repeats."

## Flagged ambiguities

- "task status sensor" - the deleted `sensor.vrt_luba_task_area_path` looked like a stable device-level status enum but was a **map-derived entity** whose display name was bugged upstream (Mammotion-HA #700). Resolved: job state is reconstructed from device-level entities only.
- "push NTP time to all devices" - resolved: the mechanism is a **Time push** (Matter commands, no NTP protocol), and "all devices" is in practice one device (the ALPSTUGA). NTP appears in this project only as clock hygiene on the hosts, chiefly rpi4.
- "open the door to the utility room" - resolved: the unit is the **cooling path**, not either door on its own. **Vrata utility** alone routes heat into **Vhod**, which has no sink and saturates; only both doors together reach the air conditioner.
- "the wired bridge" - unambiguous while one Elfin EE11A existed, ambiguous the moment the second was installed on the TIGO CCA. Resolved: **inverter bridge** and **tap bridge**, each named for what is on the far end. The distinction is physical, not cosmetic - the inverter link needs 120 ohm termination and the tap must never be terminated.
- "NFS is up" - the 2026-07-22 **NFS readiness gate** treated a `showmount` reply as proof that guests could start. On 2026-08-08 that went green 1 s before `nfsd` had even started and 91 s before the **grace period** ended, and HAOS missed its **start budget** by one second. Resolved: the term is **Storage ready**, and only a completed open-and-write on a real NFS mount proves it.
