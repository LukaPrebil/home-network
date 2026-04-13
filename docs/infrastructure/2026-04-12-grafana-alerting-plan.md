# Grafana Alerting with Telegram — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 20 Grafana-managed alerts across host health, containers, Traefik, internet speed, CrowdSec, logs, and monitoring meta-health — all routed to Telegram via the existing Kuma bot.

**Architecture:** All alerting uses Grafana Unified Alerting (provisioned via YAML files under `/etc/grafana/provisioning/alerting/`). Alert rules query Prometheus and Loki datasources. No Alertmanager is needed — Grafana handles evaluation, routing, and notification natively. Telegram contact point reuses the existing bot; we just need the token and chat ID in Ansible vault.

**Tech Stack:** Grafana 12.4.1 provisioned alerting, PromQL, LogQL, Ansible (Jinja2 templates), Telegram Bot API

---

## Baseline Metrics (from Prometheus, 2026-04-12)

These inform threshold choices:

| Metric | Current values | Notes |
|---|---|---|
| CPU usage | 1-5% across all hosts | n5p (Proxmox) highest at ~3% |
| Memory usage | 4-72% | n5p at 72% (hypervisor), omada 45%, containers 40% |
| Disk usage (root) | 25-75% | containers at 75%, adguard 46%, immich 40% |
| Load5 | 0.1-0.54 | All low, max 2-4 cores per host |
| Traefik 5xx rate | 0 req/s | Total request rate ~0.14 req/s |
| Traefik request rate | ~0.14 req/s | Low traffic homelab |
| CrowdSec active decisions | ~45k total | 25k scans, 13k web attacks, 4k greenlisted, 2k tor |
| TLS cert expiry | ~32 days | Wildcard `*.lukapg.dev` |
| Prometheus TSDB | ~6 GB | On a 33.5 GB disk (32% used, 22 GB free) |
| Download speed | ~920-940 Mbps | T-2 Slovenia |
| Upload speed | ~310-314 Mbps | T-2 Slovenia |
| Ping latency | ~2.8 ms | |
| Jitter | ~0.3 ms | |

---

## File Structure

### New files to create

| File | Purpose |
|---|---|
| `templates/grafana-alerting-rules.yml.j2` | All 20 alert rule definitions (5 groups) |
| `templates/grafana-alerting-contact-points.yml.j2` | Telegram contact point config |
| `templates/grafana-alerting-notification-policies.yml.j2` | Routing: critical vs warning severity |
| `templates/grafana-alerting-templates.yml.j2` | Custom Telegram message templates |

### Existing files to modify

| File | Change |
|---|---|
| `defaults/main.yml` | Add Telegram variables |
| `templates/grafana-datasources.yml.j2` | Add explicit `uid:` to both datasources |
| `templates/docker-compose.yml.j2` | Pass Telegram env vars to Grafana container |
| `tasks/directories.yml` | Add `grafana/provisioning/alerting` directory |
| `tasks/config.yml` | Add tasks to deploy alerting YAML files |
| `ansible/secrets.yml` | Add `vault_grafana_telegram_bot_token` and `vault_grafana_telegram_chat_id` |

All files live under `ansible/roles/monitoring-stack/` unless noted otherwise.

---

## Chunk 1: Foundation (Secrets, Datasource UIDs, Directories, Alerting Templates)

### Task 1: Add Telegram secrets to Ansible vault

**Files:**
- Modify: `ansible/secrets.yml` (vault-encrypted)
- Modify: `ansible/roles/monitoring-stack/defaults/main.yml`

- [ ] **Step 1: Add vault variables for Telegram**

Add to `ansible/secrets.yml` (via `ansible-vault edit`):

```yaml
vault_grafana_telegram_bot_token: "<bot-token-from-user>"
vault_grafana_telegram_chat_id: "<chat-id-from-user>"
```

- [ ] **Step 2: Add role defaults for Telegram**

Append to `defaults/main.yml`:

