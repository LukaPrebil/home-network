# Service Data Backups

This directory contains local backups of service data migrated from rpi4 to the containers VM. These backups enable idempotent deployments and serve as disaster recovery.

## Directory Structure

```
backups/
├── uptime-kuma/        # Uptime Kuma monitoring data
│   ├── kuma.db         # Database (excluded from git - large file)
│   ├── docker-tls/     # TLS certificates for Docker monitoring
│   ├── screenshots/    # Monitor screenshots
│   └── upload/         # Uploaded files
├── ddns-updater/       # Dynamic DNS updater data
│   ├── config.json     # DNS provider configuration
│   └── updates.json    # Update history
└── octoeverywhere/     # OctoEverywhere 3D printer companion
    ├── octoeverywhere.conf      # Service configuration
    └── octoeverywhere-store/    # State data

```

## Migration Strategy

### Two-Stage Migration
1. **Stage 1**: rpi4 → local backup (one-time)
   - Syncs data from rpi4 to this directory
   - Only runs if backup doesn't already exist
   - Stops source service briefly, then restarts it

2. **Stage 2**: local backup → containers VM (idempotent)
   - Always runs from local backup
   - Can be re-run multiple times safely
   - No dependency on rpi4

### Usage

**Initial migration with data sync:**
```bash
ansible-playbook migrate-containers.yml -e migrate_data=true
```

**Subsequent deployments (from local backup):**
```bash
ansible-playbook migrate-containers.yml
```

**Deploy in stopped state for testing:**
```bash
ansible-playbook migrate-containers.yml -e migrate_data=true -e service_state=stopped
```

## Git Considerations

### What's Tracked
- ✅ Configuration files (config.json, *.conf)
- ✅ Small state files (updates.json)
- ✅ Directory structure

### What's Excluded
- ❌ Large database files (kuma.db - 243MB)
- ❌ Log files (*.log, logs/)
- ❌ Temporary files

See `.gitignore` for complete exclusion list.

## Disaster Recovery

These backups provide:
- **Point-in-time recovery**: Restore services to known-good state
- **Configuration history**: Track changes to service configs over time
- **Migration safety**: Re-deploy without affecting production rpi4
- **Fast rebuilds**: Deploy new containers VM without rpi4 dependency

## Maintenance

**Update backups manually** (if needed):
```bash
# Sync Uptime Kuma
rsync -avz --exclude='*.log' rpi4:/home/luka/ha/kuma_data/ backups/uptime-kuma/

# Sync ddns-updater
rsync -avz --exclude='*.log' rpi4:/home/luka/ha/ddns-data/ backups/ddns-updater/

# Sync OctoEverywhere
rsync -avz --exclude='logs' --exclude='*.log' rpi4:/home/luka/ha/octo_data/ backups/octoeverywhere/
```

**Test backup integrity:**
```bash
# Verify files exist
ls -lh backups/*/

# Check configs are readable
cat backups/ddns-updater/config.json
cat backups/octoeverywhere/octoeverywhere.conf
```

## Source Information

- **Source Host**: rpi4 (192.168.1.110)
- **Source User**: luka
- **Source Base Path**: /home/luka/ha/
- **Backup Created**: During first migration run
- **Backup Method**: rsync with checksums
