# Ovis remote control (pi on the Mac)

Ovis is a browser and phone client for herdr. It gives the phone a chat view of every pi
pane on the Mac, a live terminal, Stop, and push alerts, reached at `https://ovis.lukapg.dev`
through Cloudflare Access and Traefik.

Related: `docs/infrastructure/traefik-integration.md`, `docs/network-architecture.md` (ACL
matrix), and the plan `.claude/state/plans/2026-11-03-ovis-mac-remote-control.md`.

## Topology

```
phone PWA ──HTTPS──> Cloudflare (Access, WAF) ──> Traefik (192.168.60.142)
                                                        │ Bearer token injected
                                                        ▼
                                    Mac (192.168.254.31:7317) Ovis server
                                                        │ herdr socket
                                                        ▼
                                    pi panes in herdr + their session files
```

- The Ovis server runs on the Mac, not on a VM: it reads herdr's socket, and the attached
  sessions are Mac panes. A server elsewhere would still lose a sleeping Mac over SSH.
- The Mac is not an Ansible-managed host. Its address and token reach Traefik through
  `host_vars/traefik.yml` (`traefik_ovis_backend`, `traefik_ovis_token`).
- The Ovis server binds `0.0.0.0` because Traefik reaches it across VLANs, so the token is
  mandatory for every client, not only for the public hostname.

## The gate

Three controls, all required:

1. **Cloudflare Access** proves who is asking. Self-hosted application for
   `ovis.lukapg.dev`, one policy allowing the operator's email, one-month session.
   Access never injects the token, so it cannot replace step 3.
2. **Cloudflare-only allow-list.** Traefik's `cloudflare-only` middleware refuses any request
   that does not arrive from the pinned Cloudflare edge ranges. Without it, anything on the
   LAN could send `Host: ovis.lukapg.dev` to Traefik, skip Access, and be handed the injected
   token. It also means the DNS record must stay proxied: a DNS-only record makes every
   request come from the real client and answers `403`.
3. **The token.** Traefik's `ovis-token` middleware sets
   `Authorization: Bearer <vault_ovis_token>` on every request it proxies. The browser never
   sees it. A client that reaches `:7317` directly must present the same token.

Consequences worth remembering:

- Ovis offers no **Sign out** while the proxy injects the token; sign out at Cloudflare.
- Rotating `vault_ovis_token` invalidates every device at once. For one phone, revoke the
  **paired device** instead.
- The router carries no `rate-limit` middleware: the installed app polls and holds a
  WebSocket, and the shared 100/min bucket already broke Home Assistant (see `ha-secure`).
  `cloudflare-real-ip`, `crowdsec`, `proxy-headers` and `security-headers` still apply.

## Mac setup

The Mac's own steps are manual because it is not in inventory:

```bash
# 1. Bun (the Brewfile entry is the record; this installs it)
brew install bun

# 2. Ovis as a herdr plugin: clones, builds, starts with herdr, updates in-app
herdr plugin install devswha/ovis --yes

# 3. Settings, in the plugin's env file (no dot) in the config dir
herdr plugin config-dir devswha.ovis
#   HOST=0.0.0.0
#   OVIS_TOKEN=<vault_ovis_token>
#   OVIS_TELEMETRY=0
#   PI_CODING_AGENT_DIR=/Users/luka/.pi-personal/agent

# 4. Stay awake on AC only; battery and lid close still sleep
sudo pmset -c sleep 0
```

`PI_CODING_AGENT_DIR` is not optional on macOS. Ovis ties a pane's pi process to the store
its session file must sit in by reading `/proc/<pid>/environ`, which macOS does not have, so
the server falls back to its **own** agent directory. Without this line the chat reads
`~/.pi/agent/sessions`, finds nothing for a pane writing to `~/.pi-personal/agent/sessions`,
and silently serves the empty scrollback transcript (`conversation.no_session_path` in
`~/.local/state/herdr/plugins/devswha.ovis/server.log`).