```yaml
# Telegram alerting
grafana_telegram_bot_token: "{{ vault_grafana_telegram_bot_token }}"
grafana_telegram_chat_id: "{{ vault_grafana_telegram_chat_id }}"
```

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/monitoring-stack/defaults/main.yml
git commit -m "feat(monitoring): add Telegram alerting variables"
```

Note: `secrets.yml` changes are committed separately since vault-encrypted diffs are noisy.

---

### Task 2: Add explicit UIDs to Grafana datasources

**Files:**
- Modify: `ansible/roles/monitoring-stack/templates/grafana-datasources.yml.j2`

Alert rules reference datasources by UID. Without explicit UIDs, Grafana auto-generates them and they change on re-provision.

- [ ] **Step 1: Add uid fields to both datasources**

```yaml
datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus
    access: proxy
    url: http://prometheus:{{ prometheus_port }}
    isDefault: true
    editable: false
    jsonData:
      timeInterval: 15s
      httpMethod: POST

  - name: Loki
    type: loki
    uid: loki
    access: proxy
    url: http://loki:{{ loki_port }}
    isDefault: false
    editable: false
    jsonData:
      maxLines: 1000
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/monitoring-stack/templates/grafana-datasources.yml.j2
git commit -m "feat(monitoring): add explicit UIDs to Grafana datasources"
```

---

### Task 3: Add alerting provisioning directory

**Files:**
- Modify: `ansible/roles/monitoring-stack/tasks/directories.yml`

- [ ] **Step 1: Add alerting directory to both LXC and local paths**

Add `grafana/provisioning/alerting` to the LXC directory loop (after `grafana/provisioning/dashboards/definitions`):

```yaml
    - grafana/provisioning/alerting
```

Add `{{ grafana_data_dir }}/provisioning/alerting` to the local (VM) directory loop:

```yaml
    - "{{ grafana_data_dir }}/provisioning/alerting"
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/monitoring-stack/tasks/directories.yml
git commit -m "feat(monitoring): add Grafana alerting provisioning directory"
```

---

### Task 4: Docker Compose — no changes needed

Since the contact-points file is a Jinja2 template (`.j2`), Ansible renders the Telegram bot token and chat ID directly into the YAML at deploy time. No need to pass env vars to the Grafana container — secrets are baked into the provisioning file on the remote host (not checked into git, since only the template is in the repo).

---

### Task 5: Create Telegram message template

**Files:**
- Create: `ansible/roles/monitoring-stack/templates/grafana-alerting-templates.yml.j2`

- [ ] **Step 1: Write the message template**

```yaml
{% raw %}
---
# Grafana alerting message templates
# Managed by Ansible - do not edit manually

apiVersion: 1

templates:
  - orgId: 1
    name: telegram-homelab
    template: |
      {{ define "telegram.title" -}}
      {{ if gt (len .Alerts.Firing) 0 }}🔴 {{ len .Alerts.Firing }} firing{{ end }}
      {{- if gt (len .Alerts.Resolved) 0 }}{{ if gt (len .Alerts.Firing) 0 }}, {{ end }}🟢 {{ len .Alerts.Resolved }} resolved{{ end }}
      {{- end }}

      {{ define "telegram.message" -}}
      {{ range .Alerts.Firing -}}
      <b>🔴 {{ .Labels.alertname }}</b>
      {{ if .Annotations.summary }}{{ .Annotations.summary }}{{ end }}
      {{ if .Annotations.description }}{{ .Annotations.description }}{{ end }}
      Severity: {{ .Labels.severity }}
      {{ end -}}
      {{ range .Alerts.Resolved -}}
      <b>🟢 {{ .Labels.alertname }}</b>
      {{ if .Annotations.summary }}{{ .Annotations.summary }}{{ end }}
      {{ end -}}
      {{ end }}
{% endraw %}
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/monitoring-stack/templates/grafana-alerting-templates.yml.j2
git commit -m "feat(monitoring): add Telegram message template for Grafana alerting"
```

---

### Task 6: Create Telegram contact point

**Files:**
- Create: `ansible/roles/monitoring-stack/templates/grafana-alerting-contact-points.yml.j2`

- [ ] **Step 1: Write the contact point config**

```yaml
---
# Grafana alerting contact points
# Managed by Ansible - do not edit manually

apiVersion: 1

