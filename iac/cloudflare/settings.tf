# The seven zone settings this root owns, per zone
#
# Everything else in the settings API is either a Cloudflare default this root
# has no opinion about or a value that differs between zones for reasons that are
# not decisions (see the note on tls_1_3 below). Declaring a setting is a
# statement that a dashboard change to it should show up as drift, so the list is
# deliberately short.
#
# The seven:
#
#   ssl                strict        the origin has a real certificate; flexible
#                                    would let Cloudflare talk plaintext
#   always_use_https   on            no plaintext hop for anyone
#   min_tls_version    1.2           Traefik's own floor is 1.2, so accepting
#                                    TLS 1.0 at the edge only widens the surface
#                                    without ever working end to end
#   tls_1_3            on / zrt      the two zones differ because Cloudflare
#                                    picked differently, not because anyone chose
#   security_level     medium        high would challenge too much of the LAN
#   security_header    off           Traefik already sends HSTS; a second one at
#                                    the edge would duplicate the header
#   orange_to_orange   off           pds.lukapg.dev is a proxied CNAME to its own
#                                    apex, and O2O changes how that hop resolves
#
# Two applies are used on purpose: the import first (nothing changes), then
# min_tls_version on its own so the handshake test afterwards cannot be blamed on
# anything else in the same apply.
#
# Removing an entry is not the way to hand a setting back to the dashboard: this
# resource's Delete is a no-op in the provider, so dropping the entry succeeds,
# forgets the value and keeps the account's value in place - no drift is ever
# reported for it again. Delete the entry only when the intent is to stop
# watching the setting.

locals {
  # Six string-valued settings, shared shape, per-zone values.
  lukapg_settings = {
    ssl              = "strict"
    always_use_https = "on"
    min_tls_version  = "1.2"
    tls_1_3          = "on"
    security_level   = "medium"
    orange_to_orange = "off"
  }

  tnz_settings = {
    ssl              = "strict"
    always_use_https = "on"
    min_tls_version  = "1.2"
    # "zrt" is Cloudflare's Zero Round Trip variant, which is what this zone has
    # had since it was created. Declaring "on" here would plan a change that
    # nobody asked for.
    tls_1_3          = "zrt"
    security_level   = "medium"
    orange_to_orange = "off"
  }

  # Cloudflare-side HSTS stays off because Traefik sends
  # `strict-transport-security: max-age=31536000; includeSubDomains; preload`
  # already. Two sources for one header is how a preload directive ends up
  # contradicting itself.
  hsts_off = {
    strict_transport_security = {
      enabled            = false
      max_age            = 0
      include_subdomains = false
      preload            = false
      nosniff            = false
    }
  }
}

resource "cloudflare_zone_setting" "lukapg" {
  for_each = local.lukapg_settings

  zone_id    = cloudflare_zone.lukapg.id
  setting_id = each.key
  value      = each.value
}

resource "cloudflare_zone_setting" "lukapg_security_header" {
  zone_id    = cloudflare_zone.lukapg.id
  setting_id = "security_header"
  value      = local.hsts_off
}

resource "cloudflare_zone_setting" "tnz" {
  for_each = local.tnz_settings

  zone_id    = cloudflare_zone.tnz.id
  setting_id = each.key
  value      = each.value
}

resource "cloudflare_zone_setting" "tnz_security_header" {
  zone_id    = cloudflare_zone.tnz.id
  setting_id = "security_header"
  value      = local.hsts_off
}
