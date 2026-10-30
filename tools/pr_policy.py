#!/usr/bin/env python3
"""Read-only PR policy for the public, translation-only Tendo repository.

This module MUST be executed from the trusted PR base checkout. The PR's
checkout is untrusted input, never an import path, executable, dependency, or
shell script. GitHub event metadata (not PR content) determines owner access.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import subprocess
import sys

from generate_proofreading_pages import render_pages, verify_pages
from review_tracking import validate_review
from translation_status import report
from validate_translations import PLURALS, compare_pr_scope, validate

OWNER = "DrRoglaa"
REPO = "DrRoglaa/tendo-translations"
MAX_EDITED_SIZE = 1_000_000
ROOT_DOCS = frozenset({
    "README.md", "CONTRIBUTING.md", "TRANSLATING.md", "SECURITY.md",
    "CODE_OF_CONDUCT.md", "CONTRIBUTORS.md", "LICENSING.md",
    "LICENSE-CODE", "LICENSE-TRANSLATIONS",
})


def is_owner_pr(author: str, association: str, head_repo: str,
                base_repo: str) -> bool:
    """Owner-only maintainer mode; a fork or collaborator cannot opt into it."""
    return (author == OWNER and association == "OWNER"
            and head_repo == base_repo == REPO)


def public_files(root: Path) -> set[Path]:
    """Inspect a checkout without following symlinks into other directories."""
    return {
        p.relative_to(root) for p in root.rglob("*")
        if (p.is_file() or p.is_symlink())
        and not ({".git", "__pycache__"} & set(p.relative_to(root).parts))
        and p.suffix not in {".pyc", ".pyo"}
    }


def allowed_maintainer_path(rel: Path) -> bool:
    """Bounded owner-only maintenance; never permit catalog/source edits here."""
    parts = rel.parts
    if len(parts) == 1:
        return rel.name in ROOT_DOCS
    if parts == (".github", "CODEOWNERS"):
        return True
    if len(parts) == 2 and parts[0] == ".github":
        return parts[1] == "pull_request_template.md"
    if len(parts) == 3 and parts[:2] == (".github", "workflows"):
        return rel.suffix in {".yml", ".yaml"}
    if len(parts) == 3 and parts[:2] == (".github", "ISSUE_TEMPLATE"):
        return rel.suffix in {".yml", ".yaml"}
    if len(parts) == 2 and parts[0] == "tools":
        return rel.suffix == ".py"
    if len(parts) == 2 and parts[0] == "docs":
        return rel.suffix == ".md" and rel.name != "SOURCE-PROVENANCE.md"
    if parts == ("review", "README.md"):
        return True
    if len(parts) == 3 and parts[:2] == ("review", "languages"):
        return rel.name in {f"{lang}.json" for lang in PLURALS}
    if parts[:2] == ("docs", "proofreading"):
        if len(parts) == 3:
            return parts[2] == "README.md"
        if len(parts) == 4:
            return parts[2] in PLURALS and rel.suffix == ".md"
    return False


def git_tree_issues(root: Path) -> list[str]:
    """Reject gitlinks, symlinks and executable files hidden from file walks.

    ls-tree is read-only and does not invoke Git hooks. All files in the
    approved public repository are regular, non-executable 100644 blobs.
    """
    if not (root / ".git").exists():
        return ["Submitted checkout has no Git metadata"]
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-rz", "--full-tree", "HEAD"],
            capture_output=True, check=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [f"Cannot inspect submitted Git tree: {type(exc).__name__}"]
    issues = []
    for item in result.stdout.split(b"\0"):
        if not item:
            continue
        try:
            meta, name = item.split(b"\t", 1)
            mode, kind, _oid = meta.split(b" ", 2)
            path = Path(name.decode("utf-8", "surrogateescape"))
            dest = root / path
            if mode != b"100644" or kind != b"blob":
                issues.append(f"Forbidden Git file mode or gitlink: {path}")
            elif not dest.is_file() or dest.is_symlink():
                issues.append(f"Missing, symlinked or invalid tracked file: {path}")
        except (ValueError, UnicodeError):
            issues.append("Malformed Git tree entry")
    return issues


def maintainer_scope(submission: Path, base: Path) -> list[str]:
    """Limit owner edits to reviewed maintenance paths; no removals or catalogs."""
    errors = []
    old, new = public_files(base), public_files(submission)
    for rel in sorted(old | new):
        previous, current = base / rel, submission / rel
        if previous.is_symlink() or current.is_symlink():
            errors.append(f"Symlink forbidden: {rel}")
            continue
        if rel in old and rel not in new:
            errors.append(f"File deletion requires a separate reviewed migration: {rel}")
            continue
        if rel in old and rel in new and previous.read_bytes() == current.read_bytes():
            continue
        if not allowed_maintainer_path(rel):
            errors.append(f"Protected data or out-of-scope maintainer change: {rel}")
        elif current.stat().st_size > MAX_EDITED_SIZE:
            errors.append(f"Oversized maintainer change: {rel}")
        elif rel.parts[0] == "tools" and rel.suffix == ".py":
            try:
                # Parse untrusted Python as DATA, never import or run it.
                ast.parse(current.read_text(encoding="utf-8"), filename=str(rel))
            except (UnicodeError, SyntaxError, ValueError) as exc:
                errors.append(f"Invalid maintainer Python syntax: {rel} ({type(exc).__name__})")
    return errors


def check(submission: Path, base: Path, baseline: Path,
          author: str, association: str, head_repo: str,
          base_repo: str) -> tuple[str, list[str]]:
    """Fail closed: every PR must pass catalog and review-schema validation."""
    errors = git_tree_issues(submission)
    ordinary = compare_pr_scope(submission, base, list(PLURALS))
    if not ordinary:
        mode = "contributor"
    elif is_owner_pr(author, association, head_repo, base_repo):
        mode = "maintainer"
        errors.extend(maintainer_scope(submission, base))
    else:
        mode = "contributor"
        errors.extend(ordinary)

    problems, _counts = validate(submission, baseline)
    errors.extend(problems)
    review_issues, _status, _batches = validate_review(submission)
    errors.extend(review_issues)
    # Contributor PRs cannot edit generated pages, and the public snapshot may
    # temporarily lag an accepted translation until the owner regenerates it.
    snapshot = base if mode == "contributor" else submission
    errors.extend(verify_pages(snapshot, render_pages(snapshot)))
    # Owner ledger updates must also publish a matching human-review report.
    if mode == "maintainer":
        expected_status = report(submission)
        actual = (submission / "docs/TRANSLATION-STATUS.md").read_text(encoding="utf-8")
        if actual != expected_status:
            errors.append("Maintainer review status report does not match evidence")
    return mode, errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--base-tree", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--pr-author", required=True)
    p.add_argument("--pr-author-association", required=True)
    p.add_argument("--pr-head-repo", required=True)
    p.add_argument("--pr-base-repo", required=True)
    a = p.parse_args()
    try:
        mode, errors = check(a.repo.resolve(), a.base_tree.resolve(),
                             a.baseline.resolve(), a.pr_author,
                             a.pr_author_association, a.pr_head_repo,
                             a.pr_base_repo)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        print(f"FAIL: PR validation error: {exc}", file=sys.stderr)
        return 1
    for problem in errors[:40]:
        print(f"FAIL: {problem}", file=sys.stderr)
    print(f"{'PASS' if not errors else 'FAIL'}: {mode} PR policy ({len(errors)} issue(s))")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
