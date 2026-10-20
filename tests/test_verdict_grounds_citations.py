"""The citations in verdict-grounds.md §6 name the code that enforces each rule.

§6 cites `loquitur-schemas` `src/loquitur/schemas/verdict_grounds.py` for every rule, and says
that where the code and the document disagree the code is wrong. It cites definitions by name,
`verdict_grounds.py::<name>`, which resolve in any checkout that defines them, and names each
refusal a rule's check emits by the identifier its message starts with.

This test reads the table and the module in the loquitur-schemas checkout beside this repository
and requires that every cited name is a top-level definition of the module; that the refusals the
checker `verdict_grounds_errors` emits are exactly the ones the rule rows list, each claimed by the
rule it enforces (pinned below from §3), so a new refusal no rule claims fails here too; and that
the behaviours the prose under the table describes are still in the code. The note above the
first section names the release the citations resolve in, which must be the version of that
checkout, and no commit of the unpublished development history. It skips when
loquitur-schemas is not checked out beside this repository, and fails instead under
LOQUITUR_REQUIRE_SIBLINGS.
"""

from __future__ import annotations

import re
from pathlib import Path

from code_citations import checked_out_version, citations, definitions, releases

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/specification/verdict-grounds.md"
MODULE = ROOT.parent / "loquitur-schemas" / "src/loquitur/schemas/verdict_grounds.py"
COMMIT = re.compile(r"\b[0-9a-f]{40}\b")
CHECKER = "verdict_grounds_errors"

# The identifier each refusal's message starts with, and the rule it enforces (§3).
REFUSALS = {
    "reason_codes_absent": "VG-1",
    "reason_codes_duplicated": "VG-1",
    "reason_code_not_in_catalog": "VG-2",
    "verdict_outside_vocabulary": "VG-3",
    "status_contradicts_grounds": "VG-3",
    "pass_without_affirmative_ground": "VG-4",
    "pass_without_key_checks": "VG-5",
    "reason_context_missing": "VG-6",
    "reason_context_code_not_in_catalog": "VG-7",
}
RULES = sorted(set(REFUSALS.values()))
REFUSAL = re.compile(r"[\"']([a-z_]+): ")


def _section() -> str:
    text = DOCUMENT.read_text(encoding="utf-8")
    return text.split("## 6. Where each rule is implemented", 1)[1].split("\n## ", 1)[0]


def _table() -> dict[str, tuple[list[tuple[str, str]], list[str]]]:
    rows: dict[str, tuple[list[tuple[str, str]], list[str]]] = {}
    for line in _section().splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] == "Rule" or set(cells[0]) <= {"-"}:
            continue
        refusals = re.findall(r"`([a-z_]+)`", cells[2]) if cells[2] != "—" else []
        rows[cells[0]] = (citations(cells[1]), refusals)
    return rows


def test_the_note_names_the_release_a_published_reader_can_resolve() -> None:
    """The note names the release of loquitur-schemas the citations resolve in, and no commit."""
    head = DOCUMENT.read_text(encoding="utf-8").split("\n## ", 1)[0]
    flat = " ".join(line.lstrip("> ") for line in head.splitlines())
    assert "Non-normative note on citations." in flat and "not part of the protocol" in flat
    assert not COMMIT.search(flat), "the note names a commit a published copy does not carry"
    assert releases(flat) == [("loquitur-schemas", checked_out_version("loquitur-schemas"))]


def test_the_table_cites_every_rule_by_definition_and_no_line() -> None:
    table = _table()
    assert [name for name in table if name in RULES] == RULES, sorted(table)
    assert not re.search(r"\blines? \d|\.py:\d", _section()), "§6 cites a line"
    for rule in RULES:
        assert table[rule][0] == [("verdict_grounds.py", CHECKER)], (rule, table[rule][0])


def test_every_cited_name_is_a_definition_of_the_module() -> None:
    found = definitions(MODULE)
    cited = [name for cites, _ in _table().values() for module, name in cites if module == "verdict_grounds.py"]
    assert len(cited) >= 5 + len(RULES), cited
    missing = sorted({name for name in cited if name not in found})
    assert not missing, f"not defined in verdict_grounds.py: {missing}"


def test_the_refusals_of_the_checker_are_exactly_the_ones_the_rules_claim() -> None:
    source = definitions(MODULE)[CHECKER]
    emitted = set(REFUSAL.findall(source))
    listed = {refusal: rule for rule, (_, refusals) in _table().items() for refusal in refusals}
    assert listed == REFUSALS, listed
    assert emitted == set(REFUSALS), f"{CHECKER} emits {sorted(emitted)}"


def test_the_behaviours_the_prose_describes_are_in_the_code() -> None:
    found = definitions(MODULE)
    # The two behaviours are a non-normative note, a block quote: read without its markers.
    flat = " ".join(re.sub(r"(?m)^> ?", "", _section()).split())
    assert "names the same seven rules, VG-1 to VG-7" in flat
    header = " ".join(found["__doc__"].split())
    assert "applies the seven rules VG-1 to VG-7 of verdict-grounds.md" in header
    assert all(f"(VG-{n})" in header for n in (2, 3, 4, 6, 7)) and "VG-5 --" in header
    assert "raise when handed a code the catalog does not define, through `catalog.get`" in flat
    assert "cat.get(code)" in found["max_severity"] and "max_severity(" in found["status_for_codes"]
    assert "reads `reason_codes` as a list or tuple only" in flat
    assert "isinstance(raw_codes, (list, tuple))" in found[CHECKER]
