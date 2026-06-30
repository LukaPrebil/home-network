# Mattermost (self-hosted team chat)

Self-hosted [Mattermost](https://mattermost.com) free **Team Edition** - the team's Slack alternative. Internet-exposed at `https://chat.lukapg.dev`, with scoped at-rest encryption. The exposure + encryption rationale and trade-offs are recorded in [ADR 0002](../adr/0002-mattermost-internet-exposed-with-scoped-at-rest-encryption.md).

## Architecture

| Concern | Choice |
|---|---|
| Host | LXC `mattermost` (vmid 207, 2c/4 GB/24 GB) on n5p, IP `192.168.1.151` |
| Image | `mattermost/mattermost-team-edition` + `postgres:16-alpine` (2 containers) |
| Database | Postgres on the LXC **local rootfs** (correct POSIX locking; no DB on NFS) |
| At-rest encryption | LXC rootfs on the encrypted `truenas-vms-enc` dataset; uploads on the encrypted `tank/mattermost-uploads` dataset. Both keyfile auto-unlock |
| Uploads | Encrypted NFS dataset, host-mounted on n5p and bind-mounted into the LXC |
| Exposure | Cloudflare (proxied) -> Traefik (`chat.lukapg.dev`, CrowdSec + rate-limit) -> app:8065 |
| Auth / onboarding | Local accounts, **invite-link only** (open registration disabled) |
| Mobile push | TPNS (free, best-effort; HPNS is paid) |
| Calls | Calls plugin for 1:1 + screen share; group video via external Meet/Zoom |
| User management | `mmctl --local` from the role's `bootstrap.yml` |

Message content is stored as plaintext in Postgres (no E2E - standard Slack-style server model). At-rest encryption protects only against a stolen/decommissioned disk, never against the operator or a live-host compromise.

## First deploy (order matters)

Each step that mutates live infrastructure is called out. Run from `ansible/`.

1. **Create the encrypted datasets + Proxmox storage** (TrueNAS):
   ```bash
   ansible-playbook configure-truenas.yml
   ```
   Then **export the recovery key once** (TrueNAS UI -> dataset -> Encryption -> Export Key) and store it offline (password manager). Verify: `zfs get -r encryption,keystatus tank/mattermost-vm tank/mattermost-uploads`.
2. **Confirm the LXC template suffix** on n5p (25.04 was bumped to 26.04 LTS):
   ```bash
   ssh n5p 'pveam update && pveam available --section system | grep ubuntu-26'
   ```
   Correct `lxc_template_ubuntu` / `lxc_template_url` in `vars/lxc.yml` if the build suffix is not `-1`.
3. **Provision only the mattermost LXC** (scoped, so `hermes` 206 is not created as a side effect):
   ```bash
   ansible-playbook provision-lxc.yml -e lxc_provision_only=mattermost
   ```
4. **Bind the uploads NFS dataset into the LXC** (n5p host-mount + `pct` bind):
   ```bash
   ansible-playbook setup-mattermost-nfs.yml
   ```
5. **Add the public DNS record** (manual, outward-facing): create `chat.lukapg.dev` as a **proxied** A record in Cloudflare pointing at the WAN edge, same as `pds.lukapg.dev`. (AdGuard split-DNS for the on-LAN operator is already in the `adguard` role.)
6. **Deploy** the app, reverse-proxy route, and bootstrap:
   ```bash
   ansible-playbook site.yml --tags mattermost
   ansible-playbook site.yml --tags traefik   # publish the chat.lukapg.dev route
   ansible-playbook site.yml --tags adguard    # publish the split-DNS rewrite
   ```
   Verify: `curl -I https://chat.lukapg.dev` returns 200 with a valid cert; the web client connects (no WebSocket errors).

Dry-run any step first with `--check --diff`.

## Onboarding teammates

Open registration is disabled. To add the 6 teammates:

1. Sign in as `admin` (vaulted password) at `https://chat.lukapg.dev`.
2. Team menu -> **Invite People** -> **Copy invite link**.
3. Share the link out-of-band (DM/Signal). Each person self-registers and sets their own password - no human passwords are ever stored in vault.

Password resets (no SMTP): `docker exec mattermost mmctl --local user reset-password <username>` (or via the System Console).

## Operations

- **Version bump:** edit `mattermost_version` in `roles/mattermost/defaults/main.yml`, then `ansible-playbook site.yml --tags mattermost`. Compose recreates the changed container.
- **Re-run bootstrap** (idempotent): `ansible-playbook site.yml --tags mattermost,bootstrap`.
- **GitHub bot / plugin:** enable the GitHub plugin in System Console -> Plugins; it needs a GitHub OAuth app (callback `https://chat.lukapg.dev/plugins/github/oauth/complete`). Inbound webhooks for Grafana / Uptime Kuma alerts are created under Integrations -> Incoming Webhooks.
- **Calls:** enable the Calls plugin in System Console (1:1 + screen share on the free build; group calls are paid).

## Known free-tier limits (deliberate)

- **No HPNS:** mobile push uses TPNS (best-effort, no SLA). Self-hosting a push proxy would require custom mobile app builds - not worth it at this scale.
- **Group video is paid:** 1:1 calls + screen share only; use Meet/Zoom for group calls.
- **No SSO/SAML:** local accounts only (never worth it at <=20 users).

## Troubleshooting

- **Won't start after a power event:** check the encrypted datasets are unlocked - `zfs get keystatus tank/mattermost-vm tank/mattermost-uploads` on TrueNAS (should be `available`). Keyfile auto-unlock should make this automatic.
- **Uploads fail / read-only:** the `tank/mattermost-uploads` dataset must grant write to uid 2000 (the Mattermost container user). Check the bind: `findmnt /mnt/mattermost-uploads` inside the LXC should show `nfs4`, not the local rootfs.
- **Login links broken / WebSocket errors:** confirm `MM_SERVICESETTINGS_SITEURL` is the public `https://chat.lukapg.dev` (the `.env` is rendered from the role).
