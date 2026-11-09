# Cloudflare IaC

Every Cloudflare object for `lukapg.dev` and `tnz.social` is declared in
`iac/cloudflare/`. Nothing in the account exists only because someone clicked:
a dashboard edit becomes a drift alert, and a new public hostname and its Access
gate land in one commit.

One root, one state, covering both zones and the account-level objects. The
provider is `cloudflare/cloudflare` `~> 5.28` (5.28.1), pinned in
`.terraform.lock.hcl`.

## What is declared

| File | Objects |
| --- | --- |
| `zones.tf` | both zones, their DNSSEC (`status = active`), `prevent_destroy` on all four |
| `dns_tnz.tf` | the 7 `tnz.social` records, including the three mail records and the redirect sinkhole |
| `dns_lukapg.tf` | 14 `lukapg.dev` records: nine A records from one `for_each`, the parking wildcard, `www`, `pds`, `_atproto`, `_dmarc` |
| `access.tf` | the `ovis` application and the shared allow policy |
| `app_launcher.tf` | the Cloudflare-created App Launcher and its attachment to the same policy |
| `identity.tf` | the Zero Trust organization (`prevent_destroy`) and the one-time-PIN identity provider |
| `waf.tf` | the two `lukapg.dev` custom firewall rules (geo challenge, AI-crawler block) |
| `bot.tf` | bot management on both zones |
| `redirects.tf` | the account `youtoobitch` bulk-redirect list and its account root ruleset |
| `settings.tf` | seven zone settings per zone: `ssl`, `always_use_https`, `min_tls_version`, `tls_1_3`, `security_level`, `security_header`, `orange_to_orange` |
| `imports_*.tf` | the import blocks that adopt every object above by id |

Deliberately not declared: the API tokens (a token in state is a secret in
state, and the token is needed before the first run), Universal SSL issuance,
the Free plan subscription, Cloudflare-managed ruleset versions, the domain
registrations at Porkbun, and Access applications for the other eight public
hostnames - those use their own login, and gating them is a security decision
rather than codification.

## Running it

Every command goes through the SOPS wrapper, so the token and the S3 key reach
OpenTofu from the environment and never from a var file or the state:

```bash
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/cloudflare plan'
sops exec-env iac/secrets.sops.yaml 'tofu -chdir=iac/cloudflare apply'
```

State lives in the `terraform-state` bucket at `http://192.168.30.140:9000`
(key `cloudflare.tfstate`) with `use_lockfile = true`, and is encrypted at rest
by the same enforced `pbkdf2`/`aes_gcm` block the object-store root uses. A
`terraform.tfstate` on disk means the backend failed to load - investigate, do
not commit it.

## Importing a new object

Declare an `import` block, do not run `tofu import`:

```hcl
import {
  to = cloudflare_dns_record.example
  id = "<zone_id>/<record_id>"
}
```

The first apply is then a reviewable plan that says "will be imported", and the
block stays in the tree afterwards: it costs nothing once the resource is in
state, and if the state object is ever lost, re-running apply re-adopts the same
ids instead of failing with "already exists".

Import ids, checked against 5.28.1:

| Object | Id |
| --- | --- |
| zone, DNSSEC, bot management | `<zone_id>` |
| DNS record | `<zone_id>/<record_id>` |
| zone setting | `<zone_id>/<setting_id>` |
| Access application | `accounts/<account_id>/<app_id>` |
| reusable Access policy | `<account_id>/<policy_id>` |
| identity provider | `accounts/<account_id>/<idp_id>` |
| organization | `<account_id>` |
| zone ruleset | `zones/<zone_id>/<ruleset_id>` |
| account ruleset | `accounts/<account_id>/<ruleset_id>` |
| list | `<account_id>/<list_id>` |

To delete an object through the plan, import it first, apply, then remove the
resource block and the import block and apply again. Deleting by hand leaves no
reviewable record of what went.

## Six objects a plan must never replace

If a plan wants to **replace** any of these, stop and fix the attributes instead
of applying:

- either `cloudflare_zone` - a replacement deletes every record it holds
- either `cloudflare_zone_dnssec`
- `cloudflare_zero_trust_organization` - a replacement changes the team domain
  and locks every Access app out
- `cloudflare_zero_trust_access_application.app_launcher` - Cloudflare-created;
  a replacement breaks the app list every signed-in user lands on

All six carry `prevent_destroy`, and that guard also covers the destroy half of a
replacement: the plan fails with a lifecycle error before anything runs. Treat a
plan that reports either error as a stop, not as a hint.

## CI

Three workflows, one per action. None of them filters on `paths` any more: the
plan job has to run on every pull request so a required status check always
reports, and it exits green in seconds when no root changed.

