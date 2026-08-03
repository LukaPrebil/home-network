# Security Policy

## What this repository is

This is the configuration for a personal homelab. It is published as a
reference for people building something similar, not as a supported project.
There is no release cadence, no security support window, and no guarantee that
any part of it is a good fit for your network. Read it, borrow from it, but
review anything you adopt before pointing it at your own infrastructure.

## Secrets

Tracked files hold no plaintext secrets by design. Sensitive values live in
`ansible/secrets.yml`, encrypted with ansible-vault (AES256). The vault password
itself is read from a `.vault_pass` file that is gitignored and never committed,
so a clone of this repository cannot decrypt anything.

Everything else that looks like a credential in the tracked files is a
placeholder in a `*.example` file, or a Jinja template variable that gets filled
in from the vault at deploy time.

Commits are scanned for secrets two ways: a gitleaks pre-commit hook on staged
changes, and a full-history gitleaks and TruffleHog scan in CI. History is
scanned rather than just the diff, because a secret removed from the working
tree still ships to anyone who clones the repository.

## Reporting a vulnerability

If you find a real vulnerability, or believe a secret was committed here,
please report it privately through GitHub's private vulnerability reporting:

https://github.com/LukaPrebil/home-network/security/advisories/new

Please do not open a public issue for security problems. Since this is a
personal project maintained in spare time, expect a response in days rather
than hours.
