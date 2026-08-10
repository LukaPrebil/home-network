# Utility Room Climate Advisory

Keeps the utility room cool by advising on two doors and a window rather than by adding
cooling hardware. The room holds the PV enclosure, the four BTS-5K battery modules, the
network cabinet and the laundry, and the plant adds 500 to 900 W on a summer afternoon.

See ADR 0011 for why there is no fan or split, and `CONTEXT.md` for the **cooling path**,
**plant heat** and **free cooling** definitions.

## The mechanism

The only heat sink in the building is the MSZ-AY42 split in Stopnišče. Utility room heat
reaches it along the **cooling path**:

```
Utility -> Vrata utility -> Vhod -> Notranja vrata -> conditioned space -> AC
```

The path is open only when **both** doors are open. With Notranja vrata shut, Vhod is a dead
end that saturates, and opening Vrata utility alone achieves almost nothing.

Measured on 2026-08-10: window shut and both doors open took the room from 31.7 °C to 26.1 °C
while outdoor climbed to 37 °C. The same hour the previous day, with the path shut, the room
was 31.8 °C against a 4 K cooler outdoor.

## Entities

| Entity | Role |
|---|---|
| `sensor.utility_climate_status` | The decision. State says why there is or is not a notification |
| `sensor.utility_climate_action` | The advice text, or `-` when there is nothing to do |
| `sensor.utility_temp_rate` | Derivative of the room temperature, K/h, 30 min window |
| `sensor.outdoor_temp_24hr_mean` | Statistics mean over 24 h of the ARSO outdoor temperature. Gates the purge |
| `input_number.utility_temp_engage` | Urgency threshold, default 26.0 °C |
| `input_boolean.utility_climate_active` | Whether a notification is currently displayed |
| `input_boolean.utility_doors_snoozed` | Path advice suppressed until midnight |
| `input_datetime.utility_quiet_last_sent` | Daily cap for the quiet tier |
| `binary_sensor.utility_okno` | Window |
| `binary_sensor.utility_vrata` | Utility door |
| `binary_sensor.vhod_notranja_vrata` | Vhod to living space |

The two template sensors hold all the logic. The four automations contain none, and only
render and send. Change behaviour in the sensors, not the automations.

## Decision logic

```
purge_ok     = month in 4..10 AND outdoor_24hr_mean >= 15
purge_viable = purge_ok AND zunaj <= utility - 3

want window open = purge_viable
want path open   = (utility - hisa) > 2  AND NOT (purge_viable AND zunaj > hisa)
```

The path rule carries no season branch. In summer it routes heat to the AC, in winter to the
house. The action is identical, so only urgency differs.

The path is advised shut during a purge solely when outdoor air is warmer than the house,
which is the case where an open window would push warm air through into a cooler house. When
outdoor is below the house, as at night, both open is correct and nothing is advised shut.

## Status states

Precedence, first match wins:

| State | Meaning |
|---|---|
| `cooldown` | Advice exists but within 15 min of a clear |
| `advising_urgent` | Advice exists, room at or above the engage threshold, or above 24 and rising over 0.8 K/h. Sticky, live-updating |
| `advising_quiet` | Advice exists and the path has been shut over 3 h. Plain, once per day |
| `waiting` | Advice exists but neither tier is active yet |
| `blocked` | Path advice exists but the snooze is on |
| `ok` | Engaged, nothing to do, configuration already correct |
| `dormant` | Below threshold, nothing to do |

`ok` versus `dormant` is the distinction worth knowing: both are silent, but `ok` means the
automation is awake and satisfied, `dormant` means it is not watching yet.

## Snooze

Notranja vrata is shut regularly to keep the animals in the living space, so the notification
carries **Vrata ostanejo zaprta** beside **Urejeno**. Tapping it suppresses all path advice
until midnight and clears the notification. Window advice continues, so a purge is still
offered when outdoor air drops below the room.

While snoozed with nothing else actionable the automation stays silent rather than repeating
advice already overruled. `sensor.utility_climate_status` reads `blocked` so the silence is
explainable.

## Recipients

Sent through `script.notify_home_users_dynamic`, so it reaches whoever is home: Luka and Maša
are both in the script's `user_map`, Miha and Mitja are not. The clear path deliberately skips
the presence check and fires at both phones, so a notification cannot strand on a device that
has left the house.

This is a deliberate choice to treat it as a household chore rather than an operator alert.
Low battery, 3D printer filament and Luba offline all bypass the script and address one device
directly. This one does not, because whoever is nearest the door is the person who can act,
and that is worth more than keeping the plant reasoning to one person.

## Timings

| Behaviour | Value | Why |
|---|---|---|
| Fire delay | 5 min | Long enough that door traffic never triggers |
| Clear delay | 10 s | Acting feels responsive |
| Cooldown | 15 min | A 30 s opening cannot clear then re-buzz |
| Quiet cap | 1 per day | A 1 kWh/day benefit does not warrant more |

Cooldown is derived from `input_boolean.utility_climate_active.last_changed` rather than a
dedicated timestamp helper.

## Tuning

`input_number.utility_temp_engage` is the one knob. It is a proxy: the real target is battery
cell temperature, since LFP calendar ageing roughly doubles per 10 K. Once the Elfin EE11A
bridge is installed (ADR 0007) and cell temperature is readable, retune against that and
consider pointing the whole decision at it instead of room air.

## Why the purge gate needs both month and the trailing mean

Neither signal alone is sufficient, and October is where that shows:

| Day | Month gate | Mean gate | Outcome |
|---|---|---|---|
| Cold October, mean 11 °C, room 27 °C | allows, 10 is in range | blocks | Window stays shut, plant heat kept for the house |
| Hot early October, mean 21 °C, room 30 °C | allows | allows | Window opens, room purges for free |

A tighter month window would get the second day wrong. Month alone would get the first day
wrong and dump heat you are paying the heat pump to make. The wide April to October window
plus a trailing mean threshold gets both.

## Rebuilding the statistics helper

`sensor.outdoor_temp_24hr_mean` had to be created through the UI. The `statistics` and
`filter` helpers are multi-step config flows that the management API cannot drive, so if it is
ever lost it must be recreated by hand:

> Settings > Devices & Services > Helpers > Create helper > Statistics
> Source `sensor.arso_weather_letalisce_jozeta_pucnika_ljubljana_temperatura`,
> characteristic **mean**, max age **24:00:00**, sampling size 500.

It back-fills from the recorder, so it is usable within seconds rather than needing 24 h to
warm up. If it is missing, `purge_ok` evaluates false and the automation degrades to path
advice only. That is the safe direction: path advice is the mechanism that does the work, and
an absent sensor cannot produce a wrong window recommendation.
