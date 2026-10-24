#!/usr/bin/env python3
"""Offline catalog-edit checks for optional graphical editing workflows."""
import json
from pathlib import Path
import tempfile
import unittest
from check_editor_roundtrip import compare
from validate_translations import load_json

ROOT=Path(__file__).resolve().parents[1]
NAME='Localizable.xcstrings'
KEY='tendoTodayToday'
BASE=load_json(ROOT/'docs/export-baseline.json')

class EditorRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.before=ROOT/'locales/sl'/NAME
        self.after=Path(self.tmp.name)/NAME
        self.doc=load_json(self.before)

    def run_edit(self):
        self.after.write_text(json.dumps(self.doc,ensure_ascii=False),encoding='utf-8')
        return compare(self.before,self.after,'sl',NAME,BASE['catalogs'][NAME])

    def test_no_edit_is_safe(self):
        self.assertEqual(self.run_edit(),([],0))

    def test_valid_target_edit_is_safe(self):
        self.doc['strings'][KEY]['localizations']['sl']['stringUnit']['value']='New text %1$(text)@'
        self.assertEqual(self.run_edit(),([],1))

    def test_english_edit_is_blocked(self):
        self.doc['strings'][KEY]['localizations']['en']['stringUnit']['value']='Unapproved source'
        self.assertTrue(self.run_edit()[0])

    def test_editor_comment_rewrite_is_blocked(self):
        self.doc['strings'][KEY]['comment']='Editor changed comment'
        self.assertTrue(self.run_edit()[0])

if __name__=='__main__':unittest.main()
