# The state for this root lives in the bucket this root manages.
#
# Bootstrapping order, once: apply against the implicit local backend, then add
# this block and run `tofu init -migrate-state`. From then on there is no
# terraform.tfstate on disk - if one appears, the backend failed to load and the
# state on disk is stale.
#
# use_lockfile gives optimistic locking through S3 conditional writes, so two
# concurrent applies cannot interleave. There is no DynamoDB in the estate, and
# the S3-compatible endpoint has no table service to point at.
terraform {
  backend "s3" {
    bucket = "terraform-state"
    key    = "object-store.tfstate"
    region = "us-east-1"

    endpoint = "http://192.168.30.140:9000"

    use_path_style = true
    use_lockfile   = true

    skip_credentials_validation = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    # RustFS does not implement the SDK's trailing checksum headers
    skip_s3_checksum = true
  }
}
