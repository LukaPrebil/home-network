# The two zones this root owns, and the DNSSEC that makes them signed.
#
# Both are declared with the minimum the provider requires - account and name.
# The temptation is to also pin `type`, `paused` and `vanity_name_servers`
# because the dashboard shows them; the risk is that the dashboard's values are
# provider-computed (both zones are `type = full` with Cloudflare's own
# nameservers) and pinning them turns a clean import into a replacement plan on
# the first apply. A zone replacement drops every record it holds, so it is the
# one change here that must never come from a plan.

resource "cloudflare_zone" "lukapg" {
  account = {
    id = var.cloudflare_account_id
  }

  name = "lukapg.dev"

  lifecycle {
    # A zone replacement deletes every record, the DNSSEC key and the Access
    # application bound to the hostnames in one move. Removing this guard is a
    # deliberate act: edit the lifecycle block, review the plan, and only then
    # apply.
    prevent_destroy = true
  }
}

resource "cloudflare_zone" "tnz" {
  account = {
    id = var.cloudflare_account_id
  }

  name = "tnz.social"

  lifecycle {
    prevent_destroy = true
  }
}

# DNSSEC is declared `active` because that is what the account reports: both
# zones are signed with algorithm 13 and the DS record is published at the
# registrar. Declaring it rather than importing it read-only means a disable in
# the dashboard shows up as drift instead of as silence.
resource "cloudflare_zone_dnssec" "lukapg" {
  zone_id = cloudflare_zone.lukapg.id

  # `status` is the only field this root sets. The key tag, algorithm, digest
  # and DS record are computed by Cloudflare and would only be noise in the
  # diff.
  status = "active"

  # lukapg.dev reports multi-signer DNSSEC on and tnz.social reports it off, so
  # this is a per-zone fact rather than a house style. It is declared because
  # leaving it out plans a change (`true -> null`) on every run, and a DNSSEC
  # change is one of the four objects this root must never quietly re-plan.
  dnssec_multi_signer = true

  lifecycle {
    prevent_destroy = true
  }
}

resource "cloudflare_zone_dnssec" "tnz" {
  zone_id = cloudflare_zone.tnz.id

  status = "active"

  lifecycle {
    prevent_destroy = true
  }
}
