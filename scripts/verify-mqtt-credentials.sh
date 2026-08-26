#!/usr/bin/env bash
#
# Verify that the plaintext MQTT passwords in secrets.sops.yml actually match
# the hashes in vault_mosquitto_passwd_file, by authenticating against a real
# throwaway broker.
#
# A mismatched paste passes every structural check and only fails at runtime,
# after the bridge is already deployed. This catches it beforehand.
#
# Prints PASS/FAIL only. No secret is ever echoed. Run from the repo root.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS="${REPO_ROOT}/ansible/group_vars/all/secrets.sops.yml"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"

WORK="$(mktemp -d)"
cleanup() { docker rm -f mqtt-credcheck >/dev/null 2>&1 || true; rm -rf "${WORK}"; }
trap cleanup EXIT
chmod 700 "${WORK}"

plain="$(sops -d --output-type json "${SECRETS}")"
printf '%s' "${plain}" | jq -r '.vault_mosquitto_passwd_file' > "${WORK}/passwd"
BRIDGE_PW="$(printf '%s' "${plain}" | jq -r '.vault_mosquitto_bridge_password')"
HA_PW="$(printf '%s' "${plain}" | jq -r '.vault_mosquitto_ha_password')"
BRIDGE_USER="$(grep -E '^mosquitto_bridge_username:' "${REPO_ROOT}/ansible/group_vars/all/main.yml" | cut -d'"' -f2)"
HA_USER="$(grep -E '^mosquitto_ha_username:' "${REPO_ROOT}/ansible/group_vars/all/main.yml" | cut -d'"' -f2)"
unset plain

printf 'listener 1883\nallow_anonymous false\npassword_file /mosquitto/config/passwd\n' > "${WORK}/mosquitto.conf"
chmod 600 "${WORK}/passwd"

docker run -d --name mqtt-credcheck \
  -v "${WORK}/mosquitto.conf":/mosquitto/config/mosquitto.conf:ro \
  -v "${WORK}/passwd":/mosquitto/config/passwd:ro \
  eclipse-mosquitto:2 >/dev/null
sleep 4

check() { # label user password expected(0=should succeed,1=should fail)
  local label="$1" user="$2" pass="$3" expect="$4" rc=0
  if [ -n "${user}" ]; then
    docker exec -e P="${pass}" mqtt-credcheck \
      mosquitto_pub -h localhost -u "${user}" -P "$(printf '%s' "${pass}")" \
      -t credcheck/probe -m ok >/dev/null 2>&1 || rc=1
  else
    docker exec mqtt-credcheck \
      mosquitto_pub -h localhost -t credcheck/probe -m ok >/dev/null 2>&1 || rc=1
  fi
  if [ "${rc}" -eq "${expect}" ]; then echo "PASS  ${label}"; else echo "FAIL  ${label}"; fi
}

echo "--- output below is safe to share, it contains no secrets ---"
check "${BRIDGE_USER} authenticates with vault_mosquitto_bridge_password" "${BRIDGE_USER}" "${BRIDGE_PW}" 0
check "${HA_USER} authenticates with vault_mosquitto_ha_password"         "${HA_USER}"     "${HA_PW}"     0
check "a wrong password is rejected"                                       "${BRIDGE_USER}" "wrong-on-purpose" 1
check "anonymous is rejected"                                              ""               ""            1