contactPoints:
  - orgId: 1
    name: Telegram
    receivers:
      - uid: telegram-homelab
        type: telegram
        settings:
          botToken: "{{ grafana_telegram_bot_token }}"
          chatId: "{{ grafana_telegram_chat_id }}"
          parseMode: HTML
{% raw %}
          message: |
            {{ template "telegram.title" . }}
            {{ template "telegram.message" . }}
{% endraw %}
        disableResolveMessage: false
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/monitoring-stack/templates/grafana-alerting-contact-points.yml.j2
git commit -m "feat(monitoring): add Telegram contact point for Grafana alerting"
```

---

### Task 7: Create notification policies

**Files:**
- Create: `ansible/roles/monitoring-stack/templates/grafana-alerting-notification-policies.yml.j2`

- [ ] **Step 1: Write the notification policy**

```yaml
---
# Grafana alerting notification policies
# Managed by Ansible - do not edit manually

apiVersion: 1

policies:
  - orgId: 1
    receiver: Telegram
    group_by:
      - grafana_folder
      - alertname
    group_wait: 30s
    group_interval: 5m
    repeat_interval: 4h
    routes:
      # Critical alerts: notify immediately, repeat every hour
      - receiver: Telegram
        matchers:
          - severity = critical
        group_wait: 10s
        repeat_interval: 1h
        continue: false
      # Warning alerts: batch, repeat every 6 hours
      - receiver: Telegram
        matchers:
          - severity = warning
        group_wait: 1m
        repeat_interval: 6h
        continue: false
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/monitoring-stack/templates/grafana-alerting-notification-policies.yml.j2
git commit -m "feat(monitoring): add notification policies for Grafana alerting"
```

---

### Task 8: Add config deployment tasks

**Files:**
- Modify: `ansible/roles/monitoring-stack/tasks/config.yml`

- [ ] **Step 1: Add alerting deployment tasks**

Add after the Docker Compose deployment task (end of file):

```yaml
- name: Deploy Grafana alerting message templates
  ansible.builtin.template:
    src: grafana-alerting-templates.yml.j2
    dest: "{{ grafana_data_dir }}/provisioning/alerting/templates.yml"
    mode: '0644'
  notify: Restart Monitoring Stack
  tags:
    - monitoring-stack
    - config
    - grafana
    - alerting

- name: Deploy Grafana alerting contact points
  ansible.builtin.template:
    src: grafana-alerting-contact-points.yml.j2
    dest: "{{ grafana_data_dir }}/provisioning/alerting/contact-points.yml"
    mode: '0644'
  notify: Restart Monitoring Stack
  tags:
    - monitoring-stack
    - config
    - grafana
    - alerting

- name: Deploy Grafana alerting notification policies
  ansible.builtin.template:
    src: grafana-alerting-notification-policies.yml.j2
    dest: "{{ grafana_data_dir }}/provisioning/alerting/notification-policies.yml"
    mode: '0644'
  notify: Restart Monitoring Stack
  tags:
    - monitoring-stack
    - config
    - grafana
    - alerting

- name: Deploy Grafana alerting rules
  ansible.builtin.template:
    src: grafana-alerting-rules.yml.j2
    dest: "{{ grafana_data_dir }}/provisioning/alerting/rules.yml"
    mode: '0644'
  notify: Restart Monitoring Stack
  tags:
    - monitoring-stack
    - config
    - grafana
    - alerting
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/monitoring-stack/tasks/config.yml
git commit -m "feat(monitoring): add Ansible tasks for alerting provisioning"
```

---

## Chunk 2: Alert Rules — Host Health & Proxmox

### Task 9: Write host health and Proxmox alert rules

**Files:**
- Create: `ansible/roles/monitoring-stack/templates/grafana-alerting-rules.yml.j2`

This task creates the rules file with the first two groups. Subsequent tasks append more groups.

- [ ] **Step 1: Create rules file with host health alerts**

```yaml
---
# Grafana alerting rules
# Managed by Ansible - do not edit manually

apiVersion: 1

