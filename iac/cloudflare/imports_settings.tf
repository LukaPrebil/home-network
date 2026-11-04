# Zone setting imports
#
# Setting import ids are `<zone_id>/<setting_id>`. The six string-valued settings
# live in one `for_each` per zone, so each import targets a key of it; the
# security_header setting is its own resource because its value is an object.

import {
  to = cloudflare_zone_setting.lukapg["ssl"]
  id = "e392a344536e78c92935b787d58c8ad2/ssl"
}

import {
  to = cloudflare_zone_setting.lukapg["always_use_https"]
  id = "e392a344536e78c92935b787d58c8ad2/always_use_https"
}

import {
  to = cloudflare_zone_setting.lukapg["min_tls_version"]
  id = "e392a344536e78c92935b787d58c8ad2/min_tls_version"
}

import {
  to = cloudflare_zone_setting.lukapg["tls_1_3"]
  id = "e392a344536e78c92935b787d58c8ad2/tls_1_3"
}

import {
  to = cloudflare_zone_setting.lukapg["security_level"]
  id = "e392a344536e78c92935b787d58c8ad2/security_level"
}

import {
  to = cloudflare_zone_setting.lukapg["orange_to_orange"]
  id = "e392a344536e78c92935b787d58c8ad2/orange_to_orange"
}

import {
  to = cloudflare_zone_setting.lukapg_security_header
  id = "e392a344536e78c92935b787d58c8ad2/security_header"
}

import {
  to = cloudflare_zone_setting.tnz["ssl"]
  id = "f097b5d7910b67d2f644219fc01ff7c1/ssl"
}

import {
  to = cloudflare_zone_setting.tnz["always_use_https"]
  id = "f097b5d7910b67d2f644219fc01ff7c1/always_use_https"
}

import {
  to = cloudflare_zone_setting.tnz["min_tls_version"]
  id = "f097b5d7910b67d2f644219fc01ff7c1/min_tls_version"
}

import {
  to = cloudflare_zone_setting.tnz["tls_1_3"]
  id = "f097b5d7910b67d2f644219fc01ff7c1/tls_1_3"
}

import {
  to = cloudflare_zone_setting.tnz["security_level"]
  id = "f097b5d7910b67d2f644219fc01ff7c1/security_level"
}

import {
  to = cloudflare_zone_setting.tnz["orange_to_orange"]
  id = "f097b5d7910b67d2f644219fc01ff7c1/orange_to_orange"
}

import {
  to = cloudflare_zone_setting.tnz_security_header
  id = "f097b5d7910b67d2f644219fc01ff7c1/security_header"
}
