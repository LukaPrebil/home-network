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
- **Status:** ✅ Provisioned and running
- **VMID:** 101
- **Resources:** 4 cores, 8GB RAM, 50GB disk
- **Access:** `ssh ubuntu@192.168.1.140` or `ssh ansible_user@192.168.1.140`
- **Role:** Docker role created and ready (`roles/docker/`)
- **Note:** Docker installation pending due to intermittent DNS resolution issue

### Docker Role
- ✅ Role structure created (`roles/docker/`)
- ✅ Installation tasks (Docker CE, Compose, prerequisites)
- ✅ Configuration tasks (users, daemon config)
- ✅ NFS mount tasks for TrueNAS volumes
- ✅ Modern GPG key handling (no deprecated apt-key)
- ⚠️  Known issue: Intermittent DNS resolution during GPG key download

## Next Steps

### Immediate: Complete Docker Host Setup

1. **Resolve DNS Issue** ⏳
   - Investigate systemd-resolved vs Python urllib DNS resolution
   - Current workaround: Docker repository already configured
   - Can install manually: `sudo apt install docker-ce docker-ce-cli containerd.io`

2. **Deploy Services on Docker Host** ⏳
   - AdGuard Home (DNS/DHCP)
   - Monitoring stack (Prometheus/Grafana)
   - *Arr suite for media management

3. **Create VLAN Migration Playbook** ⏳
   - Needed when Omada router is deployed
   - Will reconfigure all VMs from flat network to VLANs
   - Update IPs from 192.168.1.x to 192.168.30.x range

### Future Service VMs
After Docker Host is ready:
- AdGuard Home (DNS/DHCP)
- Nginx Proxy Manager (reverse proxy)
- Monitoring stack (Prometheus/Grafana)
- Home Assistant OS
- Media services (Plex/Jellyfin)
- Immich (photo management)

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
