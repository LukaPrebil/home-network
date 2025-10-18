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

The backup stores the IP addresses of external services like your MQTT broker. Ensure these are pointing to their current IPs.

* **Action:** In your current Home Assistant instance, navigate to **Settings > Devices & Services > MQTT**.
* **Verification:** Confirm that the broker is configured to connect to the Raspberry Pi 4 at `192.168.1.110` (where Mosquitto is currently running). This configuration will be restored from the backup.

---
## 2. Migration Procedure

This is the active cut-over process. It should be performed when you have about 30 minutes of downtime available.

### 2.1 Provision the HAOS Virtual Machine

First, create the new home for Home Assistant on the Proxmox server using the automated Ansible playbook.

* **Host:** `n5p`
* **Action:** Run the Ansible playbook to provision the HAOS VM:
  ```bash
  cd ansible
  ansible-playbook provision-haos.yml --ask-vault-pass
  ```
* **Configuration:**
    * **Hostname:** `haos`
    * **Temporary IP:** `192.168.1.144` (flat network)
    * **Final IP:** `192.168.30.7` (VLAN 30, after network migration)
    * **Resources:** 4 cores, 8GB RAM, 64GB disk on TrueNAS storage
    * **Version:** Home Assistant OS 16.2

The playbook will:
1. Download the HAOS qcow2 image (if not already cached)
2. Create the VM with appropriate settings
3. Import and resize the disk
4. Start the VM and wait for it to be ready
5. Display detailed migration instructions

### 2.2 Shutdown the Old Container

To prevent conflicts, the old Home Assistant container must be stopped before starting the new one.

* **Action:** SSH into the Raspberry Pi 4 where Home Assistant is currently running.
* **Commands:**
  ```bash
  ssh luka@192.168.1.110
  cd ~/docker  # or wherever your docker-compose.yml is located
  docker compose stop homeassistant
  ```

### 2.3 Restore from Backup

Bring the new instance online with your existing configuration.

* **Action:** In a web browser, navigate to the new HAOS instance at `http://192.168.1.144:8123`.
* **Onboarding:** You will be greeted with the onboarding screen. Select the option to **"Restore from backup"**.
* **Upload:** Upload the verified `.tar` backup file from your computer (downloaded from Google Drive). The system will process the file, restore your configuration, and reboot.

### 2.4 Configure USB Zigbee Coordinator Passthrough

After the restore is complete, you need to pass through the USB Zigbee coordinator stick from the Proxmox host to the HAOS VM.

* **Action:** SSH to the Proxmox host:
  ```bash
  ssh ansible_user@192.168.1.128
  ```

* **Find the USB device:**
  ```bash
  lsusb
  ```
  Look for your Zigbee coordinator in the output. Example:
  ```
  Bus 001 Device 003: ID 1a86:55d4 QinHeng Electronics USB Single Serial
  ```
  Note the `vendor:product` ID (e.g., `1a86:55d4`).

* **Pass through the USB device to the HAOS VM:**
  ```bash
  sudo qm set 102 --usb0 host=VENDOR_ID:PRODUCT_ID
  # Example: sudo qm set 102 --usb0 host=1a86:55d4
  ```

* **Reboot the HAOS VM:**
  ```bash
  sudo qm reboot 102
  ```

* **Verification:** After the VM reboots, the USB Zigbee stick will appear in Home Assistant at `/dev/ttyUSB0`. Your ZHA (Zigbee Home Automation) integration should automatically reconnect to it.

---
## 3. Post-Migration Validation

After the HAOS VM reboots, verify that the migration was successful and clean up the old environment.

### 3.1 Verify Integrations

* **Action:** Log in to your new Home Assistant instance at `http://192.168.1.144:8123`.
* **Verification:** Navigate to **Settings > Devices & Services**. Check that all key integrations have loaded without errors:
  * **MQTT:** Should be connected to `192.168.1.110` (rpi4)
  * **ZHA (Zigbee Home Automation):** Should show the USB coordinator at `/dev/ttyUSB0` and all your Zigbee devices
  * Test controlling some devices to confirm everything works

### 3.2 Update Network Clients

* **Action:** Any device or application that connects to Home Assistant by IP address must be updated.
* **Verification:** Update the Home Assistant mobile app on your phone and any other clients to point to the new IP address: `192.168.1.144` (temporary, will change to `192.168.30.7` after VLAN migration).

### 3.3 Decommission Old Container

Once you have confirmed the new instance has been running stable for at least 24 hours, you can permanently remove the old container.

* **Action:** On the old Docker host, edit your `docker-compose.yml` file and completely remove the `homeassistant` service definition.
* **Cleanup:** To reclaim disk space and prevent accidental startups, delete the old Home Assistant configuration volume by running `docker compose down -v`.