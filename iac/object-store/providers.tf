# RustFS speaks the S3 API, so the AWS provider drives it.
#
# The endpoint is the literal VLAN 30 address on purpose. The CI path reaches
# the object store over the rpi4 subnet route, so resolving a hostname here
# would make every plan depend on AdGuard being up - and a DNS blip must not be
# able to fail a state read.
#
# Credentials are not declared: they arrive as AWS_ACCESS_KEY_ID /
# AWS_SECRET_ACCESS_KEY through `sops exec-env iac/secrets.sops.yaml 'tofu ...'`
# and the provider picks them up from the environment. A credential written into
# a provider block lands in state; an environment variable does not.
provider "aws" {
  region = "us-east-1"

  endpoints {
    s3 = "http://192.168.30.140:9000"
  }

  # RustFS serves path-style URLs, has no account metadata service, and does not
  # validate credentials or regions the way AWS does
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_region_validation      = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
}
