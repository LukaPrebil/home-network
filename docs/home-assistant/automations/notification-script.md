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

## Live Update Notification Pattern

For automations that need live-updating notifications, use these `data` keys:

```yaml
data:
  tag: unique_tag           # Required: identifies the notification for updates/clearing
  live_update: true         # Android 16+: pins notification, allows in-place updates
  persistent: true          # Prevents swipe dismiss (Android 13 and below)
  sticky: "true"            # String, not boolean — prevents dismiss on tap
  alert_once: true          # Only buzz on first send, silent on updates
  url: /lovelace/home       # Deep link when tapped
  actions:                  # Action buttons
    - action: ACTION_ID
      title: Button Label
```
