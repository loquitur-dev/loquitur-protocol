"""The registered vocabularies satisfy their meta-schema, and a later version of one only adds.

verification-vocabularies.md sections 6 and 9 state the document and its versioning rule;
tools/registered_vocabularies.py checks both, and CI runs it against the branch's base revision.
This holds the files of this checkout, and the append-only rule on constructed versions.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from conftest import tool as load_tool

ROOT = Path(__file__).resolve().parents[1]
tool = load_tool("registered_vocabularies")
KINDS = ["asset_type", "workflow", "anchoring_method"]


def vocabulary(kind: str) -> dict:
    return json.loads((ROOT / "vocabularies" / f"{kind}.json").read_text(encoding="utf-8"))


def test_the_meta_schema_closes_the_three_kinds() -> None:
    assert tool.kinds() == KINDS


def test_every_vocabulary_of_this_checkout_holds() -> None:
    assert tool.check(ROOT) == []


@pytest.mark.parametrize("kind", KINDS)
def test_each_vocabulary_is_version_1_0_0_with_its_initial_values(kind: str) -> None:
    document = vocabulary(kind)
    assert document["kind"] == kind and document["version"] == "1.0.0"
    expected = {
        "asset_type": ["fund_nav", "property"],
        "workflow": ["fund_nav_initial", "fund_nav_update", "property_pre_listing", "property_review"],
        "anchoring_method": ["blockchain_transaction", "rfc3161_timestamp", "transparency_log_checkpoint"],
    }[kind]
    assert sorted(document["values"]) == expected
    # Claim only what exists: no profile document defines a value yet, so every profile is null.
    assert all(entry["profile"] is None for entry in document["values"].values())
    assert all(entry["since"] == "1.0.0" and entry["status"] == "active" for entry in document["values"].values())


def _broken(kind: str, change) -> list[str]:
    document = copy.deepcopy(vocabulary(kind))
    change(document)
    return tool.contract_errors(document)


@pytest.mark.parametrize(
    ("kind", "change"),
    [
        ("asset_type", lambda d: d.update(kind="vessel")),
        ("asset_type", lambda d: d.update(schema_version="v2")),
        ("asset_type", lambda d: d.update(version="1.0")),
        ("asset_type", lambda d: d.update(version="1.0.0-rc1")),
        ("asset_type", lambda d: d.update(values={})),
        ("asset_type", lambda d: d.update(extra=True)),
        ("asset_type", lambda d: d["values"].update({"Fund-NAV": d["values"]["fund_nav"]})),
        ("asset_type", lambda d: d["values"]["fund_nav"].update(since="1.1.0")),
        ("asset_type", lambda d: d["values"]["fund_nav"].update(status="retired")),
        ("asset_type", lambda d: d["values"]["fund_nav"].update(title=" \u3000")),
        ("asset_type", lambda d: d["values"]["fund_nav"].update(profile="")),
        ("asset_type", lambda d: d["values"]["fund_nav"].update(asset_types=["fund_nav"])),
        ("asset_type", lambda d: d["values"]["fund_nav"].pop("profile")),
        ("workflow", lambda d: d["values"]["fund_nav_update"].pop("asset_types")),
        ("workflow", lambda d: d["values"]["fund_nav_update"].update(asset_types=[])),
    ],
)
def test_a_document_that_breaks_section_6_is_refused(kind: str, change) -> None:
    assert _broken(kind, change)


def test_a_duplicate_member_is_not_strict_json() -> None:
    with pytest.raises(ValueError):
        tool.parse(b'{"kind": "asset_type", "kind": "workflow"}')


def _later(kind: str, change, version: str) -> tuple[dict, dict]:
    old = vocabulary(kind)
    new = copy.deepcopy(old)
    change(new)
    new["version"] = version
    return old, new


def _add(value: str, since: str):
    def change(document: dict) -> None:
        document["values"][value] = {"since": since, "status": "active", "title": "Example asset", "profile": None}

    return change


def test_an_added_value_is_a_minor_version_and_carries_it_as_since() -> None:
    assert tool.append_only_errors(*_later("asset_type", _add("example_asset", "1.1.0"), "1.1.0")) == []
    assert tool.append_only_errors(*_later("asset_type", _add("example_asset", "1.0.0"), "1.1.0"))
    assert tool.append_only_errors(*_later("asset_type", _add("example_asset", "1.0.1"), "1.0.1"))
    assert tool.append_only_errors(*_later("asset_type", _add("example_asset", "2.0.0"), "2.0.0"))


def test_deprecation_is_a_minor_version_and_never_reverses() -> None:
    def deprecate(document: dict) -> None:
        document["values"]["property"]["status"] = "deprecated"

    assert tool.append_only_errors(*_later("asset_type", deprecate, "1.1.0")) == []
    old, new = _later("asset_type", deprecate, "1.1.0")
    assert tool.append_only_errors(new, {**copy.deepcopy(old), "version": "1.2.0"})


def test_a_title_correction_is_a_patch() -> None:
    def retitle(document: dict) -> None:
        document["values"]["property"]["title"] = "Real estate"

    assert tool.append_only_errors(*_later("asset_type", retitle, "1.0.1")) == []
    assert tool.append_only_errors(*_later("asset_type", retitle, "1.1.0"))


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["values"].pop("property"),
        lambda d: d["values"]["property"].update(since="1.1.0"),
        lambda d: d.update(kind="workflow"),
    ],
)
def test_a_value_is_never_removed_and_its_since_never_changes(change) -> None:
    assert tool.append_only_errors(*_later("asset_type", change, "1.1.0"))


def test_a_workflow_keeps_its_asset_types() -> None:
    def widen(document: dict) -> None:
        document["values"]["fund_nav_update"]["asset_types"] = ["fund_nav", "property"]

    assert tool.append_only_errors(*_later("workflow", widen, "1.1.0"))


def test_an_unchanged_document_keeps_its_version() -> None:
    assert tool.append_only_errors(vocabulary("workflow"), vocabulary("workflow")) == []
    assert tool.append_only_errors(*_later("workflow", lambda d: None, "1.0.1"))


def test_the_review_reason_of_an_unknown_value_is_row_14_of_the_report_contract() -> None:
    """report-contract.md section 3.3: `vocabulary_value_unknown` is the last review reason, row 14."""
    import re

    text = (ROOT / "docs/specification/report-contract.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (\d+) \| `([a-z_]+)` \|", text, re.M)
    assert rows[-1] == ("14", "vocabulary_value_unknown"), rows[-3:]
    assert [int(number) for number, _ in rows] == list(range(1, 15))
