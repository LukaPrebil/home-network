# The account's bulk redirect
#
# The redirect exists to keep a dead hostname pointing somewhere harmless. The
# source hostname is the sinkhole A record in dns_tnz.tf: the record has to
# resolve for `http.request.full_uri in $youtoobitch` to ever match, which is why
# the two files are read together.
#
# Two objects are involved and both are account-level:
#
#   cloudflare_list    the bulk-redirect list `youtoobitch`, one item
#   cloudflare_ruleset the account root ruleset in http_request_redirect, one
#                      rule that matches a request against that list
#
# The list items are declared inline rather than with cloudflare_list_item
# resources: there is one entry, it has no independent lifecycle, and the list
# resource is what the ruleset refers to by name.

import {
  to = cloudflare_list.youtoobitch
  id = "8c4bb66b8910ded785480b1599dac8e2/b436b76012c94eccbbe87abd113adb5e"
}

import {
  to = cloudflare_ruleset.account_redirect
  id = "accounts/8c4bb66b8910ded785480b1599dac8e2/597f1ce73d204c8392face508e9f7c1f"
}

resource "cloudflare_list" "youtoobitch" {
  account_id = var.cloudflare_account_id

  name        = "youtoobitch"
  kind        = "redirect"
  description = "youtoobitch -> rickroll"

  items = [
    {
      redirect = {
        source_url = "youtoobitch.tnz.social/"
        target_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        # 301 rather than 302: the joke does not need to be re-evaluated, and a
        # permanent redirect is one fewer request against the zone.
        status_code = 301
      }
    },
  ]
}

resource "cloudflare_ruleset" "account_redirect" {
  account_id = var.cloudflare_account_id

  name  = "default"
  kind  = "root"
  phase = "http_request_redirect"

  rules = [
    {
      action      = "redirect"
      description = "YouTooBitch"
      enabled     = true
      expression  = "http.request.full_uri in $youtoobitch"

      # `from_list` is what ties the rule to the list above. The key is the
      # request field the list's source_url is compared against.
      action_parameters = {
        from_list = {
          name = "youtoobitch"
          key  = "http.request.full_uri"
        }
      }
    },
  ]
}
