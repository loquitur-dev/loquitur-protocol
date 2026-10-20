"""A count `threat-model.md` §11 states is the count of the thing it names.

§11 records the runs behind this document. Most rows name one input; a few count inputs
instead, because the run was over a table or a corpus rather than over one bundle. A number
written by hand beside such a row is a claim about how much was run, and a reader has no way
to check it: the table it counts can gain a row, or lose one, and the number stays whatever
it was.

This resolves the counts §11 states against what they count, inside this repository: the
hostile-input row against §7's table. The count of the Wycheproof corpus is held where the
corpus is, by `loquitur-verify-py`'s own suite, which reads this same cell.

Nothing here needs a verifier or a sibling checkout: it compares this document with itself.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "specification" / "threat-model.md"
OBSERVATIONS = "11. How the claims here were verified"
# A cell that counts the rows of another section of this document, as "26 cases, section 7".
COUNTS_A_SECTION = re.compile(r"^(?P<count>[0-9]+) cases, section (?P<section>[0-9]+)$")


def _sections(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if title is not None:
                found[title] = "\n".join(body)
            title, body = line[3:].strip(), []
        else:
            body.append(line)
    if title is not None:
        found[title] = "\n".join(body)
    return found


def _rows(body: str) -> list[list[str]]:
    """The body rows of the one table of ``body``, cells stripped."""
    lines = [line for line in body.splitlines() if line.lstrip().startswith("|")]
    separators = [index for index, line in enumerate(lines) if re.fullmatch(r"\s*\|(\s*:?-{3,}:?\s*\|)+\s*", line)]
    assert len(separators) == 1, f"expected one table, found {len(separators)}"
    return [[cell.strip() for cell in line.strip().split("|")[1:-1]] for line in lines[separators[0] + 1 :]]


def test_every_count_of_a_section_is_that_sections_row_count() -> None:
    sections = _sections(DOCUMENT.read_text(encoding="utf-8"))
    by_number = {title.split(".", 1)[0]: title for title in sections}
    resolved = 0
    for row in _rows(sections[OBSERVATIONS]):
        match = COUNTS_A_SECTION.fullmatch(row[1])
        if match is None:
            continue
        title = by_number[match.group("section")]
        assert int(match.group("count")) == len(_rows(sections[title])), (
            f"{row[0]!r} counts {match.group('count')} cases, and {title} has {len(_rows(sections[title]))} rows"
        )
        resolved += 1
    assert resolved == 1, f"§11 states {resolved} counts of a section, and this resolved that many"
