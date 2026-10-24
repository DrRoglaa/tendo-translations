#!/usr/bin/env python3
"""Report AI draft coverage versus independent per-language human sign-off.

--write updates the maintainer-controlled markdown status report; --check verifies it.
The Xcode `translated` state never counts as human review or public app release.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from validate_translations import CATALOGS, load_json, validate
from review_tracking import validate_review

NAMES = {"sl":"Slovenian", "de":"German", "hr":"Croatian", "it":"Italian",
         "hu":"Hungarian", "ja":"Japanese", "ko":"Korean"}


def report(root: Path) -> str:
    base = load_json(root/"docs/export-baseline.json")
    errors, counts = validate(root,root/"docs/export-baseline.json")
    review_errors, review, batches = validate_review(root,base)
    if errors or review_errors:
        raise ValueError("Validation failure: " + "; ".join((errors+review_errors)[:5]))
    lines=["# Tendo translation status — AI-assisted drafts",
           "", "**Snapshot:** 24 October 2026 private development catalogs, sanitized for public proofreading.",
           "**This measures file coverage, not human accuracy or released app availability.**",
           "", "| Language | Main UI AI draft | Info.plist AI draft | Siri AI draft | Human-approved | Stale reviews | Public release |",
           "|---|---:|---:|---:|---:|---:|---|"]
    total=sum(len(base['catalogs'][name]['keys']) for name in CATALOGS)
    for lang in base['locales']:
        c=[f"{counts[f'{lang}/{name}']}/{len(base['catalogs'][name]['keys'])}" for name in CATALOGS]
        lines.append(f"| {NAMES[lang]} (`{lang}`) | {c[0]} | {c[1]} | {c[2]} | {review[lang]['approved']}/{total} | {review[lang]['stale']} | Not verified |")
    lines += ["",f"Each additional language has **{total:,}** public entries; the seven languages have **{sum(counts.values()):,}** translated-state entries in total.",
              "",f"Review work is organized into **{len(batches)} functional batches per language** (up to 75 keys each).",
              "Independent sign-offs are recorded only by a maintainer in `review/languages/<locale>.json` with public evidence and exact source/translation hashes.",
              "A changed English source or reviewed target automatically invalidates a sign-off until it is checked again.",
              "", "There are currently **no independently documented human approvals**. Existing owner corrections are retained but do not constitute a complete language review.",
              "The private source is a development snapshot; these draft keys, including release-note text, do not establish public Tendo feature or language availability.",
              "String Studio/Xcode round trips, device layouts, accessibility, spoken strings and app release checks still require separate Mac validation.",
              "", "See [review batches](../review/README.md), [review policy](REVIEW-POLICY.md), and [source provenance](SOURCE-PROVENANCE.md).", ""]
    return "\n".join(lines)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    opts=p.add_mutually_exclusive_group()
    opts.add_argument('--write',action='store_true')
    opts.add_argument('--check',action='store_true')
    args=p.parse_args()
    root=args.repo.resolve()
    try:
        output=report(root)
        dest=root/"docs/TRANSLATION-STATUS.md"
        if args.write:
            if dest.is_symlink():raise ValueError('Unsafe status file: symlink')
            dest.write_text(output,encoding='utf-8')
            print('Status markdown updated from validated catalogs and review ledger')
        elif args.check:
            if not dest.exists() or dest.read_text(encoding='utf-8')!=output:
                print('FAIL: review status report is stale',file=sys.stderr);return 1
            print('PASS: published status matches catalogs and actual human-review records')
        else:print(output)
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'FAIL: {exc}',file=sys.stderr);return 1

if __name__=='__main__':
    raise SystemExit(main())
