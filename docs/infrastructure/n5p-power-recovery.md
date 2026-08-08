# n5p Power-Loss Recovery Runbook

How the homelab recovers after a full power outage, and what to do when it
does not. Written after the 2026-07-21/22 outage, where n5p stayed powered
off until manually started and three guests (containers VM 101, HAOS VM 102,
dev VM 148) did not auto-start. Revised after the 2026-08-08 power event,
where HAOS failed again for a reason the first fix did not model.

## Recovery chain

1. **AC power returns** - the BIOS must power the machine on (operator
   setting, see below). Fallback: Wake-on-LAN from rpi4.
2. **Proxmox boots and runs `startall`** - guests with `onboot=1` start in
   `startup` order groups.
3. **TrueNAS (VM 100, order=1) starts first** - its post-start hookscript
   blocks `startall` until the NFS export is genuinely writable, because every
   other guest's root disk lives on `truenas-vms` (NFS). "Writable" and not
   "answering": see the grace period below.
4. **order=2 group** (containers 101, HAOS 102, LXCs 200-205), then **order=3**
   (dev 148, hermes 206 when provisioned). CT 207 is `onboot: 0` and stays down.
5. **`pve-autostart-reconcile.service` sweeps up** - after `startall` finishes,
   it starts any `onboot=1` guest still down, because `startall` never retries.

## The NFSv4 grace period

The single most important thing to know when guests fail to start.

When `nfsd` starts on TrueNAS it enters a **90 second grace period** during
which it refuses every non-reclaim `OPEN` with `NFS4ERR_GRACE`, so that clients
can reclaim locks and opens from before the restart. **No guest disk can be
opened during it.** The Linux NFS client blocks and retries internally rather
than returning an error, so the symptom is a guest that hangs and then times
out, not an obvious I/O error.

PVE gives each guest a start budget of 30 s plus 5 s per NIC
(`config_aware_timeout`, x4 with PCI passthrough). HAOS gets 35 s. A guest
whose budget expires inside the grace window fails permanently, because
`startall` does not retry.

Grace runs its full 90 s only when a client the server remembers fails to come
back and reclaim, which is exactly what a power event produces: the server
returns with client records that no longer exist. When every remembered client
reclaims promptly, `nfsd` ends grace early and logs
`all clients done reclaiming`.

On 2026-08-08 grace ran 12:02:08 to 12:03:38. HAOS started at 12:03:02 and
timed out at 12:03:37, one second short.

## BIOS AC-power-restore checklist (operator, at the machine)

The Minisforum N5 Pro BIOS menu names are unknown until someone visits the
BIOS - record them here on the first visit:

- [ ] Set "Restore on AC Power Loss" (or similar) to **Power On**
- [ ] Verify **Wake-on-LAN** is enabled (often under Power Management or
      integrated NIC settings)
- [ ] ACTUAL MENU PATH / NAMES: _fill in after first BIOS visit_

Without the AC-restore setting, nothing else in this runbook matters - the
host stays off until someone presses the button or sends a WoL packet.

## Remote power-on via Wake-on-LAN

Works only with BIOS WoL enabled and standby power present (a full AC loss
followed by restore re-arms standby power; the NIC-side `wol g` flag is
re-armed at every boot by the `wol-arm.service` unit, managed by
`ansible/roles/proxmox/tasks/wol.yml`, tag `wol`).

```bash
ssh rpi4                      # the only always-on LAN device
wakeonlan <n5p-nic-mac>       # n5p primary NIC MAC
```

Verify the NIC is armed (on n5p): `ethtool enp197s0 | grep Wake-on` should
show `Wake-on: g`.

## Two traps in `startall`

Both bit on 2026-08-08 and both are worth knowing before reading any task log:

- **It never retries a failed guest.** The worker warns and moves to the next
  one. A guest that misses its start budget stays down until something else
  starts it.
- **It reports `TASK OK` even when a guest inside it failed.** The startall task
  for the 2026-08-08 boot is green in the task list despite VM 102 failing
  inside it. Never treat the startall task status as proof that guests are up.

`pve-autostart-reconcile.service` exists to cover the first. For the second,
check the guests, not the task.

## Post-outage diagnosis (guests did not start)

1. **Did the reconciler run, and did it give up?**

   ```bash
   systemctl status pve-autostart-reconcile.service
   journalctl -u pve-autostart-reconcile.service -b
   ```

   A failed unit means guests were still down after all passes. Its log names
   them.

2. **Was the NFS server in its grace period?** On TrueNAS:

   ```bash
   journalctl -k -b | grep -i grace
   # "starting 90-second grace period" with no matching "ending" line
   # means it ran the full 90s
   ```

3. **What did startall do?** Task logs live on n5p under
   `/var/log/pve/tasks/` - look for the `startall` UPID of the boot:

   ```bash
   grep -rl startall /var/log/pve/tasks/index* | tail
   # then read the matching task log for per-VM errors, e.g.
   # "Starting VM 102 failed: ... got timeout"
   ```

