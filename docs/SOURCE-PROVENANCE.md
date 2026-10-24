# Public export provenance and boundaries

This is a **sanitized, complete AI-assisted draft** extracted from an offline private Tendo development snapshot dated **24 October 2026**. It is **not** a fork of private Tendo and contains no Swift/Xcode project, original Git history, user data, or private source-file comments. It contains 2,387 main UI keys, six Info.plist keys, and 17 App Shortcuts keys per language. One intentionally empty technical `%@` entry was excluded from the main UI catalog.

The original local development snapshot contained uncommitted localization work. The public export is tied to exact **SHA-256 fingerprints of those input catalog files**, not a claim that a private commit was already reviewed or released. The hashes are recorded in the protected [`export-baseline.json`](export-baseline.json) and repeated below for independent source-handoff comparison:

| Private input catalog | SHA-256 of snapshot bytes |
|---|---|
| `Localizable.xcstrings` | `fd14c0d3a568d6dbe6487d69f006abacd0f18ba10b9fab5a56c4f6111b2c117c` |
| `InfoPlist.xcstrings` | `543427d067327340441c74cb631cd0f7d606f071f3b86e60cb47e451ed121c31` |
| `AppShortcuts.xcstrings` | `966a72aad5a411d5eb1d35cc33070164db1413de1c2fd8d5357f85fadd6bbead` |

Public `en` references and original semantic keys are preserved. Internal Swift-file references in comments were not copied: feature-based public-safe comments are used instead. Previously published public values and corrections take precedence over newer AI text when the English source is unchanged; a mismatch in English source blocks export for manual reconciliation. The protected baseline captures English/source hashes and private export-time target hashes for later three-way, read-only import proposals. It is not encrypted and is **not** a quality approval record.

The snapshot may contain wording describing development, future, or not-yet-shipped features, including What's New text. Presence in this public translation workspace must **never** be used as evidence that a feature or language has shipped. Maintain this boundary at GitHub publication review.

Translation contributions remain a separate workflow: reviewer evidence is maintained under [`review/`](../review/README.md), all ordinary community PRs remain limited to one language, and importing **human-approved** corrections requires the latest authoritative private Tendo source, explicit approval, and independent Apple-platform verification. Never publish private build logs, paths, secrets, backups or PR handoff files here.
