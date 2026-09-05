# Traefik Integration Guide

This guide explains how to integrate services with Traefik for reverse proxy functionality.

## Overview

Traefik automatically discovers services via Docker labels. Services must:
1. Be on the `traefik` Docker network
2. Have `traefik.enable=true` label
3. Define routing rules via labels

## Basic Integration Pattern

### 1. Add Traefik Network to Docker Compose

```yaml
services:
  myservice:
    # ... service configuration ...
    networks:
      - default
      - traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myservice.rule=Host(`myservice.home.local`)"
      - "traefik.http.routers.myservice.entrypoints=web"
      - "traefik.http.services.myservice.loadbalancer.server.port=8080"

networks:
  traefik:
    external: true
  default:
    driver: bridge
```

### 2. Key Labels Explained

| Label | Purpose | Example |
|-------|---------|---------|
| `traefik.enable` | Enable Traefik for this container | `true` |
| `traefik.http.routers.<name>.rule` | Routing rule (Host, Path, etc.) | `Host(\`app.home.local\`)` |
| `traefik.http.routers.<name>.entrypoints` | Which entrypoint to use | `web` or `websecure` |
| `traefik.http.services.<name>.loadbalancer.server.port` | Container port | `8080` |

## Example: Immich Integration

```yaml
services:
  immich-server:
    container_name: immich_server
    image: ghcr.io/immich-app/immich-server:release
    volumes:
      - /mnt/immich-photos:/data
    networks:
      - default
      - traefik
    labels:
      # Enable Traefik
      - "traefik.enable=true"

      # HTTP router
      - "traefik.http.routers.immich.rule=Host(`photos.home.local`)"
      - "traefik.http.routers.immich.entrypoints=web"
      - "traefik.http.services.immich.loadbalancer.server.port=2283"

      # Optional: Apply security middleware
      - "traefik.http.routers.immich.middlewares=security-headers@file"

networks:
  traefik:
    external: true
  default:
    driver: bridge
```

Now Immich is accessible at: `http://photos.home.local`

## Example: Home Assistant Integration

```yaml
services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      - ./config:/config
    networks:
      - traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hass.rule=Host(`ha.home.local`)"
      - "traefik.http.routers.hass.entrypoints=web"
      - "traefik.http.services.hass.loadbalancer.server.port=8123"

networks:
  traefik:
    external: true
```

### Trusted proxies live in the HA UI, not in YAML

The block above is the generic Docker pattern. The real deployment runs Home Assistant OS on VM 102
and is routed by the static file provider (the `ha-secure` router in `dynamic.yml.j2`), so HA sees
Traefik as the request source and needs Traefik's IP in its trusted-proxy list.

Since HA 2026.8 that list is no longer in `configuration.yaml`. The `http:` block was migrated into a
UI-backed store and deleted from the file on 2026-08-07, so the values now exist only under
Settings > System > Network, in the HTTP server section. They are invisible to grep, and re-adding
the YAML block does nothing because HA ignores it after migration.

Current entries: `192.168.1.142` (Traefik LXC), `127.0.0.1`, `172.18.0.0/16`.

