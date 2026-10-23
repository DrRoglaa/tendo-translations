#!/usr/bin/env python3
"""Offline regression tests: public edits never overwrite newer private values."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/prepare_private_import.py'
CATALOGS = ('Localizable.xcstrings', 'InfoPlist.xcstrings', 'AppShortcuts.xcstrings')
TARGET = 'tendoTodayToday'


class PrivateImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.public = self.home / 'public'
        self.private = self.home / 'private'
        shutil.copytree(ROOT / 'locales', self.public / 'locales')
        shutil.copytree(ROOT / 'docs', self.public / 'docs')
        self.private.mkdir()
        for name in CATALOGS:
            original = json.loads((ROOT / 'locales/sl' / name).read_text(encoding='utf-8'))
            # A private source includes the same locale plus the public English reference.
            (self.private / name).write_text(json.dumps(original, ensure_ascii=False), encoding='utf-8')

    def change(self, path, word):
        document = json.loads(path.read_text(encoding='utf-8'))
        document['strings'][TARGET]['localizations']['sl']['stringUnit']['value'] = word
        path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')

    def run_import(self, output=None):
        command = [sys.executable, str(SCRIPT), '--repo', str(self.public),
                   '--language', 'sl', '--private-catalogs', str(self.private)]
        if output is not None:
            command += ['--output', str(output)]
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def test_no_changes_dry_run(self):
        completed = self.run_import()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn('proposed changes=0, stale/source conflicts=0', completed.stdout)

    def test_proposes_only_public_edit(self):
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'New text %1$(text)@')
        proposal = self.home / 'proposal.json'
        completed = self.run_import(proposal)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(proposal.read_text(encoding='utf-8'))
        self.assertEqual(len(result['changes']), 1)
        self.assertEqual(result['changes'][0]['key'], TARGET)
        self.assertEqual(result['changes'][0]['language'], 'sl')

    def test_stale_edit_stops_without_writing(self):
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'Suggestion %1$(text)@')
        self.change(self.private / 'Localizable.xcstrings', 'New value %1$(text)@')
        proposal = self.home / 'proposal.json'
        completed = self.run_import(proposal)
        self.assertEqual(completed.returncode, 2)
        self.assertIn('CONFLICT', completed.stdout)
        self.assertFalse(proposal.exists())

    def test_never_writes_into_public_repo(self):
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'Suggestion %1$(text)@')
        completed = self.run_import(self.public / 'unsafe.json')
        self.assertEqual(completed.returncode, 2)
        self.assertFalse((self.public / 'unsafe.json').exists())


if __name__ == '__main__':
    unittest.main()
