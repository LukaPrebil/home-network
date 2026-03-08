# ATProto PDS Account Migration Guide

This guide covers migrating an existing Bluesky account from `bsky.social` (or any other PDS) to the self-hosted PDS at `pds.lukapg.dev` using the official `goat` CLI tool.

## Prerequisites

### Install goat

```bash
brew install goat
```

### Verify the self-hosted PDS is operational

```bash
# Health check
curl https://pds.lukapg.dev/xrpc/_health
# Expected: {"version":"0.4.x"}

# PDS metadata
goat pds describe https://pds.lukapg.dev

# DNS resolves correctly
dig pds.lukapg.dev +short
```

**Note:** This PDS uses DNS TXT record handle verification (not wildcard subdomains like `*.pds.lukapg.dev`). This allows `pds.lukapg.dev` to be proxied through Cloudflare (orange cloud) to hide the origin IP. Handles are verified via `_atproto.<domain>` TXT records — see "Setting Up a Vanity Handle" below.

## Important Concepts

- **DID (Decentralized Identifier):** Your permanent identity on AT Protocol (e.g., `did:plc:abc123`). This never changes, even when you move between PDS instances.
- **PLC Rotation Key:** A cryptographic key that authorizes changes to your DID document (like changing which PDS hosts your data). Stored in Ansible Vault as `vault_pds_plc_rotation_key`.
- **Handle:** Your human-readable name (e.g., `@luka.bsky.social` or `@lukapg.dev`). Can be changed independently of migration.
- **Repo:** Your data (posts, follows, likes, etc.) stored as a signed Merkle tree.

## Quick Migration (Recommended)

For an active `did:plc` account on bsky.social, goat can do the entire migration in one command.

### Step 1: Create an invite code on the new PDS

```bash
goat pds admin create-invite-code \
    --pds-host https://pds.lukapg.dev \
    --admin-password PDS_ADMIN_PASSWORD
```

Save the invite code for Step 3.

### Step 2: Login to your old account and request a PLC token

```bash
# Login with an app password (create one at https://bsky.app/settings/app-passwords)
goat account login -u YOUR_HANDLE.bsky.social -p YOUR_APP_PASSWORD

# Request PLC operation token (sends confirmation email)
goat account plc request-token
```

Check your email for the PLC token.

### Step 3: Run the migration

```bash
goat account migrate \
    --pds-host https://pds.lukapg.dev \
    --new-handle luka.pds.lukapg.dev \
    --new-password NEW_PASSWORD \
    --new-email YOUR_EMAIL \
    --plc-token TOKEN_FROM_EMAIL \
    --invite-code INVITE_CODE_FROM_STEP_1
```

This single command:
1. Creates an account on the new PDS with your existing DID
2. Exports your repo from the old PDS
3. Imports the repo to the new PDS
4. Exports and re-uploads any missing blobs
5. Migrates your preferences
6. Updates the PLC directory to point your DID to the new PDS
7. Activates the new account

### Step 4: Verify the migration

```bash
# Login to the new PDS
goat account login --pds-host https://pds.lukapg.dev -u YOUR_DID -p NEW_PASSWORD

# Check account status
goat account status

# Resolve your handle
goat resolve YOUR_HANDLE.bsky.social

# Check your profile via Bluesky app view
curl "https://api.bsky.app/xrpc/app.bsky.actor.getProfile?actor=YOUR_DID"
```

### Step 5: Deactivate account on old PDS

Once everything is verified:

```bash
# Login back to old PDS
goat account login -u YOUR_HANDLE.bsky.social -p YOUR_APP_PASSWORD

# Deactivate
goat account deactivate
```

## Manual Migration (Step-by-Step)

If the quick migration fails or you need more control, follow these steps.

### Step 1: Get your current account info

```bash
goat resolve YOUR_HANDLE.bsky.social
# Returns your DID

# Check your DID document to see current PDS
curl "https://plc.directory/did:plc:your-did-here"
```

### Step 2: Create an invite code and account on the new PDS

```bash
# Create invite code
goat pds admin create-invite-code \
    --pds-host https://pds.lukapg.dev \
    --admin-password PDS_ADMIN_PASSWORD

# Get PDS service DID (needed for service auth)
goat pds describe https://pds.lukapg.dev
# Note the DID from the output

# Generate a service auth token from the old PDS
goat account login -u YOUR_HANDLE.bsky.social -p YOUR_APP_PASSWORD
goat account service-auth \
    --lxm com.atproto.server.createAccount \
    --aud NEW_PDS_SERVICE_DID \
    --duration-sec 3600

# Create account on new PDS with your existing DID
goat account create \
    --pds-host https://pds.lukapg.dev \
    --existing-did YOUR_DID \
    --handle luka.pds.lukapg.dev \
    --password NEW_PASSWORD \
    --email YOUR_EMAIL \
    --invite-code INVITE_CODE \
    --service-auth SERVICE_AUTH_TOKEN
```

### Step 3: Export and import your data

