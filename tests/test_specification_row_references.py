"""A normative sentence names the row it is about, never its position in the table.

A sentence that points at a row by counting stops being true the moment a row is added,
removed or reordered, and the reader has no way to notice: the table still parses, every gate
still passes, and the prose now describes a different row.

The rule this test holds removes the whole class: a sentence may introduce the table that follows it ("each row below", "the rows
below"), because the table is right there and the reference cannot go stale; it may not point
back at a particular row by position. Pointing back names the row.

Nothing here needs a verifier or a sibling checkout: it reads this repository's specification.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = ROOT / "docs" / "specification"

# An ordinal and a row ("the first two rows", "the third row", "the last row"), or a row named
# by pointing backwards ("the row above", "the row two above", "the row before", "the preceding
# row", "the earlier row"). "a row below" and "the rows below" are not matched: they introduce
# the table that follows the sentence.
#
# Only a word that says where may sit between the row and the word that points back, so that
# "the row just above" and "the row two above" are caught with it. Any word at all would catch
# "the rows are evaluated before the envelope is read" and "each row is applied before the next
# check", where "before" is when and not where: this rule is about a reference that goes stale
# when the table is reordered, and evaluation order does not.
POSITIONAL = re.compile(
    r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|last|next)\s+"
    r"(?:\w+\s+)?rows?\b"
    r"|\brows?\s+(?:(?:just|right|directly|immediately|two|three|four|several)\s+)?"
    r"(?:above|preceding|before|earlier)\b"
    r"|\b(?:preceding|previous|earlier|foregoing|former|latter)\s+rows?\b",
    re.IGNORECASE,
)


def _documents() -> list[Path]:
    return sorted(SPECIFICATION.rglob("*.md"))


def _hits(text: str) -> list[str]:
    return [match.group(0) for match in POSITIONAL.finditer(text)]


def test_no_specification_document_points_at_a_row_by_position() -> None:
    problems = []
    for path in _documents():
        text = path.read_text(encoding="utf-8")
        for match in POSITIONAL.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            problems.append(f"{path.relative_to(ROOT).as_posix()}:{line}: {match.group(0)!r}")
    assert problems == [], "name the row, do not count it:\n" + "\n".join(problems)


def test_the_rule_reads_the_documents_and_the_forms_it_allows() -> None:
    """Anti-vacuity: the pattern must catch what it is for, and pass what the prose may say."""
    documents = _documents()
    assert len(documents) >= 10, documents
    assert any(path.name == "report-contract.md" for path in documents)
    # Sentences that point at a row by its position.
    assert _hits("and the first two rows follow from it and never hold together") == ["first two rows"]
    assert _hits("The third row is the one that surprises implementers") == ["third row"]
    assert _hits("A distinct prefix from the row above, so a signature") == ["row above"]
    assert _hits("the table's first eight rows refuse the input") == ["first eight rows"]
    assert _hits("the preceding row states it") == ["preceding row"]
    # Pointing back without an ordinal and without the word "above".
    assert _hits("the row before carries the same prefix") == ["row before"]
    assert _hits("the earlier row states the bound") == ["earlier row"]
    assert _hits("the row two above names the message") == ["row two above"]
    assert _hits("the row just above is the one meant") == ["row just above"]
    assert _hits("the latter row is evaluated first") == ["latter row"]
    # Introducing the table that follows is not pointing back at a row, and neither is naming
    # the row, which is what a sentence does instead.
    assert _hits("A run appends the error of each row below whose condition holds") == []
    assert _hits("the rows below are evaluated only against a well-formed one") == []
    assert _hits("A member outside it, or a row below broken, fails the run") == []
    assert _hits("the `invalid_zip` and `unsupported_input` rows follow from it") == []
    assert _hits("The rows from `input_not_found` to `filesystem_error` refuse the input") == []
    # "before" is when and not where here, and a rule about a stale position must not claim them.
    assert _hits("the rows are evaluated before the envelope is read") == []
    assert _hits("each row is applied before the next check") == []
    assert _hits("a row is read before it is written") == []
    # Naming the table rather than counting into it.
    assert _hits("the rows of the table above carry the codes") == []