groups:
  # ============================================================
  # Host Health (node-exporter metrics)
  # ============================================================
  - orgId: 1
    name: Host Health
    folder: Alerts
    interval: 1m
    rules:

      # 1. High CPU usage — > 85% for 5 min
      - uid: alert-high-cpu
        title: High CPU Usage
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle",job="node-exporter"}[5m])) * 100)
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 85
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: NoData
        execErrState: Error
        for: 5m
        annotations:
          summary: "CPU usage above 85% on {{ '{{' }} $labels.instance {{ '}}' }}"
          description: "CPU usage has been above 85% for 5 minutes on {{ '{{' }} $labels.instance {{ '}}' }}."
        labels:
          severity: warning

      # 2. High memory usage — available < 10% for 5 min
      - uid: alert-high-memory
        title: High Memory Usage
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: (1 - (node_memory_MemAvailable_bytes{job="node-exporter"} / node_memory_MemTotal_bytes{job="node-exporter"})) * 100
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 90
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: NoData
        execErrState: Error
        for: 5m
        annotations:
          summary: "Memory usage above 90% on {{ '{{' }} $labels.instance {{ '}}' }}"
          description: "Available memory is below 10% on {{ '{{' }} $labels.instance {{ '}}' }}."
        labels:
          severity: warning

      # 3. Disk space low — warning >85%, critical >95%
      - uid: alert-disk-warning
        title: Disk Space Low (Warning)
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: (1 - node_filesystem_avail_bytes{job="node-exporter",mountpoint="/",fstype!="tmpfs"} / node_filesystem_size_bytes{job="node-exporter",mountpoint="/",fstype!="tmpfs"}) * 100
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 85
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: NoData
        execErrState: Error
        for: 5m
        annotations:
          summary: "Disk usage above 85% on {{ '{{' }} $labels.instance {{ '}}' }}"
          description: "Root filesystem is {{ '{{' }} $values.B.Value {{ '}}' }}% full on {{ '{{' }} $labels.instance {{ '}}' }}."
        labels:
          severity: warning

      - uid: alert-disk-critical
        title: Disk Space Low (Critical)
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: (1 - node_filesystem_avail_bytes{job="node-exporter",mountpoint="/",fstype!="tmpfs"} / node_filesystem_size_bytes{job="node-exporter",mountpoint="/",fstype!="tmpfs"}) * 100
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 95
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: NoData
        execErrState: Error
        for: 5m
        annotations:
          summary: "CRITICAL: Disk usage above 95% on {{ '{{' }} $labels.instance {{ '}}' }}"
          description: "Root filesystem is {{ '{{' }} $values.B.Value {{ '}}' }}% full on {{ '{{' }} $labels.instance {{ '}}' }}. Immediate action required."
        labels:
          severity: critical

      # 4. System load high — load5 > CPU count for 10 min
      - uid: alert-high-load
        title: High System Load
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 600
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: node_load5{job="node-exporter"} / count without(cpu, mode) (node_cpu_seconds_total{job="node-exporter",mode="idle"})
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 1
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: NoData
        execErrState: Error
        for: 10m
        annotations:
          summary: "System load high on {{ '{{' }} $labels.instance {{ '}}' }}"
          description: "Load average (5m) exceeds CPU count on {{ '{{' }} $labels.instance {{ '}}' }} for over 10 minutes."
        labels:
          severity: warning

  # ============================================================
  # Proxmox Hypervisor
  # ============================================================
  - orgId: 1
    name: Proxmox
    folder: Alerts
    interval: 1m
    rules:

      # 5. Proxmox host high CPU — type="proxmox" label from prometheus config
      - uid: alert-proxmox-cpu
        title: Proxmox Host High CPU
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle",job="node-exporter",type="proxmox"}[5m])) * 100)
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 80
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: NoData
        execErrState: Error
        for: 5m
        annotations:
          summary: "Proxmox host CPU above 80%"
          description: "n5p hypervisor CPU usage is above 80% for 5 minutes. Check VM/LXC resource allocation."
        labels:
          severity: critical

  # ============================================================
  # Docker Containers (cAdvisor metrics)
  # ============================================================
  - orgId: 1
    name: Docker Containers
    folder: Alerts
    interval: 1m
    rules:

      # 6. Container restart loop — > 3 restarts in 15 min
      # Uses changes() on container start time to count restarts
      - uid: alert-container-restart
        title: Container Restart Loop
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 900
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: changes(container_start_time_seconds{job="cadvisor",container!="",container!="POD"}[15m])
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 0
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "Container {{ '{{' }} $labels.container {{ '}}' }} is in a restart loop"
          description: "Container {{ '{{' }} $labels.container {{ '}}' }} has restarted more than 3 times in the last 15 minutes."
        labels:
          severity: critical

      # 7. Container high memory — > 90% of its limit
      - uid: alert-container-memory
        title: Container High Memory
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: (container_memory_working_set_bytes{job="cadvisor",container!="",container!="POD"} / container_spec_memory_limit_bytes{job="cadvisor",container!="",container!="POD"} * 100) and container_spec_memory_limit_bytes{job="cadvisor",container!="",container!="POD"} > 0
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 90
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 5m
        annotations:
          summary: "Container {{ '{{' }} $labels.container {{ '}}' }} memory above 90%"
          description: "Container {{ '{{' }} $labels.container {{ '}}' }} is using more than 90% of its memory limit."
        labels:
          severity: warning

      # 8. Container OOM events
      - uid: alert-container-oom
        title: Container OOM Kill
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: increase(container_oom_events_total{job="cadvisor",container!="",container!="POD"}[5m])
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 0
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "OOM kill in container {{ '{{' }} $labels.container {{ '}}' }}"
          description: "Container {{ '{{' }} $labels.container {{ '}}' }} experienced an OOM kill event."
        labels:
          severity: critical

  # ============================================================
  # Traefik & Network
  # ============================================================
  - orgId: 1
    name: Traefik & Network
    folder: Alerts
    interval: 1m
    rules:

      # 9. High 5xx error rate — any 5xx errors (low traffic homelab, any 5xx is notable)
      - uid: alert-traefik-5xx
        title: Traefik 5xx Errors
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: sum(increase(traefik_service_requests_total{code=~"5.."}[5m])) by (service)
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 5
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 5m
        annotations:
          summary: "Traefik 5xx errors on {{ '{{' }} $labels.service {{ '}}' }}"
          description: "Service {{ '{{' }} $labels.service {{ '}}' }} returned more than 5 server errors in the last 5 minutes."
        labels:
          severity: warning

      # 10. Service latency degraded — p95 > 2s
      - uid: alert-traefik-latency
        title: Traefik High Latency
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: histogram_quantile(0.95, sum(rate(traefik_service_request_duration_seconds_bucket[5m])) by (le, service))
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 2
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 5m
        annotations:
          summary: "High latency on {{ '{{' }} $labels.service {{ '}}' }}"
          description: "Service {{ '{{' }} $labels.service {{ '}}' }} p95 latency exceeds 2 seconds."
        labels:
          severity: warning

      # 11. TLS certificate expiring — < 14 days
      - uid: alert-tls-expiry
        title: TLS Certificate Expiring Soon
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: (traefik_tls_certs_not_after - time()) / 86400
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 14
                    type: lt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: NoData
        execErrState: Error
        for: 1h
        annotations:
          summary: "TLS certificate expiring in {{ '{{' }} $values.B.Value {{ '}}' }} days"
          description: "Certificate for {{ '{{' }} $labels.sans {{ '}}' }} expires in less than 14 days. Check Let's Encrypt renewal."
        labels:
          severity: critical

      # 12. Internet speed degraded — download < 800 Mbps
      - uid: alert-speed-download
        title: Internet Download Speed Degraded
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 7200
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: speedtest_download_bytes{job="speedtest"} / 125000
              instant: false
              intervalMs: 60000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 800
                    type: lt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "Download speed below 800 Mbps"
          description: "Internet download speed is {{ '{{' }} $values.B.Value {{ '}}' }} Mbps (threshold: 800 Mbps)."
        labels:
          severity: warning

      # 13. Internet speed degraded — upload < 200 Mbps
      - uid: alert-speed-upload
        title: Internet Upload Speed Degraded
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 7200
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: speedtest_upload_bytes{job="speedtest"} / 125000
              instant: false
              intervalMs: 60000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 200
                    type: lt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "Upload speed below 200 Mbps"
          description: "Internet upload speed is {{ '{{' }} $values.B.Value {{ '}}' }} Mbps (threshold: 200 Mbps)."
        labels:
          severity: warning

      # 14. High latency — ping > 80ms sustained
      - uid: alert-speed-latency
        title: Internet High Latency
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 7200
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: speedtest_latency_seconds{job="speedtest"} * 1000
              instant: false
              intervalMs: 60000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 80
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "Internet latency above 80ms"
          description: "Ping latency is {{ '{{' }} $values.B.Value {{ '}}' }}ms (threshold: 80ms)."
        labels:
          severity: warning

  # ============================================================
  # CrowdSec Security
  # ============================================================
  - orgId: 1
    name: CrowdSec Security
    folder: Alerts
    interval: 2m
    rules:

      # 15. Spike in blocked IPs — large increase in active decisions
      - uid: alert-crowdsec-decisions
        title: CrowdSec Decision Spike
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 3600
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: sum(increase(cs_active_decisions[1h]))
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 500
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "CrowdSec blocked IP spike"
          description: "More than 500 new decisions added in the last hour. Possible targeted attack."
        labels:
          severity: warning

      # 16. Bucket overflow surge — unusual scenario triggers
      - uid: alert-crowdsec-overflow
        title: CrowdSec Scenario Overflow Surge
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 3600
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: sum(increase(cs_bucket_overflowed_total[1h]))
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 100
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "CrowdSec bucket overflow surge"
          description: "More than 100 scenario overflows in the last hour. Review CrowdSec dashboard for attack patterns."
        labels:
          severity: warning

  # ============================================================
  # Loki Log-Based Alerts
  # ============================================================
  - orgId: 1
    name: Log Alerts
    folder: Alerts
    interval: 2m
    rules:

      # 17. Error log spike — high rate of error-level logs
      - uid: alert-log-errors
        title: Error Log Spike
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 600
              to: 0
            datasourceUid: loki
            model:
              refId: A
              expr: sum by (hostname) (count_over_time({job=~"system|docker"} |~ "(?i)(error|err|fatal|panic|critical)" !~ "(?i)(404|no error)" [5m]))
              instant: false
              intervalMs: 60000
              maxDataPoints: 43200
              queryType: range
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 50
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "Error log spike on {{ '{{' }} $labels.hostname {{ '}}' }}"
          description: "More than 50 error-level log lines in 5 minutes on {{ '{{' }} $labels.hostname {{ '}}' }}."
        labels:
          severity: warning

      # 18. Service crash patterns — OOM, segfault, panic
      - uid: alert-log-crash
        title: Service Crash Detected
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 600
              to: 0
            datasourceUid: loki
            model:
              refId: A
              expr: sum by (hostname) (count_over_time({job=~"system|docker"} |~ "(?i)(out of memory|oom-kill|segfault|panic:|killed process)" [5m]))
              instant: false
              intervalMs: 60000
              maxDataPoints: 43200
              queryType: range
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 0
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "Crash detected on {{ '{{' }} $labels.hostname {{ '}}' }}"
          description: "OOM kill, segfault, or panic detected in logs on {{ '{{' }} $labels.hostname {{ '}}' }}."
        labels:
          severity: critical

      # 19. Auth failure spike — brute force indicator
      - uid: alert-log-auth
        title: Authentication Failure Spike
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 600
              to: 0
            datasourceUid: loki
            model:
              refId: A
              expr: sum by (hostname) (count_over_time({job="system"} |~ "(?i)(failed password|authentication failure|invalid user|refused connect)" [5m]))
              instant: false
              intervalMs: 60000
              maxDataPoints: 43200
              queryType: range
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 10
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "Auth failure spike on {{ '{{' }} $labels.hostname {{ '}}' }}"
          description: "More than 10 authentication failures in 5 minutes on {{ '{{' }} $labels.hostname {{ '}}' }}. Possible brute force attack."
        labels:
          severity: warning

  # ============================================================
  # Monitoring Meta-Health
  # ============================================================
  - orgId: 1
    name: Monitoring Health
    folder: Alerts
    interval: 5m
    rules:

      # 20. Prometheus storage filling — > 80% of monitoring disk used
      - uid: alert-prometheus-storage
        title: Prometheus Storage Filling
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              refId: A
              expr: (1 - node_filesystem_avail_bytes{instance="monitoring",mountpoint="/"} / node_filesystem_size_bytes{instance="monitoring",mountpoint="/"}) * 100
              instant: false
              intervalMs: 15000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 80
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: NoData
        execErrState: Error
        for: 10m
        annotations:
          summary: "Monitoring disk usage above 80%"
          description: "The monitoring LXC root filesystem is {{ '{{' }} $values.B.Value {{ '}}' }}% full. Prometheus and Loki data may need pruning."
        labels:
          severity: warning

      # 21. Loki ingestion errors (query Loki's own metrics via Prometheus if exposed)
      # Note: Loki exposes internal metrics at :3100/metrics which Prometheus could scrape.
      # For now, we monitor via log-based detection of Loki errors.
      - uid: alert-loki-errors
        title: Loki Ingestion Errors
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 600
              to: 0
            datasourceUid: loki
            model:
              refId: A
              expr: sum(count_over_time({container="loki"} |~ "(?i)(error|failed to flush|context deadline exceeded)" [5m]))
              instant: false
              intervalMs: 60000
              maxDataPoints: 43200
              queryType: range
          - refId: B
            datasourceUid: "__expr__"
            model:
              refId: B
              type: reduce
              expression: A
              reducer: last
              settings:
                mode: dropNN
          - refId: C
            datasourceUid: "__expr__"
            model:
              refId: C
              type: threshold
              expression: B
              conditions:
                - evaluator:
                    params:
                      - 10
                    type: gt
                  operator:
                    type: and
                  query:
                    params:
                      - B
                  reducer:
                    params: []
                    type: last
        noDataState: OK
        execErrState: Error
        for: 0s
        annotations:
          summary: "Loki ingestion errors detected"
          description: "More than 10 error log lines from Loki container in 5 minutes. Log pipeline may be degraded."
        labels:
          severity: warning
