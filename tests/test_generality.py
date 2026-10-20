"""The core schemas hold no domain value: asset types, workflows and anchoring methods are registered.

verification-vocabularies.md sections 5 to 7 move the values of asset_type, workflow and the
anchoring method out of the schemas into registered vocabularies under vocabularies/. The schemas
fix the grammar of an identifier and nothing else, so a new vertical or a new anchoring method is a
registration (section 9) and not a change to any schema. This holds that from the schemas
themselves:

  * the registry entry lists no anchoring system: its anchor carries `method` and `system`, the
    method is an identifier with no enumeration, and no string of the schema outside its example
    and its descriptions names a chain or a registered anchoring method;
  * each governed pointer is an identifier, the list of governed pointers is complete, and no
    registered asset type or workflow appears in any of the seven schemas outside an example;
  * a value added to a copy of each vocabulary is accepted by the unchanged schemas, whose bytes
    are still the ones NORMATIVE_ARTIFACTS.json binds.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from conftest import tool

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "docs/specification/schemas"
VOCABULARIES = ROOT / "vocabularies"
IDENT = "^[a-z0-9][a-z0-9_]{0,63}$"

# Every pointer whose value a registered vocabulary governs (verification-vocabularies.md section 7).
GOVERNED = {
    ("registry_entry", "/properties/asset_type"): "asset_type",
    ("registry_entry", "/properties/workflow"): "workflow",
    ("registry_entry", "/properties/anchor/properties/method"): "anchoring_method",
    ("trust_registry", "/properties/entries/items/properties/allowed_asset_types/items"): "asset_type",
    ("trust_registry", "/properties/entries/items/properties/allowed_workflows/items"): "workflow",
    ("verification_receipt", "/properties/asset_type"): "asset_type",
    ("verification_summary", "/properties/asset_type"): "asset_type",
    ("coverage_summary", "/properties/asset_type"): "asset_type",
    ("change_summary", "/properties/asset_type"): "asset_type",
    ("lineage_summary", "/properties/asset_type"): "asset_type",
}
NULLABLE = {"verification_summary", "coverage_summary", "change_summary", "lineage_summary"}
# Chain and ledger names a schema must not carry, whether or not a vocabulary registers them.
CHAIN_NAMES = {"algorand", "ethereum", "polygon", "hedera", "bitcoin", "solana", "tezos", "avalanche"}
# The member names whose values are governed; a property of one of these names, anywhere in a
# schema, must be a governed pointer, so that a new one cannot escape the list above.
GOVERNED_NAMES = {"asset_type", "workflow", "allowed_asset_types", "allowed_workflows"}


def schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def vocabulary(kind: str) -> dict[str, Any]:
    return json.loads((VOCABULARIES / f"{kind}.json").read_text(encoding="utf-8"))


def resolve(document: Any, pointer: str) -> Any:
    for token in pointer.split("/")[1:]:
        document = document[token]
    return document


def strings(node: Any, path: str = "") -> Iterator[tuple[str, str]]:
    """Every key and string value of ``node`` outside `example` and `description`, with its path."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("example", "description"):
                continue
            yield f"{path}/{key}", key
            yield from strings(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from strings(value, f"{path}/{index}")
    elif isinstance(node, str):
        yield path, node


def schema_names() -> list[str]:
    return sorted(path.name.removesuffix(".schema.json") for path in SCHEMAS.glob("*.schema.json"))


def test_registry_entry_lists_no_anchoring_system() -> None:
    entry = schema("registry_entry")
    anchor = entry["properties"]["anchor"]
    assert set(anchor["properties"]) == {"method", "system", "anchor_reference"}
    assert anchor["required"] == ["method", "system", "anchor_reference"]
    method = anchor["properties"]["method"]
    assert method["type"] == "string" and method["pattern"] == IDENT
    assert "enum" not in method and "const" not in method
    assert "enum" not in anchor["properties"]["system"] and "pattern" not in anchor["properties"]["system"]
    forbidden = CHAIN_NAMES | set(vocabulary("anchoring_method")["values"])
    found = [(path, text) for path, text in strings(entry) if text in forbidden or text == "chain"]
    assert found == [], found


@pytest.mark.parametrize(("name", "pointer"), sorted(GOVERNED))
def test_governed_pointers_are_identifiers(name: str, pointer: str) -> None:
    node = resolve(schema(name), pointer)
    assert node["pattern"] == IDENT, (name, pointer)
    assert node["type"] == (["string", "null"] if name in NULLABLE and pointer == "/properties/asset_type" else "string")
    assert not {"enum", "const", "format", "anyOf", "oneOf"} & set(node), (name, pointer)


def test_no_domain_value_in_core_schemas() -> None:
    values = set(vocabulary("asset_type")["values"]) | set(vocabulary("workflow")["values"])
    for name in schema_names():
        found = [(path, text) for path, text in strings(schema(name)) if text in values]
        assert found == [], (name, found)


def test_governed_pointer_list_is_complete() -> None:
    found: set[tuple[str, str]] = set()

    def walk(name: str, node: Any, pointer: str) -> None:
        if not isinstance(node, dict):
            return
        for member, sub in (node.get("properties") or {}).items():
            here = f"{pointer}/properties/{member}"
            if member in GOVERNED_NAMES:
                found.add((name, here + "/items" if member.startswith("allowed_") else here))
            if member == "method" and pointer.endswith("/properties/anchor"):
                found.add((name, here))
            walk(name, sub, here)
        if isinstance(node.get("items"), dict):
            walk(name, node["items"], f"{pointer}/items")
        for keyword in ("oneOf", "anyOf", "allOf"):
            for index, branch in enumerate(node.get(keyword) or ()):
                walk(name, branch, f"{pointer}/{keyword}/{index}")

    for name in schema_names():
        walk(name, schema(name), "")
    assert found == set(GOVERNED), sorted(found ^ set(GOVERNED))
    assert len(schema_names()) == 7


def _load_tool() -> Any:
    return tool("registered_vocabularies")


def _schema_digests() -> dict[str, str]:
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(SCHEMAS.glob("*.json"))}


