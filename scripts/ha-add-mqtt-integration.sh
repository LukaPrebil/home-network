#!/usr/bin/env bash
#
# Add the MQTT integration to Home Assistant, driving the same config flow the
# UI does, with the broker password read straight from sops.
#
# HAOS is not Ansible-managed, so this step cannot live in a role. Keeping it as
# a script means the integration's settings are at least reproducible, and the
# password never has to be typed or pasted anywhere.
#
# Prints flow progress only. No secret is echoed. Run from anywhere.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS="${REPO_ROOT}/ansible/group_vars/all/secrets.sops.yml"
MAIN_VARS="${REPO_ROOT}/ansible/group_vars/all/main.yml"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"

HA_URL="http://192.168.1.144:8123"

plain="$(sops -d --output-type json "${SECRETS}")"
HA_TOKEN="$(printf '%s' "${plain}" | jq -r '.vault_ha_mcp_token')"
MQTT_PW="$(printf '%s' "${plain}" | jq -r '.vault_mosquitto_ha_password')"
unset plain

BROKER_HOST="$(grep -E '^mosquitto_host:' "${MAIN_VARS}" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' || true)"
[ -n "${BROKER_HOST}" ] || BROKER_HOST="192.168.1.140"   # var is a hostvars lookup, not a literal
BROKER_PORT="$(grep -E '^mosquitto_port:' "${MAIN_VARS}" | awk '{print $2}')"
HA_USER="$(grep -E '^mosquitto_ha_username:' "${MAIN_VARS}" | cut -d'"' -f2)"

api() { # method path [body]
  local method="$1" path="$2" body="${3:-}"
  if [ -n "${body}" ]; then
    curl -sS -X "${method}" "${HA_URL}${path}" \
      -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" -d "${body}"
  else
    curl -sS -X "${method}" "${HA_URL}${path}" -H "Authorization: Bearer ${HA_TOKEN}"
  fi
}

echo "--- output below is safe to share, it contains no secrets ---"
echo "broker: ${BROKER_HOST}:${BROKER_PORT}  user: ${HA_USER}"

# Clear any half-finished mqtt flows left by earlier probing, so this run starts
# clean. The flow-list endpoint does not always answer JSON to a plain GET, so
# tolerate a non-JSON body rather than aborting: a stale flow is untidy, not
# fatal, and the create below works regardless.
for stale in $(api GET /api/config/config_entries/flow 2>/dev/null \
  | jq -r '.[]? | select(.handler=="mqtt") | .flow_id' 2>/dev/null || true); do
  echo "clearing stale mqtt flow ${stale}"
  api DELETE "/api/config/config_entries/flow/${stale}" >/dev/null || true
done

flow_id="$(api POST /api/config/config_entries/flow '{"handler":"mqtt","show_advanced_options":false}' | jq -r '.flow_id')"
echo "flow started: ${flow_id}"

api POST "/api/config/config_entries/flow/${flow_id}" '{"next_step_id":"broker"}' \
  | jq -r '"menu step -> \(.step_id // .type)"'

result="$(jq -n \
  --arg b "${BROKER_HOST}" --argjson p "${BROKER_PORT}" \
  --arg u "${HA_USER}" --arg w "${MQTT_PW}" \
  '{broker:$b, port:$p, protocol:"5", username:$u, password:$w,
    other_settings:{set_client_cert:false, set_ca_cert:"off", transport:"tcp"}}' \
  | api POST "/api/config/config_entries/flow/${flow_id}" "$(cat)")"

printf '%s' "${result}" | jq -r '
  if .type == "create_entry" then
    "RESULT: created  title=\(.title)  entry_id=\(.result.entry_id)"
  elif .errors then
    "RESULT: rejected  errors=\(.errors|tostring)"
  else
    "RESULT: \(.type // "unexpected")  step=\(.step_id // "?")"
  end'
