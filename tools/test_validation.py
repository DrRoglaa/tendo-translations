#!/usr/bin/env python3
"""No-network regression/negative tests of read-only public catalog validation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from validate_translations import CATALOGS, load_json, validate_catalog, validate

ROOT=Path(__file__).resolve().parents[1]
BASE=load_json(ROOT/'docs/export-baseline.json')

class PublicCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'Localizable.xcstrings'
        self.lang='sl'
        self.name='Localizable.xcstrings'
        self.catalog=json.loads((ROOT/'locales/sl'/self.name).read_text())

    def check(self):
        self.path.write_text(json.dumps(self.catalog,ensure_ascii=False))
        return validate_catalog(self.path,self.lang,BASE['catalogs'][self.name],self.name)

    def test_original(self):self.assertEqual(self.check(),[])
    def test_removed_key(self):
        self.catalog['strings'].pop(next(iter(self.catalog['strings'])))
        self.assertTrue(self.check())
    def test_unapproved_key(self):
        self.catalog['strings']['secretPrivateKey']={}
        self.assertTrue(self.check())
    def test_english_tampering(self):
        e=next(v for v in self.catalog['strings'].values() if 'stringUnit' in v['localizations']['en'])
        e['localizations']['en']['stringUnit']['value']='Fake source'
        self.assertTrue(self.check())
    def test_comment_tampering(self):
        next(iter(self.catalog['strings'].values()))['comment']='private source code path'
        self.assertTrue(self.check())
    def test_missing_placeholder(self):
        key='tendoTodayToday'
        self.catalog['strings'][key]['localizations']['sl']['stringUnit']['value']='Danes'
        self.assertTrue(any('Placeholder mismatch' in x for x in self.check()))
    def test_plural_missing_dual(self):
        key='tendoLocalizationActiveTaskCount'
        del self.catalog['strings'][key]['localizations']['sl']['variations']['plural']['two']
        self.assertTrue(any('plural' in x for x in self.check()))
    def test_other_locale_injected(self):
        next(iter(self.catalog['strings'].values()))['localizations']['fr']={}
        self.assertTrue(self.check())
    def test_duplicate_json_rejected(self):
        self.path.write_text('{"sourceLanguage":"en","sourceLanguage":"en"}')
        self.assertTrue(validate_catalog(self.path,self.lang,BASE['catalogs'][self.name],self.name))
    def test_string_set_token(self):
        c=json.loads((ROOT/'locales/sl/AppShortcuts.xcstrings').read_text())
        key='Create a task in ${applicationName}'
        c['strings'][key]['localizations']['sl']['stringSet']['values']=['Ustvari opravilo']
        self.path.write_text(json.dumps(c))
        self.assertTrue(any('Placeholder mismatch' in x for x in validate_catalog(self.path,'sl',BASE['catalogs']['AppShortcuts.xcstrings'],'AppShortcuts.xcstrings')))
    def test_all_catalogs(self):
        errors,counts=validate(ROOT,ROOT/'docs/export-baseline.json')
        self.assertEqual(errors,[])
        self.assertEqual(len(counts),21)

if __name__=='__main__':unittest.main()
