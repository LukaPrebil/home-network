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

The `sensor.vrt_luba_task_area_path` enum (`UNKNOWN, NOT_STARTED, WAITING, MOWING, COMPLETE, ABORTED`) is the backbone - it distinguishes a true finish from a recharge-and-resume, and a stuck/aborted job from normal running.

- **Mow complete** - `task_area_path -> COMPLETE`. Recharge-and-resume shows `WAITING`, so it never false-fires. `importance: low`, `timeout: 1800` (auto-dismiss after 30 min).
- **Needs attention** - `task_area_path -> ABORTED` **with a fresh `last_error_time`** (within 5 min), OR `lawn_mower.vrt_luba -> error`. The freshness gate means a deliberate cancel (clean `ABORTED`, no fresh error) does NOT alarm. Persistent + sticky; clears when the task leaves `ABORTED` and the mower is not in `error`.
  - Do NOT trigger on `sensor.vrt_luba_last_error_code != 0` - that sensor holds the last error *ever* (e.g. `1417` while docked and healthy), not a live-fault flag.
- **Offline** - `lawn_mower.vrt_luba = unavailable` for 10 min (long debounce absorbs cloud hiccups + this model's state-refresh lag). Clears on reconnect. Admin-only (`notify.mobile_app_sm_s926b`).
- **Rain while mowing** - `weather.forecast_home` becomes rain-like (`rainy`/`pouring`/`lightning-rainy`/`snowy-rainy`) for 5 min **and** `task_area_path = MOWING`. The mower exposes no rain-state telemetry, so this correlates HA weather with the mower being out. Clears when rain stops or the mower comes in.
- **Blade flip / replace** - thresholds derived from the live `sensor.vrt_luba_blade_wear_warning_time` (100 h): flip at 50% (template trigger, dynamic), replace at 100% (`numeric_state` above the warning-time entity). Both blade types are double-sided, so the flip stage applies to both. Persistent + sticky, each with an action button (`LUBA_BLADE_FLIPPED` / `LUBA_BLADE_REPLACED`) that sets the matching `input_boolean` and clears the notification. When the app counter resets (`blade_used_time` drops below 1 h on a fresh set), both booleans reset and both blade notifications clear.

## Known limitations / gotchas

- **No zone-keyed triggers.** Deliberate: on LiDAR Lubas the per-area entities (`switch.vrt_luba_area_*`) can duplicate/disappear/rename (Mammotion-HA issue #739), which would break zone-targeted automations. All triggers use `task_area_path` / mower state instead.
- **Rain is inferred, not reported** - the mower cannot tell HA "I stopped for rain"; the notification correlates `weather.forecast_home` with `MOWING`.
- **State-refresh lag** is lowest on cloud mode (`local_push`); triggers fire on transition edges, which tolerates the stale idle values (e.g. `task_area_path` reads a stale `MOWING` while docked).
- **Blade counter reset** must be done in the Mammotion app when installing a fresh set; that reset is what re-arms the flip/replace stages.

## Related

- Integration setup / device details: `../../../CLAUDE.md` Known Issues + memory `project_mammotion_luba_integration`.
- Shared notification script: `notification-script.md`.
- Grill decisions + trigger rationale: `.claude/state/plans/2026-07-04-mammotion-luba-notifications.md`.
