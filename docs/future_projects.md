# Future Homelab Enhancements

This document outlines potential future projects to further improve the resilience, security, and observability of the homelab.

---
## 1. Secure Remote Access (VPN)

* **Why:** To securely access your entire home network from any location, allowing you to manage services or use your AdGuard DNS on the go.
* **Recommended Tools:**
    * **WireGuard:** A modern, high-performance VPN protocol. Ideal for a traditional point-to-site setup.
    * **Tailscale:** Built on top of WireGuard, it creates a secure mesh network ("tailnet") between your devices, often without needing to open any ports on your router.
* **How it Fits:** Can be deployed as a container on the `containers` VM and managed with an Ansible role. Your DDNS service will provide a stable endpoint for the connection.

---
## 2. Intrusion Detection & Prevention

* **Why:** To automatically protect your public-facing services (behind Traefik) from malicious actors, scanners, and bots.
* **Recommended Tool:** **CrowdSec**.
* **How it Fits:** CrowdSec acts as a modern, collaborative fail2ban. It runs as a container, reads logs from your other services (like Traefik), and detects malicious patterns. When an attacker is identified, CrowdSec automatically blocks their IP address via a firewall rule. It also shares that IP with a central community blocklist, protecting you from threats identified by other users.

---
## 3. Ansible Role Testing

* **Why:** To apply professional software development practices to your infrastructure code. This allows you to test your Ansible roles in isolated environments before deploying them to your live servers, preventing errors and ensuring reliability.
* **Recommended Tool:** **Molecule**.
* **How it Fits:** Molecule is a testing framework for Ansible. You would use it locally on your MacBook. It can automatically spin up temporary Docker containers, run your Ansible role against them, run tests to verify the outcome, and then destroy the containers. This is a great way to ensure your automation code is robust.