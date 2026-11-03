# lukapg.dev DNS
#
# Fourteen records that the estate actually serves, declared as they are today.
# Everything public points at one address: Cloudflare proxies it and Traefik on
# the containers VM decides where each hostname goes, so the DNS layer here is
# deliberately dumb - one A record per hostname and no per-service cleverness.
#
# Two records deserve a note because they look wrong and are not:
#
#   *.lukapg.dev -> pixie.porkbun.com   the parking wildcard that also answers
#                                       every admin name on the LAN. Traefik's
#                                       lan-only middleware gates those, not DNS.
#   pds.lukapg.dev -> lukapg.dev        a proxied CNAME to its own apex, which
#                                       is why `orange_to_orange` matters in
#                                       settings.tf: turning O2O on would change
#                                       how that hop resolves.

locals {
  # One address for every public hostname. It comes from
  # TF_VAR_lukapg_public_ipv4 (iac/secrets.sops.yaml) and is marked sensitive so
  # it never appears in a plan, a PR comment or a CI log: these records are
  # proxied, and the origin address in a public repository defeats the proxy.
  lukapg_a_records = {
    apex      = "lukapg.dev"
    documents = "documents.lukapg.dev"
    grafana   = "grafana.lukapg.dev"
    ha        = "ha.lukapg.dev"
    jellyfin  = "jellyfin.lukapg.dev"
    kuma      = "kuma.lukapg.dev"
    ovis      = "ovis.lukapg.dev"
    photos    = "photos.lukapg.dev"
    status    = "status.lukapg.dev"
  }
}

resource "cloudflare_dns_record" "lukapg_a" {
  for_each = local.lukapg_a_records

  zone_id = cloudflare_zone.lukapg.id
  name    = each.value
  type    = "A"
  content = var.lukapg_public_ipv4
  proxied = true
  ttl     = 1
}

resource "cloudflare_dns_record" "lukapg_parking_wildcard" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "*.lukapg.dev"
  type    = "CNAME"
  content = "pixie.porkbun.com"
  proxied = true
  ttl     = 1
}

resource "cloudflare_dns_record" "lukapg_parking_www" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "www.lukapg.dev"
  type    = "CNAME"
  content = "pixie.porkbun.com"
  proxied = true
  ttl     = 1
}

resource "cloudflare_dns_record" "lukapg_pds" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "pds.lukapg.dev"
  type    = "CNAME"
  # The PDS answers on its own hostname but the certificate and the origin are
  # the apex, so the CNAME points at the apex and Cloudflare flattens it at the
  # edge. `orange_to_orange = off` in settings.tf is what keeps this working.
  content = "lukapg.dev"
  proxied = true
  ttl     = 1
}

# AT Protocol handle verification: losing this TXT drops the Bluesky handle for
# the account on this domain.
resource "cloudflare_dns_record" "lukapg_atproto" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "_atproto.lukapg.dev"
  type    = "TXT"
  content = "\"did=did:plc:6grs5apxsymn763ml4xfsa54\""
  proxied = false
  ttl     = 1
}

# DMARC with `p=none` on purpose: this domain does send mail, the reports go to
# Cloudflare's aggregator, and the policy is deliberately not enforcing yet.
resource "cloudflare_dns_record" "lukapg_dmarc" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "_dmarc.lukapg.dev"
  type    = "TXT"
  content = "\"v=DMARC1; p=none; rua=mailto:62f1059b457549abb2b45f7ee568ad18@dmarc-reports.cloudflare.net\""
  proxied = false
  ttl     = 1
}
