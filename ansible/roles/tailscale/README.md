# tailscale

Installs the Tailscale apt repo + client and enrols the host on first run.

## Inputs

| Var | Default | Notes |
|-----|---------|-------|
| `tailscale_hostname` | `{{ inventory_hostname }}` | Tailnet hostname |
| `tailscale_advertise_tags` | `""` | e.g. `tag:dev`; empty omits the flag |
| `tailscale_accept_dns` | `false` | Default keeps the host DNS resolver authoritative |
| `tailscale_accept_routes` | `false` | No subnet routers today; explicit |
| `tailscale_authkey` | `""` | Vault'd one-shot key; empty value skips `tailscale up` |
| `tailscale_extra_args` | `[]` | Extra flags to pass to `tailscale up` |

## Outputs

- `tailscale0` interface available; `100.x.x.x` IP from the tailnet.

## Operational notes

- Enrolment is gated on `tailscale status --json | .BackendState != "Running"`.
  Once a host is up, the auth-key path is skipped on every subsequent run.
- **Revoke the auth key** at <https://login.tailscale.com/admin/settings/keys>
  immediately after the first successful run. The role never needs it again
  for this host.
- The auth key is passed via `TS_AUTHKEY` env var, not `--auth-key=`, so it
  doesn't show up in `auditd` / `/var/log/auth.log` or process accounting.
