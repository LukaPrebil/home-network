# TrueNAS VM virtio-net tuning

How-to for the four tunables we apply to the TrueNAS VM (vmid 100) to
mitigate an upstream race in `virtio-net` that can wedge the VM's
network interface under sustained outbound traffic. Owns the operator
runbook; the *why* is in
`.claude/state/research/2026-05-05-research-adguard-io-stall.md`.

## What the tuning does, in one paragraph

By default the TrueNAS VM ships with a single virtio-net TX/RX queue
pair, the guest's `virtio_net.napi_tx` set to `Y`, and Proxmox's
per-VM firewall bridge stack inserted on net0. That combination is
vulnerable to a known QEMU↔guest "host waits forever for a kick" race
documented in upstream patch series ["virtio-net: Fix network stall at
the host side waiting for kick"](https://www.mail-archive.com/qemu-devel@nongnu.org/msg1059032.html)
(merged QEMU master August 2024). Sustained bidirectional throughput
— a multi-GB NFS read, a Plex stream, an Immich indexing pass — can
trigger it; once triggered, the NIC stays wedged until the VM reboots.
The mitigations:

| # | Knob | Where | Effect |
| - | ---- | ----- | ------ |
| 1 | `queues=4` on net0 | qm config 100 | 4 vhost-net threads, 4 TX/RX rings. If the race triggers on one queue, the other three keep working — total NIC death drops to ~25 % degradation. |
| 2 | `firewall=0` on net0 | qm config 100 | Removes the per-VM `fwbr/fwln/fwpr` bridge stack (4 hops → 1). Saves CPU and removes packet-path complexity that adds timing variance. Safe because `pve-firewall` is globally disabled and we don't use per-VM rules. |
| 3 | `virtio_net.napi_tx=0` | TrueNAS guest kernel cmdline | TX completions return via classical interrupts instead of NAPI batching. The race lives in the NAPI poll path; this closes it in the guest. Negligible CPU cost at home-LAN speeds. |
| 4 | QEMU ≥9.1 (host-side) | `pve-qemu-kvm` package | Carries the Aug-2024 upstream fix. Defence-in-depth alongside the guest-side knobs. Already true for `pve-qemu-kvm 10.1.2-7`. |

We deliberately do **not** disable TSO/GSO offloads — the throughput
cost (~20–30% on bulk transfers) is real and the mitigations above are
sufficient.

## Where it lives in IaC

- **net0 (`queues=4`, `firewall=0`)** — `ansible/provision-truenas.yml`.
  The playbook is a create-or-converge reconciler: first run creates
  the VM with the right net0; subsequent runs parse the live qm config,
  overlay managed fields onto the existing key=value pairs (so unknown
  fields like `tag=`, `rate=`, `link_down=` are preserved), and apply
  via `qm set` if drifted. The MAC is read from the live config and
  preserved.
- **`virtio_net.napi_tx=0`** — `ansible/configure-truenas.yml`. The
  `kernel_extra_options` play reads the current value via
  `midclt call system.advanced.config`, takes the **set union** of
  current + required options (so order changes don't cause spurious
  rewrites), and applies via `midclt call system.advanced.update` if
  any required option is missing. **No reboot in this play** — the
  change is staged in TrueNAS's config DB and activates on next boot.
- **QEMU version** — out of repo scope; verified once. `pve-qemu-kvm
  10.1.2-7` carries upstream commit `f937309f` ("virtio-net: Fix
  network stall at the host side waiting for kick", merged into QEMU
  master Aug 2024 → present in v10.1.2 tag).

## Run order and the operator reboot gate

`provision-truenas.yml` checks three drift signals on every run:

1. **on-disk net0** drift (qm config differs from desired);
2. **runtime queue** drift (live `ethtool -l` reports fewer queues
   than the managed `queues=` value — catches half-applied state from
   a prior failed run, or a config change not yet activated);
3. **cmdline** drift (options staged via `kernel_extra_options` are
   not yet present in the running guest's `/proc/cmdline`).

If any drift is detected, the playbook **fails fast** unless the
operator has explicitly opted into the reboot during this run with
`-e truenas_allow_reboot=true`. This guard exists because rebooting
TrueNAS takes every NFS-backed VM/LXC into IO wait until it comes back
— accidentally tripping it during an unrelated convergence run is the
exact failure mode we want to prevent.

```bash
cd ansible

# 1. Stage cmdline changes (no reboot, no operator gate needed).
ansible-playbook configure-truenas.yml

# 2. During a maintenance window, apply qm config and reboot.
ansible-playbook provision-truenas.yml -e truenas_allow_reboot=true
```

Either play is also safe to run without changes — the reconcilers
just report no drift.

If the playbook detects drift while not gated, it prints an explicit
error pointing here and exits non-zero. Re-run with the gate during a
maintenance window.

## Verification

After the maintenance reboot, every check should match. Anything off
→ stop and roll back the relevant change.

| Run from | Command | Expect |
| -------- | ------- | ------ |
| n5p | `qm config 100 \| grep ^net0:` | `virtio=<MAC>,bridge=vmbr0,firewall=0,queues=4` |
| n5p | `ip link \| grep fwbr100` | empty |
| n5p | `pgrep -a vhost \| grep -c vhost` | ≥ 4 (one per queue, plus other VMs') |
| tn-storage | `cat /proc/cmdline` | contains `virtio_net.napi_tx=0` |
| tn-storage | `cat /sys/module/virtio_net/parameters/napi_tx` | `N` |
| tn-storage | `ethtool -l enp6s18 \| awk '/Combined/{print $2;exit}'` | `4` |
| tn-storage | `ls /sys/class/net/enp6s18/queues` | `tx-0..3 rx-0..3` |
| any client | `dig @192.168.1.145 google.com +short +time=2 +tries=1` | answer in <1 s |

The reconciler in `provision-truenas.yml` runs the same checks
unconditionally at the end of every run (`Re-read ethtool` and
`Re-read /proc/cmdline` → `Assert multiqueue active and cmdline
applied`). A half-applied state from a prior failed run is therefore
caught on the next run rather than going silent.

Half-applied recovery: if a previous run's reboot failed mid-flight
(VM stayed down after `qm shutdown`, or restarted with old runtime
state), the next run's drift detector trips on `drift_runtime`
(ethtool returns non-zero or reports fewer queues) and re-notifies
the Restart handler chain. Re-run `provision-truenas.yml -e
truenas_allow_reboot=true` to recover.

## Rollback

Each knob is reversible.

### Roll back the qm config

```bash
# On n5p
qm set 100 -net0 virtio=<MAC>,bridge=vmbr0,firewall=1
qm shutdown 100 --timeout 120 && qm start 100
```

In IaC: revert the `--net0` line in `provision-truenas.yml` (the
create-only block) and the `truenas_net0_desired` set_fact (the
reconciliation block), then re-run.

### Roll back the kernel cmdline

```bash
# On TrueNAS via SSH
midclt call system.advanced.update '{"kernel_extra_options": ""}'
# Reboot the VM from n5p:
ssh root@n5p 'qm shutdown 100 --timeout 120 && qm start 100'
```

In IaC: drop `virtio_net.napi_tx=0` from the `truenas_kernel_extra_required`
list in `configure-truenas.yml`, re-run, then reboot.

## Maintenance window expectations

A TrueNAS VM reboot is equivalent to a stack-wide brownout for 2–5 min:

- Every NFS-backed VM/LXC on n5p (immich, traefik, omada, adguard
  primary, monitoring, media, containers, dev, haos) goes into IO wait
  until TrueNAS comes back. NFS is mounted `hard` so they recover on
  their own — no manual restarts.
- DNS goes dark for the window because AdGuard primary's root disk is
  on TrueNAS NFS. The secondary on rpi4 stays up but most clients pay
  the per-query fail-over timeout (see Layer 2 in the research artifact).
- Streaming (Plex/Jellyfin) and Immich indexing pause for the window.

Tell the household before pressing run.

## Reference

- Incident: 2026-05-05 17:07–18:01 CEST (TrueNAS NIC wedged for ~110 min,
  brought down DNS).
- Research: `.claude/state/research/2026-05-05-research-adguard-io-stall.md`.
- Plan: `.claude/state/plans/2026-05-05-plan-truenas-virtio-fix.md`.
- Upstream patch series: ["virtio-net: Fix network stall at the host
  side waiting for kick"](https://www.mail-archive.com/qemu-devel@nongnu.org/msg1059032.html),
  Wencheng Yang / Jason Wang, qemu-devel, merged Aug 2024.
- Affected stack at incident time: TrueNAS Scale 25.04.2.6 (kernel
  6.12.15-production+truenas), Proxmox VE 9.x with kernel 6.17.13-3-pve,
  pve-qemu-kvm 10.1.2-7.
