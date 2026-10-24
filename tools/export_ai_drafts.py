#!/usr/bin/env python3
"""Maintainer-only, offline export of AI drafts from a local PRIVATE Tendo snapshot.

Never uploads data, executes private scripts, or writes to private catalogs. Reuses
existing public corrections. The target repository is only modified with --apply.
The source is a reviewed private snapshot, not an automatically synced Git branch.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

from validate_translations import CATALOGS, PLURALS, load_json, sha, validate

TECHNICAL_EXCLUSIONS = {"Localizable.xcstrings": {"%@"}}
SENSITIVE_VALUE = re.compile(
    r"(?:/Users/|/home/|[A-Z]:\\|\.swift\b|\.pbxproj\b|AKIA[0-9A-Z]{16}|"
    r"(?:api[_-]?key|access[_-]?token|private[_-]?key)\s*[=:])", re.I
)
GROUP_NAMES = {
    "Brain": "Brain Dump", "Whats": "What's New", "Live": "Live Activities",
    "Watch": "Apple Watch", "Sample": "Sample data", "Shortcuts": "Shortcuts",
    "Notifications": "Notifications", "Focus": "Focus", "Onboarding": "Onboarding",
    "Settings": "Settings", "Routines": "Routines", "Common": "Common controls",
    "Today": "Today", "Now": "Now", "Tasks": "Tasks", "Guide": "Guide",
    "Momentum": "Momentum", "Accessibility": "Accessibility",
}


def safe_comment(key: str, catalog: str) -> str:
    if catalog == "AppShortcuts.xcstrings":
        return "Siri/Shortcuts phrase. Preserve the application name placeholder."
    if catalog == "InfoPlist.xcstrings":
        return "System-facing permission or app name. Use clear platform terminology."
    match = re.match(r"^tendo([A-Z][a-z]+)", key)
    area = GROUP_NAMES.get(match.group(1), match.group(1)) if match else "Interface"
    return f"{area} interface text. Review meaning, tone, and on-screen context."


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_export(root: Path, private: Path) -> tuple[dict[Path, bytes], dict]:
    """Pure preparation/validation. No filesystem writes until all inputs pass."""
    old_base = load_json(root / "docs/export-baseline.json")
    languages = old_base["locales"]
    if set(languages) != set(PLURALS):
        raise ValueError("Unsupported locale list; requires separate review")
    errors, _ = validate(root, root / "docs/export-baseline.json")
    if errors:
        raise ValueError("Existing public catalogs are invalid: " + "; ".join(errors[:4]))

    files: dict[Path, bytes] = {}
    new_base: dict = {
        "format": 1,
        "source_version": "24 October 2026 private Tendo AI-draft snapshot; not human-approved or released",
        "locales": languages,
        "source_catalog_sha256": {},
        "catalogs": {},
        "retained_public_edits": [],
    }
    totals = {}
    for name in CATALOGS:
        path = private / name
        source = load_json(path)
        if source.get("sourceLanguage") != "en" or source.get("version") not in ("1.0", "1.1"):
            raise ValueError(f"Unexpected private String Catalog schema: {name}")
        if not isinstance(source.get("strings"), dict):
            raise ValueError(f"No private entries in {name}")
        new_base["source_catalog_sha256"][name] = raw_sha256(path)
        excluded = TECHNICAL_EXCLUSIONS.get(name, set())
        if set(source["strings"]) & excluded != excluded:
            raise ValueError(f"Expected technical exclusions missing from {name}")
        keys = sorted(set(source["strings"]) - excluded)
        if not set(old_base["catalogs"][name]["keys"]).issubset(keys):
            raise ValueError(f"Previously published key disappeared from {name}; reconcile first")
        section: dict = {"keys": keys, "english": {}, "public_source": {},
                         "initial_targets": {lang: {} for lang in languages}}
        old_catalogs = {
            lang: load_json(root / "locales" / lang / name) for lang in languages
        }
        for lang, old in old_catalogs.items():
            if not set(old["strings"]).issubset(keys):
                raise ValueError(f"Previously exported key removed: {lang}/{name}")
        out_catalogs = {lang: {"sourceLanguage": "en", "strings": {},
                               "version": source["version"]} for lang in languages}
        for key in keys:
            private_entry = source["strings"][key]
            localizations = private_entry.get("localizations")
            if not isinstance(localizations, dict) or not {"en", *languages}.issubset(localizations):
                raise ValueError(f"Missing private translation/localization: {name}/{key}")
            english = copy.deepcopy(localizations["en"])
            for lang in languages:
                existing = old_catalogs[lang]["strings"].get(key)
                if existing is not None:
                    # The previous public baseline is validated above. Never silently
                    # overwrite human edits, English references or public comments.
                    if sha(existing["localizations"]["en"]) != sha(english):
                        raise ValueError(f"English source changed: {lang}/{name}/{key}; manual reconciliation required")
                    comment = existing["comment"]
                    extraction = existing["extractionState"]
                    target = copy.deepcopy(existing["localizations"][lang])
                else:
                    comment = safe_comment(key, name)
                    extraction = "manual"
                    target = copy.deepcopy(localizations[lang])
                original = localizations[lang]
                if sha(target) != sha(original):
                    new_base["retained_public_edits"].append({"language":lang,"catalog":name,"key":key})
                entry = {"comment":comment,"extractionState":extraction,
                         "localizations":{"en":copy.deepcopy(english),lang:target}}
                for text in json_strings(entry["localizations"]):
                    if SENSITIVE_VALUE.search(text):
                        raise ValueError(f"Potentially sensitive value: {lang}/{name}/{key}")
                out_catalogs[lang]["strings"][key] = entry
                section["initial_targets"][lang][key] = sha(original)
            anchor = out_catalogs[languages[0]]["strings"][key]
            section["english"][key] = sha(english)
            section["public_source"][key] = sha({"comment":anchor["comment"],
                "extractionState":anchor["extractionState"],"english":english})
            # Same public metadata is required across each locale.
            for lang in languages[1:]:
                second = out_catalogs[lang]["strings"][key]
                if (second["comment"],second["extractionState"]) != (anchor["comment"],anchor["extractionState"]):
                    raise ValueError(f"Inconsistent public metadata: {lang}/{name}/{key}")
        new_base["catalogs"][name] = section
        totals[name] = len(keys)
        for lang in languages:
            contents = json.dumps(out_catalogs[lang], ensure_ascii=False, indent=2) + "\n"
            files[Path("locales") / lang / name] = contents.encode("utf-8")
    files[Path("docs/export-baseline.json")] = (json.dumps(new_base,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    return files, {"counts":totals,"preserved_differences":len(new_base["retained_public_edits"]),
                   "source_catalog_sha256":new_base["source_catalog_sha256"]}


def json_strings(node):
    if isinstance(node, dict):
        for k,v in node.items():
            if k in ("comment", "value") and isinstance(v,str):
                yield v
            elif k == "values" and isinstance(v,list):
                yield from (s for s in v if isinstance(s,str))
            else:
                yield from json_strings(v)
    elif isinstance(node,list):
        for v in node:
            yield from json_strings(v)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--private-catalogs",type=Path,required=True)
    parser.add_argument("--apply",action="store_true",help="Explicitly write only public catalogs and export baseline")
    args=parser.parse_args()
    root=args.repo.resolve(); private=args.private_catalogs.resolve()
    if root == private or root in private.parents or private in root.parents:
        print("ERROR: private source must be an independent path",file=sys.stderr);return 2
    try:
        planned,summary=build_export(root,private)
        if args.apply:
            for rel,data in planned.items():
                target=root/rel
                if target.is_symlink() or not target.parent.is_dir():
                    raise ValueError(f"Unsafe export destination: {rel}")
                target.write_bytes(data)
        print(json.dumps({"mode":"applied" if args.apply else "preview",**summary},indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as err:
        print(f"EXPORT FAILED: {err}",file=sys.stderr);return 1

if __name__ == "__main__":
    sys.exit(main())
