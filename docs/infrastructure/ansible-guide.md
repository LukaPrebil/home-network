# Ansible Reference Guide

Detailed reference for role creation, deployment patterns, and infrastructure operations. For core conventions and quick-start commands, see [CLAUDE.md](../../CLAUDE.md).

## Prerequisites

```bash
brew install ansible
ansible-galaxy collection install community.general community.docker ansible.posix
```

SSH access to all managed hosts must be configured with key-based auth. The shared key is `~/.ssh/homelab_ansible` (except rpi4, which uses `~/.ssh/id_ed25519`).

## Project Structure

```
ansible/
├── site.yml                  # Main entrypoint — maps roles to hosts with tags
├── ansible.cfg               # Config: inventory path, vault_password_file, SSH settings
├── secrets.yml               # Ansible Vault encrypted secrets (vault_* variables)
├── .vault_pass               # Vault password file (git-ignored, referenced in ansible.cfg)
├── inventory/hosts.yml       # Static inventory — all hosts and group hierarchy
├── group_vars/               # Variables scoped to host groups
│   ├── all.yml               # Global: DNS servers, NFS paths, timezone, common packages
│   ├── proxmox_hosts.yml
│   ├── lxc.yml
│   ├── vms.yml
│   ├── haos.yml
│   └── cloudinit_template.yml
├── host_vars/                # Variables scoped to individual hosts
│   ├── n5p.yml               # Proxmox hypervisor
│   ├── tn-storage.yml        # TrueNAS
│   └── traefik.yml           # Traefik reverse proxy
├── roles/                    # All automation logic lives here
│   ├── common/               # Base config: packages, users, DNS, timezone, security
│   ├── docker/               # Docker + Docker Compose install, NFS mounts
│   ├── proxmox/              # Proxmox host tuning (network, storage, system)
│   ├── traefik/              # Traefik reverse proxy (Jinja2 Docker Compose)
│   ├── immich/               # Immich photo manager (GPU accel, NFS, Compose)
│   ├── monitoring-stack/     # Prometheus + Grafana + Loki (Compose)
│   ├── node-exporter/        # Native binary install (no Docker)
│   ├── alloy/                # Grafana Alloy agent (native binary)
│   ├── adguard/              # AdGuard Home DNS (native binary on LXC, Docker on rpi4)
│   ├── plex/                 # Plex Media Server (Compose)
│   ├── jellyfin/             # Jellyfin (Compose, same host as Plex)
│   ├── arr-stack/            # Sonarr, Radarr, Prowlarr (Compose)
│   ├── omada-controller/     # TP-Link Omada SDN (native .deb install)
│   ├── autoheal/             # Auto-restart unhealthy containers (Compose)
│   ├── otbr/                 # OpenThread Border Router (Compose)
│   ├── matter-server/        # Python Matter Server (Compose)
│   ├── uptime-kuma/          # Uptime monitoring (Compose)
│   ├── ddns-updater/         # Dynamic DNS (Compose)
│   ├── pds/                  # ATProto PDS (Compose, iSCSI storage from TrueNAS)
│   ├── ha-mcp/               # Home Assistant MCP server (Compose)
│   ├── paperless-ngx/        # Document management (Compose)
│   └── octoeverywhere/       # 3D printer remote access (Compose)
└── provision-*.yml / setup-*.yml  # One-time provisioning playbooks (kept separate)
```

## Inventory & Host Groups

Defined in `inventory/hosts.yml`. Group hierarchy:

```
all
├── proxmox_hosts        → n5p
├── truenas_hosts        → tn-storage
├── docker_hosts         → containers, rpi4
├── lxc_containers       → immich, traefik, omada, adguard, monitoring, plex
├── haos_hosts           → haos (not SSH-managed)
├── plex_hosts           → plex
├── arr_stack_hosts      → containers
├── monitoring_hosts     → monitoring
├── adguard_hosts        → adguard, rpi4
├── linux_servers        → proxmox_hosts + truenas_hosts + docker_hosts + lxc_containers + adguard_hosts
└── monitoring_agents    → proxmox_hosts + docker_hosts + lxc_containers
```

