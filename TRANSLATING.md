# Translating Tendo

You can help without Swift, Xcode, or Git. If you only want to fix one word, just open **Issues → New issue → Report a Translation Problem**.

## Get a language pack

1. Open [`locales/`](locales/) and choose your language, for example [`sl`](locales/sl/).
2. Download the three `.xcstrings` files while preserving their filenames; on GitHub, open each file and use **Download raw file**. For a full pack, use **Code → Download ZIP** and extract only your language folder.
3. Keep a copy of the original files so you can review exactly what changed.
4. Open the files in a String Catalog-compatible editor. [String Studio](https://github.com/L1cardo/String-Studio) is one option; check that your installed version handles Apple's `.xcstrings` format and variation entries. Editors and versions can behave differently.

## Translate safely

- Edit only the **target language** (`sl`, `de`, `hr`, `it`, `hu`, `ja`, or `ko`). English (`en`) is the reference and fallback.
- Never rename keys, remove entries, change comments, or rewrite English. Developer comments in public packs are deliberately sanitized to protect private implementation details.
- Keep placeholder characters and types exactly: `%1$(count)lld`, `%1$(text)@`, `%@`, and `${applicationName}` are not prose. Do not translate names inside `${…}` or `(count)`.
- Keep the *meaning* of a sentence, not just a word-for-word sequence. Check the [glossary](docs/GLOSSARY.md).
- Check plurals, particularly Slovenian **dual**, Croatian **few**, and locale-specific endings; don't collapse grammatical branches to a single form.
- Preserve newline meaning, punctuation, and accessibility-friendly clarity. Avoid assumptions about a user's gender.
- Keep **Tendo** as Tendo. Follow official Apple platform terms where they exist.
- If you're not confident, leave a comment in the PR/Issue instead of claiming native-speaker validation.

The language packs are deliberately smaller than Tendo's entire private development catalog. Don't invent app keys or add translations for unreleased UI without discussing public export first.

## Return your work

**No Git experience:** Open **Issues → New issue → Report a Translation Problem**, provide the original text and your correction, or use **Offer Translation Help** for a larger set of edits. Avoid posting personal screenshots or real private task data. GitHub Issues do not accept `.xcstrings` as normal attachments in every browser; a PR is better for bulk edits.

**Using Git:** Edit files under exactly one `locales/<language>/` folder, run the offline validator, and open a Pull Request. Your editor may reorder JSON fields; reviewers prefer small, focused diffs. Use the [PR template](.github/pull_request_template.md).

## Review, stale files, and integration

The public validator checks technical structure, not writing quality. I won't merge changes that overwrite an updated English reference, inadvertently change another language, or break placeholders/plurals. Even a public PR that passes can become stale before it is brought into Tendo. The private import step compares English and previously exported target values, and **stops on conflicts rather than picking a winner**. I then run Xcode builds, localization tests, and human review before a release decision.

There is no Tendo account, translation API, telemetry, or live app synchronization involved in this workflow.

If something is confusing, please open an Issue. That's exactly what this project is for.
