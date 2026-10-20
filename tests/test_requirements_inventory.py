"""The requirements inventory names every requirement it claims to, and nothing it cannot find.

docs/traceability/requirements.json gives each requirement of the specification an identifier
outside the prose, bound to the text by an exact sentence or by the natural key of a row of a table
docs/traceability/rule-tables.json lists (tools/requirements_inventory.py says what counts). One
test per invariant:

1. every key-word sentence is claimed by exactly one active record, and no table the list leaves out
   uses a key word;
2. every row of every listed table is claimed by exactly one active record;
3. every locator resolves, once, in the section or table it names;
4. every corpus entry is a binding declaration of the corpus the inventory is checked against: the
   archive CONFORMANCE_LOCK.json pins, or the corpus root LOQUITUR_CORPUS_ROOTS names;
5. identifiers are contiguous per part from 001, none missing and none used twice;
6. a binding record has coverage or an exclusion, or is listed as not tested with its known limit;
7. docs/traceability/README.md is the rendering of the inventory;
8. the number of records the corpus covers never falls below the inventory's floor.

The suite and static entries a record cites name files, and tests in them, that exist: a static
entry in this repository always, a suite entry in a sibling checkout when it is beside this one,
and always under LOQUITUR_REQUIRE_SIBLINGS.

Each check is also shown to fail on an inventory that breaks it, so that a check seen only passing
is not taken for one that checks something.
"""

from __future__ import annotations

import copy
import os
import posixpath
import re
from pathlib import Path

import pytest
from conftest import tool

ROOT = Path(__file__).resolve().parents[1]


INVENTORY_TOOL = tool("requirements_inventory")
RENDER_TOOL = tool("render_requirements")


@pytest.fixture(scope="module")
def material() -> tuple[dict, dict, dict]:
    return INVENTORY_TOOL.read_inventory(), INVENTORY_TOOL.read_rule_tables(), INVENTORY_TOOL.read_parts()


def test_every_record_has_the_members_and_values_the_inventory_defines(material) -> None:
    inventory, _, _ = material
    assert inventory["schema_version"] == INVENTORY_TOOL.INVENTORY_SCHEMA
    assert inventory["doc_codes"] == INVENTORY_TOOL.DOC_CODES
    assert inventory["corpus_lock"] == INVENTORY_TOOL.LOCK
    assert INVENTORY_TOOL.record_problems(inventory) == []


def test_every_keyword_sentence_and_every_listed_row_is_claimed_once(material) -> None:
    inventory, tables, parts = material
    assert INVENTORY_TOOL.claim_problems(inventory, parts, tables) == []
    assert INVENTORY_TOOL.keyword_sentences(parts), "no key-word sentence was found; the reading is broken"


def test_every_locator_resolves_once(material) -> None:
    inventory, tables, parts = material
    assert INVENTORY_TOOL.locator_problems(inventory, parts, tables) == []


def test_every_corpus_entry_is_a_binding_declaration_of_the_corpus(material) -> None:
    inventory, _, _ = material
    where, files = INVENTORY_TOOL.corpus_files()
    entries = INVENTORY_TOOL.corpus_entries(files)
    assert "verify.json" in entries, f"{where} has no vectors/verify.json"
    assert INVENTORY_TOOL.coverage_problems(inventory, entries, where) == []


def test_identifiers_are_contiguous_per_part_and_never_reused(material) -> None:
    inventory, _, _ = material
    assert INVENTORY_TOOL.identifier_problems(inventory) == []


def test_every_binding_record_is_covered_excluded_or_a_known_limit(material) -> None:
    inventory, _, _ = material
    assert INVENTORY_TOOL.gap_problems(inventory) == []


def test_the_page_is_the_rendering_of_the_inventory(material) -> None:
    inventory, tables, _ = material
    rendered = RENDER_TOOL.render(inventory, tables)
    assert (ROOT / INVENTORY_TOOL.RENDERED).read_text(encoding="utf-8") == rendered, "run tools/render_requirements.py"


def test_every_relative_link_of_the_page_resolves(material) -> None:
    # A quoted sentence links its neighbours relative to docs/specification/; on this page the
    # link must be relative to docs/traceability/.
    inventory, tables, _ = material
    page = INVENTORY_TOOL.RENDERED
    text = RENDER_TOOL.render(inventory, tables)
    targets = [target.split("#", 1)[0] for target in re.findall(r"\]\(([^)\s]+)\)", text)]
    relative = [target for target in targets if target and not re.match(r"[a-z][a-z0-9+.-]*:", target)]
    assert len(relative) > 5, f"only {len(relative)} relative links; the check is thin"
    broken = [
        target
        for target in relative
        if not (ROOT / posixpath.normpath(posixpath.join(posixpath.dirname(page), target))).is_file()
    ]
    assert not broken, f"{page} links files that are not there: {broken}"