4. **Is the autostart config still correct?**

   ```bash
   for id in 100 101 102 148; do echo "== $id"; qm config $id | grep -E 'onboot|startup|hookscript'; done
   for id in 200 201 202 203 204 205 207; do echo "== $id"; pct config $id | grep -E 'onboot|startup'; done
   ```

   Expected: VM 100 `onboot: 1`, `startup: order=1,up=120` plus
   `hookscript: local:snippets/truenas-nfs-gate.sh`; VMs 101/102 and LXCs
   200-205 `onboot: 1`, `order=2` (hermes 206: `order=3`); dev 148
   `onboot: 1`, `order=3`. **CT 207 (mattermost) is `onboot: 0` on purpose** -
   deliberately stopped since 2026-07-22, pending removal.

5. **Gate log**: the hookscript's output (`truenas-nfs-gate: ...`) appears in
   the `qmstart:100` task log, not the startall log. `storage ready after Ns`
   is the success line. A `WARNING` line means the 600 s cap expired and later
   guests probably failed on storage - fix TrueNAS first.

6. **Manual start**, in ascending startup order. Prefer just running the
   reconciler, which does the ordering for you:

   ```bash
   /usr/local/sbin/pve-autostart-reconcile.sh
   # or individually
   qm start <vmid>    # VMs
   pct start <vmid>   # LXCs
   ```

## The NFS readiness gate and its invariant

`/var/lib/vz/snippets/truenas-nfs-gate.sh` (deployed by
`ansible/provision-truenas.yml` from `ansible/templates/truenas-nfs-gate.sh.j2`)
runs in VM 100's post-start phase. Every 5 s, for up to 600 s, it tries to
create, write and remove a temp file on each mount backing an autostarting
guest (`/mnt/pve/truenas-vms`, `/mnt/pve/truenas-vms-enc`). It exits 0
regardless at the cap, because PVE only warns on post-start hook errors and the
gate must never wedge `startall`.

**It probes a write, not `showmount`, and that distinction is the whole point.**
`showmount` talks to `rpc.mountd`, which answers long before `nfsd` can serve an
open, so it goes green during the grace period. Measured against a real 90 s
grace period: `showmount` green after 1 s, the write probe after 96 s. The
reasoning and the rejected alternatives are in ADR 0009.

Before trusting a successful write, the probe resolves the containing mount and
asserts it is NFS. An absent mount leaves a local stub directory under
`/mnt/pve/` that accepts writes happily and would turn the gate green instantly.

The fixed `up=120` delay on VM 100 stays as a belt. With a correct gate it is
dominated on any boot where the server actually needs time, so it costs nothing
and still protects if the hookscript ever fails to run.

**Invariant: TrueNAS must remain ALONE in startup order=1.** The gate only
delays *later* order groups - startall's end-of-group barrier waits for the
`vm_start` worker, and the hook runs synchronously inside it (verified on
PVE 9.2.4). A guest sharing order=1 would start concurrently, ungated.

## The autostart reconciler

`pve-autostart-reconcile.service` (deployed by
`ansible/roles/proxmox/tasks/autostart_reconcile.yml`) runs once after
`pve-guests.service` and starts any `onboot=1` guest that is not running, in
ascending startup order. Six passes 30 s apart, a window deliberately longer
than the 90 s grace period so it still succeeds if the gate hits its cap.

It exits non-zero when guests remain down, so a bad boot shows up in
`systemctl --failed` instead of being silent the way `startall` is.

**Boot-only on purpose.** A periodic sweep would fight every deliberate
`qm stop` / `pct stop`. The corollary is that `onboot=1` must mean "this guest
should be running" - if you stop a guest for more than a maintenance window,
set `onboot: false` in `ansible/vars/lxc.yml` or `vars/vms.yml` and reconcile,
or the next boot brings it back.

## Reconcile tags (config drift)

onboot/startup used to be create-time-only; since 2026-07-22 they are
reconciled. After editing the declared values, or to re-converge live drift:

```bash
cd ansible
ansible-playbook provision-vms.yml --tags vm-startup-reconcile     # VMs 101, 148
ansible-playbook provision-haos.yml --tags haos-startup-reconcile  # VM 102 (qm only)
ansible-playbook provision-lxc.yml --tags lxc-startup-reconcile    # declared LXCs
ansible-playbook provision-truenas.yml                             # VM 100 + gate hookscript
ansible-playbook site.yml --tags wol --limit n5p                   # WoL arming
ansible-playbook site.yml --tags autostart-reconcile --limit n5p   # reconciler unit
```

## True verification

The only end-to-end test of this chain is a deliberate reboot of n5p while the
operator is on the LAN: all guests must come up unattended, the `qmstart:100`
task log must show `truenas-nfs-gate: storage ready after Ns`, and
`pve-autostart-reconcile.service` must finish clean with
`all onboot guests running (pass 1/6)`.

**This has not been done.** As of 2026-08-08 the two halves were verified
separately without a reboot:

- The gate was tested against a real 90 s grace period on a throwaway NFS
  export, where the old `showmount` probe went green after 1 s and the new
  write probe after 96 s. It was also shown to refuse a writable non-NFS stub,
  refuse a missing path, and exit 0 on every failure path.
- The reconciler was tested on n5p: a no-op run exits on pass 1, stopping plex
  (CT 205) is detected and started on pass 1, and CT 207 is correctly left
  alone.

What remains unproven is the two halves working together through a real
`startall`, and the gate's behaviour against TrueNAS specifically rather than a
stand-in server.
