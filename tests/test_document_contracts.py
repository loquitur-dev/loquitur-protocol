"""The member appendix is the documents it cites, row by row.

docs/specification/document-contracts.md lists every member of every document a verifier
loads, with the outcome of breaking it and the rule that states it. An appendix that repeats
rules can go stale in three ways, and each is a test here: a row can stop matching the schema
keyword it cites, a row can cite a sentence the cited document does not carry, and a
member can be added to a closed set without a row. The behavior behind the outcomes is held
in the verifiers' own suites (tests/test_spec_document_contracts.py in loquitur-verify-py and
test/spec-document-contracts.test.ts in loquitur-verify-ts), which read the same tables.

Nothing here needs a verifier, a schema library or a sibling checkout: it compares this
repository with itself.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = ROOT / "docs" / "specification"
APPENDIX = "document-contracts.md"
MEMBER_HEADER = ["member", "required", "type", "value", "refused", "outcome", "rule"]
INSTANT_PATTERN = (
    r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)Z$"
)
INSTANT_VALUE = "an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant"
CATALOG_ITEMS = "each item a code of the catalog (`reason-codes.md`)"
# A reference to another specification document is a link to its file, [`x.md`](x.md). The link is
# markup: the tests read the text a reader sees, the document name in a code span.
DOCUMENT_LINK = re.compile(r"\[`([^`\]]+\.md)`\]\(\1\)")


def document(name: str) -> str:
    return DOCUMENT_LINK.sub(r"`\1`", (SPECIFICATION / name).read_text(encoding="utf-8"))


def flat(text: str) -> str:
    """Whitespace as one space and no code-span backticks: a rewrapped paragraph still matches."""
    return " ".join(text.replace("`", "").split())


def _cells(line: str) -> list[str]:
    parts = re.split(r"(?<!\\)\|", line.strip())
    return [part.strip().replace("\\|", "|") for part in parts[1:-1]]


def tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Every Markdown table of ``text`` as (header cells, body rows)."""
    found: list[tuple[list[str], list[list[str]]]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if (
            line.lstrip().startswith("|")
            and index + 1 < len(lines)
            and re.fullmatch(r"\s*\|(\s*:?-{3,}:?\s*\|)+\s*", lines[index + 1])
        ):
            header = _cells(line)
            rows = []
            index += 2
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                rows.append(_cells(lines[index]))
                index += 1
            found.append((header, rows))
            continue
        index += 1
    return found


def sections(text: str) -> dict[str, str]:
    """The text of each ``## `` section of a document, by its title."""
    out: dict[str, str] = {}
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if title is not None:
                out[title] = "\n".join(body)
            title, body = line[3:].strip(), []
        else:
            body.append(line)
    if title is not None:
        out[title] = "\n".join(body)
    return out


def member_rows() -> dict[str, list[dict[str, str]]]:
    """Every member table of the appendix, by the title of the section that carries it."""
    out: dict[str, list[dict[str, str]]] = {}
    for title, body in sections(document(APPENDIX)).items():
        for header, rows in tables(body):
            if header == MEMBER_HEADER:
                assert title not in out, f"two member tables in section {title}"
                out[title] = [dict(zip(header, row, strict=True)) for row in rows]
    assert out, "the appendix carries no member table"
    return out


CASE_HEADER = ["case", "outcome", "rule"]


def case_rows() -> dict[str, list[dict[str, str]]]:
    """Every case table of the appendix, by the title of the section that carries it."""
    out: dict[str, list[dict[str, str]]] = {}
    for title, body in sections(document(APPENDIX)).items():
        for header, rows in tables(body):
            if header == CASE_HEADER:
                out.setdefault(title, []).extend(dict(zip(header, row, strict=True)) for row in rows)
    assert out, "the appendix carries no case table"
    return out


def one_table(text: str, header: list[str]) -> list[dict[str, str]]:
    matching = [rows for cells, rows in tables(text) if cells == header]
    assert len(matching) == 1, f"expected one table headed {header}, found {len(matching)}"
    return [dict(zip(header, row, strict=True)) for row in matching[0]]


def codes(cell: str) -> list[str]:
    return re.findall(r"`([^`]*)`", cell)


def code(cell: str) -> str:
    found = codes(cell)
    assert len(found) == 1, f"expected one code span, got {cell!r}"
    return found[0]


def section_titled(prefix: str) -> str:
    for title in member_rows():
        if title.split(". ", 1)[1].startswith(prefix):
            return title
    raise AssertionError(f"no appendix section for {prefix}")


# ---------------------------------------------------------------- the rule column


def rule_of(row: dict[str, str]) -> tuple[str, str]:
    """The cited document (or schema) and what is cited: a quoted sentence or a JSON pointer.

    A schema-backed row may cite, after its pointer, the sentence of another document that states
    what the row adds to the schema keyword; `prose_beside_the_pointer` reads it.
    """
    spans = codes(row["rule"])
    assert spans, f"row {row['member']} cites nothing"
    quoted = re.findall(r'"([^"]*)"', row["rule"].replace("`", ""))
    if spans[0].endswith(".json"):
        pointers = [span for span in spans[1:] if span.startswith("/")]
        assert len(pointers) == 1, f"row {row['member']} cites {len(pointers)} pointers"
        return spans[0], pointers[0]
    assert quoted, f"row {row['member']} cites {spans[0]} without quoting a sentence"
    return spans[0], quoted[0]


def prose_beside_the_pointer(row: dict[str, str]) -> tuple[str, str] | None:
    """The document and the quoted sentence a schema-backed row cites beside its pointer, if any."""
    spans = codes(row["rule"])
    if not spans or not spans[0].endswith(".json"):
        return None
    documents = [span for span in spans[2:] if span.endswith(".md")]
    quoted = re.findall(r'"([^"]*)"', row["rule"].replace("`", ""))
    if not documents and not quoted:
        return None
    assert len(documents) == 1 and len(quoted) == 1, f"row {row['member']} cites {documents} and {quoted}"
    return documents[0], quoted[0]


# What a schema-backed `value` cell adds to the schema keyword, and the document whose sentence
# states it: the free-string rule and the calendar rule hold whatever the schema admits.
ADDED_BY_PROSE = {
    "a code point outside W": "bundle-objects.md",
    "and a calendar instant": "canonicalization-and-hashing.md",
}


def resolve(schema: Any, pointer: str) -> Any:
    node = schema
    for token in pointer.split("/")[1:]:
        key = int(token) if token.isdigit() and isinstance(node, list) else token
        assert key in node if isinstance(node, dict) else True, f"{pointer} does not resolve"
        node = node[key]
    return node


JSON_TYPES = ("null", "boolean", "integer", "number", "string", "array", "object")


def admitted_types(row: dict[str, str]) -> set[str]:
    """The JSON types the row's `type` cell admits; `number` admits `integer` as well."""
    found = {name for name in codes(row["type"]) if name in JSON_TYPES}
    return found | {"integer"} if "number" in found else found


def json_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "integer" if value.is_integer() else "number"
    return {type(None): "null", str: "string", list: "array", dict: "object"}[type(value)]


def test_a_row_that_states_no_value_rule_refuses_only_types_it_does_not_admit() -> None:
    """`-` in the `value` column means the type cell is the whole rule (§1).

    The verifiers run one value of every type the cell refuses and, for these rows, one value of
    every type it admits, which must be accepted. A refused example of an admitted type would
    contradict the cell the verifiers read, so the two cannot drift apart silently: widening such
    a cell moves its own examples onto the accepted side, where the verifier refuses them.
    """
    checked = 0
    for rows in member_rows().values():
        for row in rows:
            if row["value"] != "-" or row["type"] == "bytes":
                continue
            admitted = admitted_types(row)
            assert admitted, f"row {row['member']} states no value rule and no JSON type"
            for span in codes(row["refused"]):
                if span.startswith("<"):
                    continue
                name = json_type(json.loads(span))
                assert name not in admitted, f"row {row['member']} refuses {span}, whose type it admits"
                checked += 1
    # The free-string rule (bundle-objects.md) gives every string row a value rule; the rows that
    # state none are the object and array ones.
    assert checked >= 6, checked


def test_every_prose_citation_is_a_sentence_of_the_document_it_names() -> None:
    cited = 0
    for rows in member_rows().values():
        for row in rows:
            name, what = rule_of(row)
            if name.endswith(".json"):
                continue
            assert (SPECIFICATION / name).is_file(), f"row {row['member']} cites {name}, which is not here"
            assert flat(what) in flat(document(name)), f"{name} does not carry: {what}"
            cited += 1
    assert cited == suite_row()["member rows"] - coverage_counts()["schema"], cited


def test_every_case_cites_a_rule_and_an_outcome() -> None:
    outcomes = {code(row["outcome"]) for row in one_table(sections(document(APPENDIX))["2. Outcomes"], OUTCOME_HEADER)}
    seen: set[str] = set()
    for rows in case_rows().values():
        for row in rows:
            case = row["case"]
            assert case not in seen, f"two cases named {case}"
            seen.add(case)
            assert re.fullmatch(r"`[a-z0-9-]+`", case), case
            assert code(row["outcome"]) in outcomes, row
            name, what = rule_of({"member": case, "rule": row["rule"]})
            if name.endswith(".json"):
                resolve(schema(name), what)
                continue
            assert flat(what) in flat(document(name)), f"{name} does not carry: {what}"
    assert len(seen) == suite_row()["case rows"], sorted(seen)


def test_every_outcome_citation_is_a_sentence_of_the_document_it_names() -> None:
    for row in one_table(sections(document(APPENDIX))["2. Outcomes"], OUTCOME_HEADER):
        name = codes(row["rule"])[0]
        quoted = re.findall(r'"([^"]*)"', row["rule"].replace("`", ""))
        assert quoted, row
        assert flat(quoted[0]) in flat(document(name)), f"{name} does not carry: {quoted[0]}"


OUTCOME_HEADER = ["outcome", "`status`", "`verdict`", "`outcome.reason`", "`errors`", "exit", "rule"]


def test_every_outcome_is_a_value_of_the_report_contract() -> None:
    report = document("report-contract.md")
    statuses = {
        code(row["`status`"]): (code(row["`verdict`"]), code(row["`exit_code`"]))
        for row in one_table(report, ["`status`", "`verdict`", "`exit_code`", "class", "meaning"])
    }
    # Rule 7 of section 5.2 names a review run by the first of its review reasons (section 3.3).
    reasons = {
        span
        for row in one_table(report, ["#", "the run", "`outcome.reason`"])
        for span in codes(row["`outcome.reason`"])
    } | {code(row["review reason"]) for row in one_table(report, ["#", "review reason", "holds when"])}
    errors = {code(row["code"]) for row in one_table(report, ["code", "class", "condition"])}
    seen = set()
    for row in one_table(sections(document(APPENDIX))["2. Outcomes"], OUTCOME_HEADER):
        seen.add(row["outcome"])
        if row["`status`"] == "none":
            assert row["exit"] == "`64`", row
            continue
        status = code(row["`status`"])
        assert statuses[status] == (code(row["`verdict`"]), code(row["exit"])), row
        # Rule 1 of section 5.2: a run carrying an error is named by that error's code.
        assert code(row["`outcome.reason`"]) in reasons | errors, row
        if row["`errors`"] != "none":
            assert code(row["`errors`"]) in errors, row
    used = {row["outcome"] for rows in member_rows().values() for row in rows}
    assert used <= seen, sorted(used - seen)


# The four sections whose contract is prose rather than a schema, and the table of the document
# that declares each one. A section names the document, the title of its section there, the
# header of the table to read, the column that carries the member's name, and the prefix an
# appendix row carries that the source table does not.
PROSE_SECTIONS = {
    "`manifest.json`": ("bundle-objects.md", "2. `manifest.json`", ["member", "type", "required"], "member", ""),
    "`p1.json`": ("bundle-objects.md", "3. `p1.json`", ["member", "type", "required", "value"], "member", ""),
    "`envelope_env1.json`": (
        "bundle-objects.md",
        "4. `envelope_env1.json`",
        ["group", "member", "type", "required"],
        "member",
        "",
    ),
    "The trust-root document": (
        "trust-root.md",
        "3. The trust-root document",
        ["field", "type", "required", "meaning"],
        "field",
        "roots[i].",
    ),
    "The registered vocabulary document": (
        "verification-vocabularies.md",
        "6. The registered vocabulary document",
        ["field", "type", "required", "meaning"],
        "field",
        "",
    ),
}

# The rows that describe a document as a whole, or an array of it, rather than one of its
# fields, and so have no row in a source table. Their type is held against the sentence they
# cite instead, by the test below. Every member row of the appendix is held by one of the three
# ways (a schema keyword, a declaring document's type column, or the sentence it cites), except
# the `bytes` rows of §6, which name no JSON type.
DOCUMENT_LEVEL_ROWS = {
    "`canonical_input.json`": ("the document",),
    "The trust-root document": ("the document", "roots"),
}


def source_table(prefix: str) -> dict[str, dict[str, str]]:
    """The declaring document's own table for a prose-backed section, by member name."""
    name, title, header, key, _prefix = PROSE_SECTIONS[prefix]
    rows = one_table(sections(document(name))[title], header)
    return {code(row[key]): row for row in rows}


def declared_types(cell: str) -> set[str]:
    """The JSON types a declaring document's `type` cell names.

    Such a cell opens with its types, joined by `or`, and may then go on to say more about the
    value: `array of strings` is an array, `string, not empty` is a string, `integer or null` is
    either. Reading the opening run of type words and stopping at the first word that is not one
    keeps those forms apart, so the cell is read as the type rule it is.
    """
    found: set[str] = set()
    for token in re.findall(r"[A-Za-z]+", flat(cell)):
        if token in JSON_TYPES:
            found.add(token)
        elif token != "or":
            break
    assert found, f"{cell!r} names no JSON type"
    return found | {"integer"} if "number" in found else found


@pytest.mark.parametrize("prefix", sorted(PROSE_SECTIONS))
def test_every_prose_backed_row_is_what_its_document_declares(prefix: str) -> None:
    """A prose-backed cell is what its own document declares, as a schema-backed one is.

    §1 says the `type` column is a rule the verifiers execute, so widening a cell must fail
    something. For §8 to §10 the cell is held against the schema keyword it cites. These four
    sections cite a document instead, and this holds them against that document's own table: a
    cell widened to admit a further type contradicts the rule it names, and this fails.

    The `required` column is held the same way, and for the same reason. Each of these four
    source tables states the requirement of every member in a column of its own, so a row that
    says a member is optional where its declaring document requires it is a contradiction of
    the kind this appendix exists to refuse, and a reader who takes the appendix at its word
    writes a verifier that accepts a document the protocol refuses.
    """
    _name, _title, _header, _key, member_prefix = PROSE_SECTIONS[prefix]
    declared = source_table(prefix)
    exempt = DOCUMENT_LEVEL_ROWS.get(prefix, ())
    checked = 0
    for row in member_rows()[section_titled(prefix)]:
        member = row["member"].strip("`")
        if member in exempt:
            continue
        key = member.removeprefix(member_prefix)
        assert key in declared, f"{prefix}: {member} is in no table of the declaring document"
        assert admitted_types(row) == declared_types(declared[key]["type"]), (
            f"{prefix}: {member} is `{row['type']}` here and {declared[key]['type']!r} where it is declared"
        )
        assert row["required"] == declared[key]["required"], (
            f"{prefix}: {member} is required {row['required']!r} here and "
            f"{declared[key]['required']!r} where it is declared"
        )
        checked += 1
    assert checked == len(declared), f"{prefix}: {checked} rows held against {len(declared)} declared"


@pytest.mark.parametrize("prefix", sorted(DOCUMENT_LEVEL_ROWS))
def test_a_document_level_row_names_the_one_type_its_sentence_names(prefix: str) -> None:
    """A row for the document as a whole is held against the sentence it cites.

    These rows have no field in the declaring document's table, so the sentence in the `rule`
    column is what states their type. It states one type, and the cell names that one: a cell
    widened to admit a second type does not match the sentence it cites, and this fails.
    """
    rows = {row["member"].strip("`"): row for row in member_rows()[section_titled(prefix)]}
    for member in DOCUMENT_LEVEL_ROWS[prefix]:
        row = rows[member]
        _name, sentence = rule_of(row)
        named = [token for token in re.findall(r"[A-Za-z]+", flat(sentence)) if token in JSON_TYPES]
        assert named, f"{member}: the sentence it cites names no JSON type"
        assert admitted_types(row) == {named[0]}, (
            f"{member}: the cell is `{row['type']}` and its sentence names {named[0]}"
        )


def test_every_member_row_names_a_type_something_holds_it_to() -> None:
    """No member row's `type` cell is held by nothing, which is what §1 claims of the column.

    A cell is held in one of three ways: it is the keyword of the schema it cites (§8 to §10),
    it is the type its declaring document's own table gives the member (§3, §4, §7 and the
    fields of §11), or it is the one type the sentence it cites names (the rows that describe a
    document as a whole). The `bytes` rows of §6 describe a file and name no JSON type, and are
    the only exemption. A new section, or a new row in one, that escapes all three fails here
    rather than joining the column quietly.

    How many rows each way holds is §14's first table, which this reads rather than repeating:
    the appendix states its own coverage and this compares the statement with the rows, so a
    count that outruns them fails here instead of standing as prose.
    """
    held = {"schema": 0, "table": 0, "sentence": 0, "bytes": 0}
    for title, rows in member_rows().items():
        prefix = next(
            (name for name in (*SCHEMA_SECTIONS, *PROSE_SECTIONS, *DOCUMENT_LEVEL_ROWS) if section_titled(name) == title),
            None,
        )
        for row in rows:
            member = row["member"].strip("`")
            if row["type"] == "bytes":
                held["bytes"] += 1
            elif prefix in SCHEMA_SECTIONS:
                held["schema"] += 1
            elif member in DOCUMENT_LEVEL_ROWS.get(prefix, ()):
                held["sentence"] += 1
            elif prefix in PROSE_SECTIONS:
                held["table"] += 1
            else:
                raise AssertionError(f"{title}: the type cell of {member} is held by nothing")
    assert held == coverage_counts(), held
    assert sum(held.values()) == suite_row()["member rows"], held


def test_the_bundle_object_sections_cover_their_closed_field_sets() -> None:
    """Every member of the three closed sets of bundle-objects.md has a row, and no other."""
    for prefix in ("`manifest.json`", "`p1.json`", "`envelope_env1.json`"):
        rows = member_rows()[section_titled(prefix)]
        assert {row["member"].strip("`") for row in rows} == set(source_table(prefix)), prefix


def test_the_trust_root_section_covers_the_closed_field_set_of_trust_root_md() -> None:
    fields = set(source_table("The trust-root document"))
    rows = member_rows()[section_titled("The trust-root document")]
    listed = {row["member"].strip("`").removeprefix("roots[i].") for row in rows}
    assert fields <= listed, sorted(fields - listed)


# ---------------------------------------------------------------- the schema-backed sections

SCHEMA_SECTIONS = {
    "`verification_receipt.json`": "verification_receipt.schema.json",
    "The registry entry": "registry_entry.schema.json",
    "The trust registry": "trust_registry.schema.json",
}


def schema(name: str) -> dict[str, Any]:
    return json.loads((SPECIFICATION / "schemas" / name).read_text(encoding="utf-8"))


def type_cell(node: dict[str, Any]) -> str:
    if "oneOf" in node and "type" not in node:
        names = {t for branch in node["oneOf"] for t in as_list(branch.get("type"))}
        # `null` last, as a nullable member's own type list writes it.
        ordered = sorted(names - {"null"}) + (["null"] if "null" in names else [])
        return " or ".join(f"`{name}`" for name in ordered)
    return " or ".join(f"`{name}`" for name in as_list(node.get("type"))) or "any"


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def value_cell(node: dict[str, Any]) -> str:
    if "oneOf" in node and "type" not in node:
        return "one of the branches of the schema's `oneOf`"
    parts = []
    if "const" in node:
        parts.append(f"exactly `{json.dumps(node['const'])}`")
    if "enum" in node:
        parts.append("one of " + ", ".join(f"`{json.dumps(value)}`" for value in node["enum"]))
    if "pattern" in node:
        parts.append(INSTANT_VALUE if node["pattern"] == INSTANT_PATTERN else f"matches `{node['pattern']}`")
    if node.get("minLength"):
        parts.append(f"at least {node['minLength']} character")
    if node.get("minimum") is not None:
        parts.append(f"at least {node['minimum']}")
    if node.get("minItems"):
        parts.append(f"at least {node['minItems']} item")
    if node.get("uniqueItems"):
        parts.append("items distinct")
    items = node.get("items")
    if isinstance(items, dict):
        if len(items.get("enum") or ()) > 8:
            parts.append(CATALOG_ITEMS)
        elif items.get("enum"):
            parts.append("each item one of " + ", ".join(f"`{json.dumps(value)}`" for value in items["enum"]))
        elif items.get("pattern"):
            parts.append(f"each item matches `{items['pattern']}`")
        elif items.get("type"):
            parts.append(f"each item {type_cell(items)}")
    if node.get("additionalProperties") is False:
        parts.append("closed field set")
    return "; ".join(parts) if parts else "-"


def free_string(node: dict[str, Any]) -> bool:
    """A member the schema types as a string and holds to no pattern, enumeration or constant."""
    return "string" in as_list(node.get("type")) and not any(key in node for key in ("pattern", "enum", "const"))


# Free by the schema alone, and held to a form by another document: the trust registry's root
# signature is compact r || s in 128 lowercase hex characters when a root authenticates it
# (trust-root.md), and the registry's contract does not hold it to anything more than the schema.
HELD_TO_A_FORM_ELSEWHERE = {("trust_registry.schema.json", "/properties/signature/properties/signature")}


def parent_of(schema_document: dict[str, Any], pointer: str) -> tuple[Any, str]:
    parent = resolve(schema_document, pointer.rsplit("/", 1)[0].rsplit("/", 1)[0]) if "/" in pointer else schema_document
    return parent, pointer.rsplit("/", 1)[1]


@pytest.mark.parametrize("prefix", sorted(SCHEMA_SECTIONS))
def test_every_schema_row_is_the_schema_keyword_it_cites(prefix: str) -> None:
    schema_document = schema(SCHEMA_SECTIONS[prefix])
    rows = member_rows()[section_titled(prefix)]
    for row in rows:
        name, pointer = rule_of(row)
        assert name == SCHEMA_SECTIONS[prefix], row
        node = resolve(schema_document, pointer)
        parent, member = parent_of(schema_document, pointer)
        required = member in (parent.get("required") or ())
        assert row["required"] == ("yes" if required else "no"), f"{row['member']}: required"
        assert row["type"] == type_cell(node), f"{row['member']}: type is {type_cell(node)}"
        expected_value = value_cell(node)
        if free_string(node) and (SCHEMA_SECTIONS[prefix], pointer) not in HELD_TO_A_FORM_ELSEWHERE:
            # bundle-objects.md, "Free strings": not empty under W, beyond what the schema holds.
            expected_value = "a code point outside W" if expected_value == "-" else expected_value + "; a code point outside W"
        assert row["value"] == expected_value, f"{row['member']}: value is {expected_value}"


@pytest.mark.parametrize("prefix", sorted(SCHEMA_SECTIONS))
def test_a_schema_row_cites_the_sentence_that_states_what_it_adds(prefix: str) -> None:
    """A row that refuses a value its schema keyword admits cites the prose rule beside the pointer."""
    cited = 0
    for row in member_rows()[section_titled(prefix)]:
        added = [name for clause, name in ADDED_BY_PROSE.items() if row["value"].endswith(clause)]
        prose = prose_beside_the_pointer(row)
        if not added:
            assert prose is None, f"{row['member']} cites prose for a value its schema keyword states"
            continue
        assert prose is not None, f"{row['member']} adds to its schema keyword and cites only the pointer"
        name, sentence = prose
        assert name == added[0], f"{row['member']} cites {name}, not {added[0]}"
        assert flat(sentence) in flat(document(name)), f"{name} does not carry: {sentence}"
        cited += 1
    assert cited, prefix


@pytest.mark.parametrize("prefix", sorted(SCHEMA_SECTIONS))
def test_every_schema_member_has_a_row(prefix: str) -> None:
    schema_document = schema(SCHEMA_SECTIONS[prefix])
    listed = {row["member"].strip("`") for row in member_rows()[section_titled(prefix)]}
    expected: set[str] = set()

    def walk(node: dict[str, Any], path: str) -> None:
        for member, sub in (node.get("properties") or {}).items():
            here = f"{path}{member}"
            expected.add(here)
            walk(sub, f"{here}.")
            items = sub.get("items")
            if isinstance(items, dict):
                walk(items, f"{here}[i].")
            for branch in sub.get("oneOf") or ():
                walk(branch, f"{here}.")

    walk(schema_document, "")
    assert expected == listed, sorted(expected ^ listed)


# ---------------------------------------------------------------- what this suite covers

COVERAGE_SECTION = "14. What each suite runs"
COVERAGE_HEADER = ["held by", "what holds it", "member rows"]
SUITE_HEADER = ["suite", "member rows", "case rows", "input rows", "report surface compared"]
THIS_SUITE = "tests/test_document_contracts.py"


def coverage_counts() -> dict[str, int]:
    """§14's first table: how many member rows each way of holding a `type` cell reaches."""
    rows = one_table(sections(document(APPENDIX))[COVERAGE_SECTION], COVERAGE_HEADER)
    return {code(row["held by"]): int(row["member rows"]) for row in rows}


def suite_row(suite: str = THIS_SUITE) -> dict[str, Any]:
    """§14's second table, for one suite: its counts as numbers and its surface as a list."""
    rows = one_table(sections(document(APPENDIX))[COVERAGE_SECTION], SUITE_HEADER)
    found = [row for row in rows if suite in codes(row["suite"])]
    assert len(found) == 1, f"§14 names {len(found)} suites at {suite}"
    row = found[0]
    return {
        "member rows": int(row["member rows"]),
        "case rows": int(row["case rows"]),
        "input rows": 0 if row["input rows"] == "-" else int(row["input rows"]),
        "surface": codes(row["report surface compared"]),
    }


def test_section_14_names_the_three_suites_and_this_one_is_among_them() -> None:
    rows = one_table(sections(document(APPENDIX))[COVERAGE_SECTION], SUITE_HEADER)
    assert len(rows) == 3, rows
    assert sum(THIS_SUITE in codes(row["suite"]) for row in rows) == 1, rows


def test_this_suite_covers_what_section_14_says_it_covers() -> None:
    """§14 is the appendix's statement of its own coverage, and this holds this suite's row.

    Every number in that row is compared with the rows this module reads: the member rows it
    holds against the rules they cite, the case rows it holds, the input rows it holds, and the
    report surface it compares, which is none, because nothing here runs a verifier. A row
    claiming more than the module reaches fails here rather than being believed.
    """
    claimed = suite_row()
    assert sum(len(rows) for rows in member_rows().values()) == claimed["member rows"]
    assert sum(len(rows) for rows in case_rows().values()) == claimed["case rows"]
    assert len(one_table(sections(document(APPENDIX))[INPUT_SECTION], INPUT_HEADER)) == claimed["input rows"]
    assert claimed["surface"] == [], claimed


INPUT_SECTION = "12. The verifier's own inputs"
INPUT_HEADER = ["input", "required", "form", "refused", "outcome", "rule"]


def test_the_bundle_row_leaves_archive_intake_optional() -> None:
    """§12 describes the form of the input, not an obligation on every verifier.

    This document is normative, so a row offering "a directory carrying `manifest.json`, or a ZIP
    archive holding one bundle root" as plain alternatives would read as a requirement to accept
    an archive, which would make a verifier that reads directory bundles only non-conforming.
    `report-contract.md` §5.3 says the opposite in as many words, so the row says which verifier
    the second form belongs to and cites it. This test holds
    the two documents together: the citation must name a sentence §5.3 carries.
    """
    row = next(
        row
        for row in one_table(sections(document(APPENDIX))[INPUT_SECTION], INPUT_HEADER)
        if row["input"] == "the bundle"
    )
    assert "archive intake is optional" in flat(row["form"]), row["form"]
    assert "report-contract.md" in row["form"] and "5.3" in row["form"], row["form"]
    assert "for a verifier that reads archives, a ZIP archive" in flat(row["form"]), row["form"]
    assert "Archive intake is optional: a verifier **MAY** read directory bundles only" in flat(
        document("report-contract.md")
    )


def test_every_input_row_cites_a_rule_and_an_outcome() -> None:
    """§12's rows are held as the member rows are: an outcome of §2 and a sentence that exists.

    The verifiers run these rows through a command line. This holds their citations here, so
    that an input row citing a sentence `report-contract.md` does not carry fails a suite of this
    repository.
    """
    outcomes = {code(row["outcome"]) for row in one_table(sections(document(APPENDIX))["2. Outcomes"], OUTCOME_HEADER)}
    for row in one_table(sections(document(APPENDIX))[INPUT_SECTION], INPUT_HEADER):
        if row["outcome"] != "-":
            assert code(row["outcome"]) in outcomes, row
        name, what = rule_of({"member": row["input"], "rule": row["rule"]})
        assert (SPECIFICATION / name).is_file(), f"input {row['input']} cites {name}, which is not here"
        assert flat(what) in flat(document(name)), f"{name} does not carry: {what}"
