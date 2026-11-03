# tnz.social DNS
#
# The rehearsal zone: seven records, no Access application, no WAF entrypoint.
# Every record here was created by hand in the dashboard, and each one carries a
# reason that is not visible from the record itself - the mail records encode
# "this domain sends no mail", the sinkhole exists only so a bulk redirect has a
# source, and the apex/www CNAMEs point at Netlify because the nameservers are
# Cloudflare's and Netlify therefore cannot manage them. Comments carry those
# reasons rather than leaving them in a chat log.

# A sinkhole: the bulk redirect list in redirects.tf matches on this hostname, so
# it must resolve (proxied, so Cloudflare answers and applies the redirect) even
# though nothing listens behind it. 192.0.2.1 is a documentation-range address
# and is never dialled because the request never leaves the edge.
resource "cloudflare_dns_record" "tnz_youtoobitch" {
  zone_id = cloudflare_zone.tnz.id
  name    = "youtoobitch.tnz.social"
  type    = "A"
  content = "192.0.2.1"
  proxied = true
  ttl     = 1
}

resource "cloudflare_dns_record" "tnz_apex" {
  zone_id = cloudflare_zone.tnz.id
  name    = "tnz.social"
  type    = "CNAME"
  content = "apex-loadbalancer.netlify.com"
  proxied = true
  # 1 is Cloudflare's "auto" TTL, which is what the dashboard leaves on every
  # record in this zone. Writing 300 here would plan a change on every apply.
  ttl = 1
}

resource "cloudflare_dns_record" "tnz_www" {
  zone_id = cloudflare_zone.tnz.id
  name    = "www.tnz.social"
  type    = "CNAME"
  content = "ephemeral-licorice-5e593d.netlify.app"
  proxied = true
  ttl     = 1
}

# The three mail records below are a claim, not a configuration: SPF `-all` plus
# a null DKIM key plus a `p=reject` DMARC policy means "this domain sends
# nothing, and do not believe anything that says otherwise". They are the reason
# the zone needs no mail infrastructure, so they must not be tidied away.
resource "cloudflare_dns_record" "tnz_spf" {
  zone_id = cloudflare_zone.tnz.id
  name    = "tnz.social"
  type    = "TXT"
  content = "\"v=spf1 -all\""
  proxied = false
  ttl     = 1

  comment = "email spoof protection - tells mail servers i dont send email from this domain"
}

resource "cloudflare_dns_record" "tnz_dmarc" {
  zone_id = cloudflare_zone.tnz.id
  name    = "_dmarc.tnz.social"
  type    = "TXT"
  content = "\"v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s;\""
  proxied = false
  ttl     = 1

  comment = "email spoof protection"
}

resource "cloudflare_dns_record" "tnz_dkim" {
  zone_id = cloudflare_zone.tnz.id
  name    = "*._domainkey.tnz.social"
  type    = "TXT"
  # An empty key: the selector exists so a receiver that looks it up finds
  # nothing usable, rather than a name that does not exist at all.
  content = "\"v=DKIM1; p=\""
  proxied = false
  ttl     = 1

  comment = "email spoof protection"
}

# AT Protocol handle verification for the Bluesky account on this domain. Losing
# it drops the handle, so it is declared next to the records that matter and not
# in a catch-all file.
resource "cloudflare_dns_record" "tnz_atproto" {
  zone_id = cloudflare_zone.tnz.id
  name    = "_atproto.tnz.social"
  type    = "TXT"
  content = "\"did=did:plc:wnk4aaan6yvnhztcqmscx2h3\""
  proxied = false
  ttl     = 1
}
