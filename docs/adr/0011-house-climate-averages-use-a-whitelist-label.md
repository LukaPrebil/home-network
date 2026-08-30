# House climate averages use a whitelist label, not a device_class sweep

Status: accepted (2026-08-30)

`sensor.average_temperature` and `sensor.average_humidity` are the house-wide indoor
climate figures. `sensor.inside_dewpoint` is computed from both, and the whole-house
ventilation reminder is decided from that dew point. They were written as entity sweeps:
take every `sensor` whose `device_class` is `temperature` (or `humidity`), drop anything on
floor `Zunaj` or labelled `Outside` / `Zunaj`, drop `thermal_comfort` entities, average the
rest. When the house held little but room sensors this was correct and needed no
maintenance.

TIGO optimizer telemetry and the SOFAR inverter bridge landed in August 2026. Neither
touched the ventilation automations. Both registered a large population of
`device_class: temperature` entities that the sweep had no way to reject: 30 rooftop PV
panel temperatures, 5 string aggregates, 7 inverter internals, and the ARSO outdoor UTCI
reading. The average grew from roughly 9 sensors to 51, of which 9 were rooms. Two inverter
sensors report a literal `0` and were averaged in as though they were cold rooms.

The result was not subtle and went unnoticed for weeks because nothing alerts on it.
Hourly statistics put `sensor.average_temperature` at **47.0 C** on 2026-08-27 and
**46.3 C** on 2026-08-28, peaking every afternoon and falling back to 22-25 C overnight.
That is the roof's diurnal curve, not the house's. `sensor.inside_dewpoint` followed it to
38-39 C, and `binary_sensor.good_to_ventilate` was comparing a real outdoor dew point
against it. The visible symptom was notification spam on 2026-08-30, which is a
downstream effect of a decision input that had been wrong since the PV work merged.

The obvious repair is to extend the blacklist: label the TIGO and SOFAR entities so the
sweep drops them. We rejected it, because the blacklist cannot express the distinction the
bug turns on. The existing exclusions all mean "outdoors", and the worst offender is not
outdoors. `sensor.utility_sofar_inverter_heatsink_temperature` sits in the utility room.
Labelling it `Outside` would be false, and the label's own description ("devices located
inside, but the entity refers to something outside") does not cover it. The real line is
between air a person breathes and a machine's own temperature. `CONTEXT.md` now names
these **room-air sensor** and **apparatus sensor**.

A blacklist is also the wrong default. It admits every new entity until someone notices,
and the failure is silent: no error, no unavailable state, just a number that drifts. This
estate keeps adding telemetry, and PV in particular will keep adding per-panel sensors.

Both averages therefore iterate `label_entities('indoor_climate')` and average the members
whose `device_class` matches, skipping `unavailable` and values outside a sanity range. The
label carries 20 entities, the temperature and humidity channels of the 9 live room devices
plus the Vhod sensor that is currently battery-dead and rejoins on its own. Adding a room
means labelling its two entities. A new integration is excluded until someone opts it in.

We considered the `min_max` helper, which is the documented native answer for averaging
several sensors and handles unavailable members declaratively. It takes a static entity
list, so it cannot follow a label, and it would need editing in two places whenever a room
is added. The label was chosen for that extensibility, accepting that the averages stay
template helpers rather than native ones.

The same label mechanism now gates the ventilation window set, under `ventilation_window`.
That decision is documented in `docs/home-assistant/automations/ventilation-humidity.md`
rather than here, because it is a behaviour choice about one automation rather than a
structural one about how house-wide figures are computed.

## Consequences

- A new room-air sensor contributes nothing until labelled `indoor_climate`. This is the
  intended failure direction, but it is a step that is easy to forget and produces no error.
- The averages remain template helpers, against the general preference for native helpers.
- Any future consumer of "indoor temperature" should read the averages rather than sweeping
  `device_class` itself, or it reintroduces this bug in a new place.
- Long-term statistics for `sensor.average_temperature` and `sensor.inside_dewpoint` before
  2026-08-30 are contaminated and should not be used for trend analysis.
