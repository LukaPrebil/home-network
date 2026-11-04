terraform {
  # OpenTofu 1.13. Same floor as iac/object-store: 1.13 is what introduced the
  # state encryption this root enforces (encryption.tf), and import blocks need
  # 1.5 or newer, so the floor is not slack - it is the first version where the
  # committed tree works as written.
  required_version = ">= 1.13"

  required_providers {
    cloudflare = {
      source = "cloudflare/cloudflare"
      # Pinned in .terraform.lock.hcl as well. The constraint only bounds an
      # explicit `init -upgrade`, so a routine init cannot move the provider
      # version the state was written with. The 5.x line is the one that
      # replaced the v4 `zone_id` string arguments with the nested `zone = {}`
      # / `account = {}` objects this root is written against.
      version = "~> 5.28"
    }
  }
}

# Comment-only edit; here so a push touches iac/ and triggers the plan job.
