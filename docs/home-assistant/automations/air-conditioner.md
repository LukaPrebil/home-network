# Air Conditioner Automations

Mitsubishi MSZ-AY42 controlled via ESP32-CAM + CN105 connector using [MitsubishiCN105ESPHome](https://github.com/echavet/MitsubishiCN105ESPHome). ESPHome config: `esphome/airconditioner.yaml`.

## Entity

`climate.air_conditioner_air_conditioner` (dual setpoint, all modes)

## Compressor frequency is not exposed

The MSZ-AY42 always returns 0 for the compressor-frequency byte in the CN105 status response, even while the compressor is actively running. This is a known limitation of the unit (the upstream MitsubishiCN105ESPHome component notes that some Mitsubishi models do not populate this field). The `compressor_frequency_sensor` was therefore removed from `esphome/airconditioner.yaml`. Use `sensor.air_conditioner_ac_input_power`, `sensor.air_conditioner_ac_stage`, and the climate entity's `hvac_action` attribute as proxies for compressor activity.

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
| `automation.ac_sync_air_purifier_enabled_toggle` | Sync `input_boolean.air_purifier_enabled` to the real switch |
| `automation.ac_recover_air_purifier_after_unexpected_off` | Re-enable purifier after unexpected off (10s delay) |
| `automation.ac_enable_purifier_and_night_mode_on_ac_start` | Enable purifier + night mode (if nighttime) when AC starts |
| `automation.ac_enable_night_mode_at_22_00` | Enable night mode at 22:00 if AC is running |
| `automation.ac_disable_night_mode_at_07_00` | Disable night mode at 07:00 (unconditional) |

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

## Air Purifier Auto-On

The air purifier (`switch.air_conditioner_ac_air_purifier`) can turn off unexpectedly during ESPHome reboots, HA restarts, or power cycles. To keep it reliably on, `input_boolean.air_purifier_enabled` acts as the source of truth for the user's desired purifier state. The raw switch is hidden from the dashboard — users toggle the boolean instead.

### How it works

1. **Sync**: When the boolean changes, the automation syncs the real switch (only turns on if AC is running)
2. **Recovery**: If the switch goes off but the boolean says on and AC is running, the switch is turned back on after 10 seconds
3. **AC start**: When the AC transitions from off to any running state, the purifier is enabled (if boolean is on)

### Helpers

- `input_boolean.air_purifier_enabled` — user's desired purifier state (default: on, icon: `mdi:air-purifier`)

## Night Mode Schedule

Night mode (`switch.air_conditioner_ac_night_mode`) is automated on a 22:00–07:00 schedule when the AC is running. No recovery mechanism — if the user toggles it off during the night, it stays off until the next scheduled trigger.

### Schedule

- **22:00**: Enable night mode (condition: AC is not off)
- **07:00**: Disable night mode (unconditional — cleans up state even if AC was turned off)
- **AC starts during 22:00–07:00**: Night mode is enabled as part of the AC-start automation (same automation that handles purifier catch-up)

## Filter Cleaning Reminder

```
Trigger: 10:00 on the 1st of every month
Actions:
  → Push notification via script.notify_home_users_dynamic
    Title: "Klimatska naprava"
    Message: "Čas je za mesečno čiščenje filtra klimatske naprave."
    + Every 3rd month (Mar, Jun, Sep, Dec): appends Plasma Quad Plus cleaning reminder
    Tag: ac_filter_reminder (sticky, deep links to /air-conditioner/0)
  → persistent_notification.create with ID "ac_filter_reminder"
```

Sends to all users at home via the shared notification script, plus creates a persistent notification in HA visible to anyone who opens the dashboard. Monthly cadence covers both runtime dust and settling dust when the unit is off. Every 3rd month the message also reminds to clean the Plasma Quad Plus filter (remove, vacuum, or soak in lukewarm water with mild detergent).

## Dashboard

Dedicated dashboard at `/air-conditioner` ("Klimatska naprava") with:
- Native HA thermostat card (climate control + mode buttons)
- Mushroom select cards (vertical/horizontal vane control — inline dropdowns)
- Native tile cards (night mode, air purifier enabled boolean — raw switch is hidden)

Available as a homescreen shortcut on iPhone/Android via the HA Companion App.
