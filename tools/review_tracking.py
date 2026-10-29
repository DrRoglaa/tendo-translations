#!/usr/bin/env python3
"""Validate translation-review batches and independent human-review evidence.

A localization's Xcode `translated` state means AI draft present, NOT approved.
Only protected maintainer records can establish independent human review.
Records remain historical; changed English or target text automatically becomes stale.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
import sys

from validate_translations import CATALOGS, PLURALS, load_json, sha

MAX_BATCH = 75
PRIORITY = {
    "Permissions & app identity": 0,
    "Accessibility": 1,
    "Focus": 2,
    "Siri & Shortcuts": 3,
    "Notifications": 4,
    "Apple Watch": 5,
    "Live Activities": 6,
}
GROUP_NAMES = {
    "Brain": "Brain Dump", "Whats": "What's New", "Live": "Live Activities",
    "Watch": "Apple Watch", "Sample": "Sample data", "Shortcuts": "Shortcuts",
    "Settings": "Settings", "Routines": "Routines", "Common": "Common controls",
    "Today": "Today", "Now": "Now", "Tasks": "Tasks", "Guide": "Guide",
    "Momentum": "Momentum", "Gentle": "Gentle reminders", "Follow": "Follow-up",
    "Icon": "Icons", "Icons": "Icon selection", "Focus": "Focus",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GITHUB_EVIDENCE = re.compile(r"^https://github\.com/DrRoglaa/tendo-translations/(?:pull|issues)/[1-9][0-9]*$")


def area_for(catalog: str, key: str) -> str:
    if catalog == "InfoPlist.xcstrings":
        return "Permissions & app identity"
    if catalog == "AppShortcuts.xcstrings":
        return "Siri & Shortcuts"
    if re.search(r"Accessibility|VoiceOver|Spoken$", key, re.I):
        return "Accessibility"
    m = re.match(r"^tendo([A-Z][a-z]+)", key)
    group = m.group(1) if m else "Other"
    return GROUP_NAMES.get(group, group)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def expected_batches(base: dict) -> list[dict]:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for catalog in CATALOGS:
        for key in base["catalogs"][catalog]["keys"]:
            groups[(area_for(catalog,key), catalog)].append(key)
    ordered = sorted(groups, key=lambda pair: (PRIORITY.get(pair[0], 100), pair[0], CATALOGS.index(pair[1])))
    batches = []
    for area, catalog in ordered:
        keys = sorted(groups[(area,catalog)])
        for start in range(0, len(keys), MAX_BATCH):
            batches.append({"id": f"{slug(area)}-{(start // MAX_BATCH)+1:02d}",
                            "area": area,"catalog": catalog,"keys": keys[start:start+MAX_BATCH]})
    return batches


def load_review_data(root: Path) -> tuple[list[dict], dict[str, list[dict]], list[str]]:
    errors=[]
    batches=[]
    ledger={}
    try:
        doc=load_json(root/"review/batches.json")
        if set(doc)!={"format","max_batch_size","batches"} or doc["format"]!=1 or doc["max_batch_size"]!=MAX_BATCH:
            raise ValueError("Invalid review batch manifest header")
        if not isinstance(doc["batches"], list):
            raise ValueError("Invalid batches list")
        batches=doc["batches"]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors.append(f"Review manifest: {exc}")
    for lang in PLURALS:
        try:
            record=load_json(root/"review/languages"/f"{lang}.json")
            if set(record)!={"format","language","reviews"} or record["format"]!=1 or record["language"]!=lang or not isinstance(record["reviews"], list):
                raise ValueError("Invalid ledger format/language")
            ledger[lang]=record["reviews"]
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"review/{lang}: {exc}")
    return batches,ledger,errors


def validate_review(root: Path, base: dict | None = None) -> tuple[list[str], dict[str, dict[str, int]], list[dict]]:
    errors=[]
    try:
        base=base or load_json(root/"docs/export-baseline.json")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"Invalid baseline: {exc}"],{},[]
    batches, ledgers, read_errors = load_review_data(root)
    errors.extend(read_errors)
    canonical_batches=expected_batches(base)
    if batches!=canonical_batches:
        errors.append("Review batches do not match the protected export key set and deterministic grouping")
    if (root/"review").exists():
        allowed={Path("review/batches.json"),Path("review/README.md")}
        allowed.update(Path("review/languages")/f"{lang}.json" for lang in PLURALS)
        for p in (root/"review").rglob("*"):
            if p.is_symlink():
                errors.append(f"Symlink forbidden: {p}")
            elif p.is_file() and p.relative_to(root) not in allowed:
                errors.append(f"Unexpected review file: {p.relative_to(root)}")
    statuses={}
    for lang in PLURALS:
        active=0;stale=0
        encountered=set()
        catalog_cache={}
        for i,record in enumerate(ledgers.get(lang,[])):
            path=f"review/languages/{lang}.json[{i}]"
            try:
                required={"catalog","key","reviewed_at","reviewer","evidence","source_hash","target_hash","independent"}
                if not isinstance(record,dict) or set(record)!=required:
                    raise ValueError("Unexpected fields or missing review evidence")
                name,key=record["catalog"],record["key"]
                if name not in CATALOGS or key not in base["catalogs"][name]["keys"]:
                    raise ValueError("Unknown catalog or key")
                if (name,key) in encountered:
                    raise ValueError("Duplicate review record for catalog/key; resolve before recording a second sign-off")
                encountered.add((name,key))
                if record["independent"] is not True:
                    raise ValueError("Independent human review not asserted")
                if not isinstance(record["reviewer"],str) or not 2<=len(record["reviewer"])<=80 or '@' in record["reviewer"]:
                    raise ValueError("Use an agreed public reviewer handle or pseudonym, never an email")
                if not isinstance(record["evidence"],str) or not GITHUB_EVIDENCE.fullmatch(record["evidence"]):
                    raise ValueError("Evidence must link to a real public repository PR or issue (reviewer checked separately)")
                if not isinstance(record["reviewed_at"],str) or date.fromisoformat(record["reviewed_at"]).isoformat()!=record["reviewed_at"]:
                    raise ValueError("Invalid ISO review date")
                for hash_key in ("source_hash","target_hash"):
                    if not isinstance(record[hash_key],str) or not SHA256.fullmatch(record[hash_key]):
                        raise ValueError(f"Invalid {hash_key}")
                source=base["catalogs"][name]["english"][key]
                if name not in catalog_cache:
                    catalog_cache[name]=load_json(root/"locales"/lang/name)
                actual=catalog_cache[name]["strings"][key]["localizations"][lang]
                if record["source_hash"]==source and record["target_hash"]==sha(actual):
                    active+=1
                else:
                    stale+=1
            except (ValueError,KeyError,TypeError,OSError) as exc:
                errors.append(f"{path}: {exc}")
        statuses[lang]={"approved":active,"stale":stale,"total":sum(len(base["catalogs"][name]["keys"]) for name in CATALOGS)}
    return errors,statuses,batches


def language_batches(root: Path, language: str, batches: list[dict], status_by_lang: dict[str,dict]) -> None:
    reviewed=load_review_data(root)[1][language]
    base=load_json(root/"docs/export-baseline.json")
    current=set()
    catalog_cache={}
    for r in reviewed:
        try:
            if r["catalog"] not in catalog_cache:
                catalog_cache[r["catalog"]]=load_json(root/"locales"/language/r["catalog"])
            c=catalog_cache[r["catalog"]]["strings"][r["key"]]["localizations"][language]
            if r["source_hash"]==base["catalogs"][r["catalog"]]["english"][r["key"]] and r["target_hash"]==sha(c):
                current.add((r["catalog"],r["key"]))
        except (OSError,TypeError,KeyError,ValueError):
            pass
    s=status_by_lang[language]
    print(f"{language}: {s['approved']}/{s['total']} independently human-approved; {s['stale']} stale approvals")
    print('| Batch | Area | Reviewed / keys |'); print('|---|---|---:|')
    for batch in batches:
        count=sum((batch["catalog"],k) in current for k in batch["keys"])
        print(f"| `{batch['id']}` | {batch['area']} | {count}/{len(batch['keys'])} |")


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument("--write-batches", action="store_true", help="Maintainer-only generation of stable source-key batches")
    ap.add_argument("--language", choices=sorted(PLURALS))
    args=ap.parse_args(); root=args.repo.resolve()
    try:
        if args.write_batches:
            target=root/"review/batches.json"
            if target.is_symlink():raise ValueError("Cannot write through symlink")
            base=load_json(root/"docs/export-baseline.json")
            doc={"format":1,"max_batch_size":MAX_BATCH,"batches":expected_batches(base)}
            target.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        errors, statuses, batches=validate_review(root)
        if errors:
            for err in errors[:40]:print("FAIL",err,file=sys.stderr)
            return 1
        if args.language: language_batches(root,args.language,batches,statuses)
        else:
            print(f"PASS: {len(batches)} protected review batches; seven independent review ledgers")
            for lang,v in statuses.items():print(f" {lang}: human-approved {v['approved']}/{v['total']}, stale {v['stale']}")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"REVIEW VALIDATION FAILED: {exc}",file=sys.stderr);return 1


if __name__ == "__main__":
    sys.exit(main())
