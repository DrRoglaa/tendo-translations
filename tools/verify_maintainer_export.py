#!/usr/bin/env python3
"""Read-only review gate for a maintainer's bulk export versus trusted public main.

No private Tendo files, Git hooks or contributor-supplied scripts are executed.
Run only against a separately inspected, maintainer-controlled branch.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

from validate_translations import CATALOGS, PLURALS, load_json, sha, validate
from review_tracking import validate_review
from generate_proofreading_pages import expected_paths, render_pages, verify_pages

ALLOWED_ADDITIONS = {
    Path('.github/workflows/verify-maintainer-export.yml'),
    Path('tools/export_ai_drafts.py'),
    Path('tools/check_editor_roundtrip.py'),
    Path('tools/test_editor_roundtrip.py'),
    Path('tools/review_tracking.py'),
    Path('tools/verify_maintainer_export.py'),
    Path('tools/test_export_ai_drafts.py'),
    Path('tools/test_review_tracking.py'),
    Path('tools/test_maintainer_export.py'),
    Path('review/README.md'),
    Path('review/batches.json'),
    Path('tools/generate_proofreading_pages.py'),
    Path('tools/test_proofreading_pages.py'),
}
ALLOWED_ADDITIONS.update(Path('review/languages')/f'{lang}.json' for lang in PLURALS)
LEAK_PATTERN = re.compile(r'(?:/Users/|/home/|Tendo/(?:Features|DesignSystem|Services|Models|Shared)/|\.swift(?::[0-9]+|\b)|\.pbxproj\b)',re.I)


def files(root: Path):
    return {p.relative_to(root) for p in root.rglob('*') if (p.is_file() or p.is_symlink())
            and not any(part in {'.git','__pycache__'} for part in p.relative_to(root).parts)
            and p.suffix not in {'.pyc','.pyo'}}


def verify(repo: Path, previous: Path) -> list[str]:
    errors=[]
    original=files(previous); updated=files(repo)
    # Only the exact deterministic page filenames are permitted, not arbitrary docs.
    try:
        stable_batches=load_json(previous/'review/batches.json')['batches']
        stable_locales=load_json(previous/'docs/export-baseline.json')['locales']
        allowed=ALLOWED_ADDITIONS | expected_paths(stable_batches,stable_locales)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        errors.append(f'Invalid trusted review manifest: {exc}')
        allowed=ALLOWED_ADDITIONS
    for rel in sorted(updated|original):
        dest=repo/rel; src=previous/rel
        if dest.is_symlink() or src.is_symlink():
            errors.append(f'Symlink forbidden: {rel}')
        if rel not in original and rel not in allowed:
            errors.append(f'Unexpected addition to public repository: {rel}')
        if rel in original and rel not in updated:
            errors.append(f'Unexpected file removal: {rel}')
        if any(piece.endswith(('.swift','.xcodeproj','.xcworkspace','.tendobackup')) for piece in rel.parts):
            errors.append(f'Private application artefact forbidden: {rel}')
    try:
        old_baseline=load_json(previous/'docs/export-baseline.json')
        latest=load_json(repo/'docs/export-baseline.json')
        if set(old_baseline['locales'])!=set(latest['locales']):
            errors.append('Unexpected locale set change')
        for lang in PLURALS:
            for name in CATALOGS:
                old=load_json(previous/'locales'/lang/name)['strings']
                new=load_json(repo/'locales'/lang/name)['strings']
                for key, entry in old.items():
                    if key not in new:
                        errors.append(f'Original public string missing: {lang}/{name}/{key}')
                        continue
                    for locale in ('en',lang):
                        if sha(entry['localizations'][locale])!=sha(new[key]['localizations'][locale]):
                            errors.append(f'Original {locale} localization changed: {lang}/{name}/{key}')
                    for meta in ('comment','extractionState'):
                        if entry.get(meta)!=new[key].get(meta):
                            errors.append(f'Existing public metadata changed: {lang}/{name}/{key}')
                for key,entry in new.items():
                    if LEAK_PATTERN.search(entry.get('comment','')):
                        errors.append(f'Internal source-path leak: {lang}/{name}/{key}')
    except (OSError,ValueError,TypeError,KeyError) as exc:
        errors.append(f'Invalid source or catalog: {exc}')
    validation_errors,_=validate(repo,repo/'docs/export-baseline.json')
    errors.extend(validation_errors)
    review_errors,_,_=validate_review(repo)
    errors.extend(review_errors)
    try:
        errors.extend(verify_pages(repo,render_pages(repo)))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        errors.append(f"Invalid generated proofreading pages: {exc}")
    return errors


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--previous',type=Path,required=True,help='Separate clean main checkout (trusted, read-only)')
    args=parser.parse_args()
    problems=verify(args.repo.resolve(),args.previous.resolve())
    for problem in problems[:35]:print('FAIL',problem)
    print(f'{"PASS" if not problems else "FAIL"}: maintainer export, preservation, privacy & review tracking ({len(problems)} issue(s))')
    return 1 if problems else 0


if __name__=='__main__':
    raise SystemExit(main())
