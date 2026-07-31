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

## Monitoring

matter-server's WebSocket port (tcp/5580 on `rpi4`) should be watched by an
Uptime Kuma monitor (manual UI step, not Ansible-managed). An alert there
plus mass-unavailable Matter devices is the trigger for this runbook.

## Reference

- Snapshot task: `ansible/configure-truenas.yml` (dataset `tank/docker-volumes`)
- Data dir: `/srv/docker/matter-server/data` on `rpi4`, NFS from TrueNAS
- Snapshot browse path: `/mnt/tank/docker-volumes/.zfs/snapshot/<name>/` on TrueNAS
- NFS guard: `ansible/roles/common/tasks/assert_nfs_mount.yml`
