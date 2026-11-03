# What the other roots and the docs need to know about this one.
#
# These are deliberately few: a root that owns buckets should publish the
# bucket name and the endpoint, and nothing that a consumer could mistake for
# permission to manage the bucket itself.

output "state_bucket" {
  description = "Bucket holding every root's state, including this root's own."
  value       = aws_s3_bucket.state.bucket
}

output "endpoint" {
  description = "S3 endpoint the state backend and the AWS provider talk to."
  value       = "http://192.168.30.140:9000"
}

output "versioning_enabled" {
  description = "Whether bucket versioning is on, which is the state rollback path."
  value       = aws_s3_bucket_versioning.state.versioning_configuration[0].status == "Enabled"
}
