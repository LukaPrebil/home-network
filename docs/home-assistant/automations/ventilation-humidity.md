# Ventilation Reminder (Humidity)

Notifies home users to open windows when indoor humidity is high and outdoor conditions are favorable.

## Entities

| Entity | Type | Purpose |
|--------|------|---------|
| `automation.remind_to_ventilate` | Automation | Sends initial notification on trigger |
| `automation.update_ventilation_notification` | Automation | Re-sends every 2 min for live update |
| `automation.clear_ventilation_notification` | Automation | Clears on improvement, tap, or swipe |
| `input_boolean.ventilation_reminder_active` | Helper | Tracks whether notification is active |
| `binary_sensor.good_to_ventilate` | Template binary sensor | Outdoor dewpoint < indoor dewpoint (with fallback) |
| `sensor.inside_dewpoint` | Template sensor | Indoor dewpoint calculated from average temp/humidity |
| `sensor.average_humidity` | Template sensor | Average indoor humidity |

## Flow

```
Trigger: 07:30 / 12:30 / 19:30 OR binary_sensor.good_to_ventilate turns on
  → Conditions: good_to_ventilate=on, AC off/fan_only, humidity > 50%
  → Send sticky live-update notification via script.notify_home_users_dynamic
  → Turn on input_boolean.ventilation_reminder_active

Every 2 minutes (while boolean is on + conditions hold):
  → Re-send notification with updated humidity value (same tag = in-place update)

Clear triggers (any of):
  → Humidity drops below 50%
  → good_to_ventilate turns off
  → User taps "Urejeno" (MARK_DONE action)
  → User swipes notification away (mobile_app_notification_cleared)

Clear actions:
  → Turn off input_boolean
  → Send clear_notification to all users (regardless of home/away)
```

## Notification

- **Tag**: `humidity_alert`
- **Title**: "Visoka vlaga"
- **Message**: Current humidity percentage with call to action
- **Features**: `live_update: true`, `persistent: true`, `sticky: "true"`, `alert_once: true`
- **Action button**: "Urejeno" (MARK_DONE)

## Good to Ventilate Sensor

`binary_sensor.good_to_ventilate` ("Lahko zračimo") is a template binary sensor that compares outdoor dewpoint against indoor dewpoint. When outdoor dewpoint is lower, opening windows will help reduce indoor moisture.

**Template logic (with fallback):**

```jinja2
{% set arso = states('sensor.letalisce_jozeta_pucnika_ljubljana_dew_point') %}
{% set metno = state_attr('weather.forecast_home', 'dew_point') %}
{% set inside = states('sensor.inside_dewpoint') | float %}
{% if arso not in ['unknown', 'unavailable'] %}
  {{ arso | float < inside }}
{% elif metno is not none %}
  {{ metno | float < inside }}
{% endif %}
```

**Data sources (in priority order):**

1. **ARSO** (`sensor.letalisce_jozeta_pucnika_ljubljana_dew_point`) — Slovenian weather agency, preferred when available
2. **Met.no** (`weather.forecast_home` → `dew_point` attribute) — Norwegian weather service, used as fallback

If both sources are unavailable, the template renders empty and the sensor becomes unavailable, which is correct — the ventilation automations will not fire without valid data.

## Notes

- The 3x/day trigger cadence prevents spam — the automation only fires at scheduled times or on sensor state change, not continuously
- `alert_once: true` prevents buzzing on each 2-minute update
- `persistent: true` + `sticky: "true"` attempt to prevent swipe/tap dismiss, but Android 14+ allows swipe anyway — the swipe dismiss is handled gracefully by the clear automation
- The `script.notify_home_users_dynamic` handles `clear_notification` as a special case, sending to ALL users (not just those at home) to ensure all devices are cleared
