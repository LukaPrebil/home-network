# lukapg.dev record imports
#
# Same shape and same reasons as imports_tnz.tf: `<zone_id>/<record_id>`, ids
# read from the account's own API listing rather than from the docs.
#
# The nine A records are one `for_each` resource, so each import targets a key
# of it. Every key is written out rather than generated: an import block has to
# name one instance, and a generated key would be a name nobody can grep for.

import {
  to = cloudflare_dns_record.lukapg_a["apex"]
  id = "e392a344536e78c92935b787d58c8ad2/682a9b321f00e87c834369e25c42a96e"
}

import {
  to = cloudflare_dns_record.lukapg_a["documents"]
  id = "e392a344536e78c92935b787d58c8ad2/bbba170a837678a2b8226c153663d0c4"
}

import {
  to = cloudflare_dns_record.lukapg_a["grafana"]
  id = "e392a344536e78c92935b787d58c8ad2/209e7f94c4da594d5c6497488466cf79"
}

import {
  to = cloudflare_dns_record.lukapg_a["ha"]
  id = "e392a344536e78c92935b787d58c8ad2/506608b838e44da8acec9e7c94ea5070"
}

import {
  to = cloudflare_dns_record.lukapg_a["jellyfin"]
  id = "e392a344536e78c92935b787d58c8ad2/9fc6361c69e822b9d6ff8180f9f5f7ab"
}

import {
  to = cloudflare_dns_record.lukapg_a["kuma"]
  id = "e392a344536e78c92935b787d58c8ad2/0a56c70e980e82b7f53c03163589d74b"
}

import {
  to = cloudflare_dns_record.lukapg_a["ovis"]
  id = "e392a344536e78c92935b787d58c8ad2/d281b7342cb00f255c09918509607ef3"
}

import {
  to = cloudflare_dns_record.lukapg_a["photos"]
  id = "e392a344536e78c92935b787d58c8ad2/2cd1c8a7a877b6274f1816370a89787d"
}

import {
  to = cloudflare_dns_record.lukapg_a["status"]
  id = "e392a344536e78c92935b787d58c8ad2/fdea9fab7e6a92bf5f4794253da84b38"
}

import {
  to = cloudflare_dns_record.lukapg_parking_wildcard
  id = "e392a344536e78c92935b787d58c8ad2/28d5b491566d0d965e8f9c23fcb6dfca"
}

import {
  to = cloudflare_dns_record.lukapg_parking_www
  id = "e392a344536e78c92935b787d58c8ad2/be104e8f0cbdd9e40748b212a923d48c"
}

import {
  to = cloudflare_dns_record.lukapg_pds
  id = "e392a344536e78c92935b787d58c8ad2/4405bff525cb864b14f68a2d9adcb684"
}

import {
  to = cloudflare_dns_record.lukapg_atproto
  id = "e392a344536e78c92935b787d58c8ad2/8f91ec0e798bbc8c5db2c63f4e117f17"
}

import {
  to = cloudflare_dns_record.lukapg_dmarc
  id = "e392a344536e78c92935b787d58c8ad2/b0938fa5764c82f420ec72470d37b617"
}

# The stale objects deleted in the next commit. Imported first so the deletion
# is visible as destroys rather than as an absence.
import {
  to = cloudflare_dns_record.stale_acme_apex_1
  id = "e392a344536e78c92935b787d58c8ad2/95bc632abcd45a8fd11ee7d9a537fd2e"
}

import {
  to = cloudflare_dns_record.stale_acme_apex_2
  id = "e392a344536e78c92935b787d58c8ad2/39b12681155631282970f11a5bf3292b"
}

import {
  to = cloudflare_dns_record.stale_acme_photos
  id = "e392a344536e78c92935b787d58c8ad2/46c2e1505bdb8c7e5dc6cb261e251731"
}

import {
  to = cloudflare_dns_record.stale_ns_curitiba
  id = "e392a344536e78c92935b787d58c8ad2/0f57bb995dd0bd5c3526b57fc7d69d4e"
}

import {
  to = cloudflare_dns_record.stale_ns_fortaleza
  id = "e392a344536e78c92935b787d58c8ad2/a8e17a2cdd74056cee391e2a4fc66ebc"
}

import {
  to = cloudflare_dns_record.stale_ns_maceio
  id = "e392a344536e78c92935b787d58c8ad2/ec9778223840e80c8b800b3c9492e827"
}

import {
  to = cloudflare_dns_record.stale_ns_salvador
  id = "e392a344536e78c92935b787d58c8ad2/7ce687165c10e47650f0360210e99eab"
}
