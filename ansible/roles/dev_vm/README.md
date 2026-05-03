# dev_vm

User-environment layer for the headless development VM.

## What it does

Layered on top of `common`, `docker`, and `tailscale`:

1. **GitHub PAT preflight** - fail fast if `vault_github_pat` is missing,
   expired, or scope-insufficient.
2. **Apt packages** - the web-dev / terminal subset of the user's macOS
   Brewfile (build tools, zsh productivity stack, Python venv, ufw, etc.).
   Symlinks `batcat`/`fdfind` to the canonical names.
3. **AWS CLI v2** - the official installer; Ubuntu's apt awscli is the v1 stub.
4. **Per-host SSH key + GitHub auto-add** - generates an ed25519 key on the
   VM, pins GitHub's host key in `known_hosts` (no TOFU), registers the
   public key with GitHub via `community.general.github_key`, then waits for
   propagation.
5. **chezmoi** - official installer + `chezmoi init --apply` against the
   user's dotfiles repo. Diff-then-apply on re-runs.
6. **Claude config tree** - clones `domengabrovsek/claude` and creates the
   symlink set under `~/.claude/` that mirrors the macOS layout. Validates
   every symlink source exists pre-link.
7. **nvm + Node LTS** - for web-dev work; Claude Code uses its own native
   installer (#8).
8. **Claude Code** - official native installer pinned to
   `dev_vm_claude_code_version`. Auto-update is left enabled.
9. **starship**, **rustup**, **tlrc** - tooling that's not in apt or that
   the user prefers to track outside the distro release.
10. **Sudoers** - full `NOPASSWD: ALL` for `luka`. The user is NOT in the
    `docker` group (so a compromised npm dep can't silently mount the host
    fs by joining a compromised process's namespace), but `sudo docker run
    -v /:/host` is still a one-liner root escape, which made the previous
    docker-only carve-out security theatre. SSH key-only auth and LAN /
    Tailscale-only ingress are the real perimeter.
11. **UFW** - LAN allowlist (`dev_vm_ssh_allow_cidrs`) + tailscale0 allow,
    `flush_handlers` before policy mutation, default deny incoming.

Patching is intentionally manual on this host. See
`docs/infrastructure/dev-vm-setup.md` for the rationale and the
`--tags dev-vm-upgrade` recipe.

## Re-running

```
ansible-playbook site.yml --tags dev-vm --limit dev
```

Every task is idempotent. `tailscale up` is gated on `BackendState != Running`
so the (revoked) auth key is never referenced after first enrolment.

## First-run requirement

The first run must be invoked over LAN (`192.168.1.139` -> `192.168.1.148`),
NOT over Tailscale. The `firewall.yml` task waits for `tailscale0` to come up
before adding allow rules, but the rule additions and the default-deny policy
are sequenced so the live ruleset goes through a brief moment where only the
LAN allowlist is reachable. Subsequent runs from any path are safe.
