# Homelab Observability Stack Implementation Plan

## 1. Overview

**Goal:** Deploy a comprehensive, automated monitoring and logging stack for the entire homelab using Grafana, Prometheus, and Loki.

**Host Machine:** The core stack will run on the `containers` VM (`192.168.30.4`).
**Deployment Method:** All components of the stack (Grafana, Prometheus, Loki, etc.) will be deployed via Docker Compose.
**Automation:** The entire setup, including component deployment and target configuration, must be managed by Ansible roles.
**Access:** The Grafana web UI will be exposed via Traefik.

---
## 2. Core Stack Deployment

An Ansible role named `monitoring-stack` should be created to deploy the following services on the `containers` VM.

* **Services:**
    * **Grafana:** The main visualization dashboard.
    * **Prometheus:** The metrics database.
    * **Loki:** The log aggregation database.
    * **cAdvisor:** For Docker container metrics.
    * **Proxmox Exporter:** To pull metrics from the Proxmox API.
    * **Omada Exporter:** To pull metrics from the Omada Controller API.
* **Volumes:** All services must use persistent volumes mapped to `/srv/docker/` (e.g., `/srv/docker/grafana`, `/srv/docker/prometheus`).
* **Networking:** Grafana should be exposed via Traefik. The Docker Compose file must include the necessary labels to route `grafana.yourdomain.com`.

---
## 3. Prometheus Configuration

Prometheus must be configured to scrape the following targets. This should be managed via an Ansible template (`prometheus.yml.j2`). All API keys and passwords must be sourced from the Ansible Vault (`secrets.yml`).

| Target System | Exporter Required | Deployed On | Scrape Target (Endpoint) |
| :--- | :--- | :--- | :--- |
| **Proxmox Host** (`n5p`) | `prometheus-pve-exporter` | `containers` VM (Docker) | `http://<exporter_ip>:9221/pve` |
| **TrueNAS VM** (`tn-storage`)| Built-in | TrueNAS (Enabled in UI) | `http://192.168.30.3:9100/metrics` (TBC) |
| **All Linux Hosts** (VMs, LXCs, RPi's) | `node_exporter` | All target hosts | `http://<host_ip>:9100/metrics` |
| **Docker Containers** | `cAdvisor` | `containers` VM (Docker) | `http://cadvisor:8080/metrics` |
| **Omada Controller** (`omada-lxc`) | `omada_exporter` | `containers` VM (Docker) | `http://<exporter_ip>:9202/metrics` |
| **Traefik Proxy** | Built-in | `containers` VM (Docker) | `http://traefik:8080/metrics` (Enabled in config) |

---
## 4. Log Aggregation (Loki) Configuration

Log collection will be handled by `promtail`.

* **Ansible Role:** A new role, `promtail`, should be created to deploy and configure `promtail` on all relevant hosts (Proxmox host, all VMs, and all LXCs).
* **Target Logs to Collect:**
    * **Proxmox Host (`n5p`):**
        * `/var/log/syslog`
        * `/var/log/auth.log`
        * `/var/log/daemon.log`
    * **All VMs/LXCs:**
        * `/var/log/syslog`
    * **Traefik:**
        * Access logs
        * Application logs
    * **Immich, Plex, etc.:**
        * Any relevant application log files.

---
## 5. Grafana Setup

The Grafana instance should be configured by the Ansible role with the following:

* **Data Sources:**
    * Auto-provision the **Prometheus** data source.
    * Auto-provision the **Loki** data source.
* **Dashboards:**
    * The role should automatically import a set of standard community dashboards. The "definition of done" is having a functional dashboard for each key service.
    * **Host Monitoring:** "Node Exporter Full" (e.g., ID `1860`) for all Linux hosts.
    * **Proxmox:** A dashboard for Proxmox VE (e.g., ID `10347`).
    * **TrueNAS:** A dashboard for TrueNAS SCALE.
    * **Docker:** A dashboard for `cAdvisor` metrics.
    * **Network:** An `omada_exporter` dashboard.
    * **Logs:** A dashboard for log exploration with Loki.

---
## 6. Ansible Implementation Strategy

The agent should create the following new roles:

1.  **`monitoring-stack`:**
    * **Target:** `containers` VM.
    * **Tasks:** Deploys the core Docker stack (Grafana, Prometheus, Loki, cAdvisor, PVE Exporter, Omada Exporter). Manages the `prometheus.yml` configuration file via a template.
2.  **`node-exporter`:**
    * **Target:** All Linux hosts (`n5p`, `rpi4`, all VMs/LXCs).
    * **Tasks:** Installs and enables the `node_exporter` service.
3.  **`promtail`:**
    * **Target:** All Linux hosts.
    * **Tasks:** Installs and configures the `promtail` service to ship the correct logs to Loki.