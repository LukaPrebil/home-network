# Laundry State Machine

Six automations and a WLED notification script that track washing machine and dryer cycles through a three-state machine: Off → Running → Unemptied → Off. Push notifications use `script.notify_home_users_dynamic` (home-only delivery, clear support).

## Entities

| Entity | Type | Purpose |
|--------|------|---------|
| `input_select.washing_machine_state` | Helper | Washing machine state (Off / Running / Unemptied) |
| `input_select.dryer_state` | Helper | Dryer state (Off / Running / Unemptied) |
| `input_datetime.washing_machine_cycle_start` | Helper | Records when washer cycle started (for duration) |
| `input_datetime.dryer_cycle_start` | Helper | Records when dryer cycle started (duration fallback) |
| `automation.helper_set_washing_machine_status_to_running` | Automation | Detect wash cycle start |
| `automation.helper_set_dryer_status_to_running` | Automation | Detect dryer cycle start |
| `automation.helper_set_washing_machine_status_to_unemptied` | Automation | Detect wash cycle end |
| `automation.helper_set_dryer_status_to_unemptied` | Automation | Detect dryer cycle end |
| `automation.helper_set_washing_machine_status_to_off` | Automation | Mark washer emptied |
| `automation.helper_set_dryer_status_to_off` | Automation | Mark dryer emptied |
| `script.wled_refresh_all_notifications` | Script | Update WLED strip with active notifications |
| `automation.kitchen_counter_full_light_switch_2` | Automation | Refresh WLED when kitchen switch toggles |

## Notification Tags

| Machine | Tag | Purpose |
|---------|-----|---------|
| Washing machine | `washing_machine_cycle` | Shared by start and done notifications (done replaces start in-place) |
| Dryer | `dryer_cycle` | Same pattern |

## State Machine

```
Off ──→ Running ──→ Unemptied ──→ Off
         (power)      (power)      (user action)
```

### Off → Running

**Washing machine**: power sensor above 5W for 10 seconds.
**Dryer**: power sensor above 1W for 10 seconds OR `sensor.tumble_dryer` transitions to `in_use`.

Condition: state must be "Off" or "Unemptied" (handles re-start mid-cycle).

Actions:
- Set `input_select` to "Running"
- Record cycle start time in `input_datetime`
- Silent push notification via `script.notify_home_users_dynamic` (channel: `Laundry`, importance: `low`):
  - **Washer**: "Cikel pranja se je začel." (tag: `washing_machine_cycle`)
  - **Dryer**: "Cikel sušenja se je začel (Program)." with translated Slovenian program name and predicted end time from `sensor.tumble_dryer_remaining_time` (tag: `dryer_cycle`)
- Call `script.wled_refresh_all_notifications`

### Running → Unemptied

**Washing machine**: power drops below 1W for 1 minute.
**Dryer**: power drops below 20W for 1 minute OR `sensor.tumble_dryer` transitions from `in_use` to `program_ended`.

Condition: state must be "Running".

Actions:
- Set `input_select` to "Unemptied"
- Push notification via `script.notify_home_users_dynamic` (replaces the start notification via same tag):
  - **Washer**: "Pranje končano! Trajanje: X min." (duration computed from `input_datetime`)
  - **Dryer**: "Sušenje končano! Program: Bombaž. Trajanje: X min." (translated program, duration from Miele `elapsed_time` sensor with `input_datetime` fallback)
  - Sticky, persistent, alert_once, chronometer (shows count-up timer)
  - Action button: "Izpraznjeno ✓" (`EMPTY_WASHING_MACHINE` / `EMPTY_DRYER`)
- Call `script.wled_refresh_all_notifications` (WLED shows notification color)

### Unemptied → Off

**Washing machine** triggers:
- Mobile app notification action: `EMPTY_WASHING_MACHINE`
- Zigbee button press (command: "on")

**Dryer** triggers:
- Dryer door sensor opens
- Mobile app notification action: `EMPTY_DRYER`
- Zigbee button press (command: "off")

Actions:
- Set `input_select` to "Off"
- Clear push notification via `script.notify_home_users_dynamic` (`clear_notification` with tag)
- Call `script.wled_refresh_all_notifications` (WLED clears notification)

## Dryer Program Translation

The dryer `sensor.tumble_dryer_program` returns English enum values (e.g., `cottons`, `minimum_iron`). A Jinja2 translation map converts these to Slovenian in both start and done notifications (e.g., "Bombaž", "Minimalno likanje"). Unknown programs fall back to title-cased English.

## WLED Notification Display

The kitchen counter has a WLED strip that serves as a visual notification display. The `script.wled_refresh_all_notifications` script manages it:

```
1. Set base state based on kitchen switch:
   → switch.switch_cabinet_light ON  → preset "Main light on"
   → switch.switch_cabinet_light OFF → preset "Main light off"
2. Wait 1 second
3. Find all entities with label "wled_notification"
4. For each entity in "Unemptied" or "on" state:
   → Apply preset "{DeviceName} notification on"
```

The `automation.kitchen_counter_full_light_switch_2` triggers `wled_refresh_all_notifications` whenever `switch.switch_cabinet_light` changes, so the WLED base state stays in sync with the kitchen light. (The `_2` suffix exists because a stale entity-registry entry held the original slug when the automation was recreated on 2026-04-17; the stale entry can be purged from the HA UI → Settings → Devices & Services → Entities, after which the automation can be renamed back.)

## Notes

- The dryer has richer integration via Miele (`sensor.tumble_dryer`) in addition to power monitoring — provides program name, elapsed time, remaining time, and energy data
- The dryer door sensor provides automatic "emptied" detection — no button press needed if you just open the door
- All 6 automations have label `push_notification`, are assigned to area `utility`, and hidden from auto-generated dashboards
- Notifications use channel `Laundry` (blue `#03A9F4`), group `laundry`, with `mdi:washing-machine` / `mdi:tumble-dryer` status bar icons
- All laundry notifications deep-link to `/home/areas-utility` (Utility area view) when tapped
