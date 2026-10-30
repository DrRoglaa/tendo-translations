#!/usr/bin/env python3
"""Render deterministic, read-only GitHub proofreading pages from public catalogs.

The .xcstrings and protected human-review ledgers remain authoritative. Pages are
maintainer-generated snapshots, never a second editable translation source.
"""
from __future__ import annotations

import argparse
import html
from pathlib import Path
import sys

from review_tracking import load_review_data, validate_review
from translation_status import NAMES
from validate_translations import CATALOGS, load_json, sha, validate

PAGE_ROOT = Path("docs/proofreading")
PLURAL_ORDER = ("zero", "one", "two", "few", "many", "other")
ISSUE_URL = "https://github.com/DrRoglaa/tendo-translations/issues/new/choose"


def escape_cell(text: str) -> str:
    """Keep catalog text literal, including Markdown/HTML syntax and line breaks."""
    value = html.escape(text, quote=True)
    for token in ("\\", "|", "`", "[", "]", "*", "_"):
        value = value.replace(token, "\\" + token)
    return value.replace("\r", "\u240d").replace("\t", "\u21e5").replace("\n", " \u21b5<br>")


def show_value(localization: dict) -> str:
    if "stringUnit" in localization:
        return escape_cell(localization["stringUnit"]["value"])
    if "stringSet" in localization:
        values = localization["stringSet"]["values"]
        return "<br>".join(f"**Alternative {i}:** {escape_cell(value)}"
                           for i, value in enumerate(values, 1))
    plural = localization["variations"]["plural"]
    return "<br>".join(f"**{category}:** {escape_cell(plural[category]['stringUnit']['value'])}"
                       for category in PLURAL_ORDER if category in plural)


def review_state(record: dict | None, english_hash: str, target: dict) -> str:
    if record is None:
        return "AI draft · unreviewed"
    if record["source_hash"] != english_hash or record["target_hash"] != sha(target):
        return "Needs human re-review (stale)"
    return f"[Human-approved]({record['evidence']})"


def source_data(root: Path):
    """Load only validated public data; record active/stale evidence per exact key."""
    baseline = load_json(root / "docs/export-baseline.json")
    errors, counts = validate(root, root / "docs/export-baseline.json")
    review_errors, statuses, batches = validate_review(root, baseline)
    if errors or review_errors:
        raise ValueError("Invalid catalogs/reviews: " + "; ".join((errors + review_errors)[:8]))
    _, ledgers, _ = load_review_data(root)
    records = {locale: {(record["catalog"], record["key"]): record for record in entries}
               for locale, entries in ledgers.items()}
    return baseline, counts, statuses, batches, records


def expected_paths(batches: list[dict], languages: list[str]) -> set[Path]:
    output = {PAGE_ROOT / "README.md"}
    for locale in languages:
        output.add(PAGE_ROOT / locale / "README.md")
        for batch in batches:
            output.add(PAGE_ROOT / locale / f"{batch['id']}.md")
    return output


