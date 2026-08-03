# Publish via a new repository rather than an in-place visibility flip

Status: proposed (2026-08-03)

This repository is being open-sourced. The obvious path - rewrite the history to strip sensitive blobs, force-push, then flip visibility from private to public - does not work, because a force-push does not remove anything from GitHub. This was verified empirically against this very repository: the 2026-06-10 `git filter-repo` purge removed commits `08025e8` (a plaintext `secrets.yml` revision), `9bffd4e` (migration backups holding an OctoEverywhere printer key and a Cloudflare DNS API token) and `c5341a5` from the local object store, yet on 2026-08-03, roughly seven weeks later, all three still resolved through the GitHub API. Four sampled pull-request merge commits (`34dd760`, `b7e726f`, `991ecab`, `19d2d63`) showed the same split: absent locally, present on the forge. The mechanism is `refs/pull/*`, which GitHub manages internally and repository administrators cannot delete or update. Because those are real refs rather than dangling objects, the commits they pin are reachable and therefore never garbage-collected, and they stay browsable for as long as the repository exists. We therefore rename this repository to `home-network-private` (keeping it private, retaining all 54 pull-request discussions for our own archaeology) and create a fresh public `home-network`, pushing the cleaned history there. The new repository's object store never receives the contaminated objects, so residual exposure is structurally zero rather than time-bounded.

## Considered options

- **Rewrite in place, force-push, then flip to public** - rejected: the pre-rewrite commits remain reachable through `refs/pull/*` regardless of fork count or garbage-collection timing. Flipping visibility converts every one of them from owner-token-gated to unauthenticated in a single click. The zero-fork, never-public status of this repository genuinely eliminates the clone and fork channel and substantially weakens the short-SHA enumeration channel, but neither of those is the channel that matters here.
- **Rewrite in place, then open a GitHub Support ticket to purge cached views and pull-request refs, and wait for written confirmation before flipping** - rejected: this is GitHub's own documented remedy and it would work, but it makes publication depend on a multi-day human-in-the-loop process at a third party, for a strictly worse end state than simply pushing clean history somewhere clean.
- **Delete the existing repository outright and recreate it** - rejected: it reaches the same clean end state and additionally destroys the contaminated object store, but it permanently discards 54 pull-request discussions and is irreversible. Renaming achieves the same isolation for the published artifact while keeping that history readable.
- **Publish under a different name and leave the existing repository untouched** - rejected: forfeits the canonical repository name for no security benefit, since renaming already isolates the contaminated store.

## Consequences

- Pull requests #1 to #55 do not carry over. Their commit subjects survive as prose in the rewritten history, but the discussions live only in the private twin. Any `(#N)` reference in a published commit message points at a pull request the public repository does not have.
- `home-network-private` permanently retains the leaked objects in its object store and must never be made public. This is the status quo risk, unchanged, but it is now a standing constraint attached to a repository whose name invites less caution than the original did.
- Credential rotation is still mandatory and is not substituted by this decision. GitHub's guidance puts revocation ahead of any history rewriting, because rotation is the only step that is irreversible in our favour. The leaked Cloudflare DNS API token in particular must be revoked in the Cloudflare dashboard; abandoning the service that used it does not invalidate it.
- Local clone audits are structurally blind to this class of exposure. `git rev-list --all --objects` only ever sees the post-rewrite object store, which is precisely why `backups/ddns-updater/config.json` escaped both the June purge scope and its rotation list. Any future pre-publish audit must query the forge API, not the working clone.
- Stars, watchers and the repository creation date reset. With one star and one watcher, both our own, this cost is nil.

## Verification

Before flipping the new repository to public, confirm from a logged-out session that it serves nothing from the old one: the three known SHAs above must return 404 against the new repository, and a fresh clone must contain no `homeassistant/.storage/` path at any revision.