Reserve `192.168.254.31` for the Mac in the Omada controller so
`traefik_ovis_backend` keeps pointing at it. If the macOS application firewall is enabled,
allow the Bun binary to receive inbound connections rather than turning the firewall off.

pi must run inside a herdr pane. A pi started in a plain terminal has no chat, status or
remote input, because Ovis attaches through herdr.

## Cloudflare setup

1. **DNS:** proxied record for `ovis` pointing where `pds` points. It must stay proxied;
   a DNS-only record makes requests arrive from the real client and Traefik answers `403`.
2. **Access application:** self-hosted, domain `ovis.lukapg.dev`, session one month, policy
   Allow -> Emails -> the operator's address.
3. **App Launcher policy:** Zero Trust -> Access controls -> Access settings -> App Launcher ->
   Manage -> add an Allow policy for the same email and enable One-time PIN. Without it, the
   PIN flow ends on the launcher with "contact your administrator to enable the Access App
   Launcher application", even though the application itself is configured. Open
   `https://ovis.lukapg.dev` to reach the app; the team-domain page is the launcher.

## Deploy

```bash
cd ansible
ansible-playbook site.yml --tags traefik
```

The route only works once the Mac answers, so install Ovis first. Cloudflare Access must
exist before the DNS record: a proxied record with no Access application is an open
terminal port.

## Alerts

Web Push fires on three events: a pane **waiting for an answer**, a **finished turn**, and a
**terminal that ended**. Two gates decide whether a given event reaches the phone.

- **Nothing is sent while a window of the app is in use.** A connected page that is visible and
  focused suppresses every alert, because that screen already shows the change. A phone in the
  foreground receives nothing; lock it or leave the app and the alerts resume.
- **A finish needs a turn worth telling.** The default preference is "long": a turn shorter than
  60 s sends nothing, and a qualifying finish waits 60 s before it goes out, so an answer typed at
  the desk calls it off. A waiting pane waits 10 s.

For pi, `done` needs no cooperation from herdr. Ovis keeps each pane's "worked since it was last
idle" itself and reports a back-to-idle that follows work as `done` until focus lands on the pane.
That is why a pi pane alerts on a finish even though herdr's pi integration reports only
`working`, `blocked` and `idle`.

`blocked` does not fire for pi. The herdr pi integration waits for a `herdr:blocked` event that
nothing in this harness emits, so a dialog in a pi pane arrives as a chat card read off the screen
and produces no "waiting for your input" push. Upstream tracks the cause in
[herdrdev/herdr#4143](https://github.com/herdrdev/herdr/issues/4143).

## Verification

```bash
# Local, on the Mac: 401 without the token, 200 with it, health green
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:7317/api/session
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:7317/api/health?scope=bridge

# Edge: Cloudflare redirects without an Access session; Traefik adds the token
curl -sI https://ovis.lukapg.dev/api/session | head -1
```

Then on the phone: pass Access, install the PWA, pair the device and enable alerts. To see a
finish alert, close or background the app on every device and let a turn run at least 60 s; a
short turn sends nothing by design, and a visible app window suppresses every alert (see
[Alerts](#alerts)). A finish was delivered this way on 2026-11-03.

## Recovery

| Symptom | Action |
| --- | --- |
| `502` from Traefik | the Mac is asleep, off the network, or Ovis is stopped: `herdr plugin action invoke devswha.ovis.status`, then `.start` |
| `401` on every request | token drift between `vault_ovis_token` and the plugin env file |
| `403` from Traefik | the request did not come from Cloudflare: the DNS record is DNS-only, or a LAN client sent the Host header itself |
| Phone lost access | revoke the paired device in Ovis Settings; rotate the token only for a real leak (`sops` edit, then `--tags traefik`) |
| Access login loop | check the Access policy still lists the email; sessions expire after a month |
| Chat empty, terminal fine | set `PI_CODING_AGENT_DIR` in the plugin env to the same agent dir the pane's pi uses, then restart Ovis (macOS cannot expose per-process env) |
