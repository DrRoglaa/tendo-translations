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
    def test_siri_alternative_count_cannot_change(self):
        c=json.loads((ROOT/'locales/sl/AppShortcuts.xcstrings').read_text())
        key='Create a task in ${applicationName}'
        c['strings'][key]['localizations']['sl']['stringSet']['values'].append('Ustvari opravilo v ${applicationName}')
        self.path.write_text(json.dumps(c,ensure_ascii=False))
        self.assertTrue(any('alternative count' in x for x in validate_catalog(self.path,'sl',BASE['catalogs']['AppShortcuts.xcstrings'],'AppShortcuts.xcstrings')))
    def test_siri_string_set_cannot_become_string_unit(self):
        c=json.loads((ROOT/'locales/sl/AppShortcuts.xcstrings').read_text())
        key='Create a task in ${applicationName}'
        c['strings'][key]['localizations']['sl']={'stringUnit':{'state':'translated','value':'Ustvari opravilo v ${applicationName}'}}
        self.path.write_text(json.dumps(c,ensure_ascii=False))
        self.assertTrue(any('StringSet versus StringUnit' in x for x in validate_catalog(self.path,'sl',BASE['catalogs']['AppShortcuts.xcstrings'],'AppShortcuts.xcstrings')))
    def test_newline_structure(self):
        key=next(k for k,v in self.catalog['strings'].items() if '\n' in v['localizations']['en'].get('stringUnit',{}).get('value',''))
        self.catalog['strings'][key]['localizations']['sl']['stringUnit']['value']=self.catalog['strings'][key]['localizations']['sl']['stringUnit']['value'].replace('\n',' ')
        self.assertTrue(any('newline structure' in x for x in self.check()))
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


class PullRequestWorkflowSecurityTests(unittest.TestCase):
    """Static checks for the trusted-validator/untrusted-catalogs CI boundary."""

    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / '.github/workflows/validate-translations.yml').read_text(encoding='utf-8')
        cls.trusted_step = cls.text.split('- name: Checkout trusted base validator', 1)[1].split('- name: Checkout proposed changes', 1)[0]
        cls.untrusted_step = cls.text.split('- name: Checkout proposed changes (data only)', 1)[1].split('- name: Test trusted validator', 1)[0]

    def test_pull_request_event_is_unprivileged(self):
        self.assertIn('  pull_request:', self.text)
        self.assertNotIn('pull_request_target', self.text)
        self.assertIn('permissions:\n  contents: read', self.text)

    def test_trusted_checkout_is_pinned_to_base(self):
        self.assertIn('ref: ${{ github.event.pull_request.base.sha || github.sha }}', self.trusted_step)
        self.assertIn('path: validation-base', self.trusted_step)
        self.assertIn('persist-credentials: false', self.trusted_step)

    def test_fork_pr_uses_exact_head_in_its_repository(self):
        self.assertIn('repository: ${{ github.event.pull_request.head.repo.full_name || github.repository }}', self.untrusted_step)
        self.assertIn('ref: ${{ github.event.pull_request.head.sha || github.sha }}', self.untrusted_step)
        self.assertNotIn('ref: ${{ github.ref }}', self.untrusted_step)
        self.assertIn('path: submission', self.untrusted_step)
        self.assertIn('persist-credentials: false', self.untrusted_step)

    def test_untrusted_checkout_is_data_only(self):
        self.assertNotIn('run: submission/', self.text)
        self.assertNotIn('python3 submission/', self.text)
        self.assertIn('python3 -m unittest discover -s validation-base/tools', self.text)
        self.assertIn('python3 validation-base/tools/validate_translations.py', self.text)
        self.assertIn('python3 validation-base/tools/review_tracking.py', self.text)
        self.assertIn('--repo submission', self.text)
        self.assertIn('--baseline validation-base/docs/export-baseline.json', self.text)
        self.assertIn('--base-tree validation-base', self.text)


if __name__=='__main__':unittest.main()