def _bound_digests() -> dict[str, str]:
    manifest = json.loads((ROOT / "docs/specification/NORMATIVE_ARTIFACTS.json").read_text(encoding="utf-8"))
    prefix = "docs/specification/schemas/"
    return {
        artifact["path"].removeprefix(prefix): artifact["sha256"]
        for artifact in manifest["artifacts"]
        if artifact["path"].startswith(prefix)
    }


def test_new_value_needs_no_schema_change(tmp_path: Path) -> None:
    tool = _load_tool()
    before = _schema_digests()
    assert before == _bound_digests()
    added = {"asset_type": "example_asset", "workflow": "example_asset_initial", "anchoring_method": "example_method"}
    for kind, value in added.items():
        old = vocabulary(kind)
        new = copy.deepcopy(old)
        new["version"] = "1.1.0"
        new["values"][value] = {"since": "1.1.0", "status": "active", "title": "Example", "profile": None}
        if kind == "workflow":
            new["values"][value]["asset_types"] = ["example_asset"]
        (tmp_path / f"{kind}.json").write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
        assert tool.contract_errors(new) == [], kind
        assert tool.append_only_errors(old, new) == [], kind

    fixtures = {}
    for name in schema_names():
        document = schema(name)
        example = copy.deepcopy(document.get("example"))
        if example is None:
            continue
        if "asset_type" in example:
            example["asset_type"] = added["asset_type"]
        if "workflow" in example:
            example["workflow"] = added["workflow"]
        if name == "registry_entry":
            example["anchor"] = {"method": added["anchoring_method"], "system": "example:1", "anchor_reference": "ref"}
        if name == "trust_registry":
            for entry in example["entries"]:
                entry["allowed_asset_types"] = [added["asset_type"]]
                entry["allowed_workflows"] = [added["workflow"]]
        fixtures[name] = example
        errors = list(jsonschema.Draft202012Validator(document).iter_errors(example))
        assert errors == [], (name, [error.message for error in errors])
    assert {"registry_entry", "trust_registry", "verification_receipt"} <= set(fixtures)
    assert _schema_digests() == before == _bound_digests()
