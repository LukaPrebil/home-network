# Dev VM Setup Plan — Proxmox / Ansible

## Overview

Headless SSH-only development VM running on existing Proxmox host (Minisforum N5 Pro, Ryzen AI 9 HX 370). Remote access via Tailscale. Intended as a VSCode Remote / Claude Code target — no desktop environment.

---

## Proxmox VM Spec

| Parameter | Value |
|-----------|-------|
| CPU | 4 vCores, type `host` |
| RAM | 8192 MB, ballooning enabled |
| Disk | 50GB, VirtIO SCSI |
| Network | VirtIO, bridged |
| OS | Ubuntu 24.04 LTS (minimal server install) |

---

## Packages

### Via apt

```yaml
packages:
  - git
  - curl
  - wget
  - unzip
  - build-essential
  - zsh
  - tmux
  - htop
  - ufw
  - fail2ban
  - ca-certificates
  - gnupg
  - unattended-upgrades
```

### Via official install methods (not apt)

| Tool | Method |
|------|--------|
| Node.js | `nvm` — allows per-project version switching |
| Docker | Official Docker apt repo |
| Tailscale | Official Tailscale install script |
| Claude Code | `npm install -g @anthropic-ai/claude-code` (after nvm/Node) |

---

## SSH Hardening

Edit `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers {{ dev_vm_user }}
```

- Generate a dedicated SSH key pair for this VM — do not reuse existing keys
- Deploy the public key via Ansible `authorized_key` module

---

## Firewall (ufw)

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0
ufw enable
```

Port 22 is intentionally not opened to the public internet. All SSH traffic arrives exclusively via the Tailscale interface (`tailscale0`).

---

## Tailscale

- Install via official script on the Proxmox host or directly inside the VM
- Enable subnet routing if full LAN access from outside is needed
- Verify direct (non-relay) connection with `tailscale status` after setup
- VM will receive a stable `100.x.x.x` IP used as the SSH target

---

## Unattended Upgrades

```bash
dpkg-reconfigure --priority=low unattended-upgrades
```

Enables automatic security patch application. No manual maintenance required for routine CVEs.

---

## Client SSH Config

Add to `~/.ssh/config` on each client machine:

```
Host devvm
  HostName 100.x.x.x
  User {{ dev_vm_user }}
  IdentityFile ~/.ssh/devvm_key
  ServerAliveInterval 60
```

VSCode Remote and Claude Code both resolve this host alias without additional configuration.

---

## Proxmox Operational Notes

- Take a snapshot before major changes (new toolchain, config edits)
- Disk can be expanded live with `qm resize <vmid> scsi0 +20G` followed by `growpart` + `resize2fs` inside the VM if 50GB proves insufficient
- RAM ballooning allows Proxmox to reclaim unused guest memory when VM is idle

---

## Ansible Variables (suggested)

```yaml
dev_vm_user: "luka"
dev_vm_tailscale_ip: "100.x.x.x"      # fill after first Tailscale auth
dev_vm_ssh_pubkey: ""                   # fill with generated public key
dev_vm_disk_size: "50G"
dev_vm_ram_mb: 8192
dev_vm_vcpus: 4
```

---

## Ansible Role Structure (suggested)

```
roles/
  dev-vm/
    tasks/
      main.yml        # include all task files
      packages.yml    # apt packages + unattended-upgrades
      ssh.yml         # sshd_config hardening + authorized_key
      firewall.yml    # ufw rules
      tailscale.yml   # tailscale install + auth
      docker.yml      # docker engine via official repo
      node.yml        # nvm + node install
      claude.yml      # claude code npm install
    vars/
      main.yml
    handlers/
      main.yml        # restart sshd, reload ufw
```