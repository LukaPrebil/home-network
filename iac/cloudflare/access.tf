# The ovis Access application and its policy
#
# This is the only public hostname behind Cloudflare Access today; the other
# seven use their own login. Adding gates to them is a security decision, not
# codification, so this root declares exactly the one that exists.
#
# The policy is inline rather than a separate cloudflare_zero_trust_access_policy
# resource because v5 treats an application's policies as part of the
# application: a policy is scoped to one app, has no meaning without it, and
# declaring it separately splits one object across two resources that can drift
# against each other.

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
      id         = cloudflare_zero_trust_access_policy.ovis_allow.id
      precedence = 1
    },
  ]
}

resource "cloudflare_zero_trust_access_policy" "ovis_allow" {
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
}
