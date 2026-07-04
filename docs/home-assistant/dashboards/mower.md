# Luba Mower Dashboard

Dedicated sidebar dashboard for the Mammotion Luba Mini 2 AWD 1500 LiDAR mower (`lawn_mower.vrt_luba`, integration `mikey0000/Mammotion-HA`, cloud mode). A curated, glanceable surface (camera + controls + status) that replaces having to hunt for the mower in the auto-generated Vrt area view, where its 77 device entities are buried among ~50 tiles.

Built entirely with **native cards + already-installed HACS customs** (no third-party mower card, no new resource, no restart), matching the estate's `dashboard-printing` and `air-conditioner` (Klima) dashboards. All config via the `ha-mcp` tools - never edit HA YAML.

## Dashboard

| Property | Value |
|----------|-------|
| URL path | `/dashboard-mower` |
| Title | Luba |
| Icon | `mdi:robot-mower` |
| Sidebar | Visible (household-facing, non-admin) |
| View type | Sections |

This is the deep-link target for every Luba notification tap (`clickAction: /dashboard-mower`); see [`../automations/mower-luba.md`](../automations/mower-luba.md).

## Header badges

`sensor.vrt_luba_battery`, `binary_sensor.vrt_luba_charging`, `sensor.vrt_luba_task_area_path` (battery / charging / task state at a glance).

## Section 1 - main (camera + controls + core status)

**Camera hero** - `picture-glance` over `camera.vrt_luba` (`camera_view: auto` = snapshot that goes live on tap, bandwidth-friendly for a mostly-docked mower; `fit_mode: cover`, full-width, 8 rows tall). Battery / charging / task-state overlaid as glance chips. Native live view uses WebRTC via go2rtc (HAOS).

**Control row** - native `button` cards (Slovenian labels), start/pause/dock via `lawn_mower.*` service `tap_action`, undock via `button.press`:

| Button | Action |
|--------|--------|
| Zaženi | `lawn_mower.start_mowing` |
| Premor | `lawn_mower.pause` |
| V postajo | `lawn_mower.dock` |
| Iz postaje | `button.press` on `button.vrt_luba_undock` |

Undock is a separate `button` entity, not a `lawn_mower` capability - HA core has no undock service (mower `supported_features: 7` = start/pause/dock only).

**Core status tiles**

| Entity | Display name |
|--------|-------------|
| `lawn_mower.vrt_luba` | Stanje |
| `sensor.vrt_luba_task_area_path` | Naloga |
| `sensor.vrt_luba_battery` | Baterija (trend-graph) |
| `sensor.vrt_luba_progress` | Napredek |
| `sensor.vrt_luba_time_left` | Preostali čas |
| `sensor.vrt_luba_activity_mode` | Način |

## Section 2 - settings + health

| Entity | Display name |
|--------|-------------|
| `sensor.vrt_luba_connection` | Povezava |
| `sensor.vrt_luba_wi_fi_rssi` | WiFi signal |
| `sensor.vrt_luba_satellites_robot` | Sateliti |
| `sensor.vrt_luba_area` | Površina |
| `sensor.vrt_luba_blade_used_time` | Obraba rezil (trend-graph) |
| `number.vrt_luba_blade_height` | Višina rezila (slider) |
| `number.vrt_luba_working_speed` | Hitrost (slider) |
| `switch.vrt_luba_rain_detection_during_mow_on_off` | Zaznavanje dežja (toggle) |
| `switch.vrt_luba_side_led_on_off` | Stranski LED (toggle) |
| `sensor.vrt_luba_total_mileage` | Skupaj prevoženo |
| `sensor.vrt_luba_total_work_time` | Skupaj delo |
| `update.vrt_luba_firmware` | Vdelana programska oprema |

## Design notes

- **Why a dedicated dashboard, not a card on the home dashboard:** the `home` and `areas` dashboards are strategy-generated; a top-level `strategy:` key replaces the entire config, so no custom card can coexist with it. A curated card must live on a manual surface. A new sidebar dashboard (like Printing / Klima) is the cleanest, fully isolated from strategy re-renders.
- **The mower still auto-appears** in the Vrt area subview (`/home/areas-driveway`) - this dashboard is additive, not a replacement. No entities were hidden (hiding is global across every UI).
- **Blueprint:** `dashboard-printing` ("Centauri Carbon") - same pattern of camera hero + native button control row + tile status grid.
- Research: `.claude/state/research/2026-07-04-research-luba-mower-dashboard-card.md`; plan: `.claude/state/plans/2026-07-04-luba-mower-dashboard.md`.
