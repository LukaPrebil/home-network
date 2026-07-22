# n5p Power-Loss Recovery Runbook

How the homelab recovers after a full power outage, and what to do when it
does not. Written after the 2026-07-21/22 outage, where n5p stayed powered
off until manually started and three guests (containers VM 101, HAOS VM 102,
dev VM 148) did not auto-start.

## Recovery chain

1. **AC power returns** - the BIOS must power the machine on (operator
   setting, see below). Fallback: Wake-on-LAN from rpi4.
2. **Proxmox boots and runs `startall`** - guests with `onboot=1` start in
   `startup` order groups.
3. **TrueNAS (VM 100, order=1) starts first** - its post-start hookscript
   blocks `startall` until the NFS export actually answers, because every
   other guest's root disk lives on `truenas-vms` (NFS).
4. **order=2 group** (containers 101, HAOS 102, all LXCs), then **order=3**
   (dev 148, hermes 206 when provisioned).

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
wakeonlan <n5p-nic-mac>   # n5p primary NIC MAC
```

Verify the NIC is armed (on n5p): `ethtool enp197s0 | grep Wake-on` should
show `Wake-on: g`.

## Post-outage diagnosis (guests did not start)

1. **What did startall do?** Task logs live on n5p under
   `/var/log/pve/tasks/` - look for the `startall` UPID of the boot:

   ```bash
   grep -rl startall /var/log/pve/tasks/index* | tail
   # then read the matching task log for per-VM errors, e.g.
   # "Starting VM 102 failed: ... got timeout"
   ```

2. **Is the autostart config still correct?**

   ```bash
   for id in 100 101 102 148; do echo "== $id"; qm config $id | grep -E 'onboot|startup|hookscript'; done
   for id in 200 201 202 203 204 205 207; do echo "== $id"; pct config $id | grep -E 'onboot|startup'; done
   ```

   Expected: everything `onboot: 1`; VM 100 `startup: order=1,up=120` plus
   `hookscript: local:snippets/truenas-nfs-gate.sh`; VMs 101/102 and all
   LXCs `order=2` (hermes 206: `order=3`); dev 148 `order=3`.

3. **Manual start** (after TrueNAS NFS is confirmed up:
   `showmount -e 192.168.1.150`):

   ```bash
   qm start <vmid>    # VMs
   pct start <vmid>   # LXCs
   ```

4. **Gate log**: the hookscript's poll output (`truenas-nfs-gate: ...`)
   appears in the startall task log; a `WARNING` line means the 600 s cap
   expired and later guests probably failed on storage - fix TrueNAS, then
   start guests manually.

## The NFS readiness gate and its invariant

`/var/lib/vz/snippets/truenas-nfs-gate.sh` (deployed by
`ansible/provision-truenas.yml` from `ansible/templates/truenas-nfs-gate.sh.j2`)
runs in VM 100's post-start phase and polls `showmount -e 192.168.1.150`
every 5 s for up to 600 s, then exits 0 regardless (PVE only warns on
post-start hook errors; the gate must never wedge `startall`). The fixed
`up=120` delay on VM 100 stays as a belt.

**Invariant: TrueNAS must remain ALONE in startup order=1.** The gate only
delays *later* order groups - startall's end-of-group barrier waits for the
`vm_start` worker, and the hook runs synchronously inside it (verified on
PVE 9.2.4). A guest sharing order=1 would start concurrently, ungated.

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
```

## True verification

The only end-to-end test of this chain is a deliberate reboot of n5p while
the operator is on the LAN: all guests must come up unattended and the new
startall task log must show the gate's poll lines.
