# Home Assistant Migration: Docker Container to HAOS VM

This document outlines the procedure for migrating the Home Assistant instance from a self-managed Docker container to a dedicated Home Assistant OS (HAOS) virtual machine on the Proxmox host (`n5p`).

**Goal:** To gain the benefits of the Home Assistant Supervisor, including the Add-on store, managed updates, and integrated backups, while improving the overall resilience and manageability of the smart home system.

---
## 1. Pre-Migration Checklist

This phase ensures all necessary data is correct and accessible before making any changes.

### 1.1 Verify the Backup

The most critical asset is a recent, complete, and valid Home Assistant backup.

* **Action:** Download the latest daily backup file (e.g., `backup_YYYY-MM-DD.tar`) from the Google Drive backup location to your local machine.
* **Verification:** Open the `.tar` archive to confirm that it contains your configuration files, specifically `configuration.yaml` and the `.storage/` directory. A backup is not considered valid until its contents have been verified.

### 1.2 Confirm External Service IPs

The backup stores the IP addresses of external services like your MQTT broker. Ensure these are pointing to their final, correct static IPs.

* **Action:** In your current Home Assistant instance, navigate to **Settings > Devices & Services > MQTT**.
* **Verification:** Confirm that the broker is configured to connect to the static IP of the Raspberry Pi 2 (`rpi2`), which is `192.168.30.6`. If not, update it and take a fresh backup.

---
## 2. Migration Procedure

This is the active cut-over process. It should be performed when you have about 30 minutes of downtime available.

### 2.1 Provision the HAOS Virtual Machine

First, create the new home for Home Assistant on the Proxmox server.

* **Host:** `n5p`
* **Action:** Create a new virtual machine using the [Proxmox VE Helper Scripts](https://tteck.github.io/Proxmox/) for Home Assistant OS.
* **Configuration:**
    * **Hostname:** `haos`
    * **Static IP:** `192.168.30.7` (VLAN 30)
    * Assign sufficient resources (e.g., 2+ cores, 4GB+ RAM, 32GB+ disk).

### 2.2 Shutdown the Old Container

To prevent conflicts, the old Home Assistant container must be stopped before starting the new one.

* **Action:** SSH into the old Docker host. Navigate to the directory containing your `docker-compose.yml` file.
* **Command:** Execute `docker compose stop homeassistant`.

### 2.3 Restore from Backup

Bring the new instance online with your existing configuration.

* **Action:** In a web browser, navigate to the new HAOS instance at `http://192.168.30.7:8123`.
* **Onboarding:** You will be greeted with the onboarding screen. Select the option to **"Restore from backup"**.
* **Upload:** Upload the verified `.tar` backup file from your computer. The system will process the file, restore your configuration, and reboot.

---
## 3. Post-Migration Validation

After the HAOS VM reboots, verify that the migration was successful and clean up the old environment.

### 3.1 Verify Integrations

* **Action:** Log in to your new Home Assistant instance.
* **Verification:** Navigate to **Settings > Devices & Services**. Check that all key integrations have loaded without errors, especially MQTT. Ensure you can see and control your Zigbee devices, confirming the connection to Zigbee2MQTT is active.

### 3.2 Update Network Clients

* **Action:** Any device or application that connects to Home Assistant by IP address must be updated.
* **Verification:** Update the Home Assistant mobile app on your phone and any other clients to point to the new IP address: `192.168.30.7`.

### 3.3 Decommission Old Container

Once you have confirmed the new instance has been running stable for at least 24 hours, you can permanently remove the old container.

* **Action:** On the old Docker host, edit your `docker-compose.yml` file and completely remove the `homeassistant` service definition.
* **Cleanup:** To reclaim disk space and prevent accidental startups, delete the old Home Assistant configuration volume by running `docker compose down -v`.