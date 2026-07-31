# Migrate the Matter fabric controller to matterjs-server and enable controller time push

Status: accepted (2026-07-31)

python-matter-server, which runs this network's entire Matter fabric (20 Thread nodes) as a standalone container on rpi4, was archived upstream on 2026-06-23; our pinned 8.1.2 is its final release and will never receive fixes or the time-synchronization feature this work needs (the fleet's only time-capable device, the ALPSTUGA air quality monitor, sits with an empty clock because nothing re-sends time after a power cycle). We migrate the standalone container to the official successor `ghcr.io/matter-js/matterjs-server`, pinned to an exact version >= 1.3.2 (the floor for correct DST handling on devices that carry no timezone database), in two phases: migrate first with time sync disabled and verify the fabric survived (compressed fabric id unchanged, all 20 nodes present), then enable `ENABLE_TIME_SYNC` after a roughly one-week soak.

## Considered options

- **Stay on 8.1.2 and add the community HACS workaround (Loweack/Matter-Time-Sync)** - rejected: leaves the fabric controller permanently EOL and bolts a third-party integration onto a dead server to imitate a feature the successor ships natively.
- **Move matter-server into HAOS as the official add-on** (whose `time_sync: auto` mode gets a host-clock guard via the Supervisor) - rejected: moves the fabric state out of the Ansible/NFS-managed estate into the unmanaged appliance VM and couples the controller lifecycle to HA upgrades.

## Consequences

- Standalone matterjs-server has no host-clock guard (the add-on's `auto` mode is add-on-only); it pushes the host clock unconditionally. Managed NTP on rpi4 is therefore a hard prerequisite, delivered as an Ansible-managed timesyncd config driven by a central `ntp_servers` variable - which is also the seam for a future local time server (planned rpi2 + GPS): repoint the variable, converge.
- Rollback is restore-from-backup only (pre-migration tar plus ZFS snapshot, taken with the server stopped). The upstream claim that legacy storage stays rollback-compatible is contradicted by the add-on migration FAQ and is not relied on.
- A known standalone-Docker migration failure mode exists (home-assistant/core#168531: a fresh fabric is created instead of migrating, which would force re-commissioning all 20 devices). The migration runbook gates on a fabric-id tripwire immediately after first start; any mismatch aborts to restore, never debug-live.
- The compose-level healthcheck is dropped in favor of the image's built-in one (the old check invoked `python3`, which does not exist in the Node-based image and would have combined with the autoheal label into a permanent restart loop).
- The image runs as uid 1000 (non-root) and silently skips a legacy node store it cannot read, so storage-file ownership is part of the migration contract: the runbook chowns the data dir to 1000:1000 before first start.
