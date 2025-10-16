# Container Migration Plan: rpi4 → containers VM + LXC

## Overview

Migrate Docker containers from Raspberry Pi 4 to the more powerful containers VM and dedicated LXCs on Minisforum N5 Pro. This migration improves performance, resource allocation, and maintainability.

## Service Migration Matrix

| Service | Source | Destination | Method | Status |
|---------|--------|-------------|--------|--------|
| **Uptime Kuma** | rpi4 (Docker) | containers VM (Docker) | Ansible + rsync data | Pending |
| **ddns-updater** | rpi4 (Docker) | containers VM (Docker) | Ansible + rsync data | Pending |
| **OctoEverywhere** | rpi4 (Docker) | containers VM (Docker) | Ansible + rsync data | Pending |
| **Omada Controller** | rpi4 (Docker) | Dedicated LXC (Native) | LXC provisioning + backup restore | Pending |
| **NPM** | rpi4 (Docker) | ❌ Retire | Replaced by Traefik | Pending |
| **Home Assistant** | rpi4 (Docker) | Dedicated HAOS VM | Separate project | Future |
| **Mosquitto** | rpi4 (Docker) | rpi2 | Separate project | Future |
| **Glances** | rpi4 (Docker) | Stay on rpi4 | Monitor rpi4 hardware | No action |

## Architecture

### Current State (rpi4)
```
rpi4 (192.168.1.110)
├── homeassistant (port 8123) - network_mode: host
├── glances (port 61208)
├── uptime-kuma (port 3001)
├── ddns-updater (port 8000)
├── octoeverywhere (bridge mode)
├── mosquitto (ports 1883, 9001)
├── omada-controller (network_mode: host)
└── nginx-proxy-manager (RETIRED)
```

### Target State

```
containers VM (192.168.1.140)
├── /srv/docker/uptime-kuma/
│   ├── docker-compose.yml
│   └── data/ (synced from rpi4)
├── /srv/docker/ddns-updater/
│   ├── docker-compose.yml
│   └── data/ (synced from rpi4)
└── /srv/docker/octoeverywhere/
    ├── docker-compose.yml
    └── data/ (synced from rpi4)

omada-controller LXC (192.168.1.XXX - TBD)
├── Native Omada Controller installation
├── MongoDB (required dependency)
└── Data restored from backup

rpi4 (192.168.1.110) - KEPT
├── homeassistant (temporary - will move to HAOS VM)
├── glances (permanent - monitors rpi4)
├── mosquitto (temporary - will move to rpi2)
└── zigbee2mqtt (permanent - needs USB dongle)
```

## Implementation Plan

### Phase 1: Preparation

#### 1.1 Research Omada Controller
- ✅ Decision: Use dedicated LXC with native .deb installation
- 🔲 Find official TP-Link .deb package or installation script
- 🔲 Determine resource requirements (CPU, RAM, Disk)
- 🔲 Plan VMID assignment (suggest 202)
- 🔲 Document backup/restore process

#### 1.2 Create Ansible Infrastructure
- 🔲 Create role: `ansible/roles/uptime-kuma/`
- 🔲 Create role: `ansible/roles/ddns-updater/`
- 🔲 Create role: `ansible/roles/octoeverywhere/`
- 🔲 Create role: `ansible/roles/omada-controller/` (for LXC)
- 🔲 Add Omada LXC to `group_vars/lxc.yml`
- 🔲 Create `host_vars/omada-controller.yml` (Avahi/mDNS config)

#### 1.3 Backup Current State
- 🔲 Create Omada Controller backup via web UI
- 🔲 Document current ddns-updater configuration
- 🔲 Verify Uptime Kuma monitors are accessible
- 🔲 Document OctoEverywhere printer connection

### Phase 2: Deploy Services (Stopped State)

#### 2.1 Deploy Containerized Services on containers VM
Run: `ansible-playbook ansible/deploy-migrated-services.yml`

This playbook will:
- Create directory structure in `/srv/docker/`
- Deploy docker-compose files
- Create traefik network connection
- **NOT start containers yet**

#### 2.2 Provision Omada Controller LXC
Run: `ansible-playbook ansible/provision-lxc.yml --tags omada`

This will:
- Create LXC container (VMID 202)
- Install Ubuntu
- Configure networking
- **NOT install Omada yet**

#### 2.3 Install Omada Controller
Run: `ansible-playbook ansible/configure-omada.yml`

This will:
- Install MongoDB
- Install Omada Controller .deb
- Configure systemd service
- Configure Avahi/mDNS for `.local` hostname
- **NOT start service yet**

### Phase 3: Migrate Data

#### 3.1 Sync Service Data
Run: `ansible-playbook ansible/sync-service-data.yml`

For each service:
- Stop source container on rpi4
- Use `rsync` to sync data to containers VM
- Restart source container on rpi4 (keep running)

#### 3.2 Restore Omada Backup
Manual process:
1. Start Omada Controller on LXC
2. Access web UI: `http://omada-controller.local:8088`
3. Complete initial setup wizard
4. Restore from backup file
5. Verify APs are discovered and connected

### Phase 4: Validation (One Service at a Time)

