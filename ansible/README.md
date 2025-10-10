# Homelab Ansible Configuration

This directory contains Ansible playbooks and roles to automate the configuration of the homelab infrastructure.

## Quick Start

### 1. Prerequisites

Install Ansible on your MacBook:
```bash
brew install ansible
```

Install required Ansible collections:
```bash
ansible-galaxy collection install community.general
```

### 2. Set Up Secrets

Create and encrypt your secrets file:
```bash
# Copy the example file
cp secrets.example.yml secrets.yml

# Edit with your actual SSH keys and passwords
vim secrets.yml

# Create a vault password file (do not commit this!)
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass

# Encrypt the secrets file
ansible-vault encrypt secrets.yml
```

### 3. Configure SSH Access

Make sure you can SSH into your Proxmox host as root:
```bash
ssh root@192.168.1.128
```

If you need to set up SSH key authentication first:
```bash
ssh-copy-id root@192.168.1.128
```

### 4. Test Connectivity

```bash
ansible all -m ping
```

### 5. Run the Playbook

Apply the complete configuration:
```bash
ansible-playbook site.yml
```

Or run specific roles with tags:
```bash
# Only run common role
ansible-playbook site.yml --tags common

# Only configure network
ansible-playbook site.yml --tags network

# Run everything except security hardening
ansible-playbook site.yml --skip-tags security
```

## Directory Structure

```
ansible/
├── ansible.cfg              # Ansible configuration
├── site.yml                 # Main playbook
├── inventory/
│   └── hosts.yml           # Host inventory
├── group_vars/
│   ├── all.yml             # Variables for all hosts
│   └── proxmox_hosts.yml   # Variables for Proxmox hosts
├── host_vars/
│   └── n5p.yml             # Host-specific variables
├── roles/
│   ├── common/             # Common configuration for all hosts
│   │   ├── tasks/
│   │   └── handlers/
│   └── proxmox/            # Proxmox-specific configuration
│       ├── tasks/
│       └── handlers/
└── secrets.yml             # Encrypted secrets (Ansible Vault)
```

## Roles

### Common Role
- Creates the `ansible_user` for automation
- Sets up admin users with zsh and oh-my-zsh
- Installs common packages
- Configures SSH security
- Sets up firewall (UFW) and fail2ban
- Configures timezone

### Proxmox Role
- Configures VLAN-aware network bridges
- Sets up storage
- Installs required Proxmox packages
- Removes subscription nag (for community edition)

## Next Steps

After running the initial configuration:

1. **Verify Network Configuration**: Check that the bridge is configured correctly
   ```bash
   ssh ansible_user@192.168.1.128
   ip addr show vmbr0
   ```

2. **Create VM Templates**: Build templates for your VMs (TrueNAS, Home Assistant, etc.)

3. **Add VM Provisioning**: Extend the playbooks to create and configure VMs using the multi-play pattern described in CLAUDE.md

4. **Configure Services**: Add roles for Docker, Home Assistant, AdGuard, etc.

## Useful Commands

```bash
# Edit encrypted secrets
ansible-vault edit secrets.yml

# View encrypted secrets
ansible-vault view secrets.yml

# Run playbook in check mode (dry run)
ansible-playbook site.yml --check

# Run with extra verbosity
ansible-playbook site.yml -v
```

## Important Notes

- Always test changes in a safe environment first
- Network changes may temporarily interrupt connectivity
- The Proxmox role configures VLAN-aware bridges but doesn't restart networking automatically
- Review `/etc/network/interfaces` on the Proxmox host after running the playbook
