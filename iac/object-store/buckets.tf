# The one bucket this root owns. It is also where this root's own state lives
# (backend.tf), which is why the root is applied once against a local backend
# and then migrated into the bucket it just created - see
# docs/infrastructure/object-storage.md.
resource "aws_s3_bucket" "state" {
  bucket = "terraform-state"

  # A bad plan must not be able to delete the bucket that holds the state of
  # every other root. Removing this resource is a manual, deliberate act:
  # remove the lifecycle block, apply, then destroy by hand.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  # Versioning is the rollback path for a corrupt or half-written state file:
  # every apply overwrites the previous object, and the previous version is the
  # one to restore.
  versioning_configuration {
    status = "Enabled"
  }
}
