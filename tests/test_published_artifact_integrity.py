"""Integrity and self-description of the published specification artifacts.

This repository publishes normative governance artifacts. Other tests cover the
*semantics* of individual artifacts (capability closure, vocabulary closure, oracle
policy, release/lock identity). These cover whether the published set is coherent
**as a package**:

  * every shipped JSON artifact parses (a corrupt artifact breaks every consumer);
  * the artifacts that name the current release set agree with one another;
  * `REPOSITORY_LAYOUT.md` describes the files that actually ship, the governance
    artifacts at the root included;
  * no packaging build residue leaks into a repository that must never be a package.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs" / "maintainers" / "REPOSITORY_LAYOUT.md"

# Artifacts that pin the *current* release set. Per-artifact provenance records
# (CRYPTOGRAPHIC_CAPABILITIES, VERIFICATION_VOCABULARIES) deliberately keep the
# release set of the branch that last changed them and are excluded here.
CURRENT_RELEASE_SET_ARTIFACTS = (
    "CONFORMANCE_AUTHORITY.json",
    "CONFORMANCE_ORACLE_POLICY.json",
    "PROTOCOL_RELEASE.json",
    "RELEASE_SET_POINTER.json",
    "public_spec_manifest.json",
    "release-set.json",
)


def _shipped_json() -> list[Path]:
    return sorted(ROOT.glob("*.json"))


def test_every_published_json_artifact_parses() -> None:
    artifacts = _shipped_json()
    assert artifacts, "no published JSON artifacts found"
    for path in artifacts:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            pytest.fail(f"published artifact {path.name} is not valid JSON: {exc}")
        assert isinstance(payload, dict) and payload, f"{path.name} is empty or not an object"


def test_artifacts_naming_the_current_release_set_agree() -> None:
    values: dict[str, str] = {}
    for name in CURRENT_RELEASE_SET_ARTIFACTS:
        path = ROOT / name
        assert path.is_file(), f"expected governance artifact missing: {name}"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "release_set_id" in payload, f"{name} does not declare release_set_id"
        values[name] = payload["release_set_id"]
    assert len(set(values.values())) == 1, f"release_set_id drift across artifacts: {values}"


def test_repository_layout_documents_every_published_artifact() -> None:
    """Every governance artifact at the root is named in the layout."""
    layout = LAYOUT.read_text(encoding="utf-8")
    for path in _shipped_json():
        assert path.name in layout, f"{path.name} ships but is not documented in REPOSITORY_LAYOUT.md"
    for directory in ("conformance", "docs", "tests", "tools"):
        if (ROOT / directory).is_dir():
            assert f"{directory}/" in layout, f"directory {directory}/ ships but is undocumented"


def test_repository_layout_names_every_tool() -> None:
    """Every tool that ships is named in the layout, and the layout names no tool that is gone.

    The layout tree names the tools one by one rather than as a directory, which is right --
    they are the repository's executable surface, and a reader deciding whether to trust a
    published copy wants to see what runs in it. A tool missing from the only file that
    enumerates them reads as "this repository has no such check".
    """
    layout = LAYOUT.read_text(encoding="utf-8")
    tools = sorted(p.name for p in (ROOT / "tools").glob("*.py"))
    assert tools, "no tools found; this check would pass over an empty directory"
    missing = [name for name in tools if name not in layout]
    assert not missing, f"these tools ship but are not named in REPOSITORY_LAYOUT.md: {missing}"
    named = re.findall(r"^│\s+[├└]─ (\S+\.py)$", layout, re.MULTILINE)
    gone = [name for name in named if name not in tools]
    assert not gone, f"REPOSITORY_LAYOUT.md names tools that do not exist: {gone}"


def _layout_tree_paths() -> list[str]:
    """Every path the layout's tree names, rebuilt from the tree's own indentation."""
    layout = LAYOUT.read_text(encoding="utf-8")
    block = layout.split("```text\n", 1)[1].split("```", 1)[0].splitlines()
    stack: list[str] = []
    paths: list[str] = []
    for line in block[1:]:
        match = re.match(r"^((?:│  |   )*)[├└]─ (\S+)", line)
        if not match:
            continue
        depth = len(match.group(1)) // 3
        stack = stack[:depth] + [match.group(2)]
        paths.append("".join(part if part.endswith("/") else part + "/" for part in stack[:-1]) + stack[-1])
    return paths


def test_repository_layout_names_each_path_where_it_is() -> None:
    """Every path the layout's tree names is where the tree puts it.

    The checks above hold that what ships is named; this holds that what is named is where the
    tree puts it, so that a reader looking for a file where the layout says it is finds it.
    """
    paths = _layout_tree_paths()
    concrete = [path for path in paths if "*" not in path]
    assert len(concrete) > 30, f"the tree parsed into {len(concrete)} paths; this check would hold over nothing"
    misplaced = [
        path
        for path in concrete
        if not ((ROOT / path.rstrip("/")).is_dir() if path.endswith("/") else (ROOT / path).is_file())
    ]
    assert not misplaced, f"REPOSITORY_LAYOUT.md names paths that are not where it puts them: {misplaced}"


def test_no_packaging_build_residue_is_present() -> None:
    """This repository must never become a Python package."""
    residue = (
        [p.name for p in ROOT.glob("*.egg-info")]
        + [p.name for p in ROOT.glob("*.dist-info")]
        + [d for d in ("build", "dist", ".eggs") if (ROOT / d).exists()]
    )
    assert not residue, f"packaging build residue present: {residue}"


def test_the_readme_describes_the_archive_this_repository_actually_pins() -> None:
    """README.md names the corpus by the lock that pins it, and states no count a new archive would move."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lock = json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
    assert "`CONFORMANCE_LOCK.json`" in readme
    assert lock["corpus_id"] not in readme and lock["artifact"] not in readme
    assert not re.search(r"loquitur-conformance-[0-9a-f]{16}", readme)
    assert not re.search(r"\b\d+ (?:files|vectors)\b", readme), "README.md states a count a new archive would move"
