"""Propose inventory records for the requirements no record claims yet, for a person to review.

    python tools/propose_requirements.py [--out FILE]

Reads the parts, docs/traceability/rule-tables.json, docs/traceability/requirements.json and the
corpus tools/requirements_inventory.py reads (the pinned archive, or the first root
LOQUITUR_CORPUS_ROOTS names). For every key-word sentence and every row of a listed table that no
active record claims, it writes a proposed record with the next free identifier of its part. For a
row keyed by a code a run reports (an error code, a review reason, a status, an authorization or
root status, a verdict-grounds rule), it proposes as corpus coverage the binding runs that report
that code, at most five, by name.

It never writes docs/traceability/requirements.json: the proposal goes to standard output, or to
--out, and a person decides what binds, what covers it and what is excluded, and copies the
records in. A proposal is not a review.

Exit codes: 0 written, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import requirements_inventory as inventory_tool  # noqa: E402

MAX_RUNS = 5


def declared_runs(files: dict[str, bytes]) -> dict[str, dict]:
    """Every binding run by its coverage entry, with the declarations a run may carry."""
    runs: dict[str, dict] = {}
    for name in (
        "verify.json",
        "additional-negatives/expected.json",
        "bundles/manifest.json",
        "summary-checks/expected.json",
    ):
        if name not in files:
            continue
        value = json.loads(files[name].decode("utf-8"))
        if name == "verify.json":
            items = value.items()
        else:
            items = ((case["id"], case) for case in value.get("cases", []))
        for case, run in items:
            runs[f"{name}#{case}"] = run
    return runs


def _expectations(run: dict) -> list[dict]:
    if "expected" in run:
        return [run["expected"]] if isinstance(run["expected"], dict) else []
    return [value for value in run.get("expected_by_intake", {}).values() if isinstance(value, dict)]


def _code(cell: str) -> str | None:
    match = re.fullmatch(r"`([^`]+)`", cell.strip())
    return match.group(1) if match else None


def _status(cell: str) -> str | None:
    """A status cell: a code, or `null` for a step not reached."""
    code = _code(cell)
    return None if code == "null" else code


def row_matcher(table: dict, cells: dict[str, str]):
    """A predicate over a run's declarations for one row of a code-keyed table, or None."""
    table_id = table["id"]
    if table_id == "RPT-errors":
        code = cells["code"].strip("`")
        return lambda e: code in (e.get("errors") or []) or e.get("reason") == code
    if table_id == "RPT-review-reasons":
        reason = cells["review reason"].strip("`")
        return lambda e: reason in (e.get("review_reasons") or [])
    if table_id == "RPT-outcomes":
        status = cells["`status`"].strip("`")
        return lambda e: e.get("status") == status
    if table_id == "RPT-reason-rules":
        reason = _code(cells["`outcome.reason`"])
        if reason is not None:
            return lambda e: e.get("reason") == reason
        if cells["#"] == "1":
            return lambda e: bool(e.get("errors")) and e.get("reason") == e["errors"][0]
        if cells["#"] == "7":
            return lambda e: (
                e.get("status") == "OFFLINE_REVIEW"
                and bool(e.get("review_reasons"))
                and e.get("reason") == e["review_reasons"][0]
            )
        return None
    if table_id == "TRA-order":
        authorization = _code(cells["`authorization_status`"])
        signature = _status(cells["`signature_status`"])
        if authorization is None:
            return None

        def matches(e: dict) -> bool:
            trust = e.get("trust_registry")
            return (
                isinstance(trust, dict)
                and trust.get("authorization_status") == authorization
                and trust.get("signature_status") == signature
            )

        return matches
    if table_id == "ROOT-order":
        status = _code(cells["status"])
        if status is None:
            return None

        def matches_root(e: dict) -> bool:
            trust = e.get("trust_registry")
            return isinstance(trust, dict) and trust.get("trust_registry_root_signature_status") == status

        return matches_root
    return None


