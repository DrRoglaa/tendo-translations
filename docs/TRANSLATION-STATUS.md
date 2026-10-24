# Tendo translation status — AI-assisted drafts

**Snapshot:** 24 October 2026 private development catalogs, sanitized for public proofreading.
**This measures file coverage, not human accuracy or released app availability.**

| Language | Main UI AI draft | Info.plist AI draft | Siri AI draft | Human-approved | Stale reviews | Public release |
|---|---:|---:|---:|---:|---:|---|
| Slovenian (`sl`) | 2387/2387 | 6/6 | 17/17 | 0/2410 | 0 | Not verified |
| German (`de`) | 2387/2387 | 6/6 | 17/17 | 0/2410 | 0 | Not verified |
| Croatian (`hr`) | 2387/2387 | 6/6 | 17/17 | 0/2410 | 0 | Not verified |
| Italian (`it`) | 2387/2387 | 6/6 | 17/17 | 0/2410 | 0 | Not verified |
| Hungarian (`hu`) | 2387/2387 | 6/6 | 17/17 | 0/2410 | 0 | Not verified |
| Japanese (`ja`) | 2387/2387 | 6/6 | 17/17 | 0/2410 | 0 | Not verified |
| Korean (`ko`) | 2387/2387 | 6/6 | 17/17 | 0/2410 | 0 | Not verified |

Each additional language has **2,410** public entries; the seven languages have **16,870** translated-state entries in total.

Review work is organized into **53 functional batches per language** (up to 75 keys each).
Independent sign-offs are recorded only by a maintainer in `review/languages/<locale>.json` with public evidence and exact source/translation hashes.
A changed English source or reviewed target automatically invalidates a sign-off until it is checked again.

There are currently **no independently documented human approvals**. Existing owner corrections are retained but do not constitute a complete language review.
The private source is a development snapshot; these draft keys, including release-note text, do not establish public Tendo feature or language availability.
String Studio/Xcode round trips, device layouts, accessibility, spoken strings and app release checks still require separate Mac validation.

See [review batches](../review/README.md), [review policy](REVIEW-POLICY.md), and [source provenance](SOURCE-PROVENANCE.md).
