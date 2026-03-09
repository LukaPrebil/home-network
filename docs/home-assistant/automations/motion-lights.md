# Motion-Activated Lights

Four automations that control lights based on motion/occupancy sensors, button presses, or door sensors.

## Automations

| Entity | Purpose |
|--------|---------|
| `automation.luka_s_room_light` | Ceiling (day) or nightstand at 10% (night) on motion |
| `automation.living_room_upstairs_light` | Toggle upstairs light via Zigbee button |
| `automation.pantry_light` | Light on when pantry door opens |
| `automation.office_light_motion` | Office light + remote on occupancy |

## Luka's Room — Motion Light

Single automation using `choose` to pick behavior based on time of day.

```
Sensor: binary_sensor.motion_sensor_aqara_p1_occupancy (Aqara P1)
Lux:    sensor.motion_sensor_aqara_p1_illuminance

Day (07:30–18:00):
  → Occupancy on + illuminance < 25 lux: turn on light.luka_ceiling
  → Occupancy off (after 5 min): turn off light.luka_ceiling

Night (18:00–07:30):
  → Occupancy on: turn on light.tradfri_bulb_light at 10%
  → Occupancy off (after 15 sec): turn off light.tradfri_bulb_light
```

The off actions don't check time — they just turn off the relevant light. This avoids edge cases at time boundaries (e.g., ceiling turned on at 17:55, off trigger fires at 18:03 after the time window shifted to night).

Consolidated from two previous automations (`luka_s_room_lights_on` + `luka_s_room_night_light`) which had overlapping time windows and broken entity references.

## Living Room — Upstairs Light

```
Trigger: Zigbee button short press (turn_on)
Action: toggle switch
```

Simple button toggle — no conditions, no motion sensor.

## Pantry Light

```
Trigger: door/contact sensor opened / not_opened (10 sec delay)
Actions:
  → Door open: turn on switch
  → Door closed (after 10 sec): turn off switch
```

No time or illumination conditions — the pantry has no windows so the light is always needed.

## Office Light — Occupancy

```
Trigger: binary_sensor.office_occupancy on / off (5 min delay)
Actions:
  → Occupancy detected: turn on light at 100% + turn on remote
  → Occupancy clear (after 5 min): turn off light + turn off remote
```

The "remote" is likely a smart plug or IR blaster for an additional device. No time or illumination conditions.
