#!/usr/bin/env python3
"""Security and API-failure tests for the immutable-base PR path guard."""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from pr_policy import REPO
from pr_scope_guard import classify_paths, evaluate, github_files

ROOT = Path(__file__).resolve().parents[1]


def change(path, status="modified", old=None):
    item = {"filename": path, "status": status}
    if old is not None:
        item["previous_filename"] = old
    return item


def decide(items, owner="translator", association="NONE", head="fork/tendo-translations"):
    return classify_paths(items, owner, association, head, REPO)


class TrustedGuardScopeTests(unittest.TestCase):
    def test_one_language_catalog_passes(self):
        self.assertEqual(decide([change("locales/sl/Localizable.xcstrings"),
                                 change("locales/sl/InfoPlist.xcstrings")]),
                         ("contributor", []))

    def test_contributor_docs_change_rejected(self):
        mode, problems = decide([change("README.md")])
        self.assertEqual(mode, "contributor")
        self.assertTrue(problems)

    def test_contributor_cannot_replace_validation_workflow(self):
        mode, problems = decide([change(".github/workflows/validate-translations.yml")])
        self.assertEqual(mode, "contributor")
        self.assertTrue(problems)

    def test_fork_workflow_override_rejected_even_when_author_owner(self):
        mode, problems = decide([change(".github/workflows/validate-translations.yml")],
                                owner="DrRoglaa", association="OWNER")
        self.assertEqual(mode, "contributor")
        self.assertTrue(problems)

    def test_two_language_changes_rejected(self):
        _, problems = decide([change("locales/sl/Localizable.xcstrings"),
                              change("locales/de/Localizable.xcstrings")])
        self.assertTrue(any("one language" in p for p in problems))

    def test_owner_docs_and_workflow_pass(self):
        mode, problems = decide([change("README.md"),
                                 change(".github/workflows/validate-translations.yml"),
                                 change("tools/test_validation.py")],
                                owner="DrRoglaa", association="OWNER", head=REPO)
        self.assertEqual((mode, problems), ("maintainer", []))

    def test_owner_cannot_modify_export_baseline(self):
        _, problems = decide([change("docs/export-baseline.json")],
                             owner="DrRoglaa", association="OWNER", head=REPO)
        self.assertTrue(problems)

    def test_owner_cannot_delete_or_rename_any_file(self):
        for item in (change("README.md", "removed"),
                     change("README.md", "renamed", old="CONTRIBUTING.md")):
            with self.subTest(item=item):
                _, problems = decide([item], owner="DrRoglaa",
                                     association="OWNER", head=REPO)
                self.assertTrue(any("migration" in problem for problem in problems))

    def test_contributor_renaming_between_languages_is_rejected(self):
        _, problems = decide([change("locales/de/Localizable.xcstrings", "renamed",
                                    old="locales/sl/Localizable.xcstrings")])
        self.assertTrue(any("one language" in p for p in problems))

    def test_unreported_old_filename_is_rejected(self):
        _, problems = decide([change("locales/sl/Localizable.xcstrings", "renamed")])
        self.assertTrue(problems)

    def test_unknown_file_status_is_rejected(self):
        _, problems = decide([change("README.md", "imaginary")])
        self.assertTrue(problems)

    def test_empty_change_list_fails_closed(self):
        self.assertTrue(decide([])[1])

    def test_github_truncation_fails_closed(self):
        _, problems = decide([change("locales/sl/Localizable.xcstrings")] * 3000)
        self.assertTrue(problems)


class TrustedGuardAPITests(unittest.TestCase):
    def test_multiple_pages_are_supported(self):
        pages = [[change("locales/sl/Localizable.xcstrings")] * 100,
                 [change("locales/sl/InfoPlist.xcstrings")]]
        with patch("pr_scope_guard.request_json", side_effect=pages):
            self.assertEqual(len(github_files(7, "read-only-token")), 101)

    def test_api_pagination_limit_is_rejected(self):
        with patch("pr_scope_guard.request_json",
                   return_value=[change("locales/sl/Localizable.xcstrings")] * 100):
            with self.assertRaises(ValueError):
                github_files(7, "read-only-token")

    def test_event_must_match_current_pr_commit(self):
        event = {
            "repository": {"full_name": REPO},
            "pull_request": {"number": 7, "head": {"sha": "old"},
                             "base": {"sha": "base"}},
        }
        current = {
            "state": "open", "head": {"sha": "new", "repo": {"full_name": REPO}},
            "base": {"sha": "base", "repo": {"full_name": REPO}},
            "user": {"login": "DrRoglaa"}, "author_association": "OWNER",
        }
        with patch("pr_scope_guard.request_json", return_value=current):
            with self.assertRaisesRegex(ValueError, "changed during validation"):
                evaluate(event, "read-only-token")

    def test_fresh_event_does_not_bypass_fork_restrictions(self):
        event = {
            "repository": {"full_name": REPO},
            "pull_request": {"number": 7, "head": {"sha": "head"},
                             "base": {"sha": "base"}},
        }
        current = {
            "state": "open", "head": {"sha": "head", "repo": {"full_name": "fork/translations"}},
            "base": {"sha": "base", "repo": {"full_name": REPO}},
            "user": {"login": "other"}, "author_association": "CONTRIBUTOR",
        }
        with patch("pr_scope_guard.request_json", return_value=current), \
             patch("pr_scope_guard.github_files", return_value=[change("tools/evil.py")]):
            self.assertTrue(evaluate(event, "read-only-token")[1])


class GuardWorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = (ROOT / ".github/workflows/trusted-pr-scope-guard.yml").read_text()
        cls.catalog = (ROOT / ".github/workflows/validate-translations.yml").read_text()

    def test_guard_runs_on_base_workflow_not_pr_merge(self):
        self.assertIn("  pull_request_target:", self.guard)
        self.assertNotIn("  pull_request:\n", self.guard)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", self.guard)
        self.assertNotIn("head.sha", self.guard)
        self.assertNotIn("head.repo", self.guard)

    def test_guard_is_read_only_and_no_submitted_checkout(self):
        self.assertIn("permissions:\n  contents: read\n  pull-requests: read", self.guard)
        self.assertIn("persist-credentials: false", self.guard)
        self.assertNotIn("submission", self.guard)
        self.assertNotIn("allow-unsafe-pr-checkout", self.guard)
        self.assertIn("python3 trusted-base/tools/pr_scope_guard.py", self.guard)

    def test_both_checks_have_unique_names(self):
        self.assertIn("name: trusted-pr-scope", self.guard)
        self.assertIn("name: validate-public-catalogs", self.catalog)
        self.assertNotIn("name: trusted-pr-scope", self.catalog)

    def test_catalog_workflow_keeps_unskipped_pr_check(self):
        self.assertIn("  pull_request:\n    branches: [main]", self.catalog)
        self.assertIn("  workflow_dispatch:", self.catalog)
        self.assertIn("    name: validate-public-catalogs", self.catalog)
        self.assertNotIn("  pull_request_target:", self.catalog)
        self.assertNotIn("    paths:", self.catalog)
        self.assertNotIn("\n    if:", self.catalog)  # No job-level conditional; required check always reports.

    def test_catalog_workflow_is_read_only(self):
        self.assertIn("permissions:\n  contents: read", self.catalog)
        self.assertNotIn("contents: write", self.catalog)
        self.assertIn("persist-credentials: false", self.catalog)
        self.assertEqual(self.catalog.count("actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"), 2)

    def test_trusted_base_code_and_untrusted_data_are_separate(self):
        self.assertIn("ref: ${{ github.event.pull_request.base.sha || github.sha }}", self.catalog)
        self.assertIn("path: validation-base", self.catalog)
        self.assertIn("repository: ${{ github.event.pull_request.head.repo.full_name || github.repository }}", self.catalog)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha || github.sha }}", self.catalog)
        self.assertIn("path: submission", self.catalog)
        self.assertIn("python3 validation-base/tools/pr_policy.py", self.catalog)
        self.assertIn("--baseline validation-base/docs/export-baseline.json", self.catalog)
        self.assertIn("--base-tree validation-base", self.catalog)
        self.assertNotIn("python3 submission/", self.catalog)
        self.assertNotIn("pip install", self.catalog)
        self.assertNotIn("allow-unsafe-pr-checkout", self.catalog)

    def test_pr_identity_comes_from_event_not_shell_interpolation(self):
        section = self.catalog.split("      - name: Validate pull request with trusted policy\n", 1)[1]
        section = section.split("      - name: ", 1)[0]
        self.assertIn("if: github.event_name == 'pull_request'", section)
        for env, context, argument in (
            ("PR_AUTHOR", "user.login", "--pr-author"),
            ("PR_ASSOCIATION", "author_association", "--pr-author-association"),
            ("PR_HEAD_REPO", "head.repo.full_name", "--pr-head-repo"),
            ("PR_BASE_REPO", "base.repo.full_name", "--pr-base-repo"),
        ):
            with self.subTest(env=env):
                self.assertIn(f"{env}: ${{{{ github.event.pull_request.{context} }}}}", section)
                self.assertIn(f'{argument} "${env}"', section)
        command = section.split("        run: |", 1)[1]
        self.assertNotIn("${{", command)
        self.assertNotIn("submission/tools", command)

    def test_manual_dispatch_does_not_claim_pr_policy_result(self):
        self.assertIn("      - name: Validate catalogs on manual dispatch\n"
                      "        if: github.event_name == 'workflow_dispatch'", self.catalog)
        self.assertIn("      - name: Validate review evidence on manual dispatch\n"
                      "        if: github.event_name == 'workflow_dispatch'", self.catalog)
        self.assertIn("python3 validation-base/tools/validate_translations.py", self.catalog)
        self.assertIn("python3 validation-base/tools/review_tracking.py", self.catalog)


if __name__ == "__main__":
    unittest.main()
