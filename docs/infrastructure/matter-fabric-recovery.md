# Matter fabric state backup and recovery

How-to for backing up and restoring the Matter fabric state held by
matter-server on `rpi4`. Covers what the fabric state is, the daily ZFS
snapshot schedule that protects it, and the capture/restore runbook.

The snapshot task is owned by `ansible/configure-truenas.yml`. This doc owns
the operator runbook.

## What the fabric state is

matter-server persists its entire fabric in its storage directory:

- Path on `rpi4` (192.168.1.110): `/srv/docker/matter-server/data`
- Backing storage: NFS from TrueNAS, dataset `tank/docker-volumes`
  (dataset-relative path `matter-server/data`)

That directory holds the fabric credentials and the node database for every
commissioned Matter device. **Losing it means re-commissioning all 20 Matter
devices by hand, one at a time.** Unlike the Thread network identity - which
is vaulted in `secrets.yml` and seeded back automatically on an empty store
(see `otbr-thread-recovery.md`) - the Matter fabric state is not vaulted and
cannot be reconstructed. Snapshots and tars are the only recovery path.

## The demonstrated failure mode

An empty data dir is not hypothetical. After a power loss, `rpi4` boots
faster than TrueNAS; its `/srv/docker` NFS mount was silently skipped and
Docker started matter-server against empty stub directories on the SD card,
taking the whole Matter network offline (see "NFS mount race after power
loss" in the repo Known Issues). Two guards exist today:

- The docker.service drop-in on `rpi4` polls the automount before Docker
  starts and retries forever on failure.
- The `common.assert_nfs_mount` guard makes every converge fail fast rather
  than deploy against a local stub.

Those guards prevent *writing* fresh state to the wrong place. They do not
protect against corruption or deletion of the real data - that is what the
snapshots and this runbook are for.

## Daily snapshot schedule

TrueNAS snapshots the whole `tank/docker-volumes` dataset:

| Setting | Value |
| --- | --- |
| Schedule | daily at 00:00 |
| Retention | 1 week |
| Recursive | no |
| Naming | `auto-%Y-%m-%d_%H-%M` (e.g. `auto-2026-07-31_00-00`) |

**Crash-consistency caveat:** these snapshots are taken while matter-server
is running, so they are crash-consistent - equivalent to the state after a
power cut. That is normally recoverable, but a tar taken with the container
stopped is the gold copy. Take one before any risky change (host rebuilds,
matter-server major upgrades, storage migrations).

## Capture (stopped-server gold copy)

On `rpi4`:

```bash
sudo docker stop matter-server
sudo tar czf /tmp/matter-fabric-$(date +%F).tgz -C /srv/docker/matter-server data
sudo docker start matter-server
```

Copy the tar somewhere durable (not the SD card, not `tank/docker-volumes`
itself). The stop keeps the on-disk state quiescent so the tar is exact, not
crash-consistent.

### Pulling files out of a snapshot instead

Snapshots are browsable read-only on TrueNAS (192.168.1.150) without any
restore step:

```bash
ls /mnt/tank/docker-volumes/.zfs/snapshot/
ls /mnt/tank/docker-volumes/.zfs/snapshot/<name>/matter-server/data/
```

Copy files out of the snapshot dir like any directory. Do not roll back the
whole dataset (`zfs rollback`) casually - `tank/docker-volumes` backs every
Docker service, not just matter-server.

## Restore

1. Stop the container on `rpi4`:

   ```bash
   sudo docker stop matter-server
   ```

2. Move the damaged state aside and restore. From a tar:

   ```bash
   sudo mv /srv/docker/matter-server/data /srv/docker/matter-server/data.broken-$(date +%F)
   sudo tar xzf /tmp/matter-fabric-<date>.tgz -C /srv/docker/matter-server
   ```

   Or from a snapshot, copying via the TrueNAS side:

   ```bash
   # on tn-storage (192.168.1.150)
   cp -a /mnt/tank/docker-volumes/.zfs/snapshot/<name>/matter-server/data \
         /mnt/tank/docker-volumes/matter-server/
   ```

3. Start the container and verify:

   ```bash
   sudo docker start matter-server
   sudo docker logs -f matter-server   # clean startup, no schema/credential errors
   ```

4. In Home Assistant, confirm the Matter devices come back as available.
   Nodes can take a few minutes to re-subscribe; a restored fabric needs no
   re-commissioning.

If devices stay unavailable, check the Thread side first
(`otbr-thread-recovery.md`) before touching the fabric state again.

## Migration runbook: python-matter-server to matterjs-server

One-time, operator-driven migration of the fabric controller from the
archived python-matter-server (8.1.2 was its final release) to its
successor `ghcr.io/matter-js/matterjs-server`. The new server reads the
old storage on first start and converts it in place. A known
standalone-Docker failure mode exists (home-assistant/core issue #168531):
the server silently creates a NEW fabric instead of converting the old
one, which would mean re-commissioning all 20 devices by hand. The
tripwire in step 8 exists to catch exactly that before anything else
touches the fabric.

Reference values for the live fabric:

- compressed_fabric_id: `4941327263744875345`
- Node count: 20

1. **Preconditions** - all of these must hold before starting:

   - Managed time sync is active on `rpi4`:
     `timedatectl show -p NTPSynchronized` reports `yes`.
   - The TrueNAS daily snapshot task for `tank/docker-volumes` is live
     (see "Daily snapshot schedule" above).
   - Home Assistant is healthy.
   - `scripts/matter_probe.py` shows 20/20 nodes available and prints
     `compressed_fabric_id` `4941327263744875345`. Note the value it
     prints - step 7 compares against it.

2. **Manual pre-migration snapshot** on TrueNAS (192.168.1.150):

   ```bash
   midclt call zfs.snapshot.create '{"dataset":"tank/docker-volumes","name":"pre-matterjs-migration"}'
   ```

3. **Stop the server** on `rpi4`. HA Matter entities go unavailable -
   expected:

   ```bash
   sudo docker stop matter-server
   ```

4. **Gold-copy tar with the server stopped**, then copy it to the
   operator machine:

   ```bash
   # on rpi4
   sudo tar czf /tmp/matter-fabric-pre-matterjs-$(date +%F).tgz -C /srv/docker/matter-server data

   # from the operator machine
   scp rpi4:/tmp/matter-fabric-pre-matterjs-<date>.tgz ~/backups/
   ```

5. **Chown the storage files to the container user** before first start:

   ```bash
   sudo chown -R 1000:1000 /srv/docker/matter-server/data
   ```

   The matterjs image runs as user 1000:1000; the python server ran as
   root with the node store at mode 0600. The loader gates legacy
   detection on `chip.json` but treats an unreadable node store as
   optional: the server then starts SILENTLY with migrated fabric
   credentials and 0 nodes, logging only a debug-level line.

6. **Converge** the role onto the new image:

   ```bash
   ansible-playbook site.yml --tags matter-server --limit rpi4
   ```

7. **Wait for container health** to reach `healthy`. The first start may
   take up to ~15 min (storage conversion plus re-interviewing 20 nodes);
   the converge itself polls for this, or watch manually on `rpi4`:

   ```bash
   sudo docker inspect --format '{{.State.Health.Status}}' matter-server
   ```

   Then confirm the node store was actually read - healthy alone does
   not prove it:

   ```bash
   sudo docker logs matter-server | grep -E "Loaded legacy server data|Injecting node"
   ```

   Expect `Loaded legacy server data from 4941327263744875345.json: 20 node(s)`
   plus one `Injecting node <n>` line per node. If these lines are
   absent, the node store was not read even though the server reports
   healthy.

8. **TRIPWIRE** - verify the fabric survived before anything else:

   ```bash
   /tmp/mp-venv/bin/python scripts/matter_probe.py
   ls /srv/docker/matter-server/data
   ```

   All of these must hold:

   - `compressed_fabric_id` equals the noted value
     (`4941327263744875345`).
   - All 20 nodes are listed.
   - No fresh `server-*` directory has appeared in the data dir alongside
     otherwise-untouched old files - that combination is the known
     new-fabric failure signature.

9. **On tripwire failure: ABORT.** Never debug the new server against
   live fabric data.

   - `sudo docker stop matter-server`
   - Restore the step-4 tar over `data/` (see "Restore" above).
   - Redeploy the previous role state (check out the pre-migration
     commit, converge with the same tags).
   - Verify with `scripts/matter_probe.py`, then investigate offline on a
     copy of the data.

10. **On success:**

    - Spot-check Matter devices in Home Assistant.
    - Add an Uptime Kuma TCP monitor for `192.168.1.110:5580` (manual UI
      step, see Monitoring below).

11. **Soak for about a week** before enabling controller time sync (that
    is a separate, later change).

### Known failure modes

- **Silent nodeless start** (this migration's attempt 1): the probe shows
  0 nodes, a fresh `server-1-fff1/` directory appears, and the legacy
  json files are byte-identical to the backup. The node store was
  unreadable to uid 1000. Restore the tar, fix ownership (step 5), retry.
- **An interrupted injection poisons retries**: the injector writes
  per-node `__version__` markers as it goes; a re-run skips marked nodes
  and never writes `commissionedNodes`. Never re-run over a half-migrated
  data dir - always restore the tar first.

## Monitoring

matter-server's WebSocket port (tcp/5580 on `rpi4`) should be watched by an
Uptime Kuma monitor (manual UI step, not Ansible-managed). An alert there
plus mass-unavailable Matter devices is the trigger for this runbook.

## Reference

- Snapshot task: `ansible/configure-truenas.yml` (dataset `tank/docker-volumes`)
- Data dir: `/srv/docker/matter-server/data` on `rpi4`, NFS from TrueNAS
- Snapshot browse path: `/mnt/tank/docker-volumes/.zfs/snapshot/<name>/` on TrueNAS
- NFS guard: `ansible/roles/common/tasks/assert_nfs_mount.yml`
