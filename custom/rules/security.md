# Secrets — team conventions

The part of upstream's `common/security.md` that holds in every repo here; the lean profile
installs this instead of `common/`. GCP specifics are in `gcp.md`.

- Never write a secret into code, a config file, a notebook, a commit message or a log:
  no API key, token, password, private key or full signed URL.
- Secrets come from the environment or a secret manager (Secret Manager on GCP, the
  Keychain on a Mac), read at runtime. A program checks at start that the ones it needs
  are there and fails with a message naming the missing one, never its value.
- `.env` files stay untracked; `.env.example` lists every variable with no values.
- A secret that was printed, committed or pasted anywhere shared is exposed: say so,
  rotate it, then remove it. Removing it alone does not help.
- Before a commit, look at the staged diff for anything that looks like a secret.
  gitleaks and detect-secrets catch most; they are not a reason to stop looking.
