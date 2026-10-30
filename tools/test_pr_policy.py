#!/usr/bin/env python3
"""Adversarial unit tests for the future trusted-base PR policy."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pr_policy import (REPO, allowed_maintainer_path, check, git_tree_issues,
                       is_owner_pr, maintainer_scope)
from translation_status import report
from validate_translations import CATALOGS, PLURALS

ROOT = Path(__file__).resolve().parents[1]


class OwnerClassificationTests(unittest.TestCase):
    def test_only_owner_same_repository_is_maintainer(self):
        self.assertTrue(is_owner_pr("DrRoglaa", "OWNER", REPO, REPO))

    def test_fork_is_never_maintainer(self):
        self.assertFalse(is_owner_pr("DrRoglaa", "OWNER", "other/tendo-translations", REPO))

    def test_collaborator_is_never_maintainer(self):
        self.assertFalse(is_owner_pr("contributor", "COLLABORATOR", REPO, REPO))

    def test_missing_or_spoofed_owner_association_is_rejected(self):
        self.assertFalse(is_owner_pr("DrRoglaa", "CONTRIBUTOR", REPO, REPO))
        self.assertFalse(is_owner_pr("drr oglaa", "OWNER", REPO, REPO))

    def test_unapproved_paths_not_maintainer_editable(self):
        for name in ("docs/export-baseline.json", "docs/SOURCE-PROVENANCE.md",
                     "review/batches.json", "locales/sl/Localizable.xcstrings",
                     "Tendo/Private.swift", "review/languages/xx.json",
                     ".github/workflows/../secret.yml"):
            with self.subTest(name=name):
                self.assertFalse(allowed_maintainer_path(Path(name)))

    def test_owner_maintenance_paths_are_bounded(self):
        for name in ("tools/pr_policy.py", ".github/workflows/validate-translations.yml",
                     ".github/ISSUE_TEMPLATE/offer-help.yml", "review/languages/sl.json",
                     "docs/proofreading/sl/focus.md", "docs/TRANSLATION-STATUS.md",
                     "README.md", ".github/CODEOWNERS"):
            with self.subTest(name=name):
                self.assertTrue(allowed_maintainer_path(Path(name)))


class PolicyDecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "base"
        self.head = Path(self.tmp.name) / "head"
        initial = {
            "README.md": "Original public docs\n",
            "docs/TRANSLATION-STATUS.md": "Original status\n",
            "docs/proofreading/sl/focus.md": "generated\n",
            "review/languages/sl.json": "{}\n",
            "review/batches.json": "{}\n",
            "locales/sl/Localizable.xcstrings": "old translation\n",
            "tools/validate_translations.py": "# trusted\n",
            ".github/workflows/validate-translations.yml": "name: PR\n",
        }
        for rel, text in initial.items():
            dest = self.base / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
        shutil.copytree(self.base, self.head)
        self.baseline = self.base / "docs/export-baseline.json"

    def change(self, rel, text):
        dest = self.head / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)

    def run_policy(self, author="DrRoglaa", association="OWNER",
                   head_repo=REPO, base_repo=REPO, catalog_errors=(), review_errors=(),
                   page_errors=(), expected_status="Original status\n"):
        # Simulate the data validator in these scope tests. The existing
        # catalog/review tests exercise the full validators independently.
        with patch("pr_policy.git_tree_issues", return_value=[]), \
             patch("pr_policy.validate", return_value=(list(catalog_errors), {})), \
             patch("pr_policy.validate_review", return_value=(list(review_errors), {}, [])), \
             patch("pr_policy.render_pages", return_value={}), \
             patch("pr_policy.verify_pages", return_value=list(page_errors)), \
             patch("pr_policy.report", return_value=expected_status):
            return check(self.head, self.base, self.baseline, author,
                         association, head_repo, base_repo)

    def test_single_locale_edit_allowed_for_everyone(self):
        self.change("locales/sl/Localizable.xcstrings", "improved translation\n")
        self.assertEqual(self.run_policy(author="translator", association="NONE",
                                         head_repo="translator/tendo-translations"),
                         ("contributor", []))

    def test_owner_catalog_edit_uses_same_contributor_rules(self):
        self.change("locales/sl/Localizable.xcstrings", "fixed translation\n")
        self.assertEqual(self.run_policy(), ("contributor", []))

    def test_owner_docs_and_tools_allowed(self):
        self.change("README.md", "Updated readme\n")
        self.change("tools/helper.py", "# this is a safe Python source\n")
        self.change(".github/workflows/validate-translations.yml", "name: checked\n")
        self.assertEqual(self.run_policy(), ("maintainer", []))

    def test_owner_generated_pages_require_exact_generation(self):
        self.change("docs/proofreading/sl/focus.md", "different\n")
        mode, issues = self.run_policy(page_errors=("Generated page is stale",))
        self.assertEqual(mode, "maintainer")
        self.assertIn("Generated page is stale", issues)

    def test_owner_review_evidence_requires_matching_status(self):
        self.change("review/languages/sl.json", '{"reviewed": []}\n')
        mode, issues = self.run_policy(expected_status="new status\n")
        self.assertEqual(mode, "maintainer")
        self.assertTrue(any("status report" in x for x in issues))

    def test_owner_review_evidence_with_matching_status(self):
        self.change("review/languages/sl.json", '{"reviewed": []}\n')
        self.change("docs/TRANSLATION-STATUS.md", "new status\n")
        self.assertEqual(self.run_policy(expected_status="new status\n"),
                         ("maintainer", []))

    def test_fork_cannot_modify_tools(self):
        self.change("tools/helper.py", "print('bad')\n")
        mode, issues = self.run_policy(head_repo="fork/tendo-translations")
        self.assertEqual(mode, "contributor")
        self.assertTrue(any("non-translation" in x for x in issues))

    def test_collaborator_cannot_modify_workflow(self):
        self.change(".github/workflows/validate-translations.yml", "name: other\n")
        mode, issues = self.run_policy(author="other", association="COLLABORATOR")
        self.assertEqual(mode, "contributor")
        self.assertTrue(issues)

    def test_owner_cannot_change_export_baseline(self):
        self.change("docs/export-baseline.json", "{}")
        mode, issues = self.run_policy()
        self.assertEqual(mode, "maintainer")
        self.assertTrue(any("Protected" in x for x in issues))

    def test_owner_cannot_change_review_batches(self):
        self.change("review/batches.json", "different")
        self.assertTrue(self.run_policy()[1])

    def test_owner_cannot_change_english_or_target_in_maintainer_mode(self):
        self.change("README.md", "docs change\n")
        self.change("locales/sl/Localizable.xcstrings", "target change\n")
        mode, issues = self.run_policy()
        self.assertEqual(mode, "maintainer")
        self.assertTrue(any("Protected" in x for x in issues))

    def test_owner_cannot_delete_files(self):
        (self.head / "README.md").unlink()
        self.assertTrue(any("deletion" in x for x in self.run_policy()[1]))

    def test_owner_cannot_add_private_swift(self):
        self.change("docs/private.swift", "struct Private {}\n")
        self.assertTrue(self.run_policy()[1])

    def test_owner_invalid_python_rejected_without_executing(self):
        self.change("tools/bad.py", "if :\n    print('never executed')\n")
        self.assertTrue(any("syntax" in x for x in self.run_policy()[1]))

    def test_owner_oversized_change_rejected(self):
        self.change("README.md", "x" * 1_000_001)
        self.assertTrue(any("Oversized" in x for x in self.run_policy()[1]))

    def test_owner_symlink_rejected(self):
        (self.head / "README.md").unlink()
        (self.head / "README.md").symlink_to("/etc/passwd")
        self.assertTrue(any("Symlink" in x for x in self.run_policy()[1]))

    def test_translation_validation_error_rejects_allowed_scope(self):
        self.change("locales/sl/Localizable.xcstrings", "target change\n")
        self.assertIn("Bad placeholder", self.run_policy(catalog_errors=("Bad placeholder",))[1])

    def test_review_error_rejects_owner_docs_pr(self):
        self.change("README.md", "Changed\n")
        self.assertIn("Invalid review evidence",
                      self.run_policy(review_errors=("Invalid review evidence",))[1])

    def test_maintainer_scope_cannot_touch_unapproved_files(self):
        self.change("docs/secret.txt", "not approved\n")
        self.assertTrue(maintainer_scope(self.head, self.base))


class GitObjectSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "repo"
        self.path.mkdir()
        subprocess.run(["git", "init", "-q", str(self.path)], check=True)
        (self.path / "README.md").write_text("safe")
        self.git("add", "README.md")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "init")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.path), *args],
                              capture_output=True, check=True)

    def test_regular_blob_is_allowed(self):
        self.assertEqual(git_tree_issues(self.path), [])

    def test_github_gitlink_cannot_hide_from_file_walk(self):
        self.git("update-index", "--add", "--cacheinfo",
                 "160000," + "a" * 40 + ",externals")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "gitlink")
        self.assertTrue(any("gitlink" in issue for issue in git_tree_issues(self.path)))

    def test_executable_file_mode_rejected(self):
        os.chmod(self.path / "README.md", 0o755)
        self.git("add", "README.md")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "executable")
        self.assertTrue(any("mode" in issue for issue in git_tree_issues(self.path)))

    def test_missing_git_checkout_is_rejected(self):
        self.assertTrue(git_tree_issues(Path(self.tmp.name) / "missing"))


class DynamicReviewStatusTests(unittest.TestCase):
    def test_approved_count_is_not_hard_coded_to_zero(self):
        counts = {f"{lang}/{name}": 1 for lang in PLURALS for name in CATALOGS}
        statuses = {lang: {"approved": (1 if lang == "sl" else 0), "stale": 0}
                    for lang in PLURALS}
        with patch("translation_status.validate", return_value=([], counts)), \
             patch("translation_status.validate_review",
                   return_value=([], statuses, [{}] * 53)):
            text = report(ROOT)
        self.assertIn("1 independently documented human approval", text)
        self.assertNotIn("no independently documented human approvals", text)


if __name__ == "__main__":
    unittest.main()