def render_pages(root: Path) -> dict[Path, str]:
    base, counts, statuses, batches, records = source_data(root)
    languages = base["locales"]
    total = sum(len(base["catalogs"][catalog]["keys"]) for catalog in CATALOGS)
    all_pages: dict[Path, str] = {}
    landing = ["# Browse Tendo translations", "",
               "Choose a language to review the **English source beside its AI-assisted draft**.",
               "These pages are generated from the public String Catalogs; they are **read-only snapshots**, not separate editable translations.",
               "A translation can be technically present without independent human approval or inclusion in a released app.",
               "", "| Language | AI drafts present | Independently approved | Review batches |",
               "|---|---:|---:|---:|"]
    for locale in languages:
        catalog_data = {name: load_json(root / "locales" / locale / name)["strings"]
                        for name in CATALOGS}
        batch_pages = []
        for batch_number, batch in enumerate(batches):
            name, batch_id = batch["catalog"], batch["id"]
            reviewed, stale = 0, 0
            rows = []
            for key in batch["keys"]:
                entry = catalog_data[name][key]
                localizations = entry["localizations"]
                record = records[locale].get((name, key))
                state = review_state(record, base["catalogs"][name]["english"][key], localizations[locale])
                reviewed += state.startswith("[Human-approved]")
                stale += state.startswith("Needs human re-review")
                context = escape_cell(entry.get("comment", ""))
                key_label = escape_cell(key)
                rows.append(f"| `{key_label}`<br>*{context}* | "
                            f"{show_value(localizations['en'])} | {show_value(localizations[locale])} | {state} |")
            prev_link = (f"[\u2190 Previous batch]({batches[batch_number-1]['id']}.md)" if batch_number else "")
            next_link = (f"[Next batch \u2192]({batches[batch_number+1]['id']}.md)" if batch_number + 1 < len(batches) else "")
            navigation = " · ".join(x for x in ["[All language batches](README.md)", prev_link, next_link] if x)
            body = [f"# {NAMES[locale]} · {batch['area']} · {batch_id}", "",
                    navigation, "",
                    f"**Catalog:** `{name}` · **Entries:** {len(batch['keys'])} · "
                    f"**Independently approved:** {reviewed} · **Stale reviews:** {stale}", "",
                    "**AI draft, not a published-language or human-approval claim.** Review every plural category and Siri alternative displayed below.",
                    "Strings with multiple lines show a visible \u21b5 marker. This page is generated and must not be edited.",
                    f"To suggest a correction, [open a translation issue]({ISSUE_URL}) or change **only this language's** original " +
                    f"[`{name}`](../../../locales/{locale}/{name}) in a Pull Request; include the batch ID and key.",
                    "", "| Key and translator context | English source | AI-assisted draft | Human review |",
                    "|---|---|---|---|", *rows, "", navigation, ""]
            all_pages[PAGE_ROOT / locale / f"{batch_id}.md"] = "\n".join(body)
            batch_pages.append(f"| [{batch_id}]({batch_id}.md) | {escape_cell(batch['area'])} | "
                               f"`{name}` | {len(batch['keys'])} | {reviewed} | {stale} |")
        index = [f"# {NAMES[locale]} proofreading (`{locale}`)", "",
                 "[\u2190 All languages](../README.md) · [How to contribute](../../../CONTRIBUTING.md)", "",
                 f"**AI drafts:** {sum(counts[f'{locale}/{name}'] for name in CATALOGS):,}/{total:,} · "
                 f"**Human-approved:** {statuses[locale]['approved']}/{total:,} · "
                 f"**Stale reviews:** {statuses[locale]['stale']} · **Batches:** {len(batches)}", "",
                 "The pages below show public English source text, the target-language draft, sanitized translator comments and review status.",
                 "Choose a batch; corrections belong in the **original String Catalog**, not these generated pages.",
                 "A maintainer refreshes these pages after catalog/review changes, so always compare against the current catalog before submitting.",
                 "", "| Batch | Area | Source catalog | Keys | Human-approved | Stale |",
                 "|---|---|---|---:|---:|---:|", *batch_pages, ""]
        all_pages[PAGE_ROOT / locale / "README.md"] = "\n".join(index)
        landing.append(f"| [{NAMES[locale]} (`{locale}`)]({locale}/README.md) | "
                       f"{sum(counts[f'{locale}/{name}'] for name in CATALOGS):,}/{total:,} | "
                       f"{statuses[locale]['approved']}/{total:,} | {len(batches)} |")
    landing.extend(["", "The \"translated\" state in Xcode means a technical draft exists; it is **not** a human sign-off.",
                    "Even a reviewed catalog does not establish Tendo's public app language availability.",
                    "", "**How to help:** Pick a language and batch, then [report an issue](" + ISSUE_URL + ") or "
                    "[contribute a single-language correction](../../CONTRIBUTING.md).",
                    "", "**Source of truth:** [`locales/`](../../locales/) and the protected "
                    "[review evidence](../../review/README.md). These generated pages may lag recently merged corrections until refreshed by a maintainer.",
                    "", "[Translation status](../TRANSLATION-STATUS.md) · [Glossary](../GLOSSARY.md) · "
                    "[Review policy](../REVIEW-POLICY.md)", ""])
    all_pages[PAGE_ROOT / "README.md"] = "\n".join(landing)
    return all_pages


def verify_pages(root: Path, pages: dict[Path, str]) -> list[str]:
    base = root / PAGE_ROOT
    expected = set(pages)
    if base.is_symlink():
        return ["Generated proofreading root is a symlink"]
    existing: set[Path] = set()
    if base.exists():
        for path in base.rglob("*"):
            if path.is_symlink():
                return [f"Generated proofreading symlink forbidden: {path.relative_to(root)}"]
            if path.is_file():
                existing.add(path.relative_to(root))
    errors = [f"Unexpected generated file: {p}" for p in sorted(existing - expected)]
    errors.extend(f"Missing generated file: {p}" for p in sorted(expected - existing))
    for path in sorted(existing & expected):
        if (root / path).read_text(encoding="utf-8") != pages[path]:
            errors.append(f"Generated page is stale: {path}")
    return errors


def write_pages(root: Path, pages: dict[Path, str]) -> None:
    # Never destroy unknown files, and never follow a symlinked destination.
    base = root / PAGE_ROOT
    if base.is_symlink():
        raise ValueError("Refusing to write through generated root symlink")
    if base.exists():
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"Refusing symlink in output tree: {path}")
            if path.is_file() and path.relative_to(root) not in pages:
                raise ValueError(f"Refusing to remove or replace unexpected file: {path}")
    for rel, text in sorted(pages.items()):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise ValueError(f"Refusing to write through symlink: {path}")
        path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="Maintainer only: regenerate checked-in Markdown pages")
    action.add_argument("--check", action="store_true", help="Verify generated pages match public catalogs and review evidence")
    args = parser.parse_args()
    try:
        root = args.repo.resolve(strict=True)
        pages = render_pages(root)
        if args.write:
            write_pages(root, pages)
            print(f"Wrote {len(pages)} public-only, read-only proofreading pages")
        else:
            errors = verify_pages(root, pages)
            if errors:
                for message in errors[:15]:
                    print("FAIL", message, file=sys.stderr)
                print(f"FAIL: {len(errors)} generated-page issue(s)", file=sys.stderr)
                return 1
            print(f"PASS: {len(pages)} generated proofreading pages match current public catalogs and reviews")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
