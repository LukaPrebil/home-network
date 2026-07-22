# tailscale

Installs the Tailscale apt repo + client and enrols the host on first run.

## Inputs

| Var | Default | Notes |
|-----|---------|-------|
| `tailscale_hostname` | `{{ inventory_hostname }}` | Tailnet hostname |
| `tailscale_advertise_tags` | `""` | e.g. `tag:dev`; empty omits the flag |
| `tailscale_accept_dns` | `false` | Default keeps the host DNS resolver authoritative |
| `tailscale_accept_routes` | `false` | Whether the host accepts tailnet-pushed subnet routes |
| `tailscale_authkey` | `""` | Vault'd one-shot key; empty value skips `tailscale up` |
| `tailscale_extra_args` | `[]` | Extra flags to pass to `tailscale up` |
| `tailscale_advertise_routes` | `[]` | LAN subnets this host advertises (e.g. `["192.168.1.0/24"]`). Non-empty triggers IP-forwarding sysctl. |

## Outputs

- `tailscale0` interface available; `100.x.x.x` IP from the tailnet.

## Operational notes

- Enrolment is gated on `tailscale status --json | .BackendState != "Running"`.
  Once a host is up, the auth-key path is skipped on every subsequent run.
- **Revoke the auth key** at <https://login.tailscale.com/admin/settings/keys>
  immediately after the first successful run. The role never needs it again
  for this host.
- The auth key is staged to a transient root-only file (`/run/tailscale-authkey`,
  mode 0600, removed right after) and passed as `--auth-key=file:...`, so it
  doesn't show up in `auditd` / `/var/log/auth.log` or process accounting.
  Do NOT switch to the `TS_AUTHKEY` env var: the tailscale CLI ignores it
  (it's a containerboot/Docker convention) and `tailscale up` then hangs on
  interactive auth.
- **Subnet routers** must have their advertised routes approved in the
  Tailscale admin console (Machines → host → Edit route settings) OR
  pre-approved via `autoApprovers.routes` in the tailnet policy file.
  IP forwarding (`net.ipv4.ip_forward`, `net.ipv6.conf.all.forwarding`)
  is enabled automatically by the role when `tailscale_advertise_routes`
  is non-empty, written to `/etc/sysctl.d/99-tailscale-subnet-router.conf`.
- After first enrol, route changes from `tailscale_advertise_routes` are
  reapplied via `tailscale set --advertise-routes=...` on every run; the
  initial `tailscale up` call short-circuits once the daemon is Running.
