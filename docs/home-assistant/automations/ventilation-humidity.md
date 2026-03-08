# Ventilation Reminder (Humidity)

Notifies home users to open windows when indoor humidity is high and outdoor conditions are favorable.

## Entities

| Entity | Type | Purpose |
|--------|------|---------|
| `automation.remind_to_ventilate` | Automation | Sends initial notification on trigger |
| `automation.update_ventilation_notification` | Automation | Re-sends every 2 min for live update |
| `automation.clear_ventilation_notification` | Automation | Clears on improvement, tap, or swipe |
| `input_boolean.ventilation_reminder_active` | Helper | Tracks whether notification is active |
| `binary_sensor.good_to_ventilate` | Sensor | Outdoor conditions favorable for ventilation |
| `sensor.average_humidity` | Sensor | Average indoor humidity |

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

## Notes

- The 3x/day trigger cadence prevents spam — the automation only fires at scheduled times or on sensor state change, not continuously
- `alert_once: true` prevents buzzing on each 2-minute update
- `persistent: true` + `sticky: "true"` attempt to prevent swipe/tap dismiss, but Android 14+ allows swipe anyway — the swipe dismiss is handled gracefully by the clear automation
- The `script.notify_home_users_dynamic` handles `clear_notification` as a special case, sending to ALL users (not just those at home) to ensure all devices are cleared
