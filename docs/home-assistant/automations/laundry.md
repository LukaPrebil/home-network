# Laundry State Machine

Six automations and a WLED notification script that track washing machine and dryer cycles through a three-state machine: Off → Running → Unemptied → Off.

## Entities

| Entity | Type | Purpose |
|--------|------|---------|
| `input_select.washing_machine_state` | Helper | Washing machine state (Off / Running / Unemptied) |
| `input_select.dryer_state` | Helper | Dryer state (Off / Running / Unemptied) |
| `automation.helper_set_washing_machine_status_to_running` | Automation | Detect wash cycle start |
| `automation.new_automation` | Automation | Detect dryer cycle start |
| `automation.helper_set_washing_machine_status_to_unemptied` | Automation | Detect wash cycle end |
| `automation.helper_set_dryer_status_to_unemptied` | Automation | Detect dryer cycle end |
| `automation.helper_set_washing_machine_status_to_off` | Automation | Mark washer emptied |
| `automation.helper_set_dryer_status_to_off` | Automation | Mark dryer emptied |
| `script.wled_refresh_all_notifications` | Script | Update WLED strip with active notifications |
| `automation.kitchen_counter_full_light_switch` | Automation | Refresh WLED when kitchen switch toggles |

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
- Send push notification ("Pralni stroj je začel cikel" / "Sušilni stroj je začel cikel")
- Call `script.wled_refresh_all_notifications`

### Running → Unemptied

**Washing machine**: power drops below 1W for 1 minute.
**Dryer**: power drops below 20W for 1 minute OR `sensor.tumble_dryer` transitions from `in_use` to `program_ended`.

Condition: state must be "Running".

Actions:
- Set `input_select` to "Unemptied"
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
- Call `script.wled_refresh_all_notifications` (WLED clears notification)

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

The `automation.kitchen_counter_full_light_switch` triggers `wled_refresh_all_notifications` whenever `switch.switch_cabinet_light` changes, so the WLED base state stays in sync with the kitchen light.

## Notes

- The dryer has richer integration via `sensor.tumble_dryer` (likely a smart appliance integration) in addition to power monitoring
- The dryer door sensor provides automatic "emptied" detection — no button press needed if you just open the door
- `automation.new_automation` is the dryer "Running" automation — the entity ID was never renamed from the HA default
