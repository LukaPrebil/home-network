# Homelab Observability Stack

## Overview

The monitoring and logging stack runs on the `monitoring` LXC (192.168.1.146), deployed via Docker Compose and managed by the `monitoring-stack` Ansible role.

**Components:**
- **Grafana** - visualization dashboards (port 3000, exposed via Traefik)
- **Prometheus** - metrics database (port 9090, 30-day retention)
- **Loki** - log aggregation database (port 3100, 30-day retention)
- **cAdvisor** - Docker container metrics (port 8080)
- **Proxmox Exporter** - pulls metrics from the Proxmox API (port 9221)
- **Omada Exporter** - pulls metrics from the Omada Controller API (port 9202)
- **Speedtest Exporter** - Ookla bandwidth tests at 30-minute intervals (port 9469)

**Volumes:** persistent data stored under `/srv/docker/` (grafana, prometheus, loki).

---

## Prometheus Scrape Targets

Configured via Ansible template (`prometheus.yml.j2`). All API keys/passwords sourced from Ansible Vault.

| Target | Exporter | Deployed On | Scrape Endpoint |
| :--- | :--- | :--- | :--- |
| Proxmox Host (`n5p`) | `prometheus-pve-exporter` | monitoring LXC (Docker) | `proxmox-exporter:9221` |
| All Linux Hosts | `node_exporter` | Each target host (native binary) | `<host_ip>:9100` |
| Loki | Built-in | monitoring LXC (Docker) | `loki:3100` |
| Containers on the monitoring LXC only | `cAdvisor` | monitoring LXC (Docker) | `cadvisor:8080` |
| Omada Controller | `omada_exporter` | monitoring LXC (Docker) | `omada-exporter:9202` |
| Traefik Proxy | Built-in | traefik LXC | `<traefik_ip>:8082` |
| Grafana Alloy agents | Built-in | Each target host (native binary) | `<host_ip>:12345` |
| Internet Bandwidth | `speedtest-exporter` | monitoring LXC (Docker) | `speedtest-exporter:9469` |
| TrueNAS (`tn-storage`) | Built-in | TrueNAS (enable in UI) | *Not yet enabled* |

**Note:** `node_exporter` targets are dynamically generated from the `monitoring_agents` inventory group via Jinja2 templating.

### Proxmox exporter credentials

The exporter authenticates as the `root@pam!monitoring` API token. The token is created with
`privsep=1`, which means it inherits nothing from `root@pam` and holds no permissions until it
is granted an ACL of its own. Without one, every scrape returns
`403 Permission check failed (/, Sys.Audit)` and `pve_up` is simply absent, which reads like a
healthy fleet rather than a broken exporter.

The `proxmox` role grants that ACL (`roles/proxmox/tasks/monitoring_acl.yml`, tag
`monitoring-acl`): `PVEAuditor` on `/`, propagating. It is idempotent, and reports what is
missing instead of failing the play when the token itself is absent.

The token cannot be created by Ansible. Proxmox generates its secret once and never shows it
again, so a rebuilt hypervisor needs the token recreated by hand and the new secret written to
`vault_proxmox_api_token_secret` before the ACL grant has anything to attach to:

```bash
pveum user token add root@pam monitoring --privsep 1
ansible-playbook site.yml --tags monitoring-acl --limit n5p
```

---

## Log Aggregation (Loki + Alloy)

Log collection is handled by **Grafana Alloy** (native binary), deployed via the `alloy` Ansible role on all hosts in the `monitoring_agents` group.

Alloy replaced the originally planned `promtail` agent. It ships logs to Loki and also exposes its own metrics for Prometheus scraping on port 12345.

### What gets shipped

Two sources, both landing in Loki:

| Source | Loki labels | Applies to |
| :--- | :--- | :--- |
| systemd journal | `job="system"`, `hostname`, `unit` | every `monitoring_agents` host |
| Docker container stdout/stderr | `job="docker"`, `hostname`, `container`, `stream` | hosts where Alloy detects a Docker engine |

