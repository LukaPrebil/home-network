# Traefik Reverse Proxy Role

This role deploys Traefik v3 as a reverse proxy for homelab services.

## Features

- **Docker-based deployment** with Docker Compose
- **Automatic service discovery** via Docker labels
- **Dashboard** for monitoring and debugging
- **File-based provider** for static routes and services
- **Security middlewares** (headers, rate limiting, HTTPS redirect)
- **Let's Encrypt support** (ACME) - optional, disabled by default
- **Separate Docker network** for proxy isolation

## Requirements

- Docker and Docker Compose installed (use the `docker` role)
- Common role applied for base system configuration

## Role Variables

See [defaults/main.yml](defaults/main.yml) for all available variables.

### Key Variables

```yaml
# Traefik version
traefik_version: "v3.2"

# Base directory
traefik_base_dir: "/opt/traefik"

# Entry points
traefik_http_port: 80
traefik_https_port: 443
traefik_dashboard_port: 8080

# Dashboard
traefik_dashboard_enabled: true
traefik_dashboard_insecure: false  # Set to true only for testing

# Docker provider
traefik_docker_exposed_by_default: false  # Require explicit labels

# Let's Encrypt (disabled by default)
traefik_acme_enabled: false
traefik_acme_email: ""
```

## Usage

### 1. Add to Inventory

```yaml
lxc_containers:
  hosts:
    traefik:
      ansible_host: 192.168.60.2
      ansible_user: root
```

### 2. Run the Playbook

```bash
ansible-playbook configure-traefik.yml
```

### 3. Configure Services to Use Traefik

Add labels to your Docker Compose services:

```yaml
services:
  myapp:
    image: myapp:latest
    networks:
      - traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.home.local`)"
      - "traefik.http.routers.myapp.entrypoints=web"
      - "traefik.http.services.myapp.loadbalancer.server.port=8080"

networks:
  traefik:
    external: true
```

## Directory Structure

```
/opt/traefik/
├── docker-compose.yml
├── config/
│   ├── traefik.yml          # Static configuration
│   └── dynamic/
│       └── dynamic.yml      # Dynamic configuration (middlewares, etc.)
└── acme/
    └── acme.json            # Let's Encrypt certificates (if enabled)
```

## Access Points

- Dashboard: `http://<host>:8080`
- HTTP: `http://<host>:80`
- HTTPS: `https://<host>:443`
- Health check: `http://<host>:8080/ping`

## Security Notes

- The dashboard is exposed on port 8080 by default
- For production, set `traefik_dashboard_insecure: false` and use authentication
- Docker socket is mounted read-only
- ACME storage has 600 permissions
- Security headers middleware is pre-configured

## Enabling Let's Encrypt

1. Set variables in `group_vars` or `host_vars`:
   ```yaml
   traefik_acme_enabled: true
   traefik_acme_email: "your-email@example.com"
   ```

2. Ensure port 80 is accessible from the internet (for HTTP challenge)

3. Re-run the playbook:
   ```bash
   ansible-playbook configure-traefik.yml
   ```

## Troubleshooting

### Check Traefik logs
```bash
docker compose -f /opt/traefik/docker-compose.yml logs -f
```

### Test configuration
```bash
# Check if Traefik is running
curl http://localhost:8080/ping

# View dashboard
curl http://localhost:8080/api/http/routers
```

### Common issues

- **Services not appearing**: Ensure services have `traefik.enable=true` label
- **Connection refused**: Check if service is on the `traefik` Docker network
- **Port conflicts**: Verify ports 80, 443, 8080 are not in use

## Tags

- `traefik` - Run all Traefik tasks
- `setup` - Directory creation only
- `docker` - Docker network setup
- `config` - Configuration file deployment
- `deploy` - Service deployment
