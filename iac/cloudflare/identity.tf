# The Zero Trust organization and the one identity provider
#
# Two objects, one file, because they are one decision: the team domain and the
# single way into it. There are no Access groups and no service tokens in the
# account, so nothing else belongs here yet.

import {
  to = cloudflare_zero_trust_organization.this
  id = "8c4bb66b8910ded785480b1599dac8e2"
}

import {
  to = cloudflare_zero_trust_access_identity_provider.onetimepin
  id = "accounts/8c4bb66b8910ded785480b1599dac8e2/7705c691-940a-47f2-a91a-f36c8862a9cb"
}

resource "cloudflare_zero_trust_organization" "this" {
  account_id = var.cloudflare_account_id

  # The team domain is baked into every Access redirect, every bookmark that has
  # completed a login, and the IdP's own callback URL. Changing it locks every
  # app out until each device is re-authenticated, which is why this resource
  # carries prevent_destroy and why the apply that touches it is reviewed by
  # hand - `auth_domain` is not a rename, it is a new estate.
  auth_domain = "lpgtnz.cloudflareaccess.com"
  name        = "lpgtnz.cloudflareaccess.com"

  # Account-level MFA: biometrics or a security key, 24h. This is the policy the
  # apps inherit, and the reason an app cannot quietly turn MFA off.
  mfa_config = {
    allowed_authenticators        = ["biometrics", "security_key"]
    session_duration              = "24h"
    amr_matching_session_duration = "24h"
  }

  # One-time PIN is the only provider, so there is no IdP chooser to show and no
  # reason to require WARP before Access.
  auto_redirect_to_identity   = false
  allow_authenticate_via_warp = false
  warp_auth_non_browser_401   = false

  # The dashboard-level switches, declared at their current values: UI read-only
  # off, unmatched requests not denied, service tokens not required to be strict,
  # and no trusted third-party accounts.
  is_ui_read_only                             = false
  deny_unmatched_requests                     = false
  strict_service_token_auth                   = false
  deny_unmatched_requests_exempted_zone_names = []

  # Automatic enforcement for inactive service tokens is off, and the account
  # declares no service tokens at all. The provider requires a concrete action
  # and threshold even when enforcement is disabled, so both are set to a value
  # that does nothing while `enabled` stays false.
  service_token_inactivity = {
    enabled                   = false
    action                    = "disable"
    inactivity_threshold_days = 30
  }

  lifecycle {
    # A replacement here is a new team domain: every Access cookie, bookmark and
    # IdP callback breaks at once. Remove the guard by hand, never through a
    # plan.
    prevent_destroy = true
  }
}

resource "cloudflare_zero_trust_access_identity_provider" "onetimepin" {
  account_id = var.cloudflare_account_id

  # The API stores an empty name for the default provider and the dashboard
  # shows "One-time PIN" from the type. An empty string is the honest value.
  name = ""
  type = "onetimepin"

  # `config` is required by the provider but has nothing settable for a
  # one-time-PIN provider: Cloudflare owns the callback URL and the provider
  # rejects any attempt to set it. An empty object is the only correct value.
  config = {}

}
