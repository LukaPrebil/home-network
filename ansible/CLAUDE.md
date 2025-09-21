# AI Agent Instructions & Ansible Guidelines

This document provides guidelines for AI agents to generate Ansible playbooks for this homelab repository. The primary goal is to maintain a fully automated, idempotent, and version-controlled infrastructure based on the architectural decisions outlined in the docs - `docs/readme.md`.

## 1. Core Principles

All generated Ansible code must adhere to the following principles:

* **Roles are the Primary Unit of Logic:** All automation logic (installing software, configuring services, etc.) must be encapsulated within a role. The top-level `site.yml` playbook should only be used for mapping roles to hosts.
* **Separate Data from Logic:** Do not hardcode configuration values. All variables, such as user names, package lists, or port numbers, must be defined in `group_vars/` or `host_vars/` files.
* **Ensure Idempotency:** Every task and role must be idempotent. The playbooks should be safely runnable multiple times, only making changes when the actual state differs from the desired state.
* **Source of Truth:** The `README.md` file is the single source of truth for all hardware, VLANs, hostnames, and IP addresses. All configurations must align with this document.

## 2. Playbook Workflow for Provisioning

When a playbook needs to **create a new resource** (like a Proxmox VM) and then **configure it in the same run**, it **must** follow this specific multi-play pattern to handle dependencies correctly:

1.  **Play 1: Provision the Resource.**
    * Target the hypervisor or relevant host (e.g., `hosts: n5p`).
    * Use the appropriate module to create the resource (e.g., `community.general.proxmox_kvm`).
    * **Crucially, use the `register` keyword** to save the result of the creation task, which includes the new resource's IP address and hostname.

2.  **Play 2: Add the New Resource to Inventory.**
    * Use the `ansible.builtin.add_host` module to dynamically add the newly created resource to Ansible's in-memory inventory.
    * Assign it to a temporary group (e.g., `just_created_vms`).

3.  **Play 3: Wait for the Resource to be Ready.**
    * Target the temporary group (e.g., `hosts: just_created_vms`).
    * Use the `ansible.builtin.wait_for_connection` module to pause the playbook until the new machine has finished booting and its SSH service is available.

4.  **Play 4: Apply Configuration Roles.**
    * Target the temporary group again (e.g., `hosts: just_created_vms`).
    * Apply all necessary configuration roles (`common`, `docker`, etc.) to the now-available machine.

This ensures a "single-apply" workflow that can build and configure infrastructure from scratch in one command.

## 3. Secrets Management

**Under no circumstances should secrets (passwords, API keys, tokens) be written in plaintext.**

All secrets must be handled using **Ansible Vault**. When generating a task that requires a secret, reference it as a vaulted variable.

* **Correct:** `db_password: "{{ vault_database_password }}"`
* **Incorrect:** `db_password: "MySuperSecretPassword123"`

The AI should assume that a `secrets.yml` file, encrypted with Ansible Vault, contains these variables.

## 4. Best Practices

* **Use Fully Qualified Collection Names (FQCN):** Always use the full module name (e.g., `ansible.builtin.apt` instead of just `apt`).
* **Name All Tasks:** Every task should have a clear, descriptive `name`.
* **Use `become: true`:** Privilege escalation should be defined at the play level, not on individual tasks.