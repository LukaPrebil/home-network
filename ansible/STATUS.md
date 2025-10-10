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

### Ansible Connectivity
- ✅ `ansible all -m ping` works
- ✅ `ansible-playbook site.yml` runs successfully
- ✅ Secrets encrypted with Ansible Vault

## What's Ready

### Proxmox Configuration
- VLAN-aware bridge on enp197s0
- Storage: local (ISOs/backups), local-lvm (VM disks)
- Users configured with SSH keys
- Ready to provision VMs

### What Proxmox Needs Before VM Creation
Before creating VMs, we should:

1. **Upload OS Images** (if not using cloud-init)
   - Ubuntu Server ISO
   - Debian ISO
   - Home Assistant OS image

2. **OR: Create Cloud-Init Templates** (recommended)
   - Download cloud image
   - Create VM template with cloud-init
   - Use Ansible to clone and customize

## Next Immediate Steps

Choose one path:

### Option A: Manual VM Creation (Quick Start)
1. Upload ISOs via Proxmox web UI
2. Create VMs manually through web UI
3. Use Ansible to configure them after creation

### Option B: Automated VM Provisioning (Better Long-Term)
1. Create Ansible playbook to:
   - Download cloud-init images
   - Create VM templates
   - Provision VMs from templates
2. Everything Infrastructure-as-Code

**Recommendation:** Option B - it takes a bit more setup now but pays off quickly.

## Ready to Start VMs?

Yes! Proxmox is ready. We can start provisioning VMs. The recommended first VM is:
- **Docker Host** (`containers` - 192.168.30.4 when VLANs are active)
  - Will host AdGuard, monitoring, and other containerized services
  - Good test case for the automation workflow

## Notes

- Currently on flat 192.168.1.0/24 network
- VLANs will be activated when Omada router is deployed
- Proxmox host runs as `ansible_user` (no sudo needed for most operations)
- For privileged operations on Proxmox, playbooks should target root via API or SSH
