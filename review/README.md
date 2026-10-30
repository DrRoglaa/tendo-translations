# Community proofreading batches

Welcome! You can help improve Tendo with **one word, one batch, or one full language**. All 2,410 strings per additional language are **AI-assisted drafts** awaiting independent human review; Xcode's `translated` state does not indicate approval.

## Pick a language and a batch

1. Pick a language in the [readable side-by-side proofreading pages](../docs/proofreading/README.md), or a folder under [`locales/`](../locales/) (`sl`, `de`, `hr`, `it`, `hu`, `ja`, `ko`).
2. Open that language's batch page (or choose a batch ID in [`batches.json`](batches.json)). These are **key lists only**, not editable translations; the same 53 batches are available for each language. Start with `permissions-app-identity-01`, `accessibility-01`, `focus-01`, `siri-shortcuts-01`, or `notifications-01`.
3. Read the English and target text side by side; check the meaning and tone, then verify any correction against the current `.xcstrings` file. For a batch with plural variations, review **every** grammatical branch.
4. Propose improvements in an Issue or a PR changing **one language only**. Put the batch ID(s) in the description and say what context was checked. You can contribute without Git or Xcode.
5. A maintainer validates the changes, obtains independent review, and **separately** records review evidence. No contributor should edit a review ledger or declare a language approved in the files.

On a local clone, list batches and current approval progress with:

```sh
python3 tools/review_tracking.py --language sl
```

Replace `sl` with your language. The generated Markdown pages are read-only, may lag recent merged changes, and are refreshed by the maintainer; never edit them in a translation PR. A batch can be split across several small PRs; review status is computed per key rather than by assuming every key in a batch was reviewed.

## What gets recorded?

`languages/<locale>.json` holds **only actual independent human approvals**. Each protected record identifies a catalog/key, review date, consented public reviewer handle or pseudonym, public evidence URL, and SHA-256 fingerprints of the exact English reference and target translation. An edit to either value automatically invalidates that sign-off until checked again; older records remain stale until replaced after fresh review; Git history retains previous evidence.

The seven ledgers start empty. A green validation check does **not** grant approval, and the maintainer never infers approval merely from a PR, a machine translation, or a language's presence in Tendo.

To check the technical coverage and actual human sign-offs:

```sh
python3 tools/translation_status.py
python3 tools/validate_translations.py
```

The [review policy](../docs/REVIEW-POLICY.md) explains how sign-offs are verified. String Studio is an optional editor; round-trip support for the expanded catalogs has not been verified on a Mac. See [Translating](../TRANSLATING.md) for safe editing and placeholders.