#### 4.1 Validate Uptime Kuma
Run: `ansible-playbook ansible/validate-uptime-kuma.yml`

Process:
1. Start container on containers VM
2. Wait for service ready (port 3001)
3. Test local access: `http://192.168.1.140:3001`
4. Verify monitors are present
5. ✅ Keep running if successful
6. ❌ Stop and debug if failed

#### 4.2 Validate ddns-updater
Run: `ansible-playbook ansible/validate-ddns-updater.yml`

Process:
1. Start container on containers VM
2. Wait for service ready (port 8000)
3. Test health endpoint: `http://192.168.1.140:8000/health`
4. Verify DNS records are updating
5. ✅ Keep running if successful

#### 4.3 Validate OctoEverywhere
Run: `ansible-playbook ansible/validate-octoeverywhere.yml`

Process:
1. Start container on containers VM
2. Test printer connectivity to 192.168.1.100
3. Verify OctoEverywhere cloud connection
4. ✅ Keep running if successful

#### 4.4 Validate Omada Controller
Run: `ansible-playbook ansible/validate-omada.yml`

Process:
1. Service should already be running (from Phase 3.2)
2. Test web UI access: `http://omada-controller.local:8088`
3. Verify all APs are connected and managed
4. Test AP management functions (reboot, config changes)
5. ✅ Keep running if successful

### Phase 5: Switch Traffic (Traefik Update)

Run: `ansible-playbook ansible/update-traefik-backends.yml`

This will:
- Update `dynamic.yml.j2` with new backend IPs:
  - `uptimekuma` service: 192.168.1.110:3001 → 192.168.1.140:3001
  - `ddns-updater` (if exposed): Add new route to 192.168.1.140:8000
- Reload Traefik configuration
- Test all public endpoints:
  - https://kuma.lukapg.dev
  - https://status.lukapg.dev

### Phase 6: Cleanup rpi4

Run: `ansible-playbook ansible/cleanup-rpi4.yml`

This will:
1. Stop migrated containers:
   - uptime-kuma
   - ddns-updater
   - octoeverywhere
   - omada-controller
2. Remove nginx-proxy-manager container (retired)
3. Update docker-compose.yml on rpi4 to remove stopped services
4. Keep running services:
   - homeassistant (until HAOS migration)
   - glances (permanent)
   - mosquitto (until rpi2 migration)

### Phase 7: Documentation

- Update `docs/readme.md` with new service locations
- Update `ansible/STATUS.md` with migration completion
- Document Omada Controller `.local` access
- Update network diagram if needed

## Rollback Strategy

### If a service fails validation:
1. **DO NOT PROCEED** to next service
2. Keep old service running on rpi4
3. Stop failed service on containers VM
4. Debug and fix issues
5. Re-run validation playbook
6. Only proceed when ALL services pass validation

### If Traefik switch causes issues:
1. Revert `dynamic.yml.j2` to old IPs
2. Run `ansible-playbook ansible/configure-traefik.yml --tags traefik`
3. Debug new services
4. Re-attempt switch

### If Omada Controller fails:
1. Original container still running on rpi4
2. Access old instance at 192.168.1.110
3. Delete Omada LXC if needed
4. Re-provision from scratch

## Resource Allocation

### Omada Controller LXC (Suggested)
- **VMID**: 202
- **Hostname**: `omada-controller`
- **IP**: 192.168.1.143 (temporary) → 192.168.1.XXX (final)
- **Cores**: 2
- **RAM**: 2GB (Omada + MongoDB)
- **Disk**: 20GB (MongoDB data + logs)
- **Network**: `network_mode` equivalent (bridge with host ports)
- **Storage**: truenas-vms

### containers VM (Already Provisioned)
- **Current**: Docker already installed
- **Additional disk usage**: ~5-10GB for new services
- **Network**: Already has traefik network capability

## Timeline Estimate

- **Phase 1 (Preparation)**: 2-3 hours
  - Omada research: 30 mins
  - Role creation: 1-2 hours
  - Backups: 30 mins

- **Phase 2 (Deploy)**: 30 mins
  - Automated playbook execution

- **Phase 3 (Data Migration)**: 30-60 mins
  - Automated rsync + manual Omada restore

- **Phase 4 (Validation)**: 1-2 hours
  - Per-service testing and verification

- **Phase 5 (Traffic Switch)**: 15 mins
  - Traefik config update

- **Phase 6 (Cleanup)**: 15 mins
  - Automated cleanup

**Total**: 4-6 hours (including debugging time)

## Success Criteria

- ✅ All services running on new infrastructure
- ✅ Traefik routes working (kuma.lukapg.dev, status.lukapg.dev)
- ✅ Omada Controller accessible via `.local` hostname
- ✅ All APs managed by new Omada instance
- ✅ DNS updates working (ddns-updater)
- ✅ OctoEverywhere connected to printer
- ✅ rpi4 cleaned up with only essential services
- ✅ Documentation updated
- ✅ No service downtime for critical services

## Next Steps

1. **Review this plan** - confirm approach
2. **Research Omada** - find best installation method
3. **Begin Phase 1** - create Ansible roles
4. **Execute migration** - one phase at a time

---

**Note**: This is a living document. Update status as you progress through each phase.
