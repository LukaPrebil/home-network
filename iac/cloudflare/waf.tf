# The lukapg.dev custom firewall rules
#
# Two rules, both created by hand in the dashboard, and both load-bearing:
#
#   rule 1  managed_challenge anything from outside Slovenia. The estate is a
#           homelab; there is no reason for a request from another country to
#           reach it without a challenge.
#   rule 2  block four AI crawler user agents except on /robots.txt. The
#           robots.txt carve-out is deliberate - a crawler that reads robots and
#           obeys it should not be blocked for asking.
#
# tnz.social deliberately has no resource here. Its entrypoint does not exist,
# and creating one because "the provider supports it" would turn the rehearsal
# zone into a second thing to maintain.
#
# The rule `ref` values are Cloudflare-managed identifiers: the first is the
# rule's id and the second is the literal string "[CF AI Audit]" the dashboard
# wrote. Neither is settable, so neither is declared, and the rules are matched
# by their position and content instead.

import {
  to = cloudflare_ruleset.lukapg_waf_custom
  id = "zones/e392a344536e78c92935b787d58c8ad2/6c76161aec0b46338ca60ae3b60dd4e5"
}

resource "cloudflare_ruleset" "lukapg_waf_custom" {
  zone_id = cloudflare_zone.lukapg.id

  name        = "default"
  description = ""
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  rules = [
    {
      action      = "managed_challenge"
      description = "Challenge requests from foreign countries"
      enabled     = true
      expression  = "(ip.src.country ne \"SI\")"
    },
    {
      action      = "block"
      description = "AI Crawl Control - Block AI bots by User Agent"
      enabled     = true
      expression  = "(http.request.uri.path ne \"/robots.txt\" and ((http.user_agent contains \"Applebot\") or (http.user_agent contains \"bingbot\") or (http.user_agent contains \"ChatGPT-User\") or (http.user_agent contains \"DuckAssistBot\")))"
    },
  ]
}
