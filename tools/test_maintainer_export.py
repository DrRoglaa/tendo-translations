#!/usr/bin/env python3
"""Owner export gate negative tests: protect old corrections and private source."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from verify_maintainer_export import verify
from generate_proofreading_pages import legacy_batch_paths, expected_paths
from validate_translations import load_json

ROOT=Path(__file__).resolve().parents[1]


class MaintainerExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)/'public'
        shutil.copytree(ROOT,self.repo,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))

    def test_same_clean_public_tree_passes(self):
        self.assertEqual(verify(self.repo,ROOT),[])

    def test_original_public_approval_cannot_be_silently_replaced(self):
        path=self.repo/'locales/sl/Localizable.xcstrings'
        catalog=json.loads(path.read_text(encoding='utf-8'))
        catalog['strings']['tendoTodayToday']['localizations']['sl']['stringUnit']['value']='Changed without consent %1$(text)@'
        path.write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf-8')
        self.assertTrue(any('Original sl localization changed' in msg for msg in verify(self.repo,ROOT)))

    def test_tampered_generated_page_is_blocked(self):
        path=self.repo/'docs/proofreading/sl/focus.md'
        path.write_text('False human-approval claim', encoding='utf-8')
        self.assertTrue(any('Generated page is stale' in msg for msg in verify(self.repo,ROOT)))

    def test_unexpected_generated_page_is_blocked(self):
        (self.repo/'docs/proofreading/sl/secret.md').write_text('unapproved', encoding='utf-8')
        self.assertTrue(any('Unexpected addition' in msg for msg in verify(self.repo,ROOT)))

    def test_retired_batch_pages_may_be_replaced_only_by_topic_pages(self):
        previous=Path(self.tmp.name)/'previous'
        shutil.copytree(ROOT, previous, ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))
        batches=load_json(ROOT/'review/batches.json')['batches']
        locales=load_json(ROOT/'docs/export-baseline.json')['locales']
        for rel in expected_paths(batches,locales):
            if rel.name != 'README.md':
                (previous/rel).unlink()
        for rel in legacy_batch_paths(batches,locales):
            path=previous/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('Former generated page',encoding='utf-8')
        self.assertEqual(verify(self.repo,previous), [])

    def test_removing_non_generated_file_is_blocked(self):
        (self.repo/'CONTRIBUTORS.md').unlink()
        self.assertTrue(any('Unexpected file removal' in msg for msg in verify(self.repo,ROOT)))

    def test_new_private_swift_source_is_blocked(self):
        (self.repo/'TendoPrivate.swift').write_text('secret = "sample"')
        self.assertTrue(any('Unexpected addition' in msg for msg in verify(self.repo,ROOT)))

    def test_leaked_private_source_comment_is_blocked(self):
        path=self.repo/'locales/sl/Localizable.xcstrings'
        catalog=json.loads(path.read_text(encoding='utf-8'))
        catalog['strings']['tendoTodayToday']['comment']='Tendo/Features/Settings/PrivateView.swift:52'
        path.write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf-8')
        self.assertTrue(any('Internal source-path leak' in msg for msg in verify(self.repo,ROOT)))


if __name__=='__main__':
    unittest.main()
