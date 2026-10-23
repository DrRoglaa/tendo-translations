#!/usr/bin/env python3
"""No-network regression/negative tests of read-only public catalog validation."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from validate_translations import CATALOGS, load_json, validate_catalog, validate, compare_pr_scope

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

class PullRequestScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / 'base'
        self.pr = Path(self.tmp.name) / 'pr'
        (self.base / 'locales/sl').mkdir(parents=True)
        (self.base / 'README.md').write_text('approved description')
        (self.base / 'locales/sl/Localizable.xcstrings').write_text('old value')
        shutil.copytree(self.base, self.pr)

    def scope(self):
        return compare_pr_scope(self.pr, self.base, ['sl', 'de'])

    def test_one_language_allowed(self):
        (self.pr / 'locales/sl/Localizable.xcstrings').write_text('new value')
        self.assertEqual(self.scope(), [])

    def test_tooling_or_docs_change_rejected(self):
        (self.pr / 'README.md').write_text('changed description')
        self.assertTrue(any('non-translation' in err for err in self.scope()))

    def test_unexpected_file_rejected(self):
        (self.pr / 'locales/sl/private.swift').write_text('do not publish')
        self.assertTrue(self.scope())

    def test_two_languages_rejected(self):
        (self.pr / 'locales/sl/Localizable.xcstrings').write_text('new value')
        (self.pr / 'locales/de').mkdir()
        (self.pr / 'locales/de/Localizable.xcstrings').write_text('new value')
        self.assertTrue(any('one locale' in err for err in self.scope()))

    def test_symlink_rejected(self):
        (self.pr / 'README.md').unlink()
        (self.pr / 'README.md').symlink_to('/etc/passwd')
        self.assertTrue(self.scope())


if __name__=='__main__':unittest.main()
