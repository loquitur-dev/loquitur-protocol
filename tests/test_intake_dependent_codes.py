"""An error code that depends on what a verifier reads is never stated without saying which.

Archive intake is optional (``report-contract.md`` §5.3): a verifier may read directory bundles
only. Two error codes of §5.3 turn on that choice rather than on the run. ``invalid_zip`` is the
answer of a verifier that reads archives to a regular file that is not a readable ZIP archive;
``unsupported_input`` is the answer of a verifier that reads none to any regular file. Exactly one
of them holds for a given verifier and input, and which one is a property of the verifier.

A sentence or a table cell that names one of those codes without saying whose intake it belongs to
therefore reads as a requirement on every conforming verifier, and half of the readers it reaches
will implement the wrong one. A table row ``not a ZIP`` → ``invalid_zip`` under a lead-in that names
no verifier does that, in a document whose preamble phrases its rules "as requirements on any
conforming verifier, not as a description of one implementation".

The rule this test holds removes the class: wherever a normative
document of this repository names ``invalid_zip`` or ``unsupported_input``, the part carrying it
says that archive intake is what the code turns on. Naming the intake is the whole requirement, so
a future document that introduces either code has to say which verifier it is talking about before
it can be committed.

A part is every line of every document, not the body of a ``## `` section alone. A heading belongs
to the section it opens, and the text before the first heading is a part of its own: the preamble
is where a document speaks for all of its sections at once, so it is the place an unscoped code
would reach furthest, and the place a rule reading section bodies alone would not look.

Nothing here needs a verifier or a sibling checkout: it reads this repository's specification.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = ROOT / "docs" / "specification"

# The two codes of report-contract.md §5.3 whose condition turns on what the verifier reads.
INTAKE_DEPENDENT = re.compile(r"\b(?:invalid_zip|unsupported_input)\b")
# What the carrying section must say. The phrase is the one §5.3 uses to state the choice.
NAMES_THE_INTAKE = "archive intake"


# What a document's text before its first ``## `` heading is called in a failure message.
PREAMBLE = "(preamble)"


def _sections(text: str) -> list[tuple[str, str]]:
    """Every part of a document as (title, text), in order, with no line left out.

    A ``## `` heading opens a section and belongs to it, so a code named in a heading is read
    with the section it titles. What comes before the first heading (the document's title, its
    status line, the note that frames the rules) is a part of its own, because a rule that
    skipped it would leave the one place that speaks for every section free to name a code.
    """
    out: list[tuple[str, str]] = []
    title, body = PREAMBLE, []
    for line in text.splitlines():
        if line.startswith("## "):
            out.append((title, "\n".join(body)))
            title, body = line[3:].strip(), [line]
        else:
            body.append(line)
    out.append((title, "\n".join(body)))
    return [(name, part) for name, part in out if part.strip()]


def _written_lines(text: str) -> Counter[str]:
    """How many times each line that carries something appears in ``text``."""
    return Counter(line for line in text.splitlines() if line.strip())


def _where(title: str) -> str:
    """How a part is named in a failure message."""
    return title if title == PREAMBLE else f"§{title}"


def _carrying_sections() -> list[tuple[str, str, str]]:
    """Every (document, part title, text) that names an intake-dependent code."""
    found: list[tuple[str, str, str]] = []
    for path in sorted(SPECIFICATION.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for title, body in _sections(text):
            if INTAKE_DEPENDENT.search(body):
                found.append((path.relative_to(ROOT).as_posix(), title, body))
    return found


def test_a_section_naming_an_intake_dependent_code_says_which_intake() -> None:
    carrying = _carrying_sections()
    problems = [
        f"{document} {_where(title)}: names {sorted(set(INTAKE_DEPENDENT.findall(body)))}"
        f" without saying {NAMES_THE_INTAKE!r}"
        for document, title, body in carrying
        if NAMES_THE_INTAKE not in body.lower()
    ]
    assert problems == [], (
        "say whose intake the code belongs to, or the row reads as a requirement on every "
        "verifier:\n" + "\n".join(problems)
    )


def test_the_rule_reads_every_line_of_every_document() -> None:
    """The sweep reads each document whole: no line belongs to no part, and none to two.

    The lines are counted, not collected into a set. A document repeats lines (a table
    separator, a cell that states the same rule twice), and a set comparison passes a part that
    was dropped whenever an identical line survives elsewhere, which is exactly the coverage
    this test claims to hold. Blank lines are left out of the count: a part of nothing but
    blank lines carries no code, and ``_sections`` drops it.
    """
    for path in sorted(SPECIFICATION.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        parts = _sections(text)
        titles = [title for title, _ in parts]
        assert len(titles) == len(set(titles)), (path.name, titles)
        rejoined = "\n".join(part for _, part in parts)
        assert _written_lines(text) == _written_lines(rejoined), path.name
        # A heading is read with the section it opens, and what precedes the first one is its own
        # part, so a code named in either is scanned.
        if "\n## " in text:
            assert any(title == PREAMBLE for title, _ in parts), path.name
            assert any(part.startswith("## ") for _, part in parts), path.name


def test_the_rule_reads_the_documents_and_the_places_it_covers() -> None:
    """Anti-vacuity: a rule that finds nothing to hold would pass whatever the documents said."""
    carrying = _carrying_sections()
    places = {(document, title) for document, title, _ in carrying}
    # The section that states the rule, the section that observes it in the reference verifiers,
    # the appendix row for the verifier's own inputs, and the hostile-input table.
    assert ("docs/specification/report-contract.md", "5. The reason surface") in places, places
    assert ("docs/specification/report-contract.md", "7. Implementations") in places, places
    assert ("docs/specification/document-contracts.md", "12. The verifier's own inputs") in places, places
    assert (
        "docs/specification/threat-model.md",
        "7. The verifier as target — observed outcomes",
    ) in places, places
    # Both codes are reached, so neither half of the pair can drop out of the sweep unnoticed.
    named = {code for _, _, body in carrying for code in INTAKE_DEPENDENT.findall(body)}
    assert named == {"invalid_zip", "unsupported_input"}, named
