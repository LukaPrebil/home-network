# Storage readiness is an end-to-end write, not a liveness reply

Status: accepted (2026-08-08)

The NFS readiness gate added on 2026-07-22 holds Proxmox `startall` inside startup
order group 1 until the TrueNAS VM can serve guest disks, so that later order groups
do not race a storage server that is still coming up. It decided readiness by polling
`showmount -e 192.168.1.150`. On 2026-08-08 a power event rebooted n5p and HAOS
(VM 102) again failed to start, with the same `got timeout` error the gate was written
to prevent.

The gate ran, and reported success at 12:02:07. `nfs-server` on TrueNAS did not start
until 12:02:08. `showmount` talks to `rpc.mountd`, which had been up since 12:02:05,
so the probe went green one second before the thing it was gating on existed. Worse,
`nfsd` enters a 90 second NFSv4 grace period when it starts, during which it refuses
every non-reclaim `OPEN` with `NFS4ERR_GRACE` so that clients can reclaim prior state
first. Grace ran from 12:02:08 to 12:03:38. No guest disk could be opened in that
window. VM 102's start attempt began at 12:03:02 with a 35 second budget (PVE's
`config_aware_timeout`: 30 s base plus 5 s for one NIC) and expired at 12:03:37, one
second before grace lifted. VM 101 survived only by accident of accounting: its
cloudinit drive is regenerated before kvm is exec'd, so its blocked time fell outside
the timed window and its budget effectively started after grace ended.

The pool was healthy throughout. It imported in 13 seconds, ONLINE, no scrub, no
resilver, no errors. Storage was never slow. It was refusing opens by protocol, and
the gate had no way to see that, because it was asking a question whose answer goes
true long before guests can start.

Readiness is therefore redefined as **a completed create, write and remove on a real
NFS mount**. This is the same operation a guest performs when it opens its disk, so
it cannot go true early: it stays blocked for the entire grace period and clears the
moment guests can actually start. It also carries no tunable that has to track a value
living on the TrueNAS side. The probe additionally resolves the containing mount and
asserts it is NFS before trusting a successful write, because an absent mount leaves a
local stub directory under `/mnt/pve/` that accepts the write happily and would turn
the gate green instantly, which is the silent-stub failure mode the Ansible-side guard
in `roles/common/tasks/assert_nfs_mount.yml` already exists to prevent.

Measured against a real 90 second grace period on a throwaway export: the old
`showmount` probe went green after 1 second, the new write probe after 96 seconds.

The gate still exits 0 in every path, including at its cap. PVE only warns on
post-start hook failures, and a wedged gate must never block the rest of `startall`.
That is also why this decision is paired with a boot-time reconciler: a correct gate
narrows the window, but only a retry can recover from a guest that failed for a reason
the gate does not model.

## Considered options

- **Keep `showmount`, then sleep a fixed 90 seconds** - rejected: it would have
  prevented this specific incident and is a two line change. But it hardcodes a value
  that is owned by the NFS server, not by us. `nfsv4gracetime` is a TrueNAS-side
  setting that can change under a SCALE upgrade with no signal on the Proxmox side,
  and the failure mode when it grows is silent and identical to the one being fixed.
  It also spends 90 seconds on every boot regardless of whether the server needs it,
  where the write probe releases as soon as the server is genuinely ready.
- **Shorten `nfsv4gracetime` / `nfsv4leasetime` on TrueNAS** - rejected: both are 90 s,
  and cutting them would shrink the window rather than detect it. TrueNAS's
  `nfs.config` middleware API exposes neither field, so any change would be an
  out-of-band edit that survives no upgrade and is invisible to the Ansible tree.
  Shortening grace also weakens the guarantee it exists to provide, namely that
  clients get to reclaim locks and opens before new ones are handed out. Trading
  correctness of lock recovery for boot speed is the wrong trade on a host whose
  guests keep databases on that export.
- **Have the gate query TrueNAS for its grace state** - rejected: the most explicit
  possible signal, since the server logs `starting 90-second grace period` and
  `ending NFSv4 grace period` verbatim. It was rejected because it couples a
  boot-critical hookscript on the hypervisor to SSH credentials for the storage VM
  and to a kernel log format that is not an API. The gate would then fail whenever
  the coupling broke, in a phase of boot where debugging is most expensive.
- **Read-only open of an existing file instead of a write** - rejected: an NFSv4
  `OPEN` is grace-blocked whether or not it is for writing, so this would detect the
  grace period just as well and touches nothing on the dataset. It was rejected as
  strictly weaker for the same cost: guests need to write, and an export that has come
  back read-only, or a dataset whose quota is exhausted, would pass a read probe and
  still fail every guest.
- **Skip the gate entirely and rely on the reconciler** - rejected: the reconciler
  alone would recover the estate, since it retries until guests come up. But it
  recovers by letting guests fail first, which on a bad boot means every order group
  after TrueNAS burns its start budget against a server that is refusing opens, and
  the first sign of trouble is a unit in `systemctl --failed`. Holding `startall` for
  the seconds the server actually needs is cheaper than failing eight guests and
  restarting them.
