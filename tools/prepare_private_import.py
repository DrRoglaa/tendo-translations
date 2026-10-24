#!/usr/bin/env python3
"""Prepare an OFFLINE, read-only, human-approved translation import proposal.

Compares protected export anchors, current public corrections, and latest PRIVATE
String Catalogs. It cannot write to Tendo. The JSON proposal is for a separate
approved, guarded Tendo integration and Xcode/device validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from validate_translations import CATALOGS, load_json, sha, validate
from review_tracking import validate_review, load_review_data


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-catalogs',required=True,type=Path,help='Local Tendo/Localization directory; read only')
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--language',required=True,choices=('sl','de','hr','it','hu','ja','ko'))
    parser.add_argument('--output',type=Path,help='Optional NEW local JSON proposal path, outside the public repository')
    args=parser.parse_args()
    root=args.repo.resolve()
    private=args.private_catalogs.resolve()
    if root == private or root in private.parents or private in root.parents:
        print('STOP: public and private directories must be separate');return 2
    errors,_=validate(root,root/'docs/export-baseline.json')
    review_errors,_,_=validate_review(root)
    if errors or review_errors:
        print('Public repository failed validation:', *(errors+review_errors)[:20],sep='\n');return 1
    base=load_json(root/'docs/export-baseline.json')
    _, ledgers, _ = load_review_data(root)
    approved={(r['catalog'],r['key']):r for r in ledgers[args.language]}
    diffs=[];conflicts=[];pending_review=0;already_integrated=0
    for catalog in CATALOGS:
        current=load_json(private/catalog)
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
            if updated_hash==current_hash:
                already_integrated+=1
                continue
            if current_hash!=initial:
                conflicts.append(f'{catalog}/{key}: private translation changed since export');continue
            evidence=approved.get((catalog,key))
            if evidence is None or evidence['source_hash']!=scope['english'][key] or evidence['target_hash']!=updated_hash:
                pending_review+=1
                continue
            diffs.append({
                'catalog':catalog,'key':key,'language':args.language,
                'expected_private_target_sha256':current_hash,
                'expected_english_sha256':scope['english'][key],
                'new_localization':updated,
                'evidence':evidence['evidence'],
            })
    print(f'{args.language}: proposed approved changes={len(diffs)}, awaiting human review={pending_review}, '
          f'already integrated={already_integrated}, stale/source conflicts={len(conflicts)}')
    for msg in conflicts[:30]:print('CONFLICT',msg)
    if conflicts:
        print('STOP: reconcile differences with the private source; no proposal written')
        return 2
    if args.output:
        dest=args.output.resolve()
        if root==dest or root in dest.parents or private==dest or private in dest.parents:
            print('Refusing to write a private-import proposal inside either repository');return 2
        try:
            with dest.open('x',encoding='utf-8') as fd:
                json.dump({'format':2,'language':args.language,'changes':diffs,
                           'awaiting_human_review':pending_review},fd,ensure_ascii=False,indent=2)
                fd.write('\n')
        except FileExistsError:
            print('Output already exists. Choose a new path; nothing overwritten.');return 2
        print(f'Isolated proposal written: {dest} (not applied to Tendo)')
    else:
        print('Dry-run only; use --output to produce an isolated review proposal')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
