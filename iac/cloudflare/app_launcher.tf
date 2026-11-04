# The App Launcher application
#
# Cloudflare creates this one when Zero Trust is first enabled, and it is the
# page a signed-in user lands on to see their apps. It exists only because ovis
# is `app_launcher_visible = true`.
#
# The policy is the same reusable policy as ovis, attached by id. One operator,
# one allow-list: a second copy of the same email rule would be two places to
# change when the address does, and two ways for the two apps to disagree.
#
# This file is separate from access.tf because the launcher is the one
# Cloudflare-created object in the tree. If the provider ever stops handling it
# cleanly, removing this file is not the whole rollback: the resource carries
# `prevent_destroy`, so the lifecycle block has to go first.

import {
  to = cloudflare_zero_trust_access_application.app_launcher
  id = "accounts/8c4bb66b8910ded785480b1599dac8e2/45b21401-69ca-4658-ae6d-f4ae6a264fb0"
}

resource "cloudflare_zero_trust_access_application" "app_launcher" {
  account_id = var.cloudflare_account_id

  name   = "App Launcher"
  domain = "lpgtnz.cloudflareaccess.com"
  type   = "app_launcher"

  # 730h, one month, matching the policy. The launcher's audience is the same
  # single operator.
  session_duration = "730h"

  # no allowed_idps and no auto-redirect: the launcher is the app that lists the
  # others, and with one IdP the chooser is a single button. Declared explicitly
  # because the provider otherwise writes its own default over it.
  allowed_idps              = []
  auto_redirect_to_identity = false

  # The API returns an empty landing-page design, but the provider fills in its
  # own default as soon as the block is declared, so an empty object plans a
  # change forever. Declaring the default explicitly is the only stable form:
  # omitting it plans a removal, and `{}` plans an addition.
  landing_page_design = {
    title = "Welcome!"
  }

  policies = [
    {
      id         = cloudflare_zero_trust_access_policy.allow_operator.id
      precedence = 1
    },
  ]

  lifecycle {
    # Cloudflare created this object when Zero Trust was first enabled, and a
    # replacement breaks the page every signed-in user lands on. The doc names it
    # as one of the objects a plan must never replace, so the guard belongs here
    # and not only in the prose.
    prevent_destroy = true
  }
}
