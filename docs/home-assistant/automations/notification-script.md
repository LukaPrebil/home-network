# Notify Home Users (Dynamic Script)

Shared notification script used by all push notification automations.

## Entity

`script.notify_home_users_dynamic`

## Purpose

Loops through a defined list of users, checks if they are home, and sends a notification. Supports `clear_notification` as a special case that sends to ALL users regardless of location.

## User Map

| Person | Notify Service |
|--------|---------------|
| `person.luka` | `notify.mobile_app_sm_s926b` |
| `person.<resident>` | `notify.mobile_app_sm_s711b` |

## Parameters

| Field | Description | Example |
|-------|-------------|---------|
| `message` | Notification text or `clear_notification` | "The dishwasher is done" |
| `title` | Notification title (default: "Home Assistant") | "Visoka vlaga" |
| `data` | Extra notification data (tag, actions, etc.) | `{ "tag": "humidity_alert" }` |

## Behavior

### Regular notifications
- Iterates through `user_map`
- Only sends to users whose person entity state is `home`
- Passes through `title`, `message`, and `data` as-is

### Clear notifications (`message: clear_notification`)
- Sends to **ALL** users regardless of home/away status
- Ensures notifications are cleared on all devices (e.g., user left home after receiving notification)
- Requires `data.tag` to identify which notification to clear

## Usage Example

```yaml
# Send notification
- action: script.notify_home_users_dynamic
  data:
    title: "Alert Title"
    message: "Alert message body"
    data:
      tag: my_alert_tag
      actions:
        - action: MY_ACTION
          title: Done

# Clear notification
- action: script.notify_home_users_dynamic
  data:
    message: clear_notification
    data:
      tag: my_alert_tag
```

## Notification Channels

All notifications use Android notification channels for organized alert behavior. Channels are created on first use and their importance is **locked by the OS** — only per-notification lowering is possible.

| Channel | Importance | Color | Used By |
|---------|-----------|-------|---------|
| `Laundry` | `default` | `#03A9F4` (blue) | Washer/dryer start (lowered to `low`) and done notifications |
| `Ventilation` | `default` | `#4CAF50` (green) | Humidity and air quality alerts |
| `Maintenance` | `default` | `#FF9800` (orange) | AC filter (lowered to `low`), battery (lowered to `low`), 3D printer |
| `Monitoring` | `default` | `#F44336` (red) | Mold risk alerts |

### Standard notification data keys

All notifications should include these keys in `data`:

```yaml
data:
  tag: unique_tag               # Required: for updates/clearing
  channel: "Channel Name"       # Android notification channel
  group: category_name          # Visual grouping in notification shade
  color: "#hex"                 # Accent color
  notification_icon: "mdi:icon" # Status bar icon
  visibility: public            # Lock screen: public/private/secret
```

### Status bar icons

| Notification | Icon |
|---|---|
| Washer | `mdi:washing-machine` |
| Dryer | `mdi:tumble-dryer` |
| Humidity | `mdi:water-percent` |
| Air quality | `mdi:molecule-co2` |
| AC filter | `mdi:air-conditioner` |
| Mold risk | `mdi:alert-circle` |
| Low battery | `mdi:battery-alert` |
| 3D printer | `mdi:printer-3d` |

## Live Update Notification Pattern

For automations that need live-updating notifications, use these `data` keys:

```yaml
data:
  tag: unique_tag           # Required: identifies the notification for updates/clearing
  live_update: true         # Android 16+: pins notification, allows in-place updates
  persistent: true          # Prevents swipe dismiss (Android 13 and below)
  sticky: "true"            # String, not boolean — prevents dismiss on tap
  alert_once: true          # Only buzz on first send, silent on updates
  url: /climate             # Deep link when tapped (see conventions below)
  actions:                  # Action buttons
    - action: ACTION_ID
      title: Button Label
```

## Notification Deep Link Conventions

Every notification should include a `url` field in `data` that links to the most relevant page when tapped:

| Notification category | `url` value | Target |
|---|---|---|
| Laundry (washer/dryer) | `/home/areas-utility` | Utility area view on Home dashboard |
| Humidity / ventilation | `/climate` | Climate dashboard (per-room temp/humidity) |
| Air quality (CO2/PM2.5) | `/air-quality` | Hidden air quality dashboard (Alpstuga + ARSO) |
| Mold risk | `/climate` | Climate dashboard |
| AC filter | `/air-conditioner/0` | AC dashboard |
