# Ansible Automation Status

Last Updated: 2025-10-10

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

### VM Configuration
- ✅ `configure-containers.yml` - Configures Docker Host with common + docker roles

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
1. ✅ `ha.lukapg.dev` → Home Assistant (192.168.1.110:8123)
2. ✅ `kuma.lukapg.dev` → Uptime Kuma (192.168.1.110:3001)
3. ✅ `status.lukapg.dev` → Uptime Kuma alt (192.168.1.110:3001)
4. ✅ `glances.lukapg.dev` → Glances monitoring (192.168.1.110:61208)
5. ✅ `traefik.lukapg.dev` → Traefik Dashboard (192.168.1.142:8080)

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

### Future Service VMs
After Docker Host is ready:
- AdGuard Home (DNS/DHCP)
- Monitoring stack (Prometheus/Grafana)
- Home Assistant OS
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
