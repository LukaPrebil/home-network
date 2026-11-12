# Import blocks: the first apply is a pure import, and recovery depends on them
#
# The bucket and its versioning already exist. This root adopted them through a
# local-backend bootstrap (docs/infrastructure/object-storage.md), so nothing
# here created them.
#
# These blocks stay in the tree after the first apply. Once an address is in
# state they are no-ops, and their remaining value is recovery: if the state
# object is ever lost, re-running apply re-adopts the same bucket by name
# instead of planning `2 to add` and adopting an empty container. That failure
# mode is the one `prevent_destroy` cannot see - the guard is state-dependent,
# so an empty state destroys nothing and the plan looks clean.
#
# The id is the bucket name, a literal rather than a reference, because a
# recovered state cannot resolve a reference to an object it does not have.

import {
  to = aws_s3_bucket.state
  id = "terraform-state"
}

import {
  to = aws_s3_bucket_versioning.state
  id = "terraform-state"
}
