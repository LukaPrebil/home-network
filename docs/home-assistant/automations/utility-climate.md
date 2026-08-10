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
purge_ok     = month in 4..10 AND outdoor_24h_mean >= 15
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

## Known gap

`sensor.outdoor_temp_24h_mean` does not exist yet. The `statistics` and `filter` helpers are
multi-step config flows that the management API cannot drive, so it must be created by hand:

> Settings > Devices & Services > Helpers > Create helper > Statistics
> Source `sensor.arso_weather_letalisce_jozeta_pucnika_ljubljana_temperatura`,
> characteristic **mean**, max age **24:00:00**, sampling size 500.
> Rename the resulting entity to `sensor.outdoor_temp_24h_mean`.

Until it exists `purge_ok` is false, so the window is never advised open and the automation
degrades to path advice only. That is the safe direction: path advice is the mechanism that
does the work, and a missing sensor cannot cause a wrong window recommendation.
