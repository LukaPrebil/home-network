# Retire self-hosted Mattermost

Status: accepted (2026-08-08). Supersedes ADR 0002 in full.

Mattermost went live on 2026-06-30 as the team's Slack replacement and was used for two days: Traefik logged 2682 requests on 30 June, 320 on 1 July, and nothing after. The container was stopped on 2026-07-22 and nobody asked for it back. What remained was a Mattermost 11.8.2 unpatched since June, publicly routed at `chat.lukapg.dev`, holding a plaintext message store nobody reads - and the 2026-08-08 power event showed it could restart itself unnoticed.

We are removing it entirely: LXC 207, the two encrypted TrueNAS datasets and their NFS exports, the `truenas-vms-enc` Proxmox storage, the Traefik router, the AdGuard split-DNS rewrite, and every reference in the Ansible tree and docs. The data is destroyed rather than archived. It was the only copy - no snapshot, replica or vzdump existed - and both alternatives were worse: `tank/backups` is unencrypted, so archiving there would discard exactly the at-rest protection ADR 0002 was written to provide, and a content-level export would have meant starting an unpatched, still-publicly-routed server.

The scoped-encryption reasoning from ADR 0002 stays valid and is carried forward: a service whose store is plaintext needs encryption at rest, ZFS cannot encrypt a dataset in place, so the answer is to provision new encrypted datasets rather than migrate the shared one. The `encryption: true` branch in `configure-truenas.yml` is deliberately kept with no consumer so the mechanism outlives the service.

Consequences: the team has no self-hosted chat and no plan for one. `chat.lukapg.dev` still resolves, because the zone's Cloudflare wildcard answers every name, but Traefik now returns 404 instead of 502 - the router, not the DNS record, is what ended the exposure. Restoring the service means a fresh deploy and fresh data.
