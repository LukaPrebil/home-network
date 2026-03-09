# Automated Blinds

Five automations that manage window blinds based on sunrise/sunset and window open/close events.

## Automations

| Entity | Purpose |
|--------|---------|
| `automation.close_blinds_in_luka_s_room` | Close blinds at sunset +1h |
| `automation.open_covers_in_luka_s_room` | Open blinds at sunrise +1.5h |
| `automation.close_blinds_in_upstairs_bathroom` | Close blinds at sunset |
| `automation.open_blinds_in_upstairs_bathroom` | Open blinds at sunrise +1h |
| `automation.window_ventilation_control` | Tilt blinds when window opens, restore on close |

## Sun-Based Schedules

### Luka's Room

```
Close: sunset + 1 hour
  → Condition: window sensor reports NOT open (skip if window is open)
  → Action: cover.close_cover for area luka_s_room

Open: sunrise + 1.5 hours
  → No conditions
  → Action: cover.open_cover for area luka_s_room
```

The close automation checks a window sensor — if the window is open, blinds stay up to avoid trapping the window behind the blind.

### Upstairs Bathroom

```
Close: sunset (no offset)
  → Action: cover.close_cover for area bathroo_upstairs

Open: sunrise + 1 hour
  → Action: cover.open_cover for area bathroo_upstairs
```

No conditions on either. The area ID `bathroo_upstairs` is a typo in HA config (missing "m").

## Window Ventilation Control

```
Mode: parallel (max 10)
Trigger: binary_sensor.myggbett_door_window_sensor_door_4 on/off

Window opened (and blind position < 98%):
  → Save current blind position as scene snapshot
  → Tilt blind open by +3% (capped at 100%)

Window closed:
  → If nighttime (after sunset+1h or before sunrise+1.5h): fully close blind
  → Else if blind already > 95%: do nothing
  → Else: restore saved scene snapshot
```

Uses a `window_map` variable to map window sensors to blinds. Currently only one mapping:
- `binary_sensor.myggbett_door_window_sensor_door_4` → `cover.tz3000_wptayaqr_ts130f_cover`

The parallel mode (max 10) supports future expansion to multiple windows. The +3% tilt allows airflow without fully opening the blind.
