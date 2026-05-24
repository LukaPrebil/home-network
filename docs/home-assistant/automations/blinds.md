# Automated Blinds

Three automations that manage window blinds based on sun position, motion, and window open/close events.

## Automations

| Entity | Purpose |
|--------|---------|
| `automation.luka_s_room_blinds` | Open on wake-up or sun fallback, close at sunset +1h |
| `automation.upstairs_bathroom_blinds` | Open at sun elevation 5°, close at sunset |
| `automation.window_ventilation_control` | Tilt blinds when window opens, restore on close |

## Luka's Room

Single automation with three trigger paths using `choose`:

```
Sensors:
  motion: binary_sensor.motion_sensor_aqara_p1_occupancy (Aqara P1)
  sun:    sun.sun (elevation attribute)
  window: binary_sensor.myggbett_door_window_sensor_door_4
  blind:  cover.tz3000_wptayaqr_ts130f_cover (area: luka_s_room)

Morning — wake-up open:
  → Trigger: motion detected
  → Conditions: after 06:30, before 12:00, sun elevation > 0°, blind position < 50%
  → Action: open cover

Morning — fallback open:
  → Trigger: sun elevation crosses above 10°
  → Conditions: after 06:30, blind position < 50%
  → Action: open cover

Evening — close:
  → Trigger: sunset + 1 hour
  → Condition: window sensor NOT open
  → Action: close cover
```

The wake-up trigger opens blinds as soon as you start moving in the morning — no fixed schedule to get wrong. The elevation > 0° guard prevents nighttime bathroom trips from opening blinds. The `position < 50` check (instead of `state: closed`) handles the case where the ventilation automation has tilted the blind to +3%.

The fallback ensures blinds still open if nobody's home or the motion sensor misses the wake-up.

Consolidated from two previous automations (`close_blinds_in_luka_s_room` + `open_covers_in_luka_s_room`).

## Upstairs Bathroom

Single automation with three trigger paths feeding a shared open branch:

```
Morning — open (whichever fires first after 06:00):
  → Trigger A: sun elevation crosses above 5°
  → Trigger B: 06:00 local (catch-up for summer mornings)
  → Conditions: after 06:00, before 12:00, sun elevation > 5°
  → Action: open cover for area bathroo_upstairs

Evening — close:
  → Trigger: sunset
  → Action: close cover for area bathroo_upstairs
```

06:00 is a hard floor — the blind never opens earlier. From late May to mid-July the sun crosses 5° elevation before 06:00 local, so the elevation trigger fires and is blocked by the time condition; the 06:00 time trigger then takes over and opens the blind. Outside that window the elevation trigger fires after 06:00 and opens directly; the 06:00 catch-up fires too but is blocked by the elevation condition until the sun is actually up.

The area ID `bathroo_upstairs` is a typo in HA config (missing "m").

Consolidated from two previous automations (`close_blinds_in_upstairs_bathroom` + `open_blinds_in_upstairs_bathroom`).

## Window Ventilation Control

```
Mode: parallel (max 10)
Trigger: binary_sensor.myggbett_door_window_sensor_door_4 on/off

Window opened (and blind position < 98%):
  → Save current blind position as scene snapshot
  → Tilt blind open by +3% (capped at 100%)

Window closed:
  → If nighttime (sun elevation < 0°): fully close blind
  → Else if blind already > 95%: do nothing
  → Else: restore saved scene snapshot
```

Uses a `window_map` variable to map window sensors to blinds. Currently only one mapping:
- `binary_sensor.myggbett_door_window_sensor_door_4` → `cover.tz3000_wptayaqr_ts130f_cover`

The parallel mode (max 10) supports future expansion to multiple windows. The +3% tilt allows airflow without fully opening the blind. Nighttime is defined as sun below horizon (`elevation < 0`), consistent with the blinds automation.
