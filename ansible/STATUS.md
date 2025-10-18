# Ansible Automation Status

Last Updated: 2025-10-18

## Current State

### Proxmox Host (n5p)
- **IP:** 192.168.1.128 (temporary, will move to 192.168.30.2)
- **Status:** ✅ Fully configured and managed by Ansible
- **Access:**
  - `ssh n5p` (as ansible_user)
  - `ssh luka@n5p` (as admin)
  - Web UI: https://192.168.1.128:8006

### TrueNAS Storage (tn-storage)
- **IP:** 192.168.1.150 (DHCP, temporary, will move to 192.168.30.3)
- **Status:** ✅ Fully configured and operational
- **Access:**
  - `ssh tn-storage` (as truenas_admin)
  - Web UI: http://192.168.1.150 (login as truenas_admin)
- **Storage:**
  - ZFS Pool: `tank` (RAIDZ1, 3x 1TB NVMe, ~2TB usable)
  - Datasets:
    - `tank/proxmox-vms` (200GB quota) - VM disk images
    - `tank/proxmox-templates` (20GB quota) - Templates/ISOs
    - `tank/docker-volumes` (100GB quota) - Docker persistent data
    - `tank/media` (no quota) - Media files for Plex/Jellyfin
    - `tank/backups` (no quota) - System backups
  - All datasets exported via NFS to Proxmox

### Ansible Connectivity
- ✅ `ansible all -m ping` works for both n5p and tn-storage
- ✅ `ansible-playbook site.yml` runs successfully
- ✅ Secrets encrypted with Ansible Vault
- ✅ Privilege escalation working on all hosts (sudo configured)

## What's Ready

### Proxmox Configuration
- ✅ VLAN-aware bridge on enp197s0
- ✅ DNS resolution configured (public DNS servers)
- ✅ Storage backends:
  - `local` - ISOs/backups on boot drive
  - `local-lvm` - VM boot disks (56GB available)
  - `truenas-vms` - VM disks on TrueNAS (200GB NFS)
  - `truenas-templates` - Templates/ISOs on TrueNAS (20GB NFS)
- ✅ Users configured with SSH keys
- ✅ Sudo and privilege escalation configured
- ✅ Ready to provision VMs with full storage backend

### TrueNAS Configuration
- ✅ VM provisioned with PCIe NVMe passthrough
- ✅ ZFS pool created and healthy
- ✅ Datasets with appropriate quotas
- ✅ NFS shares configured and exported
- ✅ Integrated with Proxmox storage
- ✅ Network access from both current (192.168.1.0/24) and future (192.168.30.0/24) networks

## Completed Playbooks

### Infrastructure
- ✅ `site.yml` - Main playbook (configures Proxmox host)
- ✅ `provision-truenas.yml` - Provisions TrueNAS VM on Proxmox
- ✅ `configure-truenas.yml` - Configures TrueNAS storage (ZFS, NFS, Proxmox integration)

### VM Provisioning
- ✅ `create-cloudinit-template.yml` - Creates Ubuntu 25.04 cloud-init template
- ✅ `provision-vms.yml` - Provisions VMs from template (declarative, idempotent)
- ✅ `provision-lxc.yml` - Provisions LXC containers (declarative, idempotent)
- ✅ `provision-haos.yml` - Provisions Home Assistant OS VM with UEFI boot

### VM Configuration
- ✅ `configure-containers.yml` - Configures Docker Host with common + docker roles
- ✅ `configure-traefik.yml` - Deploys Traefik reverse proxy
- ✅ `configure-omada.yml` - Deploys Omada SDN Controller
- ✅ `migrate-containers.yml` - Migrates services from rpi4 to containers VM

All playbooks are fully automated and idempotent.

## What's Ready

### Cloud-Init Template
- ✅ Ubuntu 25.04 (Plucky Puffin) cloud-init template
- ✅ Template ID: 9000
- ✅ Pre-configured with SSH keys and DNS
- ✅ Stored on truenas-templates
- ✅ Ready for VM cloning with VLAN support

### VM Provisioning System
- ✅ Declarative VM definitions in `group_vars/vms.yml`
- ✅ Automated provisioning with `provision-vms.yml`
- ✅ VLAN enforcement during VM creation
- ✅ Idempotent (skips existing VMs)
- ✅ Cloud-init integration for automated configuration

### Docker Host (containers)
- **IP:** 192.168.1.140 (temporary, will move to 192.168.30.4)
- **Status:** ✅ Fully configured and operational
- **VMID:** 101
- **Resources:** 4 cores, 8GB RAM, 50GB disk
- **Access:** `ssh ubuntu@192.168.1.140` or `ssh ansible_user@192.168.1.140`
- **Docker:** v28.5.1 with Compose v2.40.0
- **Storage:** NFS mount to TrueNAS (100GB at /srv/docker)
- **Ready for:** Container deployments (AdGuard, monitoring, media services)

