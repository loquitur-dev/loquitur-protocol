"""A change proposal can name every compatibility class, and no other.

docs/specification/change-proposal.schema.json lists in `compatibility_class` the classes a
change proposal can declare, and its description says that list is the set of ids
docs/specification/compatibility-classes.json declares, bound to it by this file. A declared
class missing from the list cannot be proposed truthfully: a change in it would have to be
filed under a class that misdescribes it. A listed class the catalog does not declare has no
approval rule or version policy attached. The list keeps the catalog's rank order, so that a
class appended to the catalog and not to the list shows as a missing last value in a diff.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_SCHEMA = ROOT / "docs/specification/change-proposal.schema.json"
CLASS_CATALOG = ROOT / "docs/specification/compatibility-classes.json"


def _proposal_classes() -> list[str]:
    schema = json.loads(PROPOSAL_SCHEMA.read_text(encoding="utf-8"))
    classes = schema["properties"]["compatibility_class"]["enum"]
    assert classes, "the proposal schema lists no class; every comparison below would be vacuous"
    return classes


def _declared_classes() -> list[str]:
    catalog = json.loads(CLASS_CATALOG.read_text(encoding="utf-8"))
    classes = [entry["id"] for entry in sorted(catalog["classes"], key=lambda entry: entry["rank"])]
    assert classes, "the catalog declares no class; every comparison below would be vacuous"
    return classes


def binding_failures(listed: list[str], declared: list[str]) -> list[str]:
    """Every way the proposal schema's list departs from the declared classes."""
    failures = []
    missing = [name for name in declared if name not in listed]
    if missing:
        failures.append(f"declared in compatibility-classes.json and not proposable: {missing}")
    undeclared = [name for name in listed if name not in declared]
    if undeclared:
        failures.append(f"proposable and not declared in compatibility-classes.json: {undeclared}")
    if not missing and not undeclared and listed != declared:
        failures.append(f"listed in another order than the catalog's ranks: {listed} against {declared}")
    return failures


def test_the_proposal_schema_lists_exactly_the_declared_classes_in_rank_order() -> None:
    assert binding_failures(_proposal_classes(), _declared_classes()) == []


def test_the_binding_refuses_a_missing_an_undeclared_and_a_reordered_class() -> None:
    """Non-vacuity: each departure the binding exists for is reported."""
    declared = _declared_classes()
    assert len(declared) > 1, "too few classes to reorder"
    missing = binding_failures(declared[:-1], declared)
    assert missing and declared[-1] in missing[0] and "not proposable" in missing[0], missing
    undeclared = binding_failures(declared + ["not-a-declared-class"], declared)
    assert undeclared and "not-a-declared-class" in undeclared[0] and "not declared" in undeclared[0], undeclared
    reordered = binding_failures(list(reversed(declared)), declared)
    assert reordered and "another order" in reordered[0], reordered


def test_the_schema_description_names_this_binding() -> None:
    """The schema says what binds its list; that citation resolves in this repository."""
    schema = json.loads(PROPOSAL_SCHEMA.read_text(encoding="utf-8"))
    description = schema["properties"]["compatibility_class"]["description"]
    cited = "tests/" + Path(__file__).name
    assert cited in description, description
    assert (ROOT / cited).is_file()
    assert "compatibility-classes.json" in description, description
