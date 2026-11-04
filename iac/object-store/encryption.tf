# State encryption at rest
#
# The state object sits in a bucket on a self-hosted store, so "encrypted at
# rest" is not the ZFS pool's job alone: anyone who can read the bucket, or read
# a snapshot of the zvol, would otherwise read plain JSON containing account
# identifiers and, once the Cloudflare root lands here, an Access allow-list.
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

    # A saved plan file carries the same resolved values the state does. It is
    # not covered by `state {}`, so `plan -out` would write them in the clear.
    plan {
      method   = method.aes_gcm.state
      enforced = true
    }
  }
}
