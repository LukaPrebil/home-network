# Monitoring & Alert Notifications

Three automations that send notifications for system and device events.

## Automations

| Entity | Purpose |
|--------|---------|
| `automation.low_battery_level_detection_notification_for_all_battery_sensors` | Notify when any battery sensor is low |
| `automation.notify_when_3d_printer_runs_out_of_filament` | Notify on printer filament runout |
| `automation.notify_of_proxmox_updates` | Notify when Proxmox has available updates |

## Low Battery Detection

```
Blueprint: sbyx/low-battery-level-detection-notification-for-all-battery-sensors.yaml
Action: notify.mobile_app_sm_s926b (Luka's phone only)
Title: "Low battery on some devices"
Message: "{sensors} have low battery."
```

Uses a community blueprint that scans all battery sensors automatically. Only notifies Luka (not using the shared `script.notify_home_users_dynamic`).

## 3D Printer Filament Alert

```
Trigger: sensor.fdm_print_status changes from "printing" to "pausing"
Condition: sensor.fdm_remaining_layers > 0
Action: notify.notify to device_tracker.luka_s_s24
Title: "3D Printer Alert: Filament!"
Message: "The printer has paused the print. It might be out of filament."
```

Only fires when the printer pauses mid-print (remaining layers > 0), distinguishing a filament issue from a normal print completion.

## Proxmox Update Notification

```
Trigger: sensor.node_n5p_total_updates state change (ignores unavailable/unknown)
Actions (choose):
  → updates > 0: persistent_notification.create with ID "pve_n5p_updates_available"
    Title: "Update Proxmox"
    Message: "{count} updates available" with link to node update page
  → updates = 0: persistent_notification.dismiss with ID "pve_n5p_updates_available"
```

Uses a persistent notification (in-HA, not push) with a fixed `notification_id`. The `state` trigger fires on every count change, so the notification updates in-place when new updates appear. Automatically dismisses when the node is fully updated. Links to the node's update page (`https://n5p.lan:8006/#v1:0:=node%2Fn5p:4:31::::::`).
