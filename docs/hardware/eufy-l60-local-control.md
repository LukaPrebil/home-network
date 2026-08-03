# Eufy L60 Hybrid SES - Local (Tuya) Control in Home Assistant

Setup date: 2026-06-05

## Summary

The Eufy L60 Hybrid SES (model **T2278**, firmware 1.4.5) is controlled **locally over the LAN** from Home Assistant, with no dependency on the Eufy/Anker cloud for day-to-day control. This replaces the stock app path (`app -> Eufy cloud -> device wifi -> vacuum`), which intermittently reported the device offline. HA now talks directly to the vacuum: `HA -> LAN -> vacuum`.

Integration: [`damacus/robovac`](https://github.com/damacus/robovac), installed via HACS as a custom repository, pinned to **`v2.4.3-beta.1`**.

| Fact | Value |
|---|---|
| Model | L60 Hybrid SES (`T2278`) |
| Integration | `damacus/robovac` `v2.4.3-beta.1` (HACS custom repo) |
| Transport | Tuya local protocol - AES over TCP `6668` (control), UDP `6666/6667` (discovery) |
| Entities | `vacuum.robi`, `sensor.hisa_robi_battery` |
| Device id (Tuya gwId) | `<tuya-gwid>` |
| MAC | `<vacuum-mac>` |
| Eufy account | owner account (`<eufy-account-email>`) |

The HA device is named **Robi** (a name carried over from an earlier, now-removed integration attempt for the same vacuum); the device registry confirms `model: L60 Hybrid SES`.

## Why this integration, and not `jeppesens/eufy-clean`

Eufy splits its fleet across two control platforms, and the choice of integration depends entirely on which one a given model uses:

- **Tuya platform (older line)** - the L60 family (`T2267` L60, `T2277` L60 SES, `T2278` L60 Hybrid SES). Speaks the Tuya local protocol, so it can be controlled directly over the LAN with a per-device local key.
- **Anker AIOT / MQTT platform (newer line)** - X10 Pro Omni, X8 Pro, G40 and similar. These talk to Anker's cloud MQTT broker.

`jeppesens/eufy-clean` ("Eufy Robovac MQTT") targets the **MQTT/AIOT** line. It is cloud-dependent by design (it connects to Anker's MQTT broker) and does not list the L60. It would not have removed the cloud dependency even if it had connected. `damacus/robovac` is the Tuya-**local** integration and is the correct match for a T2278.

`damacus/robovac` ships a dedicated model definition `custom_components/robovac/vacuums/T2278.py`. The `v2.x` line carries a mature, device-validated mapping (decoded status codes, working fan speeds, room/zone/map features); the older `v1.5.0` stable carried an early best-guess mapping (undecoded status, placeholder fan speed). That is why a `v2` beta was chosen over the latest stable.

## How local control works

1. The HACS config flow performs a **one-time login** to the Eufy account, then uses a derived Tuya cloud session to fetch each vacuum's **Device ID** and **16-byte local key** (`localKey`). These are stored in the HA config entry.
2. From then on, HA speaks the Tuya local protocol **directly to the vacuum over the LAN**. It keeps working when the Eufy/Anker cloud is unreachable, as long as HA and the vacuum share the network.
3. The vacuum's **IP is auto-discovered** via Tuya UDP broadcast and self-heals if it changes, so a DHCP reservation is a nice-to-have rather than a hard requirement.

The local key is fetched **only during the config flow**. There is no runtime re-auth, so a rotated key is not recovered automatically (see Operations).

## Setup steps (as performed)

1. **HACS custom repository**: add `https://github.com/damacus/robovac` as an Integration. (`damacus/robovac` is HACS-Custom, not in the default store.)
2. **Download**: install version `v2.4.3-beta.1`. This is a pre-release, so beta versions must be visible in HACS.
3. **Restart Home Assistant** to activate the integration (`pending-restart` until then).
4. **Add the integration**: Settings -> Devices & Services -> Add Integration -> "Eufy RoboVac" -> enter the **owner** Eufy email and password. Region/country auto-detects. The flow fetches every "Cleaning" device on the account and creates a `vacuum.*` entity per device (devices present in Eufy but not in the Tuya home are skipped).
5. The entity comes up `unknown`/`unavailable` for a short window while UDP discovery finds the IP and the local handshake completes, then settles to a live state (`idle`, `docked`, etc.).

## Operations and troubleshooting

### "Device is already configured" when adding

The config flow sets the **config entry's unique id to the Eufy account email**. If an entry already exists for that account (for example, a previous attempt or an older vacuum on the same account), the flow aborts with "already configured" after a successful login, and no new entity is created. This happened during setup: a stale, user-disabled entry for an older vacuum on the same account had to be deleted first (Settings -> Devices & Services -> the old robovac entry -> Delete), after which the L60 added cleanly.

### Entity shows `unavailable` right after setup

Expected for the first seconds to tens of seconds while Tuya UDP discovery resolves the IP and the AES handshake completes. It resolves on its own. If it stays unavailable, suspect, in order: (1) no IP discovered (UDP `6666/6667` blocked, or HA and the vacuum on different L2 segments / AP isolation), (2) Tuya local-protocol version mismatch (newer firmware can move to protocol 3.4/3.5 - `damacus/robovac` negotiates this, but it is the prime suspect if read works but control does not), (3) a stale local key.

### Local key rotation (no auto-recovery)

If the Eufy cloud rotates the device's local key, HA can no longer talk to the vacuum and the entity goes dead. The integration does **not** re-fetch the key at runtime. Recovery is a manual delete + re-add:

1. Settings -> Devices & Services -> the `robovac` entry -> Delete.
2. Add Integration -> "Eufy RoboVac" -> re-enter the owner Eufy credentials. This fetches the current key.

Rotation is triggered by the device re-syncing with the Eufy cloud, so it is typically infrequent for the Tuya L60 line. The permanent fix is to block the vacuum from the internet (below), which prevents it from phoning home and rotating the key.

### Offline hardening (available, not yet applied)

Full internet isolation was deliberately deferred (VLAN 40 is not yet deployed and was out of scope for this work). When wanted, the vacuum can be cut off from the Eufy/Anker cloud without waiting for VLAN segmentation, by either:

- an **AdGuard per-client rule** blocking the Eufy/Tuya cloud domains for the vacuum's IP, or
- a **gateway firewall rule** denying WAN for the vacuum's IP/MAC.

This both stabilizes the local key (no phone-home, no rotation) and reaches the intended full-offline end state. Apply it only **after** the key is extracted and local control is verified, since extraction needs the cloud. Note the one-way consequence: once blocked, the official Eufy app stops working entirely (even on the LAN), because the app is cloud-only. Control then lives exclusively in Home Assistant.

## References

- Integration: https://github.com/damacus/robovac (docs: https://damacus.github.io/robovac/)
- Model definition: `custom_components/robovac/vacuums/T2278.py` (docstring "eufy Clean L60 Hybrid SES (T2278)")
- Cloud/MQTT alternative (wrong platform for the L60): https://github.com/jeppesens/eufy-clean
- Research artifact (local, not committed): `.claude/state/research/2026-06-05-research-eufy-l60-local-control.md`