```bash
# Export repo from old PDS (still logged into old account)
goat account login -u YOUR_HANDLE.bsky.social -p YOUR_APP_PASSWORD
goat repo export YOUR_DID
# Creates a .car file like account.YYYYMMDDHHMMSS.car

# Login to new PDS
goat account login --pds-host https://pds.lukapg.dev -u YOUR_DID -p NEW_PASSWORD

# Import repo
goat repo import ./account.*.car

# Check for missing blobs and re-upload
goat account missing-blobs
goat blob export YOUR_DID
fd . ./account_blobs/ | parallel -j1 goat blob upload {}

# Migrate preferences
goat account login -u YOUR_HANDLE.bsky.social -p YOUR_APP_PASSWORD
goat bsky prefs export > prefs.json
goat account login --pds-host https://pds.lukapg.dev -u YOUR_DID -p NEW_PASSWORD
goat bsky prefs import prefs.json
```

### Step 4: Update identity (PLC directory)

```bash
# Request PLC token from old PDS
goat account login -u YOUR_HANDLE.bsky.social -p YOUR_APP_PASSWORD
goat account plc request-token
# Check email for token

# Get recommended PLC operation from new PDS
goat account login --pds-host https://pds.lukapg.dev -u YOUR_DID -p NEW_PASSWORD
goat account plc recommended > plc_unsigned.json

# Sign and submit the PLC operation
goat account plc sign --token PLC_TOKEN ./plc_unsigned.json > plc_signed.json
goat account plc submit ./plc_signed.json

# Activate the new account
goat account activate
```

### Step 5: Deactivate old account

```bash
goat account login -u YOUR_HANDLE.bsky.social -p YOUR_APP_PASSWORD
goat account deactivate
```

## Setting Up a Vanity Handle (@lukapg.dev)

After migration, use your own domain as your handle.

### Option A: DNS TXT Record (Recommended)

Add a DNS TXT record in Cloudflare:

| Name | Type | Value |
|------|------|-------|
| `_atproto.lukapg.dev` | TXT | `did=did:plc:your-did-here` |

Then update your handle:

```bash
goat account login --pds-host https://pds.lukapg.dev -u YOUR_DID -p YOUR_PASSWORD

# Update handle (goat doesn't have a dedicated command for this yet)
curl -X POST "https://pds.lukapg.dev/xrpc/com.atproto.identity.updateHandle" \
  -H "Authorization: Bearer $(goat account session | jq -r '.accessJwt')" \
  -H "Content-Type: application/json" \
  -d '{"handle":"lukapg.dev"}'
```

### Option B: .well-known Endpoint

If you control the web server at the root domain, serve this file:

```
GET https://lukapg.dev/.well-known/atproto-did
Content-Type: text/plain

did:plc:your-did-here
```

This can be done via Traefik + a simple static file server, or by adding a route in your existing web setup.

## Rollback Procedure

If something goes wrong during migration:

1. **DID not updated yet:** Simply stop and continue using the old PDS. No damage done.

2. **DID updated but data not imported:**
   ```bash
   # Use the PLC rotation key to point DID back to old PDS
   # This requires the rotation key from your Ansible Vault
   # Contact the Bluesky team on GitHub if you need help with PLC operations
   ```

3. **Old PDS already deactivated:**
   - If you still have the repo .car file, re-import to any PDS
   - The PLC rotation key allows updating the DID document to any new endpoint

## Troubleshooting

### Handle not resolving after migration

- DNS propagation can take up to 48 hours
- Verify DNS records: `dig _atproto.lukapg.dev TXT`
- Check PDS logs: `docker logs pds`

### Posts not showing in Bluesky app

- The relay/crawler needs to discover your new PDS
- Verify `PDS_CRAWLERS=https://bsky.network` is set in env
- Check if relay can reach your PDS: ensure port 443 is forwarded to Traefik

### WebSocket connection failures

- Verify Traefik is proxying WebSocket correctly
- Test: `curl -i -H "Upgrade: websocket" -H "Connection: Upgrade" https://pds.lukapg.dev/xrpc/com.atproto.sync.subscribeRepos`
- Should return HTTP 101 Switching Protocols

### iSCSI mount issues after reboot

- Check iSCSI session: `iscsiadm -m session`
- Verify automatic login: `iscsiadm -m node -o show | grep node.startup`
- Check mount: `mount | grep pds`

## Security Notes

- **Never share your PLC rotation key.** It controls your identity. It's stored in Ansible Vault (`vault_pds_plc_rotation_key`).
- **Back up the rotation key** separately from the PDS data. If you lose it and your PDS goes down, you cannot recover your identity.
- **App passwords:** Use app-specific passwords for API access instead of your main account password. Create them at https://bsky.app/settings/app-passwords.
- **Clean up exported files** (`.car` files, `prefs.json`) after migration — they contain your account data.

## References

- [goat CLI](https://github.com/bluesky-social/goat) — official ATProto CLI tool
- [Migrating PDS Account with goat](https://whtwnd.com/bnewbold.net/entries/Migrating%20PDS%20Account%20with%20%60goat%60) — Bryan Newbold's migration guide
- [PDS Account Migration docs](https://github.com/bluesky-social/pds/blob/main/ACCOUNT_MIGRATION.md) — official migration documentation
