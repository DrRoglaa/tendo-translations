# Translating Tendo

You can help without Swift, Xcode, or Git. If you only want to fix one word, just open **Issues → New issue → Report a Translation Problem**.

## Choose a review batch

The [review guide](review/README.md) lists where to begin. A batch ID (for example `focus-01`) refers to an allowlisted collection of existing keys, not a second editable copy of the translations. Choose one language and one or two batches per PR. To see the list offline, run `python3 tools/review_tracking.py --language sl` (replace `sl` with your locale).

## Get a language pack

1. Open [`locales/`](locales/) and choose your language, for example [`sl`](locales/sl/).
2. Download the three `.xcstrings` files while preserving their filenames; on GitHub, open each file and use **Download raw file**. For a full pack, use **Code → Download ZIP** and extract only your language folder.
3. Keep a copy of the original files so you can review exactly what changed. Use the files from the current repository baseline, not an old ZIP.
4. Open the files in a String Catalog-compatible editor. [String Studio](https://github.com/L1cardo/String-Studio) is one option; **round-trip compatibility with Tendo's full catalogs has not yet been confirmed**. Verify plurals, typed placeholders, Siri `stringSet` phrases and metadata. If the editor rewrites other languages or source metadata, use a text-only correction/Issue instead.

## Optional String Studio round-trip check

When using String Studio or another catalog editor, save an untouched copy of the original file. After editing (but **before** replacing the public version), validate the two files with the trusted offline utility:

```sh
python3 tools/check_editor_roundtrip.py \
  --before path/to/original/Localizable.xcstrings \
  --after path/to/edited/Localizable.xcstrings \
  --language sl --catalog Localizable.xcstrings
```

The command checks that the English reference, keys, metadata, plural categories and placeholders remain valid. It supports JSON reordering and target-wording edits. Repeat for `InfoPlist.xcstrings` or `AppShortcuts.xcstrings` as needed. **This does not establish that String Studio itself passed a macOS GUI round trip**: inspect the editor's results, especially `stringSet` Siri phrases and non-English plural categories, and run the normal validator too. Apple also documents [Xcode localization export/import](https://developer.apple.com/documentation/xcode/exporting-localizations), but raw `.xcloc` packages can include `Source Contents` from the app; **do not upload private Tendo `.xcloc` packages** to this public repository.

## Translate safely

- Edit only the **target language** (`sl`, `de`, `hr`, `it`, `hu`, `ja`, or `ko`). English (`en`) is the reference and fallback.
- Never rename keys, remove entries, change comments, or rewrite English. Developer comments in public packs are deliberately sanitized to protect private implementation details.
- Keep placeholder characters and types exactly: `%1$(count)lld`, `%1$(text)@`, `%@`, and `${applicationName}` are not prose. Do not translate names inside `${…}` or `(count)`.
- Keep the *meaning* of a sentence, not just a word-for-word sequence. Check the [glossary](docs/GLOSSARY.md).
- Check plurals, particularly Slovenian **dual**, Croatian **few**, and locale-specific endings; don't collapse grammatical branches to a single form.
- Preserve newline meaning, punctuation, and accessibility-friendly clarity. Avoid assumptions about a user's gender.
- Keep **Tendo** as Tendo. Follow official Apple platform terms where they exist.
- If you're not confident, leave a comment in the PR/Issue instead of claiming native-speaker validation.

The public packs contain all 2,410 translatable entries from the approved AI-draft snapshot for each language, including draft release-note wording. They are **not** guaranteed to match Tendo's latest private development state or released features. Don't invent keys or add unreleased UI yourself.

## Return your work

**No Git experience:** Open **Issues → New issue → Report a Translation Problem**, provide the original text and your correction, or use **Offer Translation Help** for a larger set of edits. Avoid posting personal screenshots or real private task data. GitHub Issues do not accept `.xcstrings` as normal attachments in every browser; a PR is better for bulk edits.

**Using Git:** Edit files under exactly one `locales/<language>/` folder, run the offline validator, and open a Pull Request. Mention the batch ID(s). Editors may reorder JSON fields; avoid unrelated edits and review your diff before opening the PR. Use the [PR template](.github/pull_request_template.md). Do **not** edit `review/`, the protected baseline, scripts, workflow files or documentation in translation PRs.

## Review, stale files, and integration

The public validator checks technical structure, not writing quality. I won't merge changes that overwrite an updated English reference, inadvertently change another language, or break placeholders/plurals. Even a public PR that passes can become stale before it is brought into Tendo. The private import step compares English and previously exported target values, **requires a recorded independent human review before proposing a correction**, and **stops on conflicts rather than picking a winner**. Review status is recorded by the maintainer after checking the relevant public Issue/PR; it is not based on the String Catalog `translated` state. I then run Xcode builds, localization tests, and human review before a release decision.

There is no Tendo account, translation API, telemetry, or live app synchronization involved in this workflow.

If something is confusing, please open an Issue. That's exactly what this project is for.
