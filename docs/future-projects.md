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
## ~~2. Intrusion Detection & Prevention~~ (Completed)

Deployed — see `ansible/roles/crowdsec/` and the CrowdSec section in `docs/network-architecture.md`.

---
## 3. Ansible Role Testing

* **Why:** To apply professional software development practices to your infrastructure code. This allows you to test your Ansible roles in isolated environments before deploying them to your live servers, preventing errors and ensuring reliability.
* **Recommended Tool:** **Molecule**.
* **How it Fits:** Molecule is a testing framework for Ansible. You would use it locally on your MacBook. It can automatically spin up temporary Docker containers, run your Ansible role against them, run tests to verify the outcome, and then destroy the containers. This is a great way to ensure your automation code is robust.

---
## 4. Cloudflare IaC (Completed 2026-11-03)

Both zones and every account object are now declared in `iac/cloudflare/`: 21 DNS records, the two
zones and their DNSSEC, the `ovis` and App Launcher Access applications with one shared allow policy,
the Zero Trust organization and its one-time-PIN identity provider, the `lukapg.dev` WAF rules, bot
management on both zones, the account bulk redirect, and seven zone settings per zone.

The tree plans on a pull request, applies on a merge, and a daily job pushes drift to Loki so a
dashboard edit cannot outlive the repo silently. The operator runbook - what is declared, how to
import, and which repository secrets CI still needs - is
`docs/infrastructure/cloudflare-iac.md`. Decided 2026-11-03 while planning the Ovis rollout.
