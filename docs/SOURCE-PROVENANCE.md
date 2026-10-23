# Public export provenance and boundaries

This is a *sanitized selection* from Tendo's localization work-in-progress, prepared on 23 October 2026. It is **not a fork** of the private application repository, does not contain its `.git` directory or source files, and makes no assertion about release availability.

Public main UI pack: **253** initial draft keys per locale. Five pre-release What's New keys and the rest of the private main catalog are not included. Public permission catalog: **3** keys; public Siri/App Shortcuts catalog: **17** keys. The English reference and original key IDs are preserved, but internal Swift-file path references have been replaced with public-safe translator comments. The original internal comment text is *not* published.

The protected [`export-baseline.json`](export-baseline.json) stores only an allowlist and SHA-256 digests of relevant localized values/source references. These support structural validation and stale-change detection; they are **not encrypted backups** and should not be treated as proof of editorial quality. This baseline is maintained by the developer, not updated in contributor PRs.

Contributions must be checked against the private source on a trusted local machine before integration. The public [`prepare_private_import.py`](../tools/prepare_private_import.py) prepares a **dry-run proposal only**; it does not modify Tendo. Private project paths, actual app build records, and confidential handoff metadata must remain outside this repository.
