#!/usr/bin/env python3
"""Offline regression tests: public edits never overwrite newer private values."""
import json
from pathlib import Path
from validate_translations import sha
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
        shutil.copytree(ROOT / 'review', self.public / 'review')
        self.private.mkdir()
        for name in CATALOGS:
            original = json.loads((ROOT / 'locales/sl' / name).read_text(encoding='utf-8'))
            # A private source includes the same locale plus the public English reference.
            (self.private / name).write_text(json.dumps(original, ensure_ascii=False), encoding='utf-8')

    def change(self, path, word):
        document = json.loads(path.read_text(encoding='utf-8'))
        document['strings'][TARGET]['localizations']['sl']['stringUnit']['value'] = word
        path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')

    def approve(self):
        c=json.loads((self.public / 'locales/sl/Localizable.xcstrings').read_text(encoding='utf-8'))
        item=c['strings'][TARGET]['localizations']
        ledger=self.public / 'review/languages/sl.json'
        content=json.loads(ledger.read_text(encoding='utf-8'))
        content['reviews']=[{
            'catalog':'Localizable.xcstrings','key':TARGET,
            'source_hash':sha(item['en']),'target_hash':sha(item['sl']),
            'reviewer':'independent-reviewer','evidence':'https://github.com/DrRoglaa/tendo-translations/pull/1',
            'reviewed_at':'2026-10-24','independent':True,
        }]
        ledger.write_text(json.dumps(content),encoding='utf-8')

    def run_import(self, output=None):
        command = [sys.executable, str(SCRIPT), '--repo', str(self.public),
                   '--language', 'sl', '--private-catalogs', str(self.private)]
        if output is not None:
            command += ['--output', str(output)]
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def test_no_changes_dry_run(self):
        completed = self.run_import()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn('proposed approved changes=0, awaiting human review=0', completed.stdout)

    def test_proposes_only_public_edit(self):
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'New text %1$(text)@')
        self.approve()
        proposal = self.home / 'proposal.json'
        completed = self.run_import(proposal)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(proposal.read_text(encoding='utf-8'))
        self.assertEqual(len(result['changes']), 1)
        self.assertEqual(result['changes'][0]['key'], TARGET)
        self.assertEqual(result['changes'][0]['language'], 'sl')

    def test_stale_edit_stops_without_writing(self):
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'Suggestion %1$(text)@')
        self.approve()
        self.change(self.private / 'Localizable.xcstrings', 'New value %1$(text)@')
        proposal = self.home / 'proposal.json'
        completed = self.run_import(proposal)
        self.assertEqual(completed.returncode, 2)
        self.assertIn('CONFLICT', completed.stdout)
        self.assertFalse(proposal.exists())

    def test_unreviewed_change_waits_for_human(self):
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'Draft text %1$(text)@')
        completed=self.run_import()
        self.assertEqual(completed.returncode,0, completed.stdout+completed.stderr)
        self.assertIn('proposed approved changes=0, awaiting human review=1', completed.stdout)

    def test_changed_review_is_stale_and_skipped(self):
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'Reviewed text %1$(text)@')
        self.approve()
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'Newer text %1$(text)@')
        completed=self.run_import()
        self.assertEqual(completed.returncode,0, completed.stdout+completed.stderr)
        self.assertIn('awaiting human review=1', completed.stdout)

    def test_never_writes_into_public_repo(self):
        self.change(self.public / 'locales/sl/Localizable.xcstrings', 'Suggestion %1$(text)@')
        completed = self.run_import(self.public / 'unsafe.json')
        self.assertEqual(completed.returncode, 2)
        self.assertFalse((self.public / 'unsafe.json').exists())


if __name__ == '__main__':
    unittest.main()
