# Tendo Translations 🌍

**Help Tendo speak your language. Preferably without sounding like a confused robot. 🤖**

Hey there! I'm building **Tendo**, a calm planning and focus app for iPhone, iPad, and Apple Watch. I make it independently, here in Slovenia, with a lot of care and — on some days — more coffee than strictly necessary.

I want Tendo to feel natural in more languages. An automatic translation can get the words right and the meaning hilariously wrong. If you spot one of those moments, I'd genuinely appreciate your help.

**If you speak a language, you're already qualified to help.** You don't need to know Swift, use Xcode, or open a Pull Request to suggest a correction.

## Find your way in

| I want to… | Start here |
|---|---|
| Fix one awkward sentence | [Report a translation problem](.github/ISSUE_TEMPLATE/report-translation.yml) (then go to **Issues → New issue** to submit it) |
| Browse English and translated drafts side by side | [Readable proofreading pages](docs/proofreading/README.md) — choose a language and batch |
| Help translate or proofread | [Offer translation help](.github/ISSUE_TEMPLATE/offer-help.yml) or read [Translating](TRANSLATING.md) |
| Request another language | [Request a new language](.github/ISSUE_TEMPLATE/request-language.yml) |
| Edit `.xcstrings` in Git | Read [Contributing](CONTRIBUTING.md) and open a Pull Request |

Or just open **Issues → New issue** here on GitHub. Choose whichever form fits. I personally review proposed language additions and contributions before any application integration.

## Languages and progress

English remains Tendo's source/fallback language. The seven additional languages now have **complete, sanitized AI-assisted drafts in the public String Catalogs**. These are proposals for proofreading, **not independently verified translations or shipped-language claims**.

| Language | Main UI draft | Permission/app-name draft | App Shortcuts draft | Human approved | Released |
|---|---:|---:|---:|---:|---|
| [Slovenian (`sl`)](docs/proofreading/sl/README.md) | 2,387/2,387 | 6/6 | 17/17 | 0/2,410 | Not verified |
| [German (`de`)](docs/proofreading/de/README.md) | 2,387/2,387 | 6/6 | 17/17 | 0/2,410 | Not verified |
| [Croatian (`hr`)](docs/proofreading/hr/README.md) | 2,387/2,387 | 6/6 | 17/17 | 0/2,410 | Not verified |
| [Italian (`it`)](docs/proofreading/it/README.md) | 2,387/2,387 | 6/6 | 17/17 | 0/2,410 | Not verified |
| [Hungarian (`hu`)](docs/proofreading/hu/README.md) | 2,387/2,387 | 6/6 | 17/17 | 0/2,410 | Not verified |
| [Japanese (`ja`)](docs/proofreading/ja/README.md) | 2,387/2,387 | 6/6 | 17/17 | 0/2,410 | Not verified |
| [Korean (`ko`)](docs/proofreading/ko/README.md) | 2,387/2,387 | 6/6 | 17/17 | 0/2,410 | Not verified |

That's **16,870 AI draft entries**, across the three catalogs in seven language folders. The private source contains one technical placeholder entry excluded from the public main catalog. This snapshot also includes draft release-note wording; inclusion here does not announce or verify future app features.

Review work is divided into **53 focused batches per language**, most up to 75 strings, beginning with permissions, spoken accessibility strings, Focus, Siri/App Shortcuts, and notifications. Browse the [readable side-by-side review pages](docs/proofreading/README.md), see [how to pick a batch](review/README.md), the [review policy](docs/REVIEW-POLICY.md), and the [live, validation-derived status](docs/TRANSLATION-STATUS.md).

Existing public translation corrections were retained. The automated checks safeguard the files; **only independent human reviews with evidence and matching text hashes** increase the human-approved count. No independent sign-offs are recorded yet. App release support requires separate Apple-platform testing and release approval.

## How translating works

1. Choose your language folder under [`locales/`](locales/) and, optionally, a [review batch](review/README.md).
2. Open its `.xcstrings` files in a compatible editor — [String Studio](https://github.com/L1cardo/String-Studio) is one option — or review them directly on GitHub.
3. Improve the *target-language* wording. Keep the English reference, keys, parameters and plural rules exactly as they are. Check the [glossary](docs/GLOSSARY.md).
4. Open a Pull Request **for one language**, or use a GitHub Issue if that's easier. Please add a short explanation for anything subtle.
5. I'll run the automated checks, arrange human review where possible, and then consider the translation for a separately tested Tendo build.

Don't see a string you expected? This is a **frozen development snapshot**, not live synchronization with private Tendo. [Report the missing wording](.github/ISSUE_TEMPLATE/report-translation.yml) without including personal information or private source code.

[Complete editor instructions](TRANSLATING.md) · [New languages](docs/NEW-LANGUAGES.md) · [Review policy](docs/REVIEW-POLICY.md)

## What happens after you contribute?

A green validation check means a file is structurally safe to review — **not** that its grammar is perfect. I review the submitted wording, check for stale changes against Tendo's private source, and validate any approved integration with Apple's build and localization tools. Translation contributions do **not** automatically change the app or trigger a release.

If you'd like to be credited, I can list your chosen public name or GitHub handle in [CONTRIBUTORS.md](CONTRIBUTORS.md); it's always optional. I don't expect you to work for free on demand, and it's absolutely fine to help with one tiny word.

## Privacy and licenses

Tendo's application source remains private. This repository contains only sanitized public-facing translation catalogs, review records and small offline validation tools. **Please don't post screenshots of real personal tasks, appointments, backup data, or account details.** If you need to report something sensitive, read [SECURITY.md](SECURITY.md).

Your own translation contributions are offered under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) to the extent you hold applicable rights, including reuse in free or commercial Tendo versions. The separate validation scripts are [MIT-licensed](LICENSE-CODE). Tendo's original English text, name, logos, and app are **not** open-sourced by this repository. Read [LICENSING.md](LICENSING.md) before contributing.

Thanks for making Tendo feel a little more at home, wherever home is for you.

**Made with ❤️ in Slovenia**
