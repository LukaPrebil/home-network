# Inputs that are not credentials
#
# The S3 keys and the state passphrase arrive as TF_VAR_/AWS_ environment
# variables through `sops exec-env iac/secrets.sops.yaml 'tofu ...'`, so nothing
# here has a default and nothing here is written into a var file.

variable "state_passphrase" {
  description = <<-EOT
    Passphrase for OpenTofu state encryption at rest (pbkdf2, minimum 16
    characters). Supplied as TF_VAR_state_passphrase by sops exec-env.
  EOT
  type        = string
  sensitive   = true
  nullable    = false
}