def table_cells(parts: dict, table: dict) -> list[dict[str, str]]:
    if table["kind"] != "table":
        return []
    section = inventory_tool.section_of(parts, table["document"], table["section"])
    for header, rows in inventory_tool.tables_of(section):
        if header == table["header"]:
            return [dict(zip(header, row, strict=False)) for row in rows]
    return []


def propose_coverage(table: dict, cells: dict[str, str] | None, key: str, runs: dict[str, dict]) -> list[str]:
    if table["id"] == "VG-rules":
        return sorted(
            entry
            for entry, run in runs.items()
            if entry.startswith("summary-checks/") and key in (run.get("expected", {}).get("violated_rules") or [])
        )[:MAX_RUNS]
    if cells is None:
        return []
    matcher = row_matcher(table, cells)
    if matcher is None:
        return []
    found = sorted(entry for entry, run in runs.items() if any(matcher(e) for e in _expectations(run)))
    return found[:MAX_RUNS]


def next_numbers(inventory: dict) -> dict[str, int]:
    numbers: dict[str, int] = {}
    for record in inventory["requirements"]:
        match = inventory_tool.IDENTIFIER.fullmatch(record["id"])
        if match:
            code = match.group("doc")
            numbers[code] = max(numbers.get(code, 0), int(match.group("number")))
    return numbers


def proposals(root: Path = inventory_tool.ROOT, inventory: dict | None = None) -> list[dict]:
    parts = inventory_tool.read_parts(root)
    tables = inventory_tool.read_rule_tables(root)
    if inventory is None:
        inventory = (
            inventory_tool.read_inventory(root) if (root / inventory_tool.INVENTORY).is_file() else {"requirements": []}
        )
    _, files = inventory_tool.corpus_files(root)
    runs = declared_runs(files)
    active = [r for r in inventory["requirements"] if r["status"] == "active"]
    numbers = next_numbers(inventory)
    proposed: list[dict] = []

    def new_id(document: str) -> str:
        code = inventory_tool.DOC_CODES[document]
        numbers[code] = numbers.get(code, 0) + 1
        return f"REQ-{code}-{numbers[code]:03d}"

    # Sentences and rows in document order: the parts in the order of DOC_CODES, then each part's
    # sentences before its tables.
    sentences = inventory_tool.keyword_sentences(parts)
    for document in inventory_tool.DOC_CODES:
        for sentence in (s for s in sentences if s.document == document):
            if any(
                r["locator"]["kind"] == "sentence"
                and r["document"] == document
                and r["section"] == sentence.section
                and inventory_tool.collapse(r["locator"]["text"]) in sentence.text
                for r in active
            ):
                continue
            proposed.append(
                {
                    "id": new_id(document),
                    "document": document,
                    "section": sentence.section,
                    "locator": {"kind": "sentence", "text": sentence.text},
                    "kind": sentence.kind,
                    "keyword": sentence.keyword,
                    "binds": "verifier",
                    "status": "active",
                    "since": "0.1.0",
                    "coverage": {"corpus": [], "static": [], "suites": []},
                    "exclusion": None,
                }
            )
        for table in (t for t in tables["tables"] if t["document"] == document):
            cells_by_key = {}
            if table["kind"] == "table":
                column = table["key"]
                cells_by_key = {inventory_tool._strip_code(c[column]): c for c in table_cells(parts, table)}
            for key in inventory_tool.rule_rows(parts, table):
                if any(r["locator"] == {"kind": "row", "table": table["id"], "key": key} for r in active):
                    continue
                cells = cells_by_key.get(key)
                proposed.append(
                    {
                        "id": new_id(document),
                        "document": document,
                        "section": key if table["kind"] == "headings" else table["section"],
                        "locator": {"kind": "row", "table": table["id"], "key": key},
                        "kind": "row",
                        "keyword": None,
                        "binds": "verifier",
                        "status": "active",
                        "since": "0.1.0",
                        "coverage": {"corpus": propose_coverage(table, cells, key, runs), "static": [], "suites": []},
                        "exclusion": None,
                    }
                )
    return proposed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    text = json.dumps(proposals(), indent=2, ensure_ascii=False) + "\n"
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
