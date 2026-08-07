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
_Avoid_: conflating it with the **wired bridge**, the Elfin EE11A on the inverter COM
port that will carry both monitoring and control. Both reach the same inverter; only
the bridge can be read or written.

## Relationships

- A **Job** produces exactly one **Job end**, which is either **Finished** or **Cancelled/aborted**
- **Map-derived entities** must never be referenced by automations or dashboards; only **Device-level entities** may be
- A **Fresh fault** at a low-progress **Job end** means aborted; without it, the same job end is a deliberate cancel
- A **Time push** lands only on a **Time-capable device**; the other 19 Matter nodes have nowhere to store time
- **Fabric state** loss is re-commission-class, like Thread dataset loss; the two stores back different halves of the same Matter estate
- **Passive Mode** is reachable only over the **wired bridge**; the **logger stick** answers no local protocol at all, so it can be neither read nor written
- **Blok** boundaries drive when the battery should discharge; the **viški** / **manki** spread drives why self-consumption is preferred over export

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
