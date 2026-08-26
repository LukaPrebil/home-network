# Homelab Ansible - AI Agent Guide

## Git

- Do NOT add `Co-Authored-By` trailers to commit messages
- Use conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, etc.)
- **Direct pushes to `main` are allowed for this repo** (overrides the global "always use a feature branch + PR" rule). This is a single-operator homelab repo with no CI gating merges - feature branches add ceremony without protection. Still fine to use a branch + PR when changes warrant review or staging, but do not block on it.

## Core Conventions

- **FQCN always**: `ansible.builtin.apt`, not `apt`
- **Name every task**: clear, descriptive `name:` on all tasks
- **`become: true` at play level**: not on individual tasks
- **Roles are the unit of logic**: `site.yml` only maps roles to hosts
- **Data separate from logic**: variables in `group_vars/` and `host_vars/`, never hardcoded
- **Idempotency**: every task safe to re-run; only change when state drifts
- **Document learnings immediately**: when you discover a gotcha, quirk, or non-obvious behavior during implementation, write it to the relevant doc file right away - if it's cross-cutting, add it to Known Issues below. Future sessions won't have this context
- **Compose/env changes apply via the deploy task, not handlers**: the `docker_compose_v2` task with `state: present` IS the apply mechanism - compose detects compose-file and env_file drift and recreates exactly the changed containers. Compose/env template tasks must NOT notify a restart handler (`docker compose restart` does not re-read those files; it only double-bounces the service)
- **Handlers exist only for mounted-config files**: configs bind-mounted INTO a container are invisible to compose, so those template tasks notify the role's restart handler (`docker_compose_v2` with `state: restarted` for Docker, `ansible.builtin.systemd` for native binaries). A role with no mounted configs has no handlers. Exception: traefik's dynamic config is hot-reloaded by its file provider and needs no notify at all. OTBR must NEVER be restarted in place (D-Bus EMERG crash loop) - recreate-on-drift via `state: present` is its only apply path
- **Health check after deploy, never in handlers**: every Docker service deployment verifies readiness UNCONDITIONALLY after the deploy task with `ansible.builtin.uri` (30 retries x 5s delay) against a real application endpoint - port-open `wait_for` passes while an app crash-loops behind docker-proxy. Services without an HTTP endpoint use a null-safe `docker_container_info` running-state probe. Use `meta: flush_handlers` before the check when a mounted-config notify must take effect first
- **Tags on every `include_tasks`**: always apply the role's primary tag to each `include_tasks` call - without it, subtasks are unreachable when running with `--tags`
- **NFS mount opts come from `nfs_common_opts`** in `group_vars/all/main.yml`. Each role that mounts NFS exposes `<role>_nfs_opts` defaulting to that shared baseline so changes to the baseline (timeouts, automount behavior) propagate everywhere; override per-role only for genuine exceptions.
- **Guard deploys that depend on NFS**: any deploy task that writes to an NFS-backed path must include the `common.assert_nfs_mount` guard before its first write. Usage: `include_role: name=common tasks_from=assert_nfs_mount` with `common_nfs_mount_path: "{{ target_path }}"`. The guard resolves the containing mount (via `stat -c %m`) and fails fast if it isn't NFS - prevents silently deploying against a local stub directory when the mount is missing.

## Bootstrap (once per control node)

```bash
cd ansible && ansible-galaxy collection install -r requirements.yml
```

Installs `community.docker`, `community.proxmox`, `ansible.posix`, `community.general`, `community.crypto` into `~/.ansible/collections/`. Without this step `ansible-lint` emits `syntax-check[unknown-module]` for most Docker/Proxmox tasks.

## Lint

`ansible-lint` is green on `main` (production profile). Run from the `ansible/` directory:

```bash
cd ansible && ansible-lint
```

If you add new roles or tasks, keep the conventions already in the tree so lint stays clean:

- **Role directory names** use underscores (`ha_mcp`, not `ha-mcp`). Tag names in `site.yml` stay hyphenated for CLI UX (`--tags ha-mcp`).
- **Variables inside a role** must be prefixed with the role's underscore name (`otbr_thread_channel`, not `thread_channel`).
- **`shell:` only for actual shell features** (pipes, redirects, env substitution). Everything else uses `command:`.
- **Shell pipelines** get `set -o pipefail` + `executable: /bin/bash`.
- **`register:` on `shell`/`command`** requires an explicit `changed_when` - `false` for read-only probes, `true` (or rc-based) for state-changing tasks.
- **Yaml truthy values** are `true`/`false`, not `yes`/`no`.
- `ansible/.yamllint` raises `line-length` to 300 so long Jinja expressions / apt sources lines don't trigger the default limit.

## Running Playbooks

Secrets are SOPS-encrypted (ADR 0006) and decrypted automatically by the
`community.sops` vars plugin configured in `ansible.cfg`. The age key lives at
`~/.config/sops/age/keys.txt`. There is no Ansible Vault and no `--ask-vault-pass`.