Key: `linux_servers` is the common role target. `monitoring_agents` gets node-exporter + alloy.

**HAOS**: runs as a Proxmox VM (192.168.1.144), not SSH-managed. Managed via ha-mcp MCP tools, not Ansible.

## Running Playbooks

Vault password is read from `.vault_pass` via `ansible.cfg`. Never use `--ask-vault-pass`.

```bash
# Full convergence (all hosts, all roles)
ansible-playbook site.yml

# Single service by tag
ansible-playbook site.yml --tags traefik

# Multiple related services
ansible-playbook site.yml --tags media              # Plex + Jellyfin + Arr
ansible-playbook site.yml --tags pds                # ATProto PDS

# Scope to one host
ansible-playbook site.yml --limit immich

# Skip TrueNAS (no apt — common role fails)
ansible-playbook site.yml --limit 'all:!tn-storage'

# Dry run
ansible-playbook site.yml --tags traefik --check --diff
```

## Deployment Patterns

**Most services**: Jinja2 template → `docker-compose.yml` → `docker_compose_v2` module.
Role structure: `tasks/main.yml` includes subtasks (`directories.yml`, `deploy.yml`), `defaults/main.yml` for version pins, `handlers/main.yml` for restarts, `templates/` for Compose and config files.

**Native binary installs** (no Docker): AdGuard Home on LXC, node-exporter, Alloy, Omada Controller (.deb).

**iSCSI storage** (instead of NFS): For services that use SQLite or require POSIX file locking, use iSCSI zvols from TrueNAS instead of NFS. The PDS role demonstrates this pattern — zvol defined in `host_vars/tn-storage.yml`, iSCSI target created via `configure-truenas.yml`, client setup in `roles/pds/tasks/iscsi.yml`, data mounted at `/mnt/<service>`.

## Secrets

All secrets in `secrets.yml`, encrypted with Ansible Vault. Variable naming: `vault_` prefix.

```yaml
# In secrets.yml (encrypted)
vault_database_password: "actual-secret"

# In role defaults or group_vars (plaintext reference)
db_password: "{{ vault_database_password }}"
```

**Initial setup** (one-time):
```bash
echo "your-vault-password" > .vault_pass && chmod 600 .vault_pass
ansible-vault encrypt secrets.yml
```

**Managing secrets**:
```bash
ansible-vault edit secrets.yml    # Edit encrypted file
ansible-vault view secrets.yml    # View without editing
```

**Dollar sign escaping**: Docker Compose env vars containing `$` must be escaped for Docker's interpolation:
```yaml
password: "{{ vault_some_password | replace('$', '$$') }}"
```

## Version Management

- Pin exact versions in role `defaults/main.yml` — never use `latest`
- **cAdvisor**: image is `ghcr.io/google/cadvisor`, tags have **no `v` prefix** (e.g., `v0.51.0` is wrong, `0.51.0` is correct)
- **AdGuard Home**: schema auto-migrates on binary upgrade — just update the version variable
- When bumping versions, update the variable in `defaults/main.yml` and re-run with the appropriate tag

## Provisioning Pattern (Multi-Play)

Provisioning playbooks (`provision-*.yml`) follow a strict multi-play pattern:

1. **Play 1 — Create resource**: target hypervisor (`hosts: n5p`), use `community.general.proxmox_kvm` or `proxmox`, `register` the result
2. **Play 2 — Add to inventory**: `ansible.builtin.add_host` into a temporary group
3. **Play 3 — Wait for ready**: `ansible.builtin.wait_for_connection`
4. **Play 4 — Configure**: apply roles (`common`, `docker`, service roles)

These stay as separate playbooks — they are one-time operations, not part of `site.yml`.