```

Note on Jinja2 escaping: Grafana alert annotations use `{{ }}` template syntax which conflicts with Ansible's Jinja2. We escape them as `{{ '{{' }}` and `{{ '}}' }}` in the `.j2` template so Ansible renders them as literal `{{ }}` for Grafana.

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/monitoring-stack/templates/grafana-alerting-rules.yml.j2
git commit -m "feat(monitoring): add 20 Grafana alert rules across all categories"
```

---

## Chunk 3: Deploy and Verify

### Task 10: Add vault secrets and deploy

- [ ] **Step 1: Get Telegram bot token and chat ID from user**

The user has an existing Telegram bot from Uptime Kuma. Need:
- Bot token (from @BotFather)
- Chat ID (personal or group)

- [ ] **Step 2: Add secrets to vault**

```bash
cd ansible
ansible-vault edit secrets.yml
```

Add:
```yaml
vault_grafana_telegram_bot_token: "<token>"
vault_grafana_telegram_chat_id: "<chat_id>"
```

- [ ] **Step 3: Commit vault changes**

```bash
git add ansible/secrets.yml
git commit -m "feat(monitoring): add Telegram bot secrets to vault"
```

- [ ] **Step 4: Deploy with Ansible**

```bash
ansible-playbook site.yml --tags monitoring-stack --limit monitoring
```