```bash
ansible-playbook site.yml                                          # Full convergence
ansible-playbook site.yml --tags traefik                           # Single service
ansible-playbook site.yml --limit 'all:!tn-storage'                # Skip TrueNAS (no apt)
ansible-playbook site.yml --tags traefik --check --diff            # Dry run
ansible-playbook site.yml --tags dev-vm --limit dev                # Dev VM convergence
ansible-playbook site.yml --tags tailscale --limit '<host>'        # Tailscale role only
ansible-playbook site.yml --tags apt-upgrade --limit '<host>'      # Opt-in OS package upgrade
ansible-playbook site.yml --tags dev-vm-upgrade --limit dev        # Opt-in dev-VM apt upgrade
```

For full reference (all tags, host groups, patterns): see `docs/infrastructure/ansible-guide.md`.

## Known Issues

Host-specific operational gotchas (TrueNAS, HAOS, NFS mounts, Thread/Matter, WiFi) live in the untracked `.claude/state/known-issues.md`. Read it before debugging an infrastructure failure, and append to it when a new gotcha is discovered.

## Home Assistant

Use `ha-mcp` MCP tools for all HA automation/script/helper management - never edit HA YAML files directly.

- Notification `tag` values must be unique per notification type - they control live updates and clearing
- Android notification `sticky` must be the **string `"true"`**, not boolean `true`
- The `<` character in notification messages gets parsed as HTML - use words like "pod" (Slovenian for "under") instead
- All push notification automations should have area `house` and label `push_notification`
- Use `script.notify_home_users_dynamic` for all user-facing notifications - it handles home/away filtering and `clear_notification`
- When creating/modifying automations: verify entity area assignments, hide helper entities from dashboards where appropriate
- Follow existing notification patterns for channels, importance levels, and icons - read a similar existing automation first before creating a new one

## Documentation

Read these files **only when working on the relevant topic** - do not load them all into context.

| When working on... | Read |
|---|---|
| New Ansible roles, deployment patterns, secrets, provisioning | `docs/infrastructure/ansible-guide.md` |
| Dev VM (provisioning, dotfiles, Claude config tree, patching) | `docs/infrastructure/dev-vm-setup.md` |
| Traefik reverse proxy (routing, certs, integration) | `docs/infrastructure/traefik-integration.md` |
| Monitoring stack (Prometheus, Grafana, Loki, Alloy) | `docs/infrastructure/monitoring-stack.md` |
| TrueNAS VM virtio-net tuning (kick-race mitigations) | `docs/infrastructure/truenas-virtio-tuning.md` |
| n5p power-loss recovery (BIOS, WoL, autostart, NFS gate) | `docs/infrastructure/n5p-power-recovery.md` |
| OTBR Thread dataset capture / restore / migration | `docs/infrastructure/otbr-thread-recovery.md` |
| ATProto PDS (accounts, migration, goat CLI) | `docs/services/atproto-pds-migration.md` |
| HA automations (humidity/air quality ventilation) | `docs/home-assistant/automations/ventilation-humidity.md`, `ventilation-air-quality.md` |
| HA automations (utility room climate, cooling path, window) | `docs/home-assistant/automations/utility-climate.md` |
| HA automations (motion lights, pantry, office) | `docs/home-assistant/automations/motion-lights.md` |
| HA automations (blinds, window ventilation) | `docs/home-assistant/automations/blinds.md` |
| HA automations (laundry state machine, WLED) | `docs/home-assistant/automations/laundry.md` |
| HA automations (air conditioner, away mode, filter) | `docs/home-assistant/automations/air-conditioner.md` |
| HA automations (battery, 3D printer, Proxmox, mold risk) | `docs/home-assistant/automations/monitoring-alerts.md` |
| HA automations (presence simulation) | `docs/home-assistant/automations/presence-simulation.md` |
| HA automations (Mammotion Luba mower notifications) | `docs/home-assistant/automations/mower-luba.md` |
| HA notification script / live update pattern | `docs/home-assistant/automations/notification-script.md` |
| HA dashboards (air quality) | `docs/home-assistant/dashboards/air-quality.md` |
| HA dashboards (Luba mower) | `docs/home-assistant/dashboards/mower.md` |
| Heat pump Modbus integration | `docs/hardware/orca-heatpump-modbus.md`, `docs/hardware/orca-modbus-findings.md` |
| Heat pump HACS integration plan | `docs/hardware/orca-hacs-integration-plan.md` |
| PV and battery plant (as-built, array, enclosure, constraints) | `docs/hardware/pv-battery-plant.md` |
| Sofar inverter HA integration | `docs/hardware/sofar-inverter-ha-integration.md`, `docs/hardware/sofar-modbus-findings.md` |
| Eufy L60 vacuum local (Tuya) control | `docs/hardware/eufy-l60-local-control.md` |
| Network architecture, VLANs, hardware, IP map | `docs/network-architecture.md` |
