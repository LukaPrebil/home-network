# Monitoring & Alert Notifications

Admin and household monitoring automations.

The first three (battery, 3D printer, Proxmox) are admin-only alerts that notify Luka directly — they intentionally use direct notify services, not `script.notify_home_users_dynamic`.

The mold risk automation is a household notification that uses the shared script.

## Automations

| Entity | Purpose |
|--------|---------|
| `automation.low_battery_level_detection_notification_for_all_battery_sensors` | Notify when any battery sensor is low |
| `automation.notify_when_3d_printer_runs_out_of_filament` | Notify on printer filament runout |
| `automation.notify_of_proxmox_updates` | Notify when Proxmox has available updates |
| `automation.mold_risk_notification` | Notify when mold risk detected in any room |

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
Action: notify.mobile_app_sm_s926b (Luka's phone)
Title: "3D Printer Alert: Filament!"
Message: "The printer has paused the print. It might be out of filament."
```

Only fires when the printer pauses mid-print (remaining layers > 0), distinguishing a filament issue from a normal print completion. Notifies Luka only.

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

## Mold Risk Notification

```
Trigger: time_pattern every 30 minutes
Condition: template checks if any binary_sensor.nevarnost_plesni_* is on
Actions (choose):
  → rooms at risk: push notification via script.notify_home_users_dynamic
    Title: "Nevarnost plesni"
    Message: lists rooms at risk + actionable advice (ventilate, check furniture, bathroom exhaust)
    Tag: mold_risk (live update, sticky, alert_once)
  → no risk + notification was active: clear_notification + turn off input_boolean.mold_risk_active
```

### How it works

Each room has a template binary sensor (`binary_sensor.nevarnost_plesni_*`, label: `mold_danger`) that estimates the coldest surface temperature (thermal bridge at window frames/corners) and compares it to the room's dew point from the Thermal Comfort integration.

**Formula**: `T_surface = T_indoor - k × (T_indoor - T_outdoor)`, mold risk when `dew_point >= T_surface - 2°C`

- **k = 0.25** for the main house (montažna hiša, 15cm mineral wool + 15cm EPS) — models thermal bridges, not the well-insulated wall
- **k = 0.50** for the shed (Lopa, 5cm EPS, unheated)
- Outdoor temp: ARSO Ljubljana with Met.no fallback

### Helpers

- 12× `binary_sensor.nevarnost_plesni_*` — template binary sensors (device_class: moisture, label: mold_danger)
- `input_boolean.mold_risk_active` — tracks whether a notification is currently showing
