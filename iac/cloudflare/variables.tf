# Inputs that are not credentials
#
# CLOUDFLARE_API_TOKEN and the S3 key arrive as environment variables through
# `sops exec-env iac/secrets.sops.yaml 'tofu ...'`, so nothing here has a
# default and nothing here is written into a var file.

variable "state_passphrase" {
  description = <<-EOT
    Passphrase for OpenTofu state encryption at rest (pbkdf2, minimum 16
    characters). Supplied as TF_VAR_state_passphrase by sops exec-env.
  EOT
  type        = string
  sensitive   = true
  nullable    = false
}

variable "cloudflare_account_id" {
  description = <<-EOT
    The one Cloudflare account both zones belong to. Not a credential - it
    appears in every API URL and in the state - so it is a plain default
    rather than another SOPS key. Override it to run this root against a
    different account.
  EOT
  type        = string
  nullable    = false
  default     = "8c4bb66b8910ded785480b1599dac8e2"
}
