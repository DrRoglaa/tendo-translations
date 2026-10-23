# How translation review works

I want translations to sound like a person wrote them for Tendo — not like a dictionary was dropped into a blender.

## Four distinct states

1. **Publicly exported:** a string has been cleared for inclusion in this translation-only repository. This does not mean translated.
2. **Technically present:** a target value exists and its String Catalog state is `translated`. This is a machine-checkable state, **not an endorsement of the wording**.
3. **Human reviewed:** a competent speaker has independently checked meaning, tone, UI context, grammar, placeholders, and plural forms. Public summary status changes only after a maintainer records evidence.
4. **Released:** the language has been validated in a specific distributed Tendo version on applicable devices. A GitHub PR or Xcode language setting does not establish release availability.

## What I check before accepting text

- The correction fits the actual screen, meaning, and calm Tendo voice.
- Glossary terminology stays consistent across Now, Today, Tasks, Week, Routines, Focus and Watch.
- Placeholders, dates/times, grammatical gender and plurals are handled correctly.
- Longer words still fit; where applicable the app is checked with Dynamic Type, VoiceOver, iPad layouts and Watch layouts.
- The private import reports no stale English references or concurrent target changes.
- A reviewed version is built/tested separately in Tendo before a shipping-language claim.

Please don't self-report a locale as fully validated by editing this file or [TRANSLATION-STATUS.md](TRANSLATION-STATUS.md). I maintain those status fields independently of contributor catalog edits.