**When Traefik moves to `192.168.60.2`, this list has to be updated by hand in the HA UI.** No
Ansible role covers it. The symptom of missing the step is `ha.<domain>` returning 400 ("Received
X-Forwarded-For header from an untrusted proxy") while direct `http://<haos>:8123` still works, which
is also the quickest way to tell this apart from a Traefik or certificate fault.

## Advanced: HTTPS with Let's Encrypt

Once Let's Encrypt is enabled in Traefik:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.myservice.rule=Host(`myservice.example.com`)"
  - "traefik.http.routers.myservice.entrypoints=websecure"
  - "traefik.http.routers.myservice.tls=true"
  - "traefik.http.routers.myservice.tls.certresolver=letsencrypt"
  - "traefik.http.services.myservice.loadbalancer.server.port=8080"

  # Optional: HTTP to HTTPS redirect
  - "traefik.http.routers.myservice-http.rule=Host(`myservice.example.com`)"
  - "traefik.http.routers.myservice-http.entrypoints=web"
  - "traefik.http.routers.myservice-http.middlewares=https-redirect@file"
```

## Advanced: Path-based Routing

Route based on URL path instead of hostname:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.api.rule=Host(`app.home.local`) && PathPrefix(`/api`)"
  - "traefik.http.routers.api.entrypoints=web"
  - "traefik.http.services.api.loadbalancer.server.port=8080"

  # Strip prefix before forwarding
  - "traefik.http.routers.api.middlewares=api-stripprefix"
  - "traefik.http.middlewares.api-stripprefix.stripprefix.prefixes=/api"
```

## Using Pre-configured Middlewares

The Traefik role includes several pre-configured middlewares in `dynamic.yml`:

### Security Middleware Chain (applied to all public routes)

When `traefik_cloudflare_real_ip_enabled` and `traefik_crowdsec_enabled` are true (default for the traefik host), all public routes in `dynamic.yml.j2` automatically get:

1. **cloudflare-real-ip** - traefik-warp plugin, extracts real client IP from Cloudflare proxy headers
2. **crowdsec** - CrowdSec bouncer plugin (stream mode), blocks IPs flagged by CrowdSec engine or community blocklists
3. Per-route middlewares (proxy-headers, security-headers, and rate-limit - except Home Assistant, which has a login-flow-only limiter; see below)

This chain is built via a Jinja2 namespace variable (`_ns.security_mw`) at the top of the template.

### Security Headers
```yaml
labels:
  - "traefik.http.routers.myservice.middlewares=security-headers@file"
```

### Rate Limiting
Applied to all public routes except Home Assistant. Config: 100 req/min average, 50 burst.
```yaml
labels:
  - "traefik.http.routers.myservice.middlewares=rate-limit@file"
```

### Home Assistant: login-only rate limiting

Home Assistant has no route-wide limiter. A single browser HA load consumes
almost the whole 100/min burst: the 2026-09-05 incident had 50 accepted and 44
rejected (429) requests in one 15-second interval while HA itself stayed
healthy. Normal HA traffic - UI, API, token refresh, WebSocket - has no
Traefik capacity limit. Cloudflare, CrowdSec, HA authentication, and MFA
remain the controls.

Only password and MFA submissions may be limited. The `ha-login-secure` router
matches `POST /auth/login_flow` and child paths with explicit `priority: 100`
above `ha-secure`, and attaches `ha-login-rate-limit` (10 req/min, burst 30,
keyed on `X-Real-Ip`). `/auth/token`, UI assets, authenticated APIs, and
`/api/websocket` stay on `ha-secure` without a limiter.

The limiter sits behind `traefik_ha_login_rate_limit_enabled` (default
`false` in the role, `true` in `host_vars/traefik.yml`). To unblock a
legitimate user, force the limiter off and reconverge:

```bash
ansible-playbook site.yml --tags traefik --limit traefik \
  -e traefik_ha_login_rate_limit_enabled=false
```

This changes dynamic configuration only: the file provider hot-reloads it
and Traefik does not restart. Re-enabling means converging without the
override. The Grafana alert `Home Assistant Login 429` (see the monitoring
stack docs) fires on any login-route 429 so this stays visible.

### Client trust chain (who is X-Real-Ip?)

The limiter and the CrowdSec bouncer key on `X-Real-Ip`, so every layer
trusts the pinned Cloudflare ranges only. Pin them in
`host_vars/traefik.yml` (`traefik_cloudflare_ipv4_ranges` /
`traefik_cloudflare_ipv6_ranges`, from https://www.cloudflare.com/ips-v4 and
/ips-v6):

1. **Static config**: `entryPoints.websecure.forwardedHeaders.trustedIPs`
   holds the pinned ranges. Traefik strips the forwarded headers of every
   peer outside those ranges. Never set `insecure: true` here.
2. **cloudflare-real-ip (warp)**: auto-fetches Cloudflare's published ranges
   and no longer adds `trustIp` entries. The old `192.168.1.0/24` entry made
   every LAN peer a "trusted edge" whose forged `CF-Connecting-IP` was
   honored. Now a Cloudflare peer gets `X-Real-Ip` = `CF-Connecting-IP`; any
   other peer gets its socket address, and warp strips spoofed forwarding
   headers first.
3. **crowdsec bouncer**: `forwardedHeadersCustomName: X-Real-IP` with the
   pinned ranges as `forwardedHeadersTrustedIps`, so it evaluates the same
   verified identity as the limiter.
4. **lan-only**: unchanged and still keyed on the socket address
   (`RemoteAddr`); its boundary never considers forwarded headers.

Every traefik converge drift-checks the pins against Cloudflare's official
lists (`roles/traefik/tasks/config.yml`): the fetches also run under
`--check`, a reachable list that differs from the pinned one fails the
converge, an unreachable endpoint warns and continues, and the pinned lists
are never rewritten from a fetch.

### HTTPS Redirect
```yaml
labels:
  - "traefik.http.routers.myservice.middlewares=https-redirect@file"
```

### Multiple Middlewares
```yaml
labels:
  - "traefik.http.routers.myservice.middlewares=security-headers@file,rate-limit@file"
```

### LAN-Only Services

The Traefik dashboard is not publicly routed. It is accessible only via LAN:
- Traefik dashboard: `http://traefik.lan:8080` (`192.168.1.142:8080`)

The `.lan` domain is configured as an AdGuard DNS rewrite in `roles/adguard/defaults/main.yml`.

### Internal-Only Routes (HTTPS via Traefik, no public DNS)

Internal admin UIs (Proxmox, TrueNAS, Omada Controller, AdGuard Home) are reachable at `*.lukapg.dev` URLs that are **only resolvable on the LAN** - public DNS returns NXDOMAIN. Traefik enforces a `lan-only` `ipAllowList` middleware as a defence-in-depth backstop. (Off-LAN access over the tailnet is planned but **not yet deployed** - it needs the Tailscale subnet router + a DNS override; the `lan-only` middleware already pre-allowlists the Tailscale CGNAT ranges below so it will work once that lands.)

Pattern:

1. **AdGuard split-DNS rewrite** (in `roles/adguard/defaults/main.yml`) points the name at Traefik's LAN IP (`192.168.1.142`).
2. **No Cloudflare A record** for the name. Public resolvers return NXDOMAIN.
3. **Traefik router** in `dynamic.yml.j2` attaches the `lan-only` middleware (alongside `crowdsec`, `proxy-headers`, `security-headers`).
4. **Self-signed HTTPS upstreams** (Proxmox, TrueNAS, Omada) reference per-router `serversTransport` blocks with `insecureSkipVerify: true`. AdGuard speaks plain HTTP and needs no transport block.

Example router (Proxmox VE on n5p):

```yaml
# In dynamic.yml.j2 (routers section)
proxmox-secure:
  rule: "Host(`n5p.lukapg.dev`)"
  entryPoints:
    - websecure
  service: proxmox
  tls:
    certResolver: letsencrypt
    domains:
      - main: "lukapg.dev"
        sans:
          - "*.lukapg.dev"
  middlewares:
    - lan-only
    - crowdsec
    - proxy-headers
    - security-headers

# In dynamic.yml.j2 (services section)
proxmox:
  loadBalancer:
    servers:
      - url: "https://192.168.1.128:8006"
    passHostHeader: true
    serversTransport: proxmox-tls

# In dynamic.yml.j2 (serversTransports section)
serversTransports:
  proxmox-tls:
    insecureSkipVerify: true
```

The `lan-only` middleware permits `127.0.0.1/32`, `192.168.1.0/24` (current flat LAN), `100.64.0.0/10` (Tailscale CGNAT IPv4), and `fd7a:115c:a1e0::/48` (Tailscale CGNAT IPv6). `cloudflare-real-ip` is intentionally omitted from internal routes (no Cloudflare in path) and `rate-limit` is omitted because admin SPAs poll fast enough to brush against the 100 req/min limit.

## Advanced: Static File Provider Routing (Non-Docker Services)

For services running on a different host (not co-located with Traefik), use the **static file provider** instead of Docker labels. Routes are defined in `roles/traefik/templates/dynamic.yml.j2`.

### Example: ATProto PDS with Wildcard Subdomain Routing

The PDS requires two routers - one for the main hostname and one for user handle subdomains:

```yaml
# In dynamic.yml.j2 (routers section)
routers:
  # ATProto PDS - single hostname, no wildcard subdomains needed.
  # Handles are verified via DNS TXT records (_atproto.<domain>),
  # so only pds.lukapg.dev needs routing. This allows Cloudflare
  # proxy (orange cloud) to hide the origin IP.
  pds-secure:
    rule: "Host(`pds.lukapg.dev`)"
    entryPoints:
      - websecure
    service: pds
    tls:
      certResolver: letsencrypt
      domains:
        - main: "lukapg.dev"
          sans:
            - "*.lukapg.dev"
    middlewares:
      - proxy-headers
      - rate-limit

# In dynamic.yml.j2 (services section)
services:
  pds:
    loadBalancer:
      servers:
        - url: "http://192.168.1.140:3000"
      passHostHeader: true  # Critical: PDS uses Host header for handle resolution
```

**Key points for static routing:**
- `passHostHeader: true` is essential when the backend uses the Host header for routing (e.g., multi-tenant services)
- Handles use DNS TXT verification (`_atproto.<domain>` TXT `did=did:plc:...`) - no wildcard subdomain routing needed
- `pds.lukapg.dev` is proxied through Cloudflare (orange cloud) since `*.lukapg.dev` is covered by free Universal SSL
- WebSocket connections (like ATProto's firehose) are proxied natively - no extra middleware needed

## Troubleshooting

### Service not accessible

1. **Check if container is on traefik network:**
   ```bash
   docker network inspect traefik
   ```

2. **Verify labels are applied:**
   ```bash
   docker inspect <container_name> | grep -A 20 Labels
   ```

3. **Check Traefik dashboard:**
   - Access: `http://<traefik-host>:8080`
   - Look for your service in HTTP > Routers

4. **View Traefik logs:**
   ```bash
   docker compose -f /opt/traefik/docker-compose.yml logs -f
   ```

### DNS Resolution

For `*.home.local` domains to work:
1. Add entries to `/etc/hosts` on your workstation:
   ```
   192.168.60.2  photos.home.local ha.home.local
   ```

2. Or configure DNS (AdGuard Home) with wildcard:
   ```
   *.home.local -> 192.168.60.2
   ```

## Best Practices

1. **Network Isolation**: Keep services on their own network + traefik network
2. **Explicit Labels**: Use `exposedByDefault: false` and explicit `traefik.enable=true`
3. **Unique Names**: Use unique router/service names to avoid conflicts
4. **Security**: Apply security-headers middleware to all public services
5. **Health Checks**: Traefik respects Docker healthchecks automatically

## Migration from Nginx Proxy Manager

If migrating from NPM:
1. Remove port bindings (Traefik will handle routing)
2. Add traefik network
3. Add traefik labels
4. Remove NPM proxy configuration
5. Update DNS to point to Traefik host

Example before (NPM):
```yaml
services:
  app:
    ports:
      - "8080:8080"  # Directly exposed
```

Example after (Traefik):
```yaml
services:
  app:
    networks:
      - traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app.rule=Host(`app.home.local`)"
      - "traefik.http.routers.app.entrypoints=web"
      - "traefik.http.services.app.loadbalancer.server.port=8080"

networks:
  traefik:
    external: true
```
