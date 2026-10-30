#!/usr/bin/env python3
"""Trusted GitHub-API PR path guard; never checkout/execute PR contents.

Run ONLY from the protected base repository's pull_request_target workflow.
This is a separate required check preventing contributor-edited PR workflows
from bypassing the ordinary read-only catalog validator.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pr_policy import REPO, allowed_maintainer_path, is_owner_pr
from validate_translations import CATALOGS, PLURALS

API = "https://api.github.com/repos/" + REPO
PERMITTED_CATALOGS = {
    f"locales/{lang}/{name}": lang for lang in PLURALS for name in CATALOGS
}
MAX_PR_FILES = 3000  # GitHub's REST pull-files listing limit; fail closed.


def classify_paths(files: list[dict], author: str, association: str,
                   head_repo: str, base_repo: str) -> tuple[str, list[str]]:
    """Check both paths of renames; never trust PR-authored claims of ownership."""
    problems: list[str] = []
    touched: set[str] = set()
    valid_statuses = {"added", "modified", "removed", "renamed"}
    if not files:
        return "contributor", ["Pull Request has no reported changed files"]
    if len(files) >= MAX_PR_FILES:
        return "contributor", ["Pull Request file count reached API safety limit"]
    for item in files:
        filename, status = item.get("filename"), item.get("status")
        if not isinstance(filename, str) or status not in valid_statuses:
            problems.append("Malformed or unsupported GitHub changed-file record")
            continue
        touched.add(filename)
        if status == "renamed":
            old = item.get("previous_filename")
            if not isinstance(old, str) or not old:
                problems.append(f"Rename without original filename: {filename}")
            else:
                touched.add(old)

    catalog_locales = {PERMITTED_CATALOGS[p] for p in touched if p in PERMITTED_CATALOGS}
    all_catalogs = len(catalog_locales) == 1 and all(p in PERMITTED_CATALOGS for p in touched)
    if not problems and all_catalogs:
        return "contributor", []

    if is_owner_pr(author, association, head_repo, base_repo):
        for item in files:
            if item.get("status") in {"removed", "renamed"}:
                problems.append(f"Owner deletion/rename requires separate migration: {item.get('filename')}")
        for name in sorted(touched):
            if not allowed_maintainer_path(Path(name)):
                problems.append(f"Protected or unapproved owner PR path: {name}")
        return "maintainer", problems

    problems.extend(f"Contributor may not modify: {name}" for name in sorted(touched)
                    if name not in PERMITTED_CATALOGS)
    if len(catalog_locales) > 1:
        problems.append("Contributor PR must change exactly one language")
    if not problems:
        problems.append("Unapproved contributor PR path combination")
    return "contributor", problems


def request_json(url: str, token: str) -> object:
    req = Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "tendo-trusted-pr-scope-guard",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(req, timeout=15) as response:
        if response.status != 200:
            raise ValueError(f"GitHub API responded with HTTP {response.status}")
        return json.load(response)


def github_files(number: int, token: str) -> list[dict]:
    files = []
    for page in range(1, 32):
        rows = request_json(f"{API}/pulls/{number}/files?per_page=100&page={page}", token)
        if not isinstance(rows, list):
            raise ValueError("GitHub API returned invalid PR file list")
        if len(rows) > 100:
            raise ValueError("GitHub API returned oversized page")
        files.extend(rows)
        if len(files) >= MAX_PR_FILES:
            raise ValueError("GitHub API PR file limit reached; manual review needed")
        if len(rows) < 100:
            return files
    raise ValueError("GitHub API pagination limit reached")


def evaluate(event: dict, token: str) -> tuple[str, list[str]]:
    if event.get("repository", {}).get("full_name") != REPO:
        raise ValueError("Unrecognized base repository")
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        raise ValueError("Missing GitHub pull_request_target payload")
    number = pr.get("number")
    if type(number) is not int or number <= 0:
        raise ValueError("Invalid Pull Request number")
    current = request_json(f"{API}/pulls/{number}", token)
    if not isinstance(current, dict) or current.get("state") != "open":
        raise ValueError("Pull Request is not open")
    # GitHub can advance the PR during a run; do not approve stale file lists.
    for part in ("head", "base"):
        if current[part]["sha"] != pr[part]["sha"]:
            raise ValueError("Pull Request changed during validation; rerun on latest commit")
    if current["base"]["repo"]["full_name"] != REPO:
        raise ValueError("Unexpected Pull Request target")
    return classify_paths(
        github_files(number, token), current["user"]["login"],
        current["author_association"], current["head"]["repo"]["full_name"],
        current["base"]["repo"]["full_name"],
    )


def main() -> int:
    try:
        path = os.environ["GITHUB_EVENT_PATH"]
        token = os.environ["GITHUB_TOKEN"]
        if not token:
            raise ValueError("Missing read-only GitHub token")
        with open(path, encoding="utf-8") as fp:
            event = json.load(fp)
        mode, problems = evaluate(event, token)
    except (OSError, ValueError, KeyError, TypeError, HTTPError, URLError) as exc:
        print(f"FAIL: trusted PR scope guard: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    for problem in problems[:30]:
        print(f"FAIL: {problem}", file=sys.stderr)
    print(f"{'PASS' if not problems else 'FAIL'}: trusted {mode} PR path guard ({len(problems)} issue(s))")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
