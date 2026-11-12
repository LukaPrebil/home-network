# Object storage (RustFS)

S3-compatible object storage inside the estate: one RustFS container on the
`containers` VM, its data on an iSCSI zvol from TrueNAS, and the buckets that
hold Terraform state for the IaC roots in `iac/`.

This doc owns the operator runbook: what is running, how to check it, how to
recover it, and the behaviours that surprised us. The automation is split
between `ansible/roles/rustfs` (service, keys, mount), `ansible/host_vars/tn-storage.yml`
plus `ansible/configure-truenas.yml` (zvol, iSCSI target, snapshot task), and
`iac/object-store` (the bucket itself).

## As built

| Piece | Value |
| --- | --- |
| S3 endpoint | `http://192.168.30.140:9000` (VLAN 30 bind only, never the WAN) |
| Console (port 9001) | disabled - `RUSTFS_CONSOLE_ENABLE=false` |
| Container | `rustfs`, image `rustfs/rustfs:1.0.4`, `restart: unless-stopped` |
| Runtime user | uid/gid `10001:10001` (the image's own `rustfs` user, no root) |
| Compose / env / rc config | `/opt/rustfs/` (`docker-compose.yml`, `rustfs.env` 0600, `rc/config.toml` 0600) |
| Data path (host) | `/mnt/rustfs`, XFS label `rustfs-data` |
| Data path (container) | `/data` (`RUSTFS_VOLUMES=/data`) |
| Backing storage | TrueNAS zvol `tank/rustfs`, 10 GiB, lz4 |
| iSCSI target | `iqn.2005-10.org.freenas.ctl:rustfs`, CHAP, allowlisted to the containers VM IQN |
| Buckets | `terraform-state` (versioned, `prevent_destroy`) |
| Snapshots | daily 00:00, 1 week retained, `auto-%Y-%m-%d_%H-%M` |

## Why a zvol and not an NFS share

RustFS prohibits NFS as a storage medium outright and wants a local
filesystem; XFS is its preferred one. That is the same reasoning that put the
PDS and Uptime Kuma data on iSCSI zvols, so the estate now has three of them
and the same client-side pattern (`tasks/iscsi.yml`) in three roles.

Two consequences worth remembering:

- **A node drain of TrueNAS is not a thing here, but a TrueNAS outage is.** The
  zvol is the only copy of the buckets, snapshots live on the same pool, and the
  containers VM's own disk is on `truenas-vms` NFS. TrueNAS is a single point of
  failure for this service, exactly as it already is for everything else in the
  estate.
- **Snapshots of a mounted zvol are crash-consistent**, not quiesced. A restore
  may need `xfs_repair` before the filesystem mounts. Bucket versioning is the
  cleaner rollback for a bad *object*; snapshots are for losing the zvol.

## The rc client

All administration and every verification below runs the pinned CLI in a
throwaway container. It needs no install, and the config is a 0600 file owned by
the container's uid so no secret is ever in a command line:

```bash
# on the containers VM (192.168.30.140)
R() { docker run --rm -i --env XDG_CONFIG_HOME=/cfg \
  --volume /opt/rustfs/rc:/cfg/rc:ro rustfs/rc:v0.1.37 "$@"; }
```

Aliases in `/opt/rustfs/rc/config.toml`: `local` (root credential), plus one per
consumer key. `R ls local/` lists buckets, `R alias list` shows aliases without
secrets.

## Keys

RustFS mints an access-key/secret-key pair per consumer, and each pair carries
its own policy. Every key below reaches one bucket, except `tf-bootstrap`, which
keeps an all-bucket policy because it exists to create the bucket it later
stores state in. That exception is why the claim here is not "one leaked key
reaches one bucket".

| Alias / key | Policy | Used by |
| --- | --- | --- |
| `local` (root) | admin, full IAM rights | Ansible only - the readiness check and key management |
| `tf-bootstrap` | all buckets | the object-store root that creates `terraform-state` |
| `tf-control` | `terraform-state` only | operator Terraform runs |
| `tf-ci` | `terraform-state` only | CI Terraform jobs |

The secrets live in `ansible/group_vars/all/secrets.sops.yml`
(`vault_rustfs_*`). The object store is created by the role, not by hand:

```bash
cd ansible && ansible-playbook site.yml --tags rustfs --limit containers
```

The role creates a user only when it is absent and never rewrites an existing
secret. To rotate a consumer key: `R admin user rm tf-control` (repeat for
`tf-ci`), update the SOPS value, converge. `local` is the root credential from
`rustfs.env`, not an IAM user, so it is not in that list. The bootstrap key
rotation additionally requires updating `AWS_SECRET_ACCESS_KEY` in
`iac/secrets.sops.yaml`.

## Verifying the service

```bash
# on the containers VM
findmnt -no FSTYPE,SOURCE /mnt/rustfs        # xfs /dev/sdX
systemctl cat mnt-rustfs.mount               # Requires=/After=iscsid.service
R ls local/                                  # bucket list - the authenticated check
R bucket version info local/terraform-state   # Versioning: Enabled

# from the operator machine
cd ansible && ansible-playbook site.yml --tags rustfs --limit containers
```

The converge is idempotent: a second run reports `changed=0`. Its readiness step
is an authenticated S3 bucket listing that also asserts `terraform-state` is in
it, not a port or `/health` probe - `curl :9000/health` answers `200` with a
wrong credential too, and `R ls local/` alone succeeds against a blank or
unmounted zvol, which is the failure it exists to catch.

## Terraform state

`iac/object-store` declares `terraform-state` and keeps its own state inside it
(key `object-store.tfstate`). Credentials reach OpenTofu only through the
environment:

```bash
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store plan'
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store apply'
```

### State encryption

The state object is encrypted at rest by OpenTofu itself, independent of the bucket:
`pbkdf2` derives a key from a passphrase, `aes_gcm` encrypts with it, and `enforced = true`
refuses a plaintext state outright instead of reading it as if nothing were wrong. The object
in the bucket is `{"serial":N,...,"encrypted_data":...}`, so a snapshot of the zvol or a read
of the bucket yields no account identifiers.

The passphrase is `TF_VAR_state_passphrase` in `iac/secrets.sops.yaml`, which is why every
command goes through `sops exec-env`. Without it OpenTofu cannot read the state and says so:
that failure is intended, because a silent fallback to "no state" would let a plan propose
creating buckets that already exist.

Rotating the passphrase is a state migration, not a value swap: add the new provider and keep
the old one as a `fallback` method, apply, then remove the old one. Never delete the old
passphrase before the state has been rewritten with the new one.

CI needs the same variable as a secret. The Cloudflare root inherits this block unchanged, and
its state holds an Access allow-list, so encryption is not optional there either.

### The root credential is not in state

The assertion reads the Ansible secret directly, so no canary copy of the root credential has to
sit in the environment OpenTofu runs in:

```bash
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store plan -json' \
  | jq -r '..|strings' | grep -c "$(sops -d --extract '["vault_rustfs_root_secret_key"]' ansible/group_vars/all/secrets.sops.yml)"   # 0
```

### Bootstrapping a new root (chicken and egg)

The bucket must exist before a backend can point at it. Every command carries
the `sops exec-env` wrapper, including the first `init` against the local
backend: the plan and apply need the S3 credentials, and every command needs the
state passphrase. `-input=false` keeps each wrapped run non-interactive, which
matters in CI: a prompted `tofu init` under `sops exec-env` waits on stdin and
hangs with no output.

```bash
# 1. with no backend.tf in the root
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store init -input=false'
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store plan -input=false'
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store apply -input=false'
# 2. add backend.tf, then migrate the state into the bucket it just created
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store init -input=false -migrate-state -force-copy'
# 3. delete the leftover terraform.tfstate and terraform.tfstate.backup, then
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store plan -input=false'
```

The root carries `import` blocks for `terraform-state` and its versioning, so
the apply in step 1 adopts the existing bucket instead of creating an empty one.
That is also the recovery path when the state object goes missing - see
"The state object is missing or corrupt" below.

There is no `terraform.tfstate` on disk in steady state. One appearing means the
backend failed to load - investigate, do not commit it (it is gitignored).

### Locking

`use_lockfile = true` gives optimistic locking through S3 conditional writes;
the estate has no DynamoDB and the endpoint has no table service. A held lock
fails the run with `Error acquiring the state lock` and names the ID; after
confirming no apply is actually running:

```bash
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store force-unlock <LOCK_ID>'
```

### Rolling back a bad state write

Versioning makes the previous state object recoverable. Stop CI and any running
apply first - restoring state under a live plan corrupts both. There is no
lockfile to disable CI: turn the workflows off, restore, turn them back on.

```bash
gh workflow disable iac-apply.yml
gh workflow disable iac-drift.yml
```

```bash
R bucket version list --json local/terraform-state/object-store.tfstate \
  | jq -r '[..|objects|select(.version_id? // empty)] | .[] | "\(.version_id) \(.last_modified)"'
R undo --version-id <full-version-id> local/terraform-state/object-store.tfstate
```

**Use the full ID from `--json`.** The human-readable `bucket version list`
truncates version IDs to 8 characters, and those truncated IDs are rejected with
`InvalidArgument`.

When the state reads back the way you expect, turn CI on again:

```bash
gh workflow enable iac-apply.yml
gh workflow enable iac-drift.yml
```

### The state object is missing or corrupt

The bucket is healthy but `object-store.tfstate` is gone, truncated, or fails to
decrypt. Nothing needs restoring by hand: the root's `import` blocks adopt the
bucket and its versioning by name, and `prevent_destroy` cannot help here because
an empty state is not a destroy.

```bash
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store init -input=false'
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store plan -input=false'   # 2 to import, 0 to add
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store apply -input=false'
```

Read the plan before applying it. `2 to import` is the recovery; `2 to add` means
the import block is missing or its id is wrong, and applying it would create a
second, empty bucket. If a readable older version exists, the versioning rollback
above restores the state with the outputs and nothing to import.

## Growing the zvol

Grow in place; do not rebuild. The filesystem is XFS, so it grows online:

```bash
# 1. raise volsize in ansible/host_vars/tn-storage.yml, then
cd ansible && ansible-playbook configure-truenas.yml    # zfs grows the block device
# 2. on the containers VM
sudo xfs_growfs /mnt/rustfs
findmnt -no SIZE /mnt/rustfs
```

The zvol is exposed over iSCSI, so step 1 needs the guest to re-read the size;
`rescan-scsi-sg3.sh` (or a re-login of the target) is the fallback if the device
still reports the old size before `xfs_growfs`.

## Recovering the data

### From a snapshot (zvol lost or corrupted)

1. On the containers VM, take the service down and release the device:
   ```bash
   sudo docker stop rustfs
   sudo systemctl stop mnt-rustfs.mount
   sudo iscsiadm -m node --targetname iqn.2005-10.org.freenas.ctl:rustfs --logout
   ```
2. On `tn-storage`, pick and roll back a snapshot (never from a live session):
   ```bash
   sudo zfs list -t snapshot -o name,used tank/rustfs
   sudo zfs rollback tank/rustfs@auto-YYYY-MM-DD_HH-MM
   ```
3. Back on the containers VM, log in and remount:
   ```bash
   sudo iscsiadm -m node --targetname iqn.2005-10.org.freenas.ctl:rustfs --login
   sudo systemctl start mnt-rustfs.mount
   findmnt -no FSTYPE,SOURCE /mnt/rustfs        # xfs /dev/sdX
   ```
4. Bring the store and its data back, then prove both:
   ```bash
   sudo systemctl start docker                  # the mount stop took it down too
   sudo docker start rustfs                     # `docker stop` left it explicitly stopped
   R ls local/                                  # terraform-state is in the list
   sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/object-store plan -input=false'   # no changes
   ```
   `restart: unless-stopped` does not revive the container, because
   `docker stop` records an explicit stop. The daemon is down as well: the
   service's `RequiresMountsFor=/mnt/rustfs` drop-in pulls `docker.service`
   down with the mount, so starting the container before the daemon fails.
   `findmnt` alone is not the end of the procedure - it proves the filesystem,
   not the data.

If `findmnt` reports the device without a filesystem, or the mount fails with a
corrupt-structure error, `xfs_repair -n /dev/sdX` first (read-only), then
`xfs_repair` - crash-consistent snapshots can need it.

To keep the current data and inspect the old snapshot instead, `zfs clone` the
snapshot to a new zvol and attach a throwaway iSCSI extent to it rather than
rolling back.

**This path is untested on this dataset.** It follows ZFS and the role's own
mount/unit layout, but the first snapshot lands at the first 00:00 after the
zvol was created, and no restore has been rehearsed. Rehearse it once before
trusting it with anything that is not reproducible.

A rollback moves the IAM database back with the bucket, so a consumer key
rotated after the snapshot no longer matches
`ansible/group_vars/all/secrets.sops.yml` and every `tofu` run answers `403`. The
role never rewrites an existing secret. Fix it the way rotation does: remove the
user (`R admin user rm tf-control`, repeat for `tf-ci`), converge on containers,
then re-run `R ls local/`.

### From bucket versioning (bad object, zvol healthy)

Already covered under "Rolling back a bad state write" - the same
`version list` / `undo` pair restores any versioned object.

### The passphrase or the age key is lost

Unrecoverable by construction: `encryption.tf` enforces `aes_gcm`, so the state
object is ciphertext without `TF_VAR_state_passphrase`, and
`iac/secrets.sops.yaml` is ciphertext without `~/.config/sops/age/keys.txt`.
There is no escrow copy of either in this repository.

What remains is a rebuild. It loses no user data, because the bucket holds
state, not content. Delete the `object-store.tfstate` object from the bucket,
keep the bucket, and follow "The state object is missing or corrupt" - the
import blocks re-adopt it. Every other root needs the same treatment, because
its state is encrypted with the same lost passphrase. The Ansible secrets under
`ansible/group_vars/all/*.sops.yml` are encrypted to the same age key and are
lost with it, so the converge that recreates `tf-ci` and the `rc` aliases needs a
fresh key first.

### The bootstrap credential was rotated

`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `iac/secrets.sops.yaml` are
the pair every `tofu` run uses. After a rotation on the store, update both values
there and converge on containers so the `rc` aliases follow. CI reads the same
pair from repository secrets, so update those in the same pass, or the plan job
fails with `403` while local runs succeed.

## Behaviours worth knowing

- **The container runs as uid 10001.** Anything bind-mounted in has to be
  writable by that id; `/mnt/rustfs` is chowned by the role, and the chown is on
  the filesystem root inode so it survives the remount.
- **The image logs to `/logs` inside the container** (`RUSTFS_OBS_LOG_DIRECTORY`
  is set in the image), so container logs are the only log surface and they do
  not touch the host filesystem. `docker logs rustfs` it is.
- **`region = "us-east-1"` is a signing label, not a location.** SigV4 needs a region string.
  The role sets `RUSTFS_REGION` (`rustfs_region`) to `us-east-1` explicitly rather than
  leaving it to the image default, because the provider, the backend and every `rc` alias
  sign with the same value and a silent disagreement breaks every credential path at once.
  Nothing is sent to AWS and the bytes
  stay on the zvol. Setting the server to `eu-central-1` works only if the provider, the backend
  and every alias change with it; it buys clarity and nothing else.
- **`/health` needs no credential.** It is a liveness endpoint; the deploy's
  readiness check is the authenticated bucket listing precisely because of that.
- **`rc admin policy` needs a recent `rustfs/rc`.** Pinned at v0.1.37, which is verified; very early CLI builds return
  `HTTP 501 NotImplemented` against a server that does implement the call.
- **Deleting a versioned bucket is not `rc rb`.** `R object remove
  <bucket>/ --recursive --versions --force` clears data versions but leaves
  delete markers, and `rb` then fails with "not empty after verification". Remove
  each delete marker by full version ID (`object remove --version-id <id>
  <bucket>/<key>`) before `rb`. This matters when retiring a bucket, not for
  day-to-day operation.
- **Every apply leaves two lock-object versions** behind in
  `<bucket>/<key>.tflock` (versioning is on for the whole bucket). Harmless, and
  unbounded in principle; a lifecycle rule on the `.tflock` prefix is the fix if
  it ever matters.
- **The console is disabled on purpose.** Nothing uses it, `rc` covers
  administration, and an unused web login is another thing to patch. Turn it on
  for one debugging session by setting `RUSTFS_CONSOLE_ENABLE=true` in
  `roles/rustfs/templates/rustfs.env.j2` and converging.
- **`/mnt/rustfs` must be mounted before the container starts.** A missing mount
  means RustFS writes into a stub directory on the VM's rootfs. Three things
  enforce the order: the fstab entry carries `x-systemd.requires=iscsid.service`,
  the deployment verifies with a real S3 call, and the role installs
  `/etc/systemd/system/docker.service.d/wait-for-rustfs-mount.conf` with
  `RequiresMountsFor=/mnt/rustfs`, so a failed mount at boot stops Docker instead
  of starting the container against a stub. That drop-in is a systemd dependency
  rather than a retry loop, so it fails fast.
- **The guard covers boot, not a mount that disappears later.** If the iSCSI
  session drops while Docker runs, the container keeps its namespace and writes
  into whatever sits at that path. The tell is an empty bucket list: check
  `findmnt -no FSTYPE,SOURCE /mnt/rustfs`, restore the mount, restart the
  container. A Prometheus rule on the mountpoint is the planned detection and is
  not installed yet.
- **PDS and Uptime Kuma have no such guard.** The PDS zvol was found unmounted on
  2026-11-03, three and a half days after a reboot, with the container writing to
  `/mnt/pds` on the rootfs. See `.claude/state/known-issues.md`; the same fix is
  owed to both.

## Not done

- Boot guards for the `pds` and `uptime-kuma` zvols: rustfs has one, they do not,
  and PDS has already failed this way once.
- No alert yet on a missing `/mnt/rustfs` mountpoint.
- No replication off the host, and no restic-style consumer yet - both were out
  of scope for the first cut.
- One bucket only: `iac/object-store` adds the next one when something needs it.
- No TLS on the endpoint. It is VLAN 30 and tailnet only; TLS plus a hostname
  would drag in AdGuard for the CI path, which is the reason the endpoint is a
  literal address.
