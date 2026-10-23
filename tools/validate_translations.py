#!/usr/bin/env python3
"""Read-only validation of a sanitized Tendo translation export.

CI runs this exact script from the trusted base checkout against an untrusted PR
checkout. No code, hooks, or tools from the contributor's checkout are executed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

CATALOGS = ("Localizable.xcstrings", "InfoPlist.xcstrings", "AppShortcuts.xcstrings")
NAMED = re.compile(r"%\d+\$\([a-zA-Z][\w]*\)(?:lld|ld|d|u|f|@)")
PRINTF = re.compile(r"%(?:\d+\$)?(?:lld|ld|d|u|f|@)")
SHORTCUT = re.compile(r"\$\{[a-zA-Z][a-zA-Z0-9]*\}")
PLURALS = {
    "sl": {"one", "two", "few", "other"},
    "hr": {"one", "few", "other"},
    "de": {"one", "other"},
    "it": {"one", "other"},
    "hu": {"other"},
    "ja": {"other"},
    "ko": {"other"},
}
ALLOWED_STATES = {"new", "translated", "needs_review", "stale"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 5_000_000:
        raise ValueError(f"Invalid, oversized, or symlinked JSON file: {path}")

    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def leaf_text(unit: dict) -> list[str]:
    if "stringUnit" in unit:
        v = unit["stringUnit"]
        if not isinstance(v, dict) or not isinstance(v.get("value"), str) or v.get("state") not in ALLOWED_STATES:
            raise ValueError("Invalid stringUnit value/state")
        return [v["value"]]
    if "stringSet" in unit:
        v = unit["stringSet"]
        if not isinstance(v, dict) or not isinstance(v.get("values"), list) or not v["values"] or not all(isinstance(x, str) for x in v["values"]) or v.get("state") not in ALLOWED_STATES:
            raise ValueError("Invalid stringSet values/state")
        return v["values"]
    raise ValueError("Missing stringUnit or stringSet")


def branches(value: dict, lang: str, name: str) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise ValueError("Localization must be an object")
    if "variations" in value:
        if set(value) != {"variations"} or set(value["variations"]) != {"plural"}:
            raise ValueError("Unexpected localization variation")
        plural = value["variations"]["plural"]
        if not isinstance(plural, dict) or "other" not in plural:
            raise ValueError("Missing 'other' plural branch")
        if not set(plural).issubset({"zero", "one", "two", "few", "many", "other"}):
            raise ValueError("Unsupported plural branch")
        if lang != "en" and set(plural) != PLURALS[lang]:
            raise ValueError(f"{lang}: expected plural categories {sorted(PLURALS[lang])}")
        return {k: leaf_text(v) for k, v in plural.items()}
    return {"simple": leaf_text(value)}


def tokens(text: str) -> Counter:
    # Normalize escaped percent first. Placeholders must be kept in each target leaf.
    result = Counter(NAMED.findall(text))
    remainder = NAMED.sub("", text).replace("%%", "")
    result.update(PRINTF.findall(remainder))
    result.update(SHORTCUT.findall(text))
    return result


def validate_catalog(path: Path, lang: str, baseline: dict, name: str) -> list[str]:
    errors = []
    try:
        catalog = load_json(path)
        if set(catalog) != {"sourceLanguage", "strings", "version"} or catalog["sourceLanguage"] != "en":
            raise ValueError("Invalid String Catalog top-level structure")
        if catalog["version"] not in ("1.0", "1.1"):
            raise ValueError("Unexpected String Catalog version")
        if not isinstance(catalog["strings"], dict) or set(catalog["strings"]) != set(baseline["keys"]):
            missing = set(baseline["keys"]) - set(catalog["strings"])
            extra = set(catalog["strings"]) - set(baseline["keys"])
            raise ValueError(f"Keys differ: {len(missing)} missing, {len(extra)} unapproved")
        for key, entry in catalog["strings"].items():
            try:
                if not isinstance(entry, dict) or set(entry) != {"comment", "extractionState", "localizations"}:
                    raise ValueError("Unexpected entry fields")
                loc = entry["localizations"]
                if not isinstance(loc, dict) or set(loc) != {"en", lang}:
                    raise ValueError(f"Only en and {lang} are allowed")
                anchor = {"comment": entry["comment"], "extractionState": entry["extractionState"], "english":loc["en"]}
                if sha(anchor) != baseline["public_source"][key] or sha(loc["en"]) != baseline["english"][key]:
                    raise ValueError("English reference, metadata, or developer comment was modified")
                en_branches = branches(loc["en"], "en", name)
                tr_branches = branches(loc[lang], lang, name)
                if ("simple" in en_branches) != ("simple" in tr_branches):
                    raise ValueError("Plural versus simple structure changed")
                ref_token_counts = {tuple(sorted(tokens(t).items())) for values in en_branches.values() for t in values}
                if len(ref_token_counts) != 1:
                    raise ValueError("Source plural branches have inconsistent placeholder structure")
                expected = next(iter(ref_token_counts))
                for vals in tr_branches.values():
                    for text in vals:
                        if tuple(sorted(tokens(text).items())) != expected:
                            raise ValueError(f"Placeholder mismatch: expected {dict(expected)}, found {dict(tokens(text))}")
                        if "\x00" in text or len(text)>2000:
                            raise ValueError("Invalid translated string length or NUL")
                if name == "InfoPlist.xcstrings" and key == "CFBundleDisplayName" and tr_branches != {"simple":["Tendo"]}:
                    raise ValueError("The Tendo brand name must remain unchanged")
            except (TypeError, ValueError, KeyError) as err:
                errors.append(f"{lang}/{name}/{key}: {err}")
    except (OSError, ValueError, TypeError, KeyError) as err:
        errors.append(f"{lang}/{name}: {err}")
    return errors


def compare_pr_scope(repo: Path, base_tree: Path, locales: list[str]) -> list[str]:
    """Reject changes outside one public language pack in ordinary contributor PRs.

    Compare trees without executing anything in the submitted checkout; Git metadata
    and generated Python caches are never evaluated as contribution content.
    Maintainer tooling/documentation changes require a separately reviewed process.
    """
    def files(root: Path) -> set[Path]:
        return {
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() or path.is_symlink()
            if not any(part in {".git", "__pycache__"} for part in path.relative_to(root).parts)
            if path.suffix not in {".pyc", ".pyo"}
        }

    original = files(base_tree)
    proposed = files(repo)
    permitted = {
        Path("locales") / lang / catalog
        for lang in locales for catalog in CATALOGS
    }
    problems = []
    changed_languages = set()
    for rel in sorted(original | proposed):
        a = base_tree / rel
        b = repo / rel
        try:
            if a.is_symlink() or b.is_symlink():
                problems.append(f"Symlinks are forbidden in contributions: {rel}")
                continue
            if a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes():
                continue
        except OSError:
            pass
        if rel not in permitted:
            problems.append(f"Unapproved non-translation change: {rel}")
        else:
            changed_languages.add(rel.parts[1])
    if len(changed_languages) > 1:
        problems.append("Please change only one locale per Pull Request")
    return problems


def validate(repo: Path, baseline_path: Path, base_tree: Path | None = None) -> tuple[list[str], dict[str, int]]:
    errors=[]
    base = load_json(baseline_path)
    languages = base.get("locales")
    if set(languages or []) != set(PLURALS) or len(languages or []) != len(PLURALS):
        # This is intentionally fixed to the originally approved seven locales.
        errors.append("Unexpected locale set; new languages need a reviewed baseline update")
        return errors, {}
    if set(base.get("catalogs", {})) != set(CATALOGS):
        return ["Missing or unexpected catalog definition"], {}
    if base_tree is not None:
        errors.extend(compare_pr_scope(repo, base_tree, languages))
        if (repo/"docs/export-baseline.json").read_bytes() != baseline_path.read_bytes():
            errors.append("Protected export baseline edited; maintainer re-export needed")
    counts={}
    for lang in languages:
        for name in CATALOGS:
            path=repo/"locales"/lang/name
            errors += validate_catalog(path,lang,base["catalogs"][name],name)
            if path.is_file():
                try:
                    c=load_json(path)
                    translated=0
                    for v in c["strings"].values():
                        node=v["localizations"][lang]
                        vals = node.get("variations",{}).get("plural",{}).values() if "variations" in node else [node]
                        if all((x.get("stringUnit",x.get("stringSet",{})).get("state") == "translated") for x in vals):
                            translated+=1
                    counts[f"{lang}/{name}"]=translated
                except (ValueError,KeyError,TypeError):
                    pass
    # Reject unexpected content in /locales; public packs are constrained to curated files.
    for entry in (repo/"locales").rglob("*"):
        if entry.is_symlink():
            errors.append(f"Symlinks are not permitted in language packs: {entry}")
        elif entry.is_file() and (entry.parent.name not in languages or entry.name not in CATALOGS):
            errors.append(f"Unexpected language pack file: {entry.relative_to(repo)}")
    return errors,counts


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--baseline",type=Path)
    parser.add_argument("--base-tree",type=Path)
    args=parser.parse_args()
    root=args.repo.resolve()
    baseline=args.baseline or (root/"docs/export-baseline.json")
    try:
        errors,counts=validate(root,baseline,args.base_tree)
    except (OSError,ValueError,TypeError,KeyError) as err:
        print(f"VALIDATION FAILED: {err}",file=sys.stderr)
        return 1
    for error in errors:print("FAIL",error,file=sys.stderr)
    print(f"Validated {len(counts)} language/catalog combinations ({sum(counts.values())} translated public entries)")
    if errors:
        print(f"FAILED: {len(errors)} issue(s)",file=sys.stderr)
        return 1
    print("PASS: schema, source references, keys, placeholders, plurals, locale scope")
    return 0

if __name__ == "__main__":
    sys.exit(main())
