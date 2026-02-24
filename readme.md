# Home Network

Ansible-managed homelab running on Proxmox (Minisforum N5 Pro) with TrueNAS storage, Docker services, and LXC containers.

## Quick Start

```bash
cd ansible
ansible-playbook site.yml                    # Full convergence
ansible-playbook site.yml --tags traefik     # Single service
ansible-playbook site.yml --check --diff     # Dry run
```

## Repository Structure

- `ansible/` — All Ansible automation (roles, inventory, playbooks)
- `docs/` — Network architecture, VLANs, IP map, service documentation
- `esphome/` — ESPHome device configurations (compiled and flashed to microcontrollers)

## Documentation

- **[Architecture & Network Docs](docs/readme.md)** — Hardware, VLANs, IP assignments, implementation status
- **[CLAUDE.md](CLAUDE.md)** — AI agent instructions and project conventions
