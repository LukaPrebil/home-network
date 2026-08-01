# Dev VM (`dev`) - Setup, Operations, and Recovery

Headless Ubuntu 26.04 development VM on Proxmox `n5p`, mirroring the macOS
workstation environment. Remote access via LAN (allowlisted MacBook IP) and
Tailscale.

## Why this exists

A long-lived single-user box for VSCode Remote SSH + Claude Code targets.
The macOS workstation is the primary editor; the dev VM runs language
toolchains, build artifacts, Docker, and `claude` itself so the laptop stays
clean.

## Architecture

```
Proxmox n5p (192.168.1.128)
└── ubuntu-cloudinit-template (VMID 9000, 26.04, 10GB)
    └── dev (VMID 148, 6c / 16GB / 100GB on truenas-vms)
        ├── common role        (ansible_user, sudoers, sshd hardening)
        ├── docker role        (Docker engine + compose plugin)
        ├── tailscale role     (apt repo install, tag:dev)
        └── dev_vm role        (apt packages, AWS CLI, SSH-key + GitHub
                                auto-add, chezmoi, claude config tree,
                                nvm + Node LTS, Claude Code, starship,
                                rustup, tlrc, docker sudoers, UFW)
```

| Layer | Source | Source of truth |
|------|---|---|
| OS image | `cloud-init` template (`ubuntu-cloudinit-template`) | `ansible/group_vars/cloudinit_template.yml` |
| VM declaration | `ansible/group_vars/vms.yml` (entry `dev`) | this repo |
| Inventory | `ansible/inventory/hosts.yml` (`dev_hosts`) | this repo |
| User vars | `ansible/host_vars/dev.yml` | this repo |
| Dotfiles | `git@github.com:LukaPrebil/dotfiles.git` (chezmoi) | external |
| Claude config | `git@github.com:domengabrovsek/claude.git` + symlinks under `~/.claude/` | external |

## Software stack on the VM

- **Shell**: zsh + oh-my-zsh (via chezmoi-tracked `dot_oh-my-zsh/`) + starship.
- **Language toolchains**: nvm + Node LTS (chezmoi configures
  `dot_zshrc`), rustup + cargo, Python 3 with venv module, AWS CLI v2.
- **CLI productivity**: bat, eza, fd, fzf, ripgrep, jq, zoxide,
  zsh-syntax-highlighting, git-delta, git-lfs, ffmpeg, lolcat, tlrc,
  tmux, htop, tree.
- **Container runtime**: Docker engine + compose plugin. `luka` invokes via
  `sudo docker` (passwordless, see "Docker access" below).
- **Editor target**: Claude Code (official native installer, pinned via
  `dev_vm_claude_code_version`).
- **Session multiplexer**: herdr (manual install, see "Known gotchas");
  attach from the Mac with `herdr --remote dev`.
- **Remote access**: Tailscale (`tag:dev`).

## Access

| Path | Address | When |
|------|---------|------|
| LAN | `192.168.1.148` | At home (any device on the home /24) |
| MagicDNS | `dev.lan` (if AdGuard rewrite added) or `dev.<tailnet>.ts.net` | Always |
| Tailscale | `100.x.x.x` (visible in `tailscale status`) | Off-LAN |

UFW posture: default deny in / allow out, allowlist `192.168.1.0/24` on
22/tcp, allow all on `tailscale0`. Run `sudo ufw status verbose` on the VM
to confirm. Tighten the allowlist to a smaller CIDR or specific /32s by
editing `dev_vm_ssh_allow_cidrs` in `host_vars/dev.yml` and re-running
the role.

## How to re-run the role

The role is idempotent.

```bash
cd ansible
ansible-playbook site.yml --tags dev-vm --limit dev
```

`tailscale up` is gated on `BackendState != Running`, so the (revoked)
auth key is never referenced after the first successful enrolment.

If `vault_github_pat` is empty (the steady state), the GitHub preflight task
fails loudly. To re-run with auth: mint a fresh 7-day fine-grained PAT
(SSH keys: Read+Write only), update vault, run, revoke.