### Docker Role
- ✅ Role structure created (`roles/docker/`)
- ✅ Docker CE v28.5.1 + Compose v2.40.0 installed
- ✅ Configuration tasks (users, daemon config)
- ✅ NFS mount to TrueNAS docker-volumes (100GB)
- ✅ Modern GPG key handling (no deprecated apt-key)
- ✅ Successfully tested and deployed

### Traefik Role
- ✅ Role structure created (`roles/traefik/`)
- ✅ Docker Compose deployment configuration
- ✅ Static configuration (traefik.yml)
- ✅ Dynamic configuration with security middlewares
- ✅ Dashboard and API endpoints
- ✅ Docker provider for automatic service discovery
- ✅ File provider for static routes
- ✅ Let's Encrypt/ACME with DNS-01 challenge (Cloudflare)
- ✅ Wildcard certificate support (`*.lukapg.dev`)
- ✅ Deployment playbook: `configure-traefik.yml`
- ✅ **DEPLOYED TO PRODUCTION** (LXC on 192.168.1.142)

### Container Migration Roles
- ✅ `uptime-kuma` - Role for Uptime Kuma monitoring service
- ✅ `ddns-updater` - Role for dynamic DNS updates (Cloudflare)
- ✅ `octoeverywhere` - Role for 3D printer remote access (Elegoo Neptune)
- ✅ Migration playbook: `migrate-containers.yml`
- ✅ Validation playbooks: `validate-uptime-kuma.yml`, `validate-ddns-updater.yml`, `validate-octoeverywhere.yml`
- ✅ Two-stage migration: rpi4 → local backup → containers VM
- ✅ Local backups stored in `backups/` directory for disaster recovery
- ✅ **ALL SERVICES MIGRATED TO CONTAINERS VM**

## Next Steps

### Immediate: Deploy Containerized Services

1. **Deploy AdGuard Home** ⏳
   - DNS filtering and DHCP server
   - Will replace temporary public DNS servers
   - Configure as primary DNS for network

2. **Deploy Monitoring Stack** ⏳
   - Prometheus for metrics collection
   - Grafana for visualization
   - Node exporter for system metrics

3. **Create VLAN Migration Playbook** ⏳
   - Needed when Omada router is deployed
   - Will reconfigure all VMs from flat network to VLANs
   - Update IPs from 192.168.1.x to 192.168.30.x range

### ✅ Completed: Traefik Reverse Proxy (Production)

**Status:** 🎉 **LIVE IN PRODUCTION**

Traefik has been successfully deployed and is serving all external services:

**Deployment Details:**
- **Host:** Traefik LXC container (`192.168.1.142`)
- **Access:** https://traefik.lukapg.dev (Dashboard)
- **Certificate:** Wildcard Let's Encrypt cert for `*.lukapg.dev`
- **Challenge Type:** DNS-01 via Cloudflare API
- **Services Proxied:** 5 active routes

**Active Services:**
1. ✅ `ha.lukapg.dev` → Home Assistant (192.168.1.144:8123) **[HAOS VM]**
2. ✅ `kuma.lukapg.dev` → Uptime Kuma (192.168.1.140:3001) **[MIGRATED]**
3. ✅ `status.lukapg.dev` → Uptime Kuma alt (192.168.1.140:3001) **[MIGRATED]**
4. ✅ `glances.lukapg.dev` → Glances monitoring (rpi4 - decommissioned)
5. ✅ `photos.lukapg.dev` → Immich photo management (192.168.1.141:2283)
6. ✅ `traefik.lukapg.dev` → Traefik Dashboard (192.168.1.142:8080)

**Features Enabled:**
- ✅ Cloudflare proxy compatible (DNS-01 challenge)
- ✅ Automatic HTTP → HTTPS redirect
- ✅ HSTS with 1-year max-age
- ✅ HTTP/2 and modern cipher suites
- ✅ Security headers (XSS protection, content type sniffing, etc.)
- ✅ Automatic certificate renewal (60 days before expiry)
- ✅ Rate limiting middleware
- ✅ Proxy headers for backend services

**Migration Complete:**
- ✅ Replaced Nginx Proxy Manager (NPM) on rpi4
- ✅ All services migrated successfully
- ✅ NPM ready to be decommissioned

### ✅ Completed: Container Migration from rpi4 (Production)

**Status:** 🎉 **ALL SERVICES MIGRATED**

Three containerized services have been successfully migrated from rpi4 to containers VM:

**Migrated Services:**
1. ✅ **Uptime Kuma** (monitoring)
   - Source: rpi4 (192.168.1.110:3001)
   - Destination: containers VM (192.168.1.140:3001)
   - Data: 243MB database + configuration migrated
   - Traefik backend updated
   - Live: https://kuma.lukapg.dev, https://status.lukapg.dev

2. ✅ **ddns-updater** (DNS updates)
   - Source: rpi4 (192.168.1.110:8000)
   - Destination: containers VM (192.168.1.140:8000)
   - Data: Cloudflare configuration + DNS records
   - Running and updating DNS records

3. ✅ **OctoEverywhere** (3D printer access)
   - Source: rpi4 (octoeverywhere-elegoo-connect)
   - Destination: containers VM (192.168.1.140)
   - Data: Elegoo Neptune companion configuration
   - Connected to printer at 192.168.1.100

