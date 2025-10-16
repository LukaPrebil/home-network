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

### Security Headers
```yaml
labels:
  - "traefik.http.routers.myservice.middlewares=security-headers@file"
```

### Rate Limiting
```yaml
labels:
  - "traefik.http.routers.myservice.middlewares=rate-limit@file"
```

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
