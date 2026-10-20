"""A document that cites files this repository does not carry says so before its first section.

Several documents cite a reference implementation. Its files are not in this repository, so a
reader who is told to open them cannot. Where a normative section specifies a rule, the document
refers to that section instead. Every citation sits in a document whose top carries a
non-normative note saying that the citations are not part of the protocol and naming what a
reader of a published copy can resolve: the release of the cited repository, which must be the
version of its checkout beside this one.

A citation that names a line is only true of one state of the file, and the published copies of
these repositories carry one commit each, so no such state can be resolved there. The citations
therefore name a definition, `<module>.py::<name>`, which any checkout that still defines it
resolves.

This test finds every Markdown file of the repository that cites code and requires that note above
its first section. It also resolves the citation no other test resolves: the one of reason-codes.md
in the loquitur-verify-py checkout beside this repository, which skips without that sibling and
fails instead under LOQUITUR_REQUIRE_SIBLINGS. threat-model.md and verdict-grounds.md have tests
of their own for the same resolution.
"""

from __future__ import annotations

import re
from pathlib import Path

from code_citations import checked_out_version, citations, definitions, releases

ROOT = Path(__file__).resolve().parents[1]
VERIFY_SOURCE = ROOT.parent / "loquitur-verify-py" / "src" / "loquitur" / "verify"
REASON_CODES = ROOT / "docs/specification/reason-codes.md"

CITES_CODE = re.compile(
    r"[A-Za-z0-9_./-]+\.(?:py|ts|mjs|js|md|json):\d+"  # a file and a line
    r"|`[A-Za-z0-9_]+\.py::[A-Za-z_][A-Za-z0-9_]*`"  # a definition of a module
    r"|`:\d+(?:-\d+)?`"  # a further line of the file cited just before
    r"|\blines? \d+"  # a line of a module the paragraph names
)
NOTE = re.compile(r"> \*\*Non-normative note on citations\.\*\*(?P<body>(?:.*\n>.*)*)")
COMMIT = re.compile(r"`([0-9a-f]{40})`")
# The documents that cite code. A pattern that stopped matching would otherwise make the note
# check pass over nothing.
CITING = {
    "docs/specification/reason-codes.md",
    "docs/specification/threat-model.md",
    "docs/specification/verdict-grounds.md",
}


def _markdown() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.relative_to(ROOT).parts)


def _changelog(path: Path) -> bool:
    return path.name == "CHANGELOG.md"


def test_every_document_that_cites_code_carries_a_note_above_its_first_section() -> None:
    citing = {
        p.relative_to(ROOT).as_posix()
        for p in _markdown()
        if not _changelog(p) and CITES_CODE.search(p.read_text(encoding="utf-8"))
    }
    assert citing == CITING
    problems = []
    for rel in sorted(citing):
        head = (ROOT / rel).read_text(encoding="utf-8").split("\n## ", 1)[0]
        note = NOTE.search(head)
        if note is None:
            problems.append(f"{rel}: no citation note above the first section")
            continue
        body = " ".join(line.lstrip("> ") for line in note.group("body").splitlines())
        named_commits, named_releases = COMMIT.findall(body), releases(body)
        # What a reader of a published copy can resolve: the release the cited repository's
        # published copy carries, which is the version of the checkout the citations are checked
        # against. A commit of a development history cannot be resolved there.
        if named_commits:
            problems.append(f"{rel}: the note names a commit")
        if not named_releases:
            problems.append(f"{rel}: the note names no release")
        for repository, version in named_releases:
            if version != checked_out_version(repository):
                problems.append(f"{rel}: release {version} of {repository} is not the checked-out version")
        if "part of the protocol" not in body:
            problems.append(f"{rel}: the note does not say the citations are not part of the protocol")
    assert not problems, "\n".join(problems)


def test_no_document_cites_a_line() -> None:
    problems = []
    for path in _markdown():
        if _changelog(path):
            continue
        for cited in re.findall(r"([A-Za-z0-9_./-]+\.(?:py|ts|mjs|js|md|json)):\d+", path.read_text(encoding="utf-8")):
            problems.append(f"{path.relative_to(ROOT).as_posix()}: {cited} is cited by line")
        if re.search(r"\blines? \d+", path.read_text(encoding="utf-8")):
            problems.append(f"{path.relative_to(ROOT).as_posix()}: cites a line of a module the text names")
    assert not problems, "\n".join(problems)


def test_the_reason_codes_citation_names_the_docstring_that_states_the_property() -> None:
    assert citations(REASON_CODES.read_text(encoding="utf-8")) == [("narrative.py", "__doc__")]
    docstring = definitions(VERIFY_SOURCE / "narrative.py")["__doc__"]
    # The sentence the citation supports: the same input yields byte-identical output.
    assert "byte-identical output" in " ".join(docstring.split())
    assert "Determinism mandate" in docstring
