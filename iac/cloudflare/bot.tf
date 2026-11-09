# Bot management, identical on both zones
#
# The settings below are the actual decision; the rest of the API surface is
# echoed computed state that this root does not own. The one control that used to
# live here and no longer can is covered in the note before the resources.
#
# The two zones are declared separately rather than with a for_each because bot
# management is a per-zone object and a future divergence (fighting mode off on
# the rehearsal zone, say) should be one edit, not a conditional.
#
# This resource's Delete is a no-op in the provider, like the zone settings: a
# removed resource block succeeds, forgets the state and leaves the account's
# value untouched, so it ends drift coverage rather than reverting anything.

import {
  to = cloudflare_bot_management.lukapg
  id = "e392a344536e78c92935b787d58c8ad2"
}

import {
  to = cloudflare_bot_management.tnz
  id = "f097b5d7910b67d2f644219fc01ff7c1"
}

# `ai_bots_protection` is deliberately not declared.
#
# It reads as a per-zone switch, but Cloudflare has migrated the control to the
# per-vendor `ai_agents` block (anthropic_agent, openai_agent, google_agent,
# instinct, muse). The old field is now *derived* from that block: a write of
# "block" is accepted and then immediately reported back as "disabled", which is
# why an apply fails with "provider produced an unexpected new value" and the
# plan can never converge. Measured on both zones on 2026-11-09.
#
# The pinned provider (5.28.1) has no `ai_agents` attribute at all, so the intent
# - keep AI crawlers out - cannot be expressed here yet. It is expressed at the
# edge instead: the AI-crawler rule in waf.tf blocks the four user agents by name,
# and it is the control that actually holds. Declare `ai_agents` here once a
# provider release models it; until then an undeclared field is honest, whereas a
# declared "disabled" would read as a decision to allow crawlers.

resource "cloudflare_bot_management" "lukapg" {
  zone_id = cloudflare_zone.lukapg.id

  # Bot Fight Mode: challenge automated traffic that Cloudflare's model scores as
  # definitely automated. Free-plan equivalent of a managed rule.
  fight_mode = true
  # Run the JS detections as well, which raises the cost of a headless scraper.
  enable_js               = true
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

  fight_mode = true
  enable_js  = true

  crawler_protection      = "enabled"
  content_bots_protection = "disabled"
  ai_training             = "disallow"
  aisearch                = "disabled"
  ai_user                 = "disabled"

  is_robots_txt_managed = true
}
