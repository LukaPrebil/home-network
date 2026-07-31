# Mammotion Luba Mower Notifications

Push notifications for the Mammotion Luba Mini 2 AWD 1500 LiDAR mower (`lawn_mower.vrt_luba`, integration `mikey0000/Mammotion-HA`, cloud mode).

All are managed via the `ha-mcp` tools (never edit HA YAML directly). Household-facing notifications go through `script.notify_home_users_dynamic` (home/away filtered); the offline alert is admin-only (Luka direct). See `notification-script.md` for the shared script and the standard `data` keys.

## Channel & conventions

- **Channel:** `Mower` (green `#8BC34A`, `mdi:robot-mower`), `group: mower` so all Luba alerts stack together.
- **Language:** household alerts are Slovenian (like laundry/mold); the offline alert is English (like battery/Proxmox admin alerts).
- **Deep link:** every notification `clickAction` -> `/dashboard-mower` (the dedicated "Luba" mower dashboard in the sidebar - see [`../dashboards/mower.md`](../dashboards/mower.md)). Previously targeted the auto-generated "Vrt" area subview (`/home/areas-driveway`); repointed to the curated dashboard so a tap lands on the camera + controls surface rather than the 77-entity area pile. A storage-dashboard path also always resolves, avoiding the built-in `/home` panel ambiguity.
- Every automation: area `house`, label `push_notification`.

## Automations

| Entity | Purpose |
|--------|---------|
| `automation.luba_kosnja_koncana` | Mow complete |
| `automation.luba_potrebuje_pomoc` | Needs attention / stuck (persistent) |
| `automation.luba_offline` | Offline / lost connection (Luka direct) |
| `automation.luba_dez_med_kosnjo` | Rain while mowing |
| `automation.luba_obrni_rezila` | Blade flip reminder (persistent) |
| `automation.luba_zamenjaj_rezila` | Blade replace reminder (persistent) |
| `automation.luba_potrditev_rezil` | Blade action-button handler (Flipped/Replaced) |
| `automation.luba_reset_stevca_rezil` | Blade counter re-arm on reset |

Helpers (hidden from dashboards): `input_boolean.luba_blade_flip_acked`, `input_boolean.luba_blade_replace_acked`.

## Trigger design (why these signals)

Job state is reconstructed from device-level entities only (see `docs/adr/0003-luba-device-level-entities-only.md` and the Luba section of `CONTEXT.md`). The backbone: a job end is `sensor.vrt_luba_progress` resetting to `0`; the progress value *before* the reset (read race-free via `trigger.from_state` - progress resets ~4 ms after the dock state change, so dock-triggered reads are racy) classifies it: `>= 90` is finished (observed completions peak at 99, never 100), `1-89` with a fresh fault is aborted, `1-89` without one is a deliberate cancel (silent). Progress survives recharges, rain pauses, and overnight waits, so mid-job interruptions never look like a job end.

- **Mow complete** - `progress` state trigger `to: "0"` + condition `trigger.from_state.state | int(0) >= 90`. A cancel above 90 % notifies as finished (harmless). `importance: low`, `timeout: 1800` (auto-dismiss after 30 min).
- **Needs attention** - `lawn_mower.vrt_luba -> error`, OR a premature job end (`progress` reset from 1-89 %) **with a fresh `last_error_time`** (within 15 min - widened from 5 after observing an 8-minute error-to-dock gap on 2026-07-30). The freshness gate means a deliberate cancel does NOT alarm. Persistent + sticky; clears when a new mow starts (`lawn_mower -> mowing`) or the mower leaves `error` into a real state (`to: docked/mowing/paused/returning` - the explicit `to:` list stops transport flaps through `unavailable` from wiping the alert).
  - Do NOT trigger on `sensor.vrt_luba_last_error_code != 0` - that sensor holds the last error *ever* (e.g. `1417` while docked and healthy), not a live-fault flag.
- **Offline** - `lawn_mower.vrt_luba = unavailable` for 10 min (long debounce absorbs cloud hiccups + this model's state-refresh lag). Clears on reconnect. Admin-only (`notify.mobile_app_sm_s926b`).
- **Rain while mowing** - `weather.forecast_home` becomes rain-like (`rainy`/`pouring`/`lightning-rainy`/`snowy-rainy`) for 5 min **and** `lawn_mower.vrt_luba` in `mowing`/`returning` (demonstrably out in the yard; `paused` is excluded because it cannot distinguish an in-yard pause from sitting on the dock overnight, which previously risked a false "returning home" alert). The mower exposes no rain-state telemetry, so this correlates HA weather with the mower being out. Clears when rain stops or the mower is no longer out.
- **Blade flip / replace** - thresholds derived from the live `sensor.vrt_luba_blade_wear_warning_time` (100 h): flip at 50% (template trigger, dynamic), replace at 100% (`numeric_state` above the warning-time entity). Both blade types are double-sided, so the flip stage applies to both. Persistent + sticky, each with an action button (`LUBA_BLADE_FLIPPED` / `LUBA_BLADE_REPLACED`) that sets the matching `input_boolean` and clears the notification. When the app counter resets (`blade_used_time` drops below 1 h on a fresh set), both booleans reset and both blade notifications clear.

## Known limitations / gotchas

- **No map-derived entities anywhere.** Deliberate: on LiDAR Lubas every entity generated from map/task objects - area switches (`switch.vrt_luba_area_*`), saved-task buttons, and task-area sensors - can duplicate/disappear/rename on map sync (Mammotion-HA issues #739/#604/#337). This bit hard on 2026-07-30: `sensor.vrt_luba_task_area_path`, the original trigger backbone, was actually a per-task-area sensor masquerading under a bugged generic display name (issue #700) and was deleted by the integration at a job end, killing three automations. All triggers now use device-level entities only (`progress`, `lawn_mower` state, `last_error_time`) per `docs/adr/0003-luba-device-level-entities-only.md`.
- **Rain is inferred, not reported** - the mower cannot tell HA "I stopped for rain"; the notification correlates `weather.forecast_home` with `MOWING`.
- **State-refresh lag** is lowest on cloud mode (`local_push`); triggers fire on transition edges, which tolerates stale idle values. Transport flaps (sub-minute `unavailable` blips across all mower entities at once) are tolerated by design: `int(0)` defaults make flap-restored values fail the numeric gates, and the needs-attention clear trigger filters `unavailable` out via its explicit `to:` list.
- **Blade counter reset** must be done in the Mammotion app when installing a fresh set; that reset is what re-arms the flip/replace stages.

## Related

- Integration setup / device details: `../../../CLAUDE.md` Known Issues + memory `project_mammotion_luba_integration`.
- Shared notification script: `notification-script.md`.
- Grill decisions + trigger rationale: `.claude/state/plans/2026-07-04-mammotion-luba-notifications.md` (original), `.claude/state/plans/2026-07-31-luba-trigger-redesign.md` (post-deletion redesign).
- Device-level-entities-only decision: `docs/adr/0003-luba-device-level-entities-only.md`; glossary: `CONTEXT.md` (Mammotion Luba section).