- [ ] **Step 5: Verify Grafana starts and loads alerting config**

Check Grafana health:
```bash
curl -s http://192.168.1.146:3000/api/health | jq '.'
```

Check provisioned alert rules via Grafana API:
```bash
curl -s -u admin:<password> http://192.168.1.146:3000/api/v1/provisioning/alert-rules | jq '.[].title'
```

Check contact points:
```bash
curl -s -u admin:<password> http://192.168.1.146:3000/api/v1/provisioning/contact-points | jq '.[].name'
```

- [ ] **Step 6: Test Telegram notification**

Use the Grafana UI: Alerting → Contact Points → Telegram → Test. Verify the message arrives in Telegram.

- [ ] **Step 7: Verify alert evaluation**

In Grafana UI: Alerting → Alert Rules. Check that:
- All 20 rules appear across 6 groups
- Rules show "Normal" state (green) for healthy metrics
- No rules show "Error" state (query issues)

---

## Alert Summary Table

| # | UID | Title | Query Source | Threshold | For | Severity |
|---|---|---|---|---|---|---|
| 1 | alert-high-cpu | High CPU Usage | Prometheus | > 85% | 5m | warning |
| 2 | alert-high-memory | High Memory Usage | Prometheus | > 90% | 5m | warning |
| 3 | alert-disk-warning | Disk Space Low (Warning) | Prometheus | > 85% | 5m | warning |
| 4 | alert-disk-critical | Disk Space Low (Critical) | Prometheus | > 95% | 5m | critical |
| 5 | alert-high-load | High System Load | Prometheus | load5/cores > 1 | 10m | warning |
| 6 | alert-proxmox-cpu | Proxmox Host High CPU | Prometheus | > 80% | 5m | critical |
| 7 | alert-container-restart | Container Restart Loop | Prometheus | > 3 in 15m | 0s | critical |
| 8 | alert-container-memory | Container High Memory | Prometheus | > 90% limit | 5m | warning |
| 9 | alert-container-oom | Container OOM Kill | Prometheus | any event | 0s | critical |
| 10 | alert-traefik-5xx | Traefik 5xx Errors | Prometheus | > 5 in 5m | 5m | warning |
| 11 | alert-traefik-latency | Traefik High Latency | Prometheus | p95 > 2s | 5m | warning |
| 12 | alert-tls-expiry | TLS Certificate Expiring | Prometheus | < 14 days | 1h | critical |
| 13 | alert-speed-download | Download Speed Degraded | Prometheus | < 800 Mbps | 0s | warning |
| 14 | alert-speed-upload | Upload Speed Degraded | Prometheus | < 200 Mbps | 0s | warning |
| 15 | alert-speed-latency | Internet High Latency | Prometheus | > 80ms | 0s | warning |
| 16 | alert-crowdsec-decisions | CrowdSec Decision Spike | Prometheus | > 500/hr | 0s | warning |
| 17 | alert-crowdsec-overflow | CrowdSec Overflow Surge | Prometheus | > 100/hr | 0s | warning |
| 18 | alert-log-errors | Error Log Spike | Loki | > 50 in 5m | 0s | warning |
| 19 | alert-log-crash | Service Crash Detected | Loki | any event | 0s | critical |
| 20 | alert-log-auth | Auth Failure Spike | Loki | > 10 in 5m | 0s | warning |
| — | alert-prometheus-storage | Prometheus Storage Filling | Prometheus | > 80% disk | 10m | warning |
| — | alert-loki-errors | Loki Ingestion Errors | Loki | > 10 in 5m | 0s | warning |