## First-run requirement (LAN, not Tailscale)

The first role run **must** be invoked from the LAN
(`192.168.1.139` -> `192.168.1.148`), not over Tailscale. The `firewall.yml`
task adds the `tailscale0` allow rule before flipping to default-deny, but
`tailscale0` only exists after the `tailscale` role has run AND `tailscaled`
is up, which in turn requires DNS and apt to have come up first. Until that
point a Tailscale-side connection has no exposed firewall rule. Subsequent
runs from any path are safe.

## Day-to-day operations

### Patching strategy

This box does **not** run `unattended-upgrades`. The threat model that
justifies daily auto-patching (high-availability, internet-exposed services)
doesn't apply: single-user, behind UFW (LAN allowlist + Tailscale only),
no public ingress, fully rebuildable from Ansible + git in ~20 minutes.

Patching is a manual ritual:

```bash
# When you feel like it, or every couple of weeks
ansible-playbook site.yml --tags dev-vm-upgrade --limit dev
```

The play runs `apt dist-upgrade` + `autoremove`, then prints whether a
reboot is required. The opt-in tag `dev-vm-upgrade` is double-tagged with
`never`, so it cannot run as part of a full `site.yml` convergence by
mistake.

### Pre-upgrade snapshots

`n5p` runs a weekly cron (Sundays 02:00) via `roles/proxmox/tasks/snapshot_cron.yml`
that snapshots every VM with `snapshot_weekly: true` in
`group_vars/vms.yml`. The dev VM is in scope. Rolling retention keeps the
last 4 `auto-YYYY-MM-DD` snapshots per VM.

### Rollback

```bash
# from n5p
sudo qm listsnapshot 148                    # see auto-YYYY-MM-DD snapshots
sudo qm rollback 148 auto-2026-04-26        # VM stops, restarts from snapshot
```

`qm rollback` is a hard reset of the VM disk. Anything not pushed to a git
remote at the time of the snapshot is gone. If you need to preserve
work-in-progress, `git stash` and push to a branch first.

### Backup posture

There is no separate backup. Recovery is "rebuild from Ansible + git":
re-clone the cloud-init template, re-run `provision-vms.yml`, then re-run
`site.yml --tags dev-vm`. The whole loop is ~20 minutes and produces a
byte-equivalent box (versions are pinned).

### Growing the VM later

```bash
# RAM (online)
sudo qm set 148 --memory 24576

# Disk (online + in-VM resize)
sudo qm resize 148 scsi0 +50G
# then in the VM:
sudo growpart /dev/sda 1
sudo resize2fs /dev/sda1
```

If `truenas-vms` quota is tight, bump `tank/proxmox-vms` quota on TrueNAS
first. 300 GB current; expect ~30-40 GB live + 5-15 GB across 4 weekly
snapshots.

### Revoking the per-host SSH key from GitHub

If the VM is ever destroyed or compromised: visit
<https://github.com/settings/keys>, find the key titled
`luka@dev (homelab)`, delete it. The VM identity is contained to that one
key - no impact on macOS workflows.

## Sudo and Docker access

`luka` has full `NOPASSWD: ALL` sudo via `/etc/sudoers.d/luka` (managed by
`roles/dev_vm/tasks/sudoers.yml`). The user is intentionally **not** in
the `docker` group: group membership lets any process running as `luka`
silently use the docker socket, while `sudo docker` at least leaves an
audit trail in the system log. The passwordless choice is honest about
the threat model - `sudo docker run -v /:/host` is itself a root escape,
so any sudo carve-out that includes docker effectively grants full root.
With SSH restricted to keys + LAN/Tailscale, the password gate would only
add per-command friction without changing what an attacker who reaches
`luka`'s shell can do.

## Optional hardening

If a per-host key with a passphrase is preferred over a passphraseless one,
set a passphrase manually after the role runs:

