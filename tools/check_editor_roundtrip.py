#!/usr/bin/env python3
"""Check an optional String Studio/Xcode .xcstrings editor round-trip offline.

Compare a BEFORE catalog and an edited AFTER file without replacing either.
Only one target locale's localized values/states may change; all English references,
key lists, comments, metadata, plural categories and Siri alternatives are protected.
This is structural validation, NOT a substitute for an actual macOS editor test.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

from validate_translations import CATALOGS, PLURALS, load_json, validate_catalog


def compare(before: Path, after: Path, lang: str, name: str, baseline: dict) -> tuple[list[str],int]:
    errors=validate_catalog(before,lang,baseline,name)
    errors+=validate_catalog(after,lang,baseline,name)
    if errors:return errors,0
    a=load_json(before)
    b=load_json(after)
    changed=0
    for key in a['strings']:
        left=copy.deepcopy(a['strings'][key])
        right=copy.deepcopy(b['strings'][key])
        x=left['localizations'].pop(lang)
        y=right['localizations'].pop(lang)
        if left!=right:
            errors.append(f'{name}/{key}: editor changed a protected English reference or catalog field')
        if x!=y:
            changed+=1
    return errors,changed


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--language',choices=sorted(PLURALS),required=True)
    parser.add_argument('--catalog',choices=CATALOGS,required=True)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    try:
        base=load_json(args.repo/'docs/export-baseline.json')
        errors,changed=compare(args.before,args.after,args.language,args.catalog,base['catalogs'][args.catalog])
    except (OSError,ValueError,TypeError,KeyError) as exc:
        errors,changed=[str(exc)],0
    for e in errors[:25]:print('FAIL',e)
    if errors:
        print(f'FAIL: editor round-trip ({len(errors)} structural or placeholder error(s))');return 1
    print(f'PASS: {changed} target-localization entry/entries changed; protected metadata is intact')
    print('Not a human-language review or proof of macOS String Studio/Xcode compatibility')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