| Workflow | Trigger | What it does |
| --- | --- | --- |
| `iac-plan.yml` | every pull request | derives the changed roots from a git diff, then `fmt -check`, `init -lockfile=readonly`, `validate` and `plan -detailed-exitcode` for each, and posts one sticky comment with a section per root |
| `iac-apply.yml` | push to `main`, `main` only by hand | derives the changed roots, then plans each to a file and applies that file, under `concurrency: {group: tofu-apply, cancel-in-progress: false}`. `iac/object-store` is skipped: it is applied from the control node |
| `iac-drift.yml` | daily 04:10 UTC, manual | one matrix leg per root, each pushing its own `root` label, a summary and the plan to Loki |

The merge is the approval gate. There is no separate deploy step.

### Repository secrets the operator still has to add

Every IaC job checks for all seven first and fails with the missing names rather
than skipping silently, so an unconfigured repository shows red, not green.

| Secret | What it is |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | the same account-owned token as `iac/secrets.sops.yaml` (id `39b4c7e1…`). Scopes: `Zone DNS Write`, `Zone WAF Write`, `Bot Management Write`, `Zone Settings Write`, `Zone Write`, `DNS Read`, `Access: Apps and Policies Write`, `Access: Organizations, Identity Providers, and Groups Write`, `Account Rulesets Write`, `Account Filter Lists Edit`. No IP restriction |
| `AWS_ACCESS_KEY_ID` | the `tf-ci` RustFS key (`terraform-state` bucket only) |
| `AWS_SECRET_ACCESS_KEY` | its secret |
| `TF_VAR_STATE_PASSPHRASE` | the same passphrase as `TF_VAR_state_passphrase` in `iac/secrets.sops.yaml` - without it OpenTofu refuses to read the encrypted state |
| `TF_VAR_LUKAPG_PUBLIC_IPV4` | the same origin address as `TF_VAR_lukapg_public_ipv4` in `iac/secrets.sops.yaml` - the root requires it, so a run without it fails at the variable rather than planning the records against nothing |
| `TS_OAUTH_CLIENT_ID` | Tailscale OAuth client for an ephemeral `tag:ci` node |
| `TS_OAUTH_SECRET` | its secret |

The Tailscale client needs two grants through the existing rpi4 subnet router
(which advertises `192.168.30.0/24` plus `192.168.60.142/32`):

| Destination | Used by |
| --- | --- |
| `192.168.30.140:9000` | every job - the object store holding all roots' state |
| `192.168.30.146:3100` | `iac-drift.yml` only - the Loki push |

No new node on the containers VM and no port forward: the runner joins the
tailnet, reaches both over the subnet route, and the node is removed when the job
ends. Every job probes both endpoints before it runs `tofu`, so a missing grant
fails with the endpoint named instead of surfacing later as a bare `curl: (7)`.

### Dependabot

`.github/dependabot.yml` covers two things: the Actions SHAs in
`.github/workflows/`, and the provider constraints in both `iac/` roots. Weekly, on Monday
morning.

A Dependabot pull request runs with the **Dependabot** secret scope, not the Actions scope, which
is why every secret the plan job reads exists twice. A provider bump touches
`iac/cloudflare/versions.tf`, so the plan job runs and the bump is reviewed against a real plan.

Two things Dependabot does not do here. It updates the constraint, not the lock entry: run
`tofu init -upgrade` in the branch and commit the regenerated `.terraform.lock.hcl`. And it does not
touch `tofu_version` in the workflows or the image pins in the Ansible templates, which stay manual
because they are not manifests Dependabot reads.

### Drift

`iac-drift.yml` runs one matrix leg per root and pushes two streams per leg to
`http://192.168.30.146:3100/loki/api/v1/push`:

- `{job="tofu-drift", root="<root>", status="clean"|"drift"|"error"}`, with the
  run URL in the line
- `{job="tofu-drift", root="<root>", status="<same>", kind="plan"}`, with the plan

The run id is deliberately **not** a stream label: a per-run label would mint a
new stream every night. The URL travels in the summary line instead, and the plan
is selected by `root` and `status`.

Grafana holds both rules in the **IaC Drift** group
(`ansible/roles/monitoring_stack/templates/grafana-alerting-rules.yml.j2`):

- `alert-tofu-drift` - fires per root on a `status="drift"` line, and its
  description names the root, the command to run and the Loki query holding the
  plan
- `alert-tofu-drift-absent` - fires when fewer than two `status="clean"|"drift"`
  lines have arrived in 30 hours in total, one per root in the matrix. The number
  is the root count, so it has to be bumped when the drift matrix grows. A scheduled job that stopped running
  looks exactly like a job that keeps finding nothing, so silence alerts on its
  own. It counts only `clean` and `drift`, because an `error` line means nothing
  was verified: letting it count would silence the one alert that notices a broken
  job.

## Verifying by hand

The operator's resolver answers `*.lukapg.dev` with the **LAN** address
(AdGuard split-DNS), so a bare `curl https://ha.lukapg.dev` reaches Traefik and
not Cloudflare. Pin the edge when the question is about the edge:

```bash
E1=104.21.28.99   # lukapg.dev edge
E2=104.21.2.168   # tnz.social edge

# The crawler block, and its robots.txt carve-out
curl -s -o /dev/null -w '%{http_code}\n' --resolve ha.lukapg.dev:443:$E1 \
  -A 'ChatGPT-User' https://ha.lukapg.dev/            # 403
curl -s -o /dev/null -w '%{http_code}\n' --resolve ha.lukapg.dev:443:$E1 \
  -A 'ChatGPT-User' https://ha.lukapg.dev/robots.txt  # 200

# The bulk redirect
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  --resolve youtoobitch.tnz.social:443:$E2 https://youtoobitch.tnz.social/   # 301

# Access still gates ovis, and the audience it reports
curl -sI --resolve ovis.lukapg.dev:443:$E1 https://ovis.lukapg.dev/api/session

# The TLS floor: a handshake must fail, and openssl needs the legacy level to
# even attempt TLS 1.1
openssl s_client -tls1_1 -cipher 'DEFAULT@SECLEVEL=0' \
  -connect $E1:443 -servername ha.lukapg.dev </dev/null   # tlsv1 alert protocol version
```

`dig` against a public resolver is the right tool for records; `dig` on the
operator machine answers from AdGuard and will disagree for the admin names.

## Provider quirks worth knowing

Each of these cost a plan iteration, and each is why the tree looks the way it
does:

- **Inline Access policies cannot carry a session duration.** In 5.x the nested
  `policies` type on `cloudflare_zero_trust_access_application` has no
  `session_duration`, so an inline policy silently falls back to the app's
  duration. The 730h session lives on a `cloudflare_zero_trust_access_policy`
  resource, referenced from the app by id.
- **`landing_page_design` on the App Launcher** cannot be omitted (plans a
  removal) and cannot be `{}` (the provider fills in `title = "Welcome!"` and
  then plans an addition forever). The default is declared explicitly.
- **`connection_rules` on a reusable policy** carry clipboard formats
  `["text", "file"]` and the provider's schema only accepts `["text"]`, so the
  attribute cannot be declared at all; `ignore_changes = [connection_rules]`
  covers that one field.
- **`service_token_inactivity`** requires a concrete `action` and threshold even
  when `enabled = false`, and the API stores null for both while it is off.
  Omitting the block plans a change on every run.
- **`is_robots_txt_managed`** defaults to false in the provider and is true in
  the account. Leaving it undeclared plans a change that would hand `robots.txt`
  back to the origin - which would also disarm the `/robots.txt` carve-out in the
  crawler block.
- **Rule `ref` values** are Cloudflare's own identifiers (one of them is the
  literal `[CF AI Audit]`), are not settable, and are therefore not declared.
- **`trusted_accounts`** on the organization is rejected as read-only.

## The origin address is treated as public

The nine `lukapg.dev` A records point at one origin address, supplied as
`TF_VAR_lukapg_public_ipv4` from `iac/secrets.sops.yaml` and declared `sensitive`, so no plan,
comment or CI log prints it, and neither root's saved plan file carries it in the
clear (`plan {}` in both `encryption.tf`). That closes future leakage only: the address was
committed once in `afa4de7` ("feat(iac): import the lukapg.dev records"), which is not an
ancestor of `main` but is still reachable through a pull-request ref, and GitHub keeps those
permanently. It is published and is treated as known.

The accepted position is defence in depth rather than concealment. Only `ovis` carries the
`cloudflare-only` middleware, so a client that knows the address can send `Host: ha.lukapg.dev`
straight to Traefik and skip the geo challenge, Bot Fight Mode and the AI-crawler block. What still
stands in the way is CrowdSec on the Traefik access log, the per-route rate limits, and each
service's own authentication. Two alternatives were considered and deferred: putting
`cloudflare-only` on every public router, which breaks LAN access because AdGuard rewrites
`ha.lukapg.dev` and `grafana.lukapg.dev` to Traefik, and fronting the public routes with Cloudflare
Tunnel, which removes the inbound port entirely.

If the address is ever changed, only the SOPS value moves: the records are proxied, so nothing in
DNS changes.

## Recovery

- **Lost or corrupted state**: the committed `import` blocks re-adopt every
  object by id. Restore the previous state version from the versioned bucket
  first if there is one - that is faster and keeps resource addresses stable.
- **A bad apply**: revert the merge commit on `main`; `iac-apply.yml` applies the
  reverted tree. For a state that will not decrypt, restore the object version.
- **A dashboard edit that drifted**: it will appear as a difference in the next
  plan. Either correct the tree (a reviewed PR) or revert the dashboard change -
  the drift is the bug, not the alert.
- **An object deleted out of band while its resource is still in state**: the
  plan tries to create it and the retained `import` block fails first with
  "cannot import non-existent remote object", so the recreate never appears. Delete
  that one `import` block, apply the recreate, then put the block back. The blocks
  are insurance against a lost state, not a guarantee that every plan is a full
  description of intent.