Note: 22 rules total. Disk has both warning (85%) and critical (95%) thresholds. Container CPU throttling was replaced with OOM detection since `container_oom_events_total` is a directly actionable metric. The speedtest metric names (`speedtest_download_bytes`, `speedtest_upload_bytes`) match the billimek exporter in use — confirmed from the dashboard which shows data in Mbps using the same `/125000` conversion.

---

## Decisions & Trade-offs

1. **Grafana Unified Alerting over Alertmanager**: Simpler setup, no extra container, native Loki support. Trade-off: less flexible routing than Alertmanager, but sufficient for a single Telegram destination.

2. **Provisioned YAML over API**: Alerts are version-controlled in git and deployed via Ansible. Trade-off: can't edit alerts in Grafana UI (read-only), but that's intentional for infrastructure-as-code.

3. **OOM events instead of CPU throttling**: `container_oom_events_total` is directly actionable (a container was killed). CPU pressure metrics (`container_pressure_cpu_*`) are harder to threshold meaningfully on a low-traffic homelab.

4. **Jinja2 escaping for Grafana templates**: Grafana annotation templates use `{{ }}` which conflicts with Ansible. The `{{ '{{' }}` escape pattern is verbose but reliable.

5. **Speedtest `for: 0s`**: Speedtest runs every 30 minutes. Any degraded reading is worth flagging immediately since the next data point is 30 minutes away.

6. **CrowdSec thresholds (500 decisions/hr, 100 overflows/hr)**: Conservative starting points. With 45k existing active decisions, the baseline rate is significant. These may need tuning after observing normal churn.

7. **Loki alert `noDataState: OK`**: Log queries may return zero results (no matching log lines) which is healthy. Setting `NoData → OK` prevents false alerts when there are simply no errors to find.
