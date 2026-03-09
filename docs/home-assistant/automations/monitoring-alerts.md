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
Triggers:
  → Binary sensor update on Proxmox device
  → sensor.node_n5p_total_updates goes above 0
Action: persistent_notification with ID "pve_n5p_updates_available"
Title: "Update Proxmox"
Message: "{count} updates available" with link to http://n5p.lan:8006/
```

Uses a persistent notification (in-HA notification, not push) with a fixed `notification_id` so it gets replaced on each trigger rather than stacking. Links directly to the Proxmox web UI.
