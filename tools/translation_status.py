#!/usr/bin/env python3
"""Print public starter-pack technical completion; NOT linguistic review."""
import json
from pathlib import Path
from validate_translations import CATALOGS, load_json, validate

root=Path(__file__).resolve().parents[1]
errors,counts=validate(root,root/'docs/export-baseline.json')
if errors:
    raise SystemExit('Validation failed; cannot compute reliable statistics')
base=load_json(root/'docs/export-baseline.json')
print('| Locale | Main UI public starter pack | Permission text | Siri phrases | Human reviewed | Released |')
print('|---|---:|---:|---:|---|---|')
for lang in base['locales']:
    a=[f'{counts[f"{lang}/{name}"]}/{len(base["catalogs"][name]["keys"])}' for name in CATALOGS]
    print(f'| {lang} | {a[0]} | {a[1]} | {a[2]} | No | Not verified |')
print('\nThese denominators refer ONLY to approved public starter-pack keys; they are NOT whole-app completion.')
