# Ventilation Reminder (Air Quality)

Notifies home users to open windows when the living room air quality monitor reports poor or worse conditions.

## Entities

| Entity | Type | Purpose |
|--------|------|---------|
| `automation.remind_air_quality` | Automation | Sends initial notification on trigger |
| `automation.update_air_quality_notification` | Automation | Re-sends every 2 min for live update |
| `automation.clear_air_quality_notification` | Automation | Clears on improvement, tap, or swipe |
| `input_boolean.air_quality_reminder_active` | Helper | Tracks whether notification is active |
| `input_datetime.air_quality_snooze_until` | Helper | Snooze timestamp after user dismiss |
| `sensor.alpstuga_air_quality_monitor_air_quality` | Sensor | Air quality enum (good → extremely_poor) |
| `sensor.alpstuga_air_quality_monitor_carbon_dioxide` | Sensor | CO2 in ppm |
| `sensor.alpstuga_air_quality_monitor_pm2_5` | Sensor | PM2.5 in µg/m³ |

## Flow

```
Trigger: air quality changes to poor / very_poor / extremely_poor
  → Conditions:
      - Humidity ventilation notification is NOT active (avoid double-nag)
      - Air quality notification is NOT already active
      - Snooze has expired (now > air_quality_snooze_until)
  → Send sticky live-update notification via script.notify_home_users_dynamic
  → Turn on input_boolean.air_quality_reminder_active

Every 2 minutes (while boolean is on + air quality still poor+):
  → Re-send notification with updated CO2/PM2.5 values (same tag = in-place update)

Clear triggers (any of):
  → Air quality improves to good / moderate / fair
  → User taps "Urejeno" (AIR_QUALITY_DONE action)
  → User swipes notification away (mobile_app_notification_cleared)

Clear actions:
  → Turn off input_boolean
  → Send clear_notification to all users
  → If user-initiated dismiss (tap/swipe): set snooze to now + 2 hours
  → If natural improvement: no snooze set
```

## Notification

- **Tag**: `air_quality_alert`
- **Title**: "Slaba kakovost zraka"
- **Message format**:
  ```
  Kakovost zraka: poor
  CO2: 1100 ppm | PM2.5: 6.0 µg/m³
  Priporočeno: CO2 pod 700 ppm, PM2.5 pod 10 µg/m³  (italic)
  Prosim, odpri okna za 5 minut.
  ```
- **Features**: `live_update: true`, `persistent: true`, `sticky: "true"`, `alert_once: true`
- **Action button**: "Urejeno" (AIR_QUALITY_DONE)

## Reference Values

Based on 30-day sensor history and health guidelines:

| Metric | Your typical range | Recommended | Source |
|--------|-------------------|-------------|--------|
| CO2 | 390–2400 ppm (avg ~1200) | pod 700 ppm | User preference |
| PM2.5 | 1–129 µg/m³ (avg ~9) | pod 10 µg/m³ | User preference |

## Snooze Behavior

When the user dismisses the notification (tap or swipe) while air quality is still poor, a 2-hour snooze prevents the notification from immediately re-triggering. This avoids spam when the user acknowledges but can't ventilate right now.

Natural air quality improvement does NOT set the snooze — the system is ready to notify again immediately if air quality degrades.

## Mutual Exclusion

This automation checks `input_boolean.ventilation_reminder_active` and will NOT fire if the humidity ventilation notification is already active. Both automations serve the same purpose (open windows), so only one notification is shown at a time.
