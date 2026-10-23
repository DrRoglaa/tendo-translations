# Contributing to Tendo translations

Thanks for being here. I appreciate everything from one corrected button label to a careful review of hundreds of strings.

## The easiest way

No Git knowledge is necessary. Go to **Issues → New issue** and pick **Report a Translation Problem**, **Offer Translation Help**, or **Request a New Language**. Write in English or the language you're contributing to. Please give enough context for me to understand the wording.

## Pull Request workflow

1. Read [TRANSLATING.md](TRANSLATING.md), the [glossary](docs/GLOSSARY.md) and the [review policy](docs/REVIEW-POLICY.md).
2. Fork the repository, or make a branch from an up-to-date copy. Name it something understandable, like `translation/sl-today-review`.
3. Edit **only one language** under `locales/<language>/` per PR, leaving all keys, comments, English references, and files in other languages untouched.
4. Run `python3 tools/validate_translations.py` and `python3 -m unittest discover -s tools -p 'test_*.py'` with Python 3.10 or newer.
5. Open a PR with the screen/context, what changed, and any uncertainty. The template will help.

Please do **not** modify the protected export baseline, workflow files, or scripts as part of a translation PR. If you spot a validation bug, open a separate Issue; maintainer-reviewed tooling updates follow a different process. A PR can contain more than one catalog (`Localizable`, `InfoPlist`, `AppShortcuts`) **for the same language**.

### Editing with String Studio

See [TRANSLATING.md](TRANSLATING.md) for practical steps. Different editors may reformat JSON; that's fine, but not if they remove keys or change English. If your editor rewrites unrelated languages, discard those unrelated changes before sending the files back. A macOS editor round trip has not yet been validated for these public packs.

## What I check

The automated checks cover JSON structure, the approved public key list, placeholders, the English reference, locale isolation, and plural structures. They can't judge whether a translation is natural or respectful. Before inclusion in Tendo, I check the human-reviewed wording and resolve concurrent edits against the latest private source.

Translation quality matters more than speed. If you are uncertain, explain your alternative rather than marking it fully reviewed.

## Community standards and licensing

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md), don't upload private data, and review [LICENSING.md](LICENSING.md): translation submissions must be available for Tendo to use, including in future commercial versions. Contributions are acknowledged only with consent. Please submit only work you can legally contribute; avoid copying from other apps or machine-translation services whose terms disallow reuse.

Thank you — every good translation makes the experience nicer for somebody.
