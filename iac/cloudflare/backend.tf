# Remote state in the RustFS bucket, same pattern as iac/object-store/backend.tf.
#
# Nothing lives on disk: if a terraform.tfstate appears in this directory the
# backend failed to load and the local file is stale - treat that as an error,
# not as a fallback.
#
# use_lockfile gives optimistic locking through S3 conditional writes, so the
# apply workflow (iac-apply.yml) and an operator's plan cannot interleave. The
# estate has no DynamoDB, and the S3-compatible endpoint has no table service to
# point at, so lockfile-based locking is the only option here.
terraform {
  backend "s3" {
    bucket = "terraform-state"
    key    = "cloudflare.tfstate"
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
