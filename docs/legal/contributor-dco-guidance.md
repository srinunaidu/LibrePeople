# Contributor DCO Guidance

> PREPARED-ONLY note: proposed process only. No Contributor Licence
> Agreement (CLA) exists or is required. The intended licence direction
> (AGPL-3.0-or-later, PROPOSED) has no legal effect until a root
> `LICENSE` is published with clearance.

## DCO, not CLA

- This project uses the Developer Certificate of Origin (DCO).
- There is **no CLA** to sign — do not invent one, and do not ask
  contributors to sign any agreement beyond the DCO sign-off.

## How to sign off

- Sign every commit with `Signed-off-by` using `git commit -s`:

  ```sh
  git commit -s -m "scope: concise description"
  ```

- This appends a trailer such as:

  ```text
  Signed-off-by: Your Name <you@example.com>
  ```

- For a series, sign each commit (`git rebase --signoff` can retrofit).
- The `Signed-off-by` trailer certifies, per the DCO 1.1 text
  (<https://developercertificate.org/>), that you wrote the change or
  have the right to contribute it, and that you agree to its
  contribution under the project's (proposed) terms.

## What reviewers check

- Every commit in the PR carries a `Signed-off-by` trailer.
- The sign-off identity plausibly matches the author.
- Third-party code is only accepted with a compatible licence and its
  provenance recorded in `docs/legal/` (see `CONTRIBUTING.md`
  "Third-party rules").

## If sign-off is missing

- The PR will be asked to re-push with sign-offs (`git commit -s`
  / `git rebase --signoff`) — no merge until every commit is signed.
