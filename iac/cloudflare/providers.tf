provider "cloudflare" {
  # No token argument, by design: CLOUDFLARE_API_TOKEN arrives from
  # `sops exec-env iac/secrets.sops.yaml 'tofu ...'` and the provider picks it up
  # from the environment. A token written into a provider block lands in state;
  # an environment variable does not.
  #
  # account_id is the one thing the provider cannot infer: the zones, the Access
  # applications and the account rulesets all live under it, and v5 takes it per
  # resource. Passing it here keeps the default for every resource that nests an
  # `account = {}` block.
  account_id = var.cloudflare_account_id
}
