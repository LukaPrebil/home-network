# The ovis Access application and its policy
#
# This is the only public hostname behind Cloudflare Access today; the other
# seven use their own login. Adding gates to them is a security decision, not
# codification, so this root declares exactly the one that exists.
#
# The policy is a reusable account-level object shared with the App Launcher (see
# app_launcher.tf) and attached here by id. The comment on the resource explains
# why it cannot be an inline block.

import {
  to = cloudflare_zero_trust_access_application.ovis
  id = "accounts/8c4bb66b8910ded785480b1599dac8e2/1f9e0a74-26a8-4200-9519-fe8f94dcc0d4"
}

resource "cloudflare_zero_trust_access_application" "ovis" {
  account_id = var.cloudflare_account_id

  name   = "ovis"
  domain = "ovis.lukapg.dev"
  type   = "self_hosted"

  # 24h at the app and 730h at the policy, which is what the estate has: the
  # app's own duration is what the dashboard shows, the policy's is what Access
  # actually honours. Both are declared so neither can drift unwatched.
  session_duration = "24h"

  # One-time PIN is the only identity provider in the account, so the app is
  # pinned to it and skips the chooser. Without auto_redirect the phone gets an
  # IdP picker with one option in it.
  allowed_idps              = ["7705c691-940a-47f2-a91a-f36c8862a9cb"]
  auto_redirect_to_identity = true
  app_launcher_visible      = true

  # Three flags the dashboard left at non-default values. Declaring them is not
  # decoration: leaving any one out puts a change in every plan, and a plan that
  # always has something in it stops being read.
  #
  # http_only_cookie_attribute is the one that matters - the provider defaults it
  # to true and this app has it off.
  http_only_cookie_attribute = false
  enable_binding_cookie      = false
  options_preflight_bypass   = false

  # MFA lives on the account's organization (24h, biometrics or a security key)
  # and the API echoes it here with mfa_disabled false - i.e. MFA is not turned
  # off for this app.
  mfa_config = {
    allowed_authenticators = ["biometrics", "security_key"]
    mfa_disabled           = false
    session_duration       = "24h"
  }

  # The policy is a reusable, account-level policy referenced by id rather than
  # an inline `policies` block. That is not a style choice: in provider 5.x the
  # inline policy type has no `session_duration` field at all, so an inline policy
  # silently falls back to the app's 24h and the operator's month-long session
  # disappears. The standalone resource is the only place the provider exposes
  # session_duration, and `app_count` is how Cloudflare reports the attachment.
  policies = [
    {
      id         = cloudflare_zero_trust_access_policy.allow_operator.id
      precedence = 1
    },
  ]
}

# The policy is the account's original reusable policy, adopted by id rather than
# recreated. It was the one object both applications already shared before this
# root existed, so importing it keeps the estate's identity and means the tree
# manages the object the operator actually has.
import {
  to = cloudflare_zero_trust_access_policy.allow_operator
  id = "8c4bb66b8910ded785480b1599dac8e2/b6eee043-df23-4fbe-8e54-388c2980aa4f"
}

resource "cloudflare_zero_trust_access_policy" "allow_operator" {
  account_id = var.cloudflare_account_id

  name     = "Allow Luka's email"
  decision = "allow"

  # 730h is one month, and it is the duration the phone actually experiences:
  # Cloudflare takes the policy's session over the app's when both are set. The
  # app's 24h above is what the dashboard shows, not what a logged-in device
  # gets.
  session_duration = "730h"

  include = [
    {
      email = {
        email = "luka.prebil.grintal@proton.me"
      }
    }
  ]

  lifecycle {
    # Cloudflare stores RDP clipboard rules on every reusable policy, and this
    # object carries `["text", "file"]` for both directions. The provider's
    # schema only accepts `["text"]`, so the value cannot be declared - writing
    # it fails validation, and omitting it plans a removal of a field nobody
    # configured. Ignoring exactly this one attribute is the narrowest way to
    # stop that noise; everything that defines the policy's behaviour - decision,
    # include, name and session_duration - is still tracked.
    ignore_changes = [connection_rules]
  }
}
