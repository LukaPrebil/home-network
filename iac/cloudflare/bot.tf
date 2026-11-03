# Bot management, identical on both zones
#
# Three settings are the actual decision; the rest of the API surface is echoed
# computed state that this root does not own. `ai_bots_protection = "block"` is
# the one that matters: it is what stops a scraper that is not on the WAF's
# user-agent list, and it is why the AI-bot rule in waf.tf has anything left to
# block.
#
# The two zones are declared separately rather than with a for_each because bot
# management is a per-zone object and a future divergence (fighting mode off on
# the rehearsal zone, say) should be one edit, not a conditional.

import {
  to = cloudflare_bot_management.lukapg
  id = "e392a344536e78c92935b787d58c8ad2"
}

import {
  to = cloudflare_bot_management.tnz
  id = "f097b5d7910b67d2f644219fc01ff7c1"
}

resource "cloudflare_bot_management" "lukapg" {
  zone_id = cloudflare_zone.lukapg.id

  # Bot Fight Mode: challenge automated traffic that Cloudflare's model scores as
  # definitely automated. Free-plan equivalent of a managed rule.
  fight_mode = true
  # Run the JS detections as well, which raises the cost of a headless scraper.
  enable_js = true
  # Block AI bots outright rather than letting them crawl and rate-limit later.
  ai_bots_protection = "block"

  crawler_protection      = "enabled"
  content_bots_protection = "disabled"
  ai_training             = "disallow"
  aisearch                = "disabled"
  ai_user                 = "disabled"

  # Cloudflare serves the zone's robots.txt. It is on in the account and the
  # provider's default is off, so leaving it undeclared would plan a change that
  # silently hands robots.txt back to the origin.
  is_robots_txt_managed = true
}

resource "cloudflare_bot_management" "tnz" {
  zone_id = cloudflare_zone.tnz.id

  fight_mode         = true
  enable_js          = true
  ai_bots_protection = "block"

  crawler_protection      = "enabled"
  content_bots_protection = "disabled"
  ai_training             = "disallow"
  aisearch                = "disabled"
  ai_user                 = "disabled"

  is_robots_txt_managed = true
}
