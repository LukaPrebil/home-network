# State encryption at rest
#
# Copy of iac/object-store/encryption.tf: the Cloudflare token never enters
# state, but the state does carry the Access allow-list (the operator's email
# address), the account and zone identifiers, and every record the estate
# serves. One root, one rule: a bucket reader must not be able to read it.
#
# pbkdf2 + aes_gcm is the passphrase-based option, and the passphrase comes from
# SOPS through TF_VAR_state_passphrase. There is no KMS in the estate, and the
# point of this block is to keep one more copy of the state out of reach.
#
# A passphrase-based key needs the passphrase for every read. If it is missing,
# OpenTofu refuses to read the state rather than silently planning from scratch:
# that failure is the intended one.

terraform {
  encryption {
    key_provider "pbkdf2" "state" {
      passphrase = var.state_passphrase
    }

    method "aes_gcm" "state" {
      keys = key_provider.pbkdf2.state
    }

    state {
      method = method.aes_gcm.state
      # enforced refuses plaintext outright, so a state object that arrives
      # unencrypted is treated as tampering rather than read.
      enforced = true
    }
  }
}
