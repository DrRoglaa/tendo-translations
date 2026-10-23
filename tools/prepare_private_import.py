#!/usr/bin/env python3
"""Offline dry-run: compare community edits with *local* private String Catalogs.

This tool NEVER writes to or modifies Tendo. It can produce an isolated change
proposal in JSON for separate maintainer review, approval and Xcode testing.
Run only on your own trusted machine. Do not upload its private paths/output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from validate_translations import CATALOGS, canonical, load_json, sha, validate


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-catalogs',required=True,type=Path,help='Local Tendo/Localization directory; read only')
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--language',required=True,choices=('sl','de','hr','it','hu','ja','ko'))
    parser.add_argument('--output',type=Path,help='Optional NEW local JSON proposal path, outside the public repository')
    args=parser.parse_args()
    root=args.repo.resolve()
    errors,_=validate(root,root/'docs/export-baseline.json')
    if errors:
        print('Public pack failed validation:', *errors[:20],sep='\n');return 1
    base=load_json(root/'docs/export-baseline.json')
    diffs=[];conflicts=[]
    for catalog in CATALOGS:
        current=load_json(args.private_catalogs/catalog)
        public=load_json(root/'locales'/args.language/catalog)
        scope=base['catalogs'][catalog]
        for key,provided in public['strings'].items():
            if key not in current.get('strings',{}):
                conflicts.append(f'{catalog}/{key}: private key removed');continue
            actual=current['strings'][key].get('localizations',{})
            if sha(actual.get('en')) != scope['english'][key]:
                conflicts.append(f'{catalog}/{key}: English reference changed');continue
            initial=scope['initial_targets'][args.language][key]
            updated=provided['localizations'][args.language]
            updated_hash=sha(updated)
            if updated_hash==initial:continue
            current_hash=sha(actual.get(args.language))
            if updated_hash==current_hash:continue  # Already integrated, no action
            if current_hash!=initial:
                conflicts.append(f'{catalog}/{key}: private translation changed since export');continue
            diffs.append({'catalog':catalog,'key':key,'language':args.language,'new_localization':updated})
    print(f'{args.language}: proposed changes={len(diffs)}, stale/source conflicts={len(conflicts)}')
    for msg in conflicts[:30]:print('CONFLICT',msg)
    if conflicts:
        print('STOP: reconcile differences with the private source; no proposal written')
        return 2
    if args.output:
        dest=args.output.resolve()
        if root==dest or root in dest.parents:
            print('Refusing to write a private-import proposal inside the public repository');return 2
        try:
            with dest.open('x',encoding='utf-8') as fd:
                json.dump({'format':1,'language':args.language,'changes':diffs},fd,ensure_ascii=False,indent=2)
                fd.write('\n')
        except FileExistsError:
            print('Output already exists. Choose a new path; nothing overwritten.');return 2
        print(f'Isolated proposal written: {dest} (not applied to Tendo)')
    else:
        print('Dry-run only; use --output to produce an isolated review proposal')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
