#!/usr/bin/env python3
"""Review-evidence tests: machine drafts never create independent human approval."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from review_tracking import expected_batches, validate_review
from validate_translations import CATALOGS, PLURALS, load_json, sha

ROOT=Path(__file__).resolve().parents[1]
BASE=load_json(ROOT/'docs/export-baseline.json')
KEY='tendoTodayToday'
NAME='Localizable.xcstrings'


class ReviewTrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'review/languages').mkdir(parents=True)
        (self.root/'review/batches.json').write_bytes((ROOT/'review/batches.json').read_bytes())
        for lang in PLURALS:
            (self.root/'review/languages'/f'{lang}.json').write_bytes((ROOT/'review/languages'/f'{lang}.json').read_bytes())
        (self.root/'locales/sl').mkdir(parents=True)
        shutil.copyfile(ROOT/'locales/sl'/NAME,self.root/'locales/sl'/NAME)

    def sign_off(self):
        data=load_json(self.root/'locales/sl'/NAME)
        loc=data['strings'][KEY]['localizations']
        record={'catalog':NAME,'key':KEY,'reviewer':'volunteer-reviewer',
                'evidence':'https://github.com/DrRoglaa/tendo-translations/pull/1',
                'reviewed_at':'2026-10-24','independent':True,
                'source_hash':sha(loc['en']),'target_hash':sha(loc['sl'])}
        path=self.root/'review/languages/sl.json'
        led=load_json(path);led['reviews'].append(record)
        path.write_text(json.dumps(led),encoding='utf-8')
        return record

    def test_empty_ledgers_do_not_approve_drafts(self):
        errors,status,batches=validate_review(self.root, BASE)
        self.assertEqual(errors,[])
        self.assertTrue(batches)
        self.assertEqual(status['sl']['approved'],0)
        self.assertEqual(status['sl']['total'],2410)

    def test_independent_review_counts_exact_key(self):
        self.sign_off()
        errors,status,_=validate_review(self.root,BASE)
        self.assertEqual(errors,[])
        self.assertEqual(status['sl']['approved'],1)
        self.assertEqual(status['de']['approved'],0)

    def test_review_becomes_stale_after_edit(self):
        self.sign_off()
        path=self.root/'locales/sl'/NAME
        catalog=load_json(path)
        catalog['strings'][KEY]['localizations']['sl']['stringUnit']['value']='Modified after review'
        path.write_text(json.dumps(catalog),encoding='utf-8')
        errors,status,_=validate_review(self.root,BASE)
        self.assertEqual(errors,[])
        self.assertEqual(status['sl']['approved'],0)
        self.assertEqual(status['sl']['stale'],1)

    def test_fake_evidence_is_rejected(self):
        self.sign_off()
        path=self.root/'review/languages/sl.json'
        led=load_json(path);led['reviews'][0]['evidence']='https://example.invalid/review'
        path.write_text(json.dumps(led),encoding='utf-8')
        errors,_,_=validate_review(self.root,BASE)
        self.assertTrue(any('Evidence must link' in e for e in errors))

    def test_nonindependent_review_is_rejected(self):
        self.sign_off()
        path=self.root/'review/languages/sl.json'
        led=load_json(path);led['reviews'][0]['independent']=False
        path.write_text(json.dumps(led),encoding='utf-8')
        errors,_,_=validate_review(self.root,BASE)
        self.assertTrue(any('Independent human review' in e for e in errors))

    def test_duplicate_signoff_is_rejected(self):
        self.sign_off()
        path=self.root/'review/languages/sl.json'
        led=load_json(path);led['reviews'].append(copy.deepcopy(led['reviews'][0]))
        path.write_text(json.dumps(led),encoding='utf-8')
        errors,_,_=validate_review(self.root,BASE)
        self.assertTrue(any('Duplicate review' in e for e in errors))

    def test_manifest_cannot_drop_unreviewed_key(self):
        path=self.root/'review/batches.json'
        doc=load_json(path);doc['batches'][0]['keys'].pop()
        path.write_text(json.dumps(doc),encoding='utf-8')
        errors,_,_=validate_review(self.root,BASE)
        self.assertTrue(any('batches do not match' in e for e in errors))

    def test_batch_integrity_all_2410_keys(self):
        batches=expected_batches(BASE)
        self.assertEqual(sum(len(b['keys']) for b in batches),2410)
        self.assertTrue(all(1<=len(b['keys'])<=75 for b in batches))
        self.assertEqual(len(batches),53)


if __name__=='__main__':
    unittest.main()