def test_a_quoted_link_is_moved_to_the_page() -> None:
    quoted = "See [`a.md`](a.md) and [`b`](sub/b.md#x), [here](#y) and [web](https://example.org/z.md)."
    assert RENDER_TOOL._relink(quoted, "trust-root.md") == (
        "See [`a.md`](../specification/a.md) and [`b`](../specification/sub/b.md#x),"
        " [here](../specification/trust-root.md#y) and [web](https://example.org/z.md)."
    )


def test_corpus_coverage_never_falls_below_the_floor(material) -> None:
    inventory, _, _ = material
    assert INVENTORY_TOOL.floor_problems(inventory) == []
    covered = sum(
        1 for record in inventory["requirements"] if record["status"] == "active" and record["coverage"]["corpus"]
    )
    assert inventory["corpus_covered_floor"] <= covered


def test_every_static_and_suite_entry_names_a_test_that_exists(material) -> None:
    inventory, _, _ = material
    problems, absent = INVENTORY_TOOL.suite_problems(inventory, ROOT.parent)
    assert problems == []
    if absent and os.environ.get("LOQUITUR_REQUIRE_SIBLINGS", "").strip().lower() in {"1", "true", "yes", "on"}:
        pytest.fail(f"LOQUITUR_REQUIRE_SIBLINGS is set and these repositories are not beside this one: {absent}")
    if absent:
        pytest.skip(f"not checked out beside this repository, so their entries were not resolved: {absent}")


# ---- each check fails where it should ----------------------------------------------------------------


def test_a_sentence_no_record_claims_is_found(material) -> None:
    inventory, tables, parts = material
    broken = copy.deepcopy(inventory)
    dropped = next(r for r in broken["requirements"] if r["id"] == "REQ-CAN-001")
    assert dropped["kind"] == "keyword"
    broken["requirements"].remove(dropped)
    found = INVENTORY_TOOL.claim_problems(broken, parts, tables)
    assert len(found) == 1 and "0 records claim the sentence" in found[0]
    assert INVENTORY_TOOL.identifier_problems(broken) != [], "a deleted record leaves a gap in its part's numbers"


def test_a_row_claimed_twice_and_a_retired_record_are_told_apart(material) -> None:
    inventory, tables, parts = material
    broken = copy.deepcopy(inventory)
    row = next(r for r in broken["requirements"] if r["locator"]["kind"] == "row")
    twin = copy.deepcopy(row)
    twin["id"] = "REQ-RPT-999"
    broken["requirements"].append(twin)
    assert any("2 records claim it" in p for p in INVENTORY_TOOL.claim_problems(broken, parts, tables))
    twin["status"], twin["retired_in"] = "retired", "0.2.0"
    assert INVENTORY_TOOL.claim_problems(broken, parts, tables) == []


def test_a_locator_that_no_longer_matches_is_found(material) -> None:
    inventory, tables, parts = material
    broken = copy.deepcopy(inventory)
    record = next(r for r in broken["requirements"] if r["locator"]["kind"] == "sentence")
    record["locator"]["text"] += " and something the section does not say"
    assert any(record["id"] in p for p in INVENTORY_TOOL.locator_problems(broken, parts, tables))
    row = next(r for r in broken["requirements"] if r["locator"]["kind"] == "row")
    row["locator"]["key"] = "no-such-row"
    assert any(row["id"] in p for p in INVENTORY_TOOL.locator_problems(broken, parts, tables))


def test_an_unknown_corpus_entry_a_gap_and_a_lowered_floor_are_found(material) -> None:
    inventory, _, _ = material
    broken = copy.deepcopy(inventory)
    record = next(r for r in broken["requirements"] if r["coverage"]["corpus"])
    record["coverage"]["corpus"].append("verify.json#no_such_run")
    assert INVENTORY_TOOL.coverage_problems(broken, {"verify.json"}, "a corpus") != []
    record["coverage"] = {"corpus": [], "static": [], "suites": []}
    record["exclusion"] = None
    assert any(record["id"] in p for p in INVENTORY_TOOL.gap_problems(broken))
    assert INVENTORY_TOOL.floor_problems(broken) != []


def test_the_reading_of_key_words_and_sentences() -> None:
    assert INVENTORY_TOOL.keyword_of("A verifier **MUST NOT** read roots.") == ("keyword", "MUST NOT")
    assert INVENTORY_TOOL.keyword_of("An operator `SHOULD` keep it.") == ("advisory", "SHOULD")
    assert INVENTORY_TOOL.keyword_of("The code `REQUIRED_CLAIMS_PRESENT` is info.") is None
    assert INVENTORY_TOOL.keyword_of('as binding as one written with "MUST".') is None
    assert INVENTORY_TOOL.keyword_of("a verifier must not assume it") is None
    assert INVENTORY_TOOL.split_sentences("One rule, e.g. this. Two `x` here. 3 more.") == [
        "One rule, e.g. this.",
        "Two `x` here.",
        "3 more.",
    ]
