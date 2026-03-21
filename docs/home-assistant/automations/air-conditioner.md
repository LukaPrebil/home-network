# Air Conditioner Automations

Mitsubishi MSZ-AY42 controlled via ESP32-CAM + CN105 connector using [MitsubishiCN105ESPHome](https://github.com/echavet/MitsubishiCN105ESPHome). ESPHome config: `esphome/airconditioner.yaml`.

## Entity

`climate.air_conditioner_air_conditioner` (dual setpoint, all modes)

## Remote Temperature

The AC's internal sensor sits in the return air path inside the stairwell unit, which causes short cycling — it reads the target temperature quickly while the rest of the house is still warm/cold.

A `min_max` helper (`sensor.ac_average_temperature`, type: mean) averages temperature sensors from conditioned rooms and feeds it to the ESP32 via the ESPHome `homeassistant` sensor platform. The ESP pushes this value to the AC unit via `set_remote_temperature()`, replacing the internal sensor reading.

### Included rooms

Dnevna soba spodaj, Dnevna soba, Spalnica, Lukova soba, Mihova soba, Kopalnica, WC, Hodnik

### Excluded rooms

Vhod, Pisarna, Utility (usually closed), Lopa, Vrt (outside)

### Timeout

`remote_temperature_timeout: 30min` — if the HA sensor goes unavailable, the AC falls back to its internal sensor.

## Automations

| Entity | Purpose |
|--------|---------|
| `automation.ac_away_mode_widen_setpoints_when_everyone_leaves` | Widen setpoints and adjust fan when everyone leaves |
| `automation.ac_away_mode_restore_setpoints_when_someone_arrives` | Restore saved setpoints and fan when first person arrives |
| `automation.ac_monthly_filter_cleaning_reminder` | Monthly filter cleaning reminder (1st of month) |

## Away Mode

Two automations that adjust the AC when all people leave home and restore when someone arrives. The house always has pets (2 dogs, 1 cat), so the adjustments are conservative — comfort is maintained, just less aggressively.

### When everyone leaves

```
Trigger: zone.home person count drops to 0
Condition: AC is not off AND away mode is not already active
Actions:
  1. Save current target_temp_high, target_temp_low, and fan_mode to helpers
  2. Adjust based on current mode:
     → heat_cool: widen both setpoints by ±2°C, fan to auto
     → cool/dry:  raise target_temp_high by 2°C, fan to auto
     → heat:      lower target_temp_low by 2°C, fan to auto
     → fan_only:  fan to middle (max air purification, noise doesn't matter)
  3. Turn on input_boolean.ac_away_mode
```

### When someone arrives

```
Trigger: zone.home person count goes above 0
Condition: input_boolean.ac_away_mode is on
Actions:
  1. Restore target_temp_high and target_temp_low from helpers
  2. Restore fan_mode from helper
  3. Turn off input_boolean.ac_away_mode
```

### Helpers

- `input_boolean.ac_away_mode` — tracks whether away adjustments are active
- `input_number.ac_saved_target_high` — saved cooling setpoint (16–31°C)
- `input_number.ac_saved_target_low` — saved heating setpoint (16–31°C)
- `input_select.ac_saved_fan_mode` — saved fan mode (auto/quiet/low/medium/middle/high)

## Filter Cleaning Reminder

```
Trigger: 10:00 on the 1st of every month
Actions:
  → Push notification via script.notify_home_users_dynamic
    Title: "Klimatska naprava"
    Message: "Čas je za mesečno čiščenje filtra klimatske naprave."
    Tag: ac_filter_reminder (sticky, deep links to /air-conditioner/0)
  → persistent_notification.create with ID "ac_filter_reminder"
```

Sends to all users at home via the shared notification script, plus creates a persistent notification in HA visible to anyone who opens the dashboard. Monthly cadence covers both runtime dust and settling dust when the unit is off.

## Dashboard

Dedicated dashboard at `/air-conditioner` ("Klimatska naprava") with:
- Native HA thermostat card (climate control + mode buttons)
- Mushroom select cards (vertical/horizontal vane control — inline dropdowns)
- Native tile cards (night mode, air purifier switches)

Available as a homescreen shortcut on iPhone/Android via the HA Companion App.
