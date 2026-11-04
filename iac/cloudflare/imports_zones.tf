# Import blocks: the first apply is a pure import
#
# Nothing in this root was created by OpenTofu. Every object already exists in
# the account, so the first apply must be an import - declared here rather than
# run as `tofu import` on the command line, because a CLI import is invisible to
# review and leaves no record of which id was adopted.
#
# These blocks stay in the tree after the first apply. Once a resource is in
# state they are no-ops, and their remaining value is recovery: if the state
# object is ever lost, re-running apply re-adopts the same objects by id instead
# of failing with "already exists". That is why the ids are literals here and
# not references - a recovered state cannot resolve a reference to an object it
# does not have.
#
# The zone ids are the two this account owns. They are identifiers, not secrets:
# they appear in every API URL, in the state, and in the plan output.

import {
  to = cloudflare_zone.lukapg
  id = "e392a344536e78c92935b787d58c8ad2"
}

import {
  to = cloudflare_zone.tnz
  id = "f097b5d7910b67d2f644219fc01ff7c1"
}

# DNSSEC imports by zone id: one signing key per zone, so the object's identity
# and the zone's are the same string.
import {
  to = cloudflare_zone_dnssec.lukapg
  id = "e392a344536e78c92935b787d58c8ad2"
}

import {
  to = cloudflare_zone_dnssec.tnz
  id = "f097b5d7910b67d2f644219fc01ff7c1"
}