Host logs come from journald, not from `/var/log/syslog`. Debian 13 ships no rsyslog, so that file
never existed on n5p or rpi4 and the file source shipped nothing from either for the whole of
Loki's retention while reporting healthy. journald needs no package and exists everywhere, which
removes the failure mode rather than papering over it. Alloy runs as root here, so it needs no
`adm` / `systemd-journal` group membership.

Alloy drops every `__journal_*` label before forwarding, so the `unit` label is promoted explicitly
by a `loki.relabel` component. Without it there is no way to tell which service produced a line.

Do not rewrite the log alerts to filter on journald `PRIORITY`. Every line on this fleet is
`PRIORITY=6`: services log to stdout and their units carry `StandardOutput=journal`, so systemd
stamps everything info regardless of the application's own `[error]` marker. A severity-based rule
would match nothing and look permanently healthy. The text regex is load-bearing.

The `container` label has Docker's leading slash stripped, so it reads `immich_server` rather than
`/immich_server`.

`loki.source.docker` tails only the targets it is handed and discovers nothing by itself. It is fed
by a `discovery.docker` component; without one it starts cleanly, reports healthy, and ships zero
lines. Container log shipping was broken exactly that way until 2026-08-22, which is why a service
could crash repeatedly with no trace anywhere outside the container's own log.

### Proving a host actually ships

A source with an empty target list is a valid config: the component reports healthy, `/ready`
answers 200, and the alerts reading its stream simply go quiet, which looks exactly like a healthy
host. Liveness cannot detect it. Ask the source to account for its throughput instead.

Two guards do that, added 2026-08-25 after n5p and rpi4 were found to have shipped nothing for a
full 30-day retention window while every signal read green:

- The `alloy` role fails the converge unless `loki_source_journal_target_lines_total` is present
  and non-zero on the host it just configured.
- The `Host Log Shipping Stopped` alert fires when a host reads no journal lines in 2 hours. Its
  expression carries an `or` arm because the counter *disappearing* leaves an absent series rather
  than a zero one, which a plain `== 0` would never match.

To check by hand: `curl -s localhost:12345/metrics | grep loki_source_journal`.

### Alerting on log content

Loki and Grafana log the text of every query they serve, so their own container logs contain
whatever keywords a log-content alert searches for, including that alert's own evaluation. Any rule
matching on log text must exclude the `loki` and `grafana` containers or it will fire on itself.
Filtering the offending log lines by marker is not durable: Loki emits query text from
`metrics.go`, `engine.go` and `roundtrip.go`, and that set changes between versions.

For the same reason, the error-spike rule is scoped to `job="system"` only. Its threshold is
calibrated for host logs, and container logs carry routine application chatter where the word
"error" is normal.

**Loki's own health cannot be judged from its logs at all.** Excluding the `loki` container works
for rules that are about something else, but not for a rule about Loki. A log rule on
`{container="loki"}` matches the echo of its own evaluation and flaps indefinitely, and this holds
even for a rule searching the literal string `level=error`, because the query text containing it is
echoed on an otherwise ordinary `level=info` line. Loki's health is therefore taken from its
metrics: Prometheus scrapes `loki:3100` and the ingestion alert reads
`loki_request_duration_seconds_count{route="loki_api_v1_push"}`, firing on sustained non-2xx
responses. Judge any component that logs the queries it serves by its metrics, not its logs.

---

## Grafana

The Grafana instance is auto-provisioned by the Ansible role with:

**Data Sources** (provisioned via YAML templates):
- Prometheus
- Loki

**Dashboards:**
- **Host Monitoring**: Node Exporter Full (ID `1860`) for all Linux hosts
- **Proxmox**: Proxmox VE dashboard (ID `10347`)
- **Docker**: cAdvisor metrics dashboard
- **Network**: Omada Exporter dashboard
- **Logs**: Loki log exploration dashboard

---

## Ansible Roles

| Role | Target Hosts | Description |
|------|-------------|-------------|
| `monitoring-stack` | `monitoring` LXC | Core Docker stack (Grafana, Prometheus, Loki, cAdvisor, exporters) |
| `node-exporter` | All `monitoring_agents` | Native binary install of `node_exporter` - no Docker |
| `alloy` | All `monitoring_agents` | Native binary install of Grafana Alloy log/metrics agent |
