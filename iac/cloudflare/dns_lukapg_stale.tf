# The seven stale lukapg.dev objects
#
# These are leftovers, imported here so that deleting them is a reviewed apply
# with seven destroys in the plan instead of a hand-run API call with no record
# of what went:
#
#   three _acme-challenge TXT records  from earlier ACME validation runs when
#                                      certificates were issued through DNS
#                                      rather than HTTP. The live certificate is
#                                      the wildcard, so nothing still validates
#                                      against them.
#   four apex NS records               pointing at Porkbun inside a zone whose
#                                      delegation comes from the registrar.
#                                      Apex NS records in an authoritative zone
#                                      are inert; they only make `dig NS` answer
#                                      with names that are not the nameservers.
#
# This file exists for one commit and is then removed, together with its import
# blocks, so the deletion lands in history as a plan the reviewer could read.

resource "cloudflare_dns_record" "stale_acme_apex_1" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "_acme-challenge.lukapg.dev"
  type    = "TXT"
  content = "\"2YG6falbmX_hDLU6kuORn7ibPPiVq7tl2sNk7dVDBCQ\""
  proxied = false
  ttl     = 1
}

resource "cloudflare_dns_record" "stale_acme_apex_2" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "_acme-challenge.lukapg.dev"
  type    = "TXT"
  content = "\"0Gdtt4fJpVAjZ1yEs10VB0nb4W--DYrRSVpfL7_q1OA\""
  proxied = false
  ttl     = 1
}

resource "cloudflare_dns_record" "stale_acme_photos" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "_acme-challenge.photos.lukapg.dev"
  type    = "TXT"
  content = "\"r_b7Bi9mgOFwwXVPk7yJJXOUNJGueWDWUjgyFTttWk4\""
  proxied = false
  # 120 rather than auto: this one was set by hand when it was created.
  ttl = 120
}

resource "cloudflare_dns_record" "stale_ns_curitiba" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "lukapg.dev"
  type    = "NS"
  content = "curitiba.ns.porkbun.com"
  proxied = false
  ttl     = 1
}

resource "cloudflare_dns_record" "stale_ns_fortaleza" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "lukapg.dev"
  type    = "NS"
  content = "fortaleza.ns.porkbun.com"
  proxied = false
  ttl     = 1
}

resource "cloudflare_dns_record" "stale_ns_maceio" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "lukapg.dev"
  type    = "NS"
  content = "maceio.ns.porkbun.com"
  proxied = false
  ttl     = 1
}

resource "cloudflare_dns_record" "stale_ns_salvador" {
  zone_id = cloudflare_zone.lukapg.id
  name    = "lukapg.dev"
  type    = "NS"
  content = "salvador.ns.porkbun.com"
  proxied = false
  ttl     = 1
}
