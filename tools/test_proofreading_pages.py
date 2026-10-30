#!/usr/bin/env python3
"""Generated GitHub review pages are complete, safe, deterministic and non-authoritative."""
import copy
from pathlib import Path
import tempfile
import unittest

from generate_proofreading_pages import (PAGE_ROOT, escape_cell, expected_paths,
                                        render_pages, review_state, show_value,
                                        verify_pages, write_pages)
from validate_translations import load_json, sha

ROOT = Path(__file__).resolve().parents[1]


class ProofreadingPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = render_pages(ROOT)
        cls.batches = load_json(ROOT / 'review/batches.json')['batches']
        cls.languages = load_json(ROOT / 'docs/export-baseline.json')['locales']

    def test_every_language_and_batch_has_a_page(self):
        self.assertEqual(set(self.pages), expected_paths(self.batches, self.languages))
        self.assertEqual(len(self.pages), 7 * 53 + 7 + 1)
        # Ordinary single-language PRs cannot regenerate these pages; only the
        # maintainer gate enforces snapshot freshness on publication.

    def test_catalog_keys_appear_exactly_once_in_each_languages_batch_pages(self):
        for language in self.languages:
            for batch in self.batches:
                page = self.pages[PAGE_ROOT / language / f"{batch['id']}.md"]
                rows = [line for line in page.splitlines() if line.startswith('| `')]
                self.assertEqual(len(rows), len(batch['keys']))
                for key in batch['keys']:
                    self.assertIn(f'| `{escape_cell(key)}`<br>', page)

    def test_multiline_plural_and_shortcuts_are_visible(self):
        sl = self.pages[PAGE_ROOT / 'sl' / 'README.md']
        self.assertIn('2,410/2,410', sl)
        self.assertIn('Human-approved:** ', sl)
        main_pages = '\n'.join(text for path, text in self.pages.items()
                               if str(path).startswith('docs/proofreading/sl/')
                               and path.name != 'README.md')
        self.assertIn('**one:**', main_pages)
        self.assertIn('**two:**', main_pages)
        self.assertIn('**few:**', main_pages)
        self.assertIn('**other:**', main_pages)
        self.assertIn('**Alternative 1:**', main_pages)
        self.assertIn('${applicationName}', main_pages)

    def test_markdown_and_html_are_escaped_without_mangling_source(self):
        raw = '<script>alert(1)</script> | [click](example) *text* `code`\nline 2'
        rendered = escape_cell(raw)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('\\|', rendered)
        self.assertIn('\\[click\\]', rendered)
        self.assertIn('\\*text\\*', rendered)
        self.assertIn('\\`code\\`', rendered)
        self.assertIn('↵<br>', rendered)
        self.assertEqual(show_value({'stringUnit': {'value': raw}}), rendered)

    def test_review_status_is_evidence_and_hash_based(self):
        sl = load_json(ROOT / 'locales/sl/Localizable.xcstrings')
        key = 'tendoTodayToday'
        target = sl['strings'][key]['localizations']['sl']
        english = sha(sl['strings'][key]['localizations']['en'])
        self.assertEqual(review_state(None, english, target), 'AI draft · unreviewed')
        record = {'source_hash': english, 'target_hash': sha(target),
                  'evidence': 'https://github.com/DrRoglaa/tendo-translations/pull/7'}
        self.assertIn('Human-approved', review_state(record, english, target))
        altered = copy.deepcopy(target)
        altered['stringUnit']['value'] += ' changed'
        self.assertIn('Needs human re-review', review_state(record, english, altered))
        self.assertIn('Needs human re-review', review_state(record, '0' * 64, target))

    def test_tamper_missing_and_extra_pages_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = PAGE_ROOT / 'sl' / 'focus-01.md'
            extra = PAGE_ROOT / 'sl' / 'unauthorized.md'
            (root / path).parent.mkdir(parents=True)
            (root / path).write_text(self.pages[path], encoding='utf-8')
            self.assertTrue(any('Missing generated file' in e for e in verify_pages(root, self.pages)))
            (root / path).write_text('misleading approval', encoding='utf-8')
            self.assertTrue(any('stale' in e for e in verify_pages(root, self.pages)))
            (root / extra).write_text('unexpected', encoding='utf-8')
            self.assertTrue(any('Unexpected generated file' in e for e in verify_pages(root, self.pages)))
            with self.assertRaises(ValueError):
                write_pages(root, self.pages)

    def test_symlinks_are_never_followed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / PAGE_ROOT).parent.mkdir(parents=True)
            (root / PAGE_ROOT).symlink_to('/tmp', target_is_directory=True)
            self.assertTrue(any('symlink' in e for e in verify_pages(root, self.pages)))
            with self.assertRaises(ValueError):
                write_pages(root, self.pages)


if __name__ == '__main__':
    unittest.main()
