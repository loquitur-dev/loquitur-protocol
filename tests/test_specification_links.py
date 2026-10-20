"""Every reference to a specification document is a link to its file.

The specification documents cite one another by file name and section, and on a host that renders
Markdown a reader follows a citation only when the name is a link. tools/link_specification_references.py
writes the links; these tests hold every document to them, so a reference added without its link
fails here rather than standing as text a reader cannot follow.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import tool

ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = ROOT / "docs" / "specification"
links = tool("link_specification_references")

NAMES = {"report-contract.md", "bundle-objects.md"}


def test_every_reference_to_a_specification_document_is_linked() -> None:
    assert len(links.documents(ROOT)) >= 20, "the specification folder has fewer documents than it should"
    assert links.check(ROOT) == []


def test_every_relative_link_names_a_file_of_the_folder() -> None:
    for path in sorted(SPECIFICATION.glob("*.md")):
        for target in re.findall(r"\]\(([^)\s#]+\.md)\)", path.read_text(encoding="utf-8")):
            assert (SPECIFICATION / target).is_file(), f"{path.name} links to {target}, which is not a file"


def test_an_unlinked_reference_is_reported() -> None:
    text = "See `report-contract.md` §5.3.\n"
    assert links.problems(text, NAMES) == ["line 1: `report-contract.md` is not linked"]
    assert links.link(text, NAMES) == "See [`report-contract.md`](report-contract.md) §5.3.\n"
    assert links.problems(links.link(text, NAMES), NAMES) == []


def test_a_link_to_another_target_is_reported() -> None:
    text = "See [`report-contract.md`](bundle-objects.md) §5.3.\n"
    assert links.problems(text, NAMES) == ["line 1: `report-contract.md` links to bundle-objects.md, not to its file"]


def test_code_blocks_headings_and_other_files_are_left_alone() -> None:
    text = "\n".join(
        [
            "## 1. Cites `report-contract.md`",
            "```text",
            "`bundle-objects.md`",
            "```",
            "`GOVERNANCE.md` and ``report-contract.md`` and `docs/report-contract.md`.",
            "",
        ]
    )
    assert links.problems(text, NAMES) == []
    assert links.link(text, NAMES) == text
