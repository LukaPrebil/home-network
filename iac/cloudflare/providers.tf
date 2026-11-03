provider "cloudflare" {
  # Deliberately empty.
  #
  # No token argument: CLOUDFLARE_API_TOKEN arrives from
  # `sops exec-env iac/secrets.sops.yaml 'tofu ...'` and the provider picks it up
  # from the environment. A token written into a provider block lands in state;
  # an environment variable does not.
  #
  # No account_id either: v5 dropped the provider-level account and takes
  # `account = { id = ... }` per resource, so the account is threaded through
  # var.cloudflare_account_id at the few resources that need it. Setting it in
  # two places would invite them to disagree.
}
