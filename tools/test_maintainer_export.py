#!/usr/bin/env python3
"""Owner export gate negative tests: protect old corrections and private source."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from verify_maintainer_export import verify

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
