# Tendo Translations 🌍

**Help Tendo speak your language. Preferably without sounding like a confused robot. 🤖**

Hey there! I'm building **Tendo**, a calm planning and focus app for iPhone, iPad, and Apple Watch. I make it independently, here in Slovenia, with a lot of care and — on some days — more coffee than strictly necessary.

I want Tendo to feel natural in more languages. An automatic translation can get the words right and the meaning hilariously wrong. If you spot one of those moments, I'd genuinely appreciate your help.

**If you speak a language, you're already qualified to help.** You don't need to know Swift, use Xcode, or open a Pull Request to suggest a correction.

## Find your way in

| I want to… | Start here |
|---|---|
| Fix one awkward sentence | [Report a translation problem](.github/ISSUE_TEMPLATE/report-translation.yml) (then go to **Issues → New issue** to submit it) |
| Help translate or proofread | [Offer translation help](.github/ISSUE_TEMPLATE/offer-help.yml) or read [Translating](TRANSLATING.md) |
| Request another language | [Request a new language](.github/ISSUE_TEMPLATE/request-language.yml) |
| Edit `.xcstrings` in Git | Read [Contributing](CONTRIBUTING.md) and open a Pull Request |

Or just open **Issues → New issue** here on GitHub. Choose whichever form fits. I personally review proposed language additions and contributions before any application integration.

## Languages and progress

English is Tendo's source/fallback language. These seven languages have **early AI-assisted drafts**:

| Language | Public UI starter pack | Human proofreading | Released availability |
|---|---:|---|---|
| Slovenian (`sl`) | 253/253 draft entries | Not independently reviewed | Not verified |
| German (`de`) | 253/253 draft entries | Not independently reviewed | Not verified |
| Croatian (`hr`) | 253/253 draft entries | Not independently reviewed | Not verified |
| Italian (`it`) | 253/253 draft entries | Not independently reviewed | Not verified |
| Hungarian (`hu`) | 253/253 draft entries | Not independently reviewed | Not verified |
| Japanese (`ja`) | 253/253 draft entries | Not independently reviewed | Not verified |
| Korean (`ko`) | 253/253 draft entries | Not independently reviewed | Not verified |

**Important:** 253/253 is the technical status of the *sanitized public starter pack only*, **not** full-app completion. The source development snapshot had 258 of 2,291 main UI entries marked translated (11.3%) in each additional language. Five pre-release release-note entries are not exported here; the remaining app strings have not yet been cleared for public export. Three permission strings and 17 App Shortcut phrases per language are also in the starter packs; those are unreviewed drafts too.

No translation in this repository has independent native-speaker sign-off. Nothing here should be interpreted as a confirmed App Store language release. See [full status and explanation](docs/TRANSLATION-STATUS.md).

## How translating works

1. Choose your language folder under [`locales/`](locales/).
2. Open its `.xcstrings` files in a compatible editor — [String Studio](https://github.com/L1cardo/String-Studio) is one option — or review them directly on GitHub.
3. Improve the *target-language* wording. Keep the English reference, keys, parameters and plural rules exactly as they are. Check the [glossary](docs/GLOSSARY.md).
4. Open a Pull Request **for one language**, or use a GitHub Issue if that's easier. Please add a short explanation for anything subtle.
5. I'll run the automated checks, arrange human review where possible, and then consider the translation for a separately tested Tendo build.

Don't see a string you want to translate? That's intentional: this repository contains a **sanitized selection**, not the entire private Tendo localization catalog. [Ask for its public inclusion](.github/ISSUE_TEMPLATE/report-translation.yml), giving the screen and visible wording without sharing personal data.

[Complete editor instructions](TRANSLATING.md) · [New languages](docs/NEW-LANGUAGES.md) · [Review policy](docs/REVIEW-POLICY.md)

## What happens after you contribute?

A green validation check means a file is structurally safe to review — **not** that its grammar is perfect. I review the submitted wording, check for stale changes against Tendo's private source, and validate any approved integration with Apple's build and localization tools. Translation contributions do **not** automatically change the app or trigger a release.

If you'd like to be credited, I can list your chosen public name or GitHub handle in [CONTRIBUTORS.md](CONTRIBUTORS.md); it's always optional. I don't expect you to work for free on demand, and it's absolutely fine to help with one tiny word.

## Privacy and licenses

Tendo's application source remains private. This repository contains only selected public-facing translation resources and simple offline validation tools. **Please don't post screenshots of real personal tasks, appointments, backup data, or account details.** If you need to report something sensitive, read [SECURITY.md](SECURITY.md).

Your own translation contributions are offered under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) to the extent you hold applicable rights, including reuse in free or commercial Tendo versions. The separate validation scripts are [MIT-licensed](LICENSE-CODE). Tendo's original English text, name, logos, and app are **not** open-sourced by this repository. Read [LICENSING.md](LICENSING.md) before contributing.

Thanks for making Tendo feel a little more at home, wherever home is for you.

**Made with ❤️ in Slovenia**
