# tnz.social record imports
#
# Record import ids are `<zone_id>/<record_id>`. The record ids below came from
# the account's own API listing, not from the docs, because a record has no
# stable name to import by: two TXT records can share a name, and the id is the
# only thing that says which of them is which.

import {
  to = cloudflare_dns_record.tnz_youtoobitch
  id = "f097b5d7910b67d2f644219fc01ff7c1/7dfedcc16223cc24412419a47a66087b"
}

import {
  to = cloudflare_dns_record.tnz_apex
  id = "f097b5d7910b67d2f644219fc01ff7c1/9d5db07d048bccdce30a1769898dd028"
}

import {
  to = cloudflare_dns_record.tnz_www
  id = "f097b5d7910b67d2f644219fc01ff7c1/8ce0bd8dfee490056c4259a6677938f8"
}

import {
  to = cloudflare_dns_record.tnz_spf
  id = "f097b5d7910b67d2f644219fc01ff7c1/7cd019074d54c8c2a01c20bdb90605bb"
}

import {
  to = cloudflare_dns_record.tnz_dmarc
  id = "f097b5d7910b67d2f644219fc01ff7c1/c7454ce6f892f18daf4770ba10970e8d"
}

import {
  to = cloudflare_dns_record.tnz_dkim
  id = "f097b5d7910b67d2f644219fc01ff7c1/b0cf48c82346dc2be8702dca3f399c61"
}

import {
  to = cloudflare_dns_record.tnz_atproto
  id = "f097b5d7910b67d2f644219fc01ff7c1/0ba049c5a0668892b682d541b589d1a7"
}