**Migration Architecture:**
- Two-stage migration pattern: rpi4 → local backup → containers VM
- Local backups in `backups/` directory for disaster recovery
- Idempotent roles: can redeploy from backups without touching rpi4
- Ansible roles: `uptime-kuma`, `ddns-updater`, `octoeverywhere`
- Playbooks: `migrate-containers.yml`, `validate-*.yml`

**rpi4 Cleanup:**
- ✅ Migrated containers stopped and removed from rpi4
- ✅ Original data preserved on rpi4 as additional backup
- Remaining on rpi4: Home Assistant, Mosquitto, Glances

### ✅ Completed: Omada Controller LXC (Production)

**Status:** 🎉 **RUNNING AND CONFIGURED**

TP-Link Omada SDN Controller successfully deployed on dedicated LXC:

**Infrastructure:**
- LXC Container: omada (VMID 202, IP 192.168.1.143)
- Resources: 2 cores, 4GB RAM, 24GB disk
- Unprivileged container on truenas-vms storage
- Auto-start enabled (onboot: true)

**Software Stack:**
- Omada Controller: v5.15.24.19 (native .deb installation)
- MongoDB: v7.0.25 (Jammy/22.04 packages for Ubuntu 25.04 compatibility)
- Java: OpenJDK 17
- Service: tpeap (active and running)

**Access:**
- Web UI (HTTPS): https://192.168.1.143:8043
- Web UI (HTTP): http://192.168.1.143:8088
- SSH: `ssh root@192.168.1.143` or `ssh omada`

**Configuration:**
- ✅ Backup restored successfully via UI
- ✅ All network devices reconnected
- ✅ Site configuration preserved
- ✅ User accounts and settings intact

**Ansible Automation:**
- Role: `roles/omada-controller/`
- Playbook: `configure-omada.yml`
- Features: Prerequisites, installation, backup/restore support
- MongoDB: Auto-installs from Jammy repository

**Next Steps:**
- Add to Traefik reverse proxy (optional)
- Configure SSL certificate (optional, already has self-signed)
- Document network integration

### ✅ Completed: Home Assistant OS VM (Production)

**Status:** 🎉 **RUNNING IN PRODUCTION**

Home Assistant has been successfully migrated from rpi4 to a dedicated HAOS VM:

**Infrastructure:**
- VM: haos (VMID 102, IP 192.168.1.144)
- Resources: 4 cores, 8GB RAM, 64GB disk on truenas-vms
- UEFI boot with EFI disk (required for HAOS)
- Auto-start enabled (onboot: true)

**Software:**
- Home Assistant OS: v16.2
- Core: Restored from backup with all integrations intact
- ZHA: USB Zigbee coordinator passed through from Proxmox host
- MQTT: Connected to broker at 192.168.1.110 (will migrate when rpi services move)

**Access:**
- Web UI: http://192.168.1.144:8123
- Public: https://ha.lukapg.dev (via Traefik)
- SSH: Via "SSH & Web Terminal" add-on (optional)

**Traefik Integration:**
- ✅ Backend updated to point to 192.168.1.144:8123
- ✅ Reverse proxy working with Let's Encrypt certificate
- ✅ Mobile apps updated to new URL

**Ansible Automation:**
- Playbook: `provision-haos.yml`
- Configuration: `group_vars/haos.yml`
- Features: Automated image download, UEFI boot setup, network configuration guide
- Documentation: `docs/homeassistant_migration.md`

**Migration Complete:**
- ✅ All ZHA Zigbee devices working (USB stick passed through)
- ✅ All automations and integrations restored
- ✅ Old container on rpi4 removed
- ✅ 24+ hours of stable operation

**rpi4 Status:**
- ✅ All Docker containers stopped and removed
- ✅ System decommissioned - no services running
- ✅ Available for repurposing or retirement

### Future Service VMs
- AdGuard Home (DNS/DHCP)
- Monitoring stack (Prometheus/Grafana)
- Media services (Plex/Jellyfin)

## Storage Architecture

```
Proxmox (n5p)
├── local (boot drive)
│   └── ISOs, backups, configs
├── local-lvm (boot drive)
│   └── VM boot disks only
└── TrueNAS NFS Mounts
    ├── truenas-vms → /mnt/tank/proxmox-vms
    │   └── VM disk images (200GB)
    ├── truenas-templates → /mnt/tank/proxmox-templates
    │   └── Cloud-init templates, ISOs (20GB)
    └── (Future: direct NFS mount to VMs)
        ├── /srv/docker → /mnt/tank/docker-volumes
        ├── /mnt/media → /mnt/tank/media
        └── /mnt/backups → /mnt/tank/backups
```

## Notes

- Currently on flat 192.168.1.0/24 network
- VLANs will be activated when Omada router is deployed
- All IPs are temporary and will migrate to VLAN 30 (192.168.30.0/24)
- TrueNAS datasets have conservative quotas that can be increased as needed
- All infrastructure is defined in code and fully reproducible
