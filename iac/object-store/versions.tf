terraform {
  # OpenTofu 1.13. The repo's only IaC root today; the Cloudflare root follows
  # the same shape.
  required_version = ">= 1.13"

  required_providers {
    aws = {
      source = "hashicorp/aws"
      # Pinned in .terraform.lock.hcl as well: the constraint only bounds an
      # explicit `init -upgrade`, so a routine init cannot move the provider
      # version under the state.
      version = "~> 6.71"
    }
  }
}