```bash
ssh-keygen -p -f ~/.ssh/id_ed25519
```

Then start an `ssh-agent` with a timeout in your zsh profile:

```bash
eval "$(ssh-agent -t 28800 -s)"  # 8h auto-expiry
```

This narrows the window in which a compromised npm dep could exfil a
usable key. The role does not enforce this; it's a manual opt-in for the
user.

## Known gotchas

- **`bat` and `fd` apt-shim renames**: Ubuntu's `bat` package installs
  `/usr/bin/batcat`, and `fd-find` installs `/usr/bin/fdfind` (to avoid
  clashing with existing binaries elsewhere). The role symlinks both to
  `/usr/local/bin/bat` and `/usr/local/bin/fd` so chezmoi-applied aliases
  and muscle memory work.
- **chezmoi laying down macOS-only files**: `dot_Brewfile` and
  `dot_wezterm.lua` are tracked in the dotfiles repo for the macOS box.
  On Linux they're inert files; nothing reads them. A `.chezmoiignore`
  with OS guards in the dotfiles repo would clean this up - tracked as a
  follow-up.
- **Brewfile -> apt drift**: as new tools are added to the macOS Brewfile,
  the dev VM apt list in `host_vars/dev.yml` does not auto-track. Manual
  sync until a drift detector script lands.
- **GitHub PAT lifecycle**: the PAT is one-shot. Mint, run, revoke, clear
  `vault_github_pat` to `""` in `secrets.yml`. Re-runs without re-minting
  fail loudly at the preflight task.
- **Tailscale auth key lifecycle**: same shape. After first enrolment the
  `tailscale up` task is skipped on every subsequent run; revoke the key
  in the admin console immediately.
- **`tailscale0` race on first run**: the firewall task waits for the
  interface up to 60 s. If `tailscaled` hasn't enrolled yet (e.g. invalid
  auth key), the wait times out. Fix the auth key in vault and re-run.
- **Pinned GitHub host key drift**: GitHub has rotated this key once
  (March 2023). When they rotate again, the `git clone` and SSH-T tasks
  fail closed. Update `dev_vm_github_host_key` in `host_vars/dev.yml`
  from <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints>.
- **No IPv6 work on the VM by design**: the LAN itself does carry
  unmanaged ISP IPv6 (Telekom GUA + ULA via Innbox RA, with the Innbox
  advertising itself as the v6 nameserver - v6 DNS therefore bypasses
  AdGuard, which binds IPv4-only), but none of it is IaC-managed and the
  dev VM does no ULA / IPv6 configuration; Tailscale handles
  cross-network reachability, so v6 dual-stack adds surface without
  payoff.
- **`docker_hosts` vs `dev_hosts`**: the dev VM runs Docker but isn't in
  `docker_hosts`. `docker_hosts` is the deployment-target group for
  monitoring stack / reverse proxy / etc.; the dev VM is a workstation,
  not a service host. Keep them separate.
- **herdr is not Ansible-managed**: installed 2026-07-23 via the official
  install script (`curl -fsSL https://herdr.dev/install.sh | sh`) as `luka`,
  binary at `~/.local/bin/herdr` plus a manual `sudo ln -sf` shim into
  `/usr/local/bin` (same pattern as bat/fd, since `~/.local/bin` is not on
  the VM's PATH). Deliberately not added to the `dev_vm` role: the local
  client's `herdr --remote dev` auto-installs/updates the server binary on
  attach and keeps client/server versions in sync, so an Ansible pin would
  fight the self-updater. After a VM rebuild the first `herdr --remote dev`
  restores the binary; only the `/usr/local/bin` symlink needs re-creating
  by hand. The VM's `~/.config/herdr/config.toml` (also manual, not
  chezmoi-tracked) sets `shell_mode = "login"`: herdr's `auto` mode only
  uses login shells on macOS, and on Linux non-login panes skip
  `~/.zprofile`, losing `~/.local/bin` from PATH - claude and cargo appear
  missing inside herdr panes without it.
