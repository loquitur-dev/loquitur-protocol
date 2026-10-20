"""Render the reason-code register in docs/specification/reason-codes.md from the catalog.

The register is the enumeration of every code in `loquitur.reason_codes.v1` with its
category and severity. It is GENERATED, never typed. A hand-maintained list of several dozen
identifiers beside the file that defines them drifts silently, and a specification that lists
the wrong codes is worse than one that lists none, because a reader acts on it.

Four files have to agree before the register means anything, and this tool refuses to
render unless they do:

  * docs/specification/reason-codes/v2.0/catalog.json: the entries, each carrying the
    code, its category, its severity and the three audience narratives;
  * docs/specification/schemas/verification_summary.schema.json: the enum that closes
    `reason_codes` on a verification summary;
  * docs/specification/schemas/registry_entry.schema.json: the enum that closes
    `reason_codes` on a public registry entry;
  * docs/specification/schemas/verification_receipt.schema.json: the enum that closes
    `reason_codes` on a verification receipt.

Key parity between the catalog and those three enums is what makes the vocabulary closed.
If they disagree, the register cannot be written at all: there is no single answer to
"what are the codes", and printing either side would publish a claim the other file
contradicts. Category and severity values are checked against the enums in the catalog's
own meta-schema, docs/specification/reason-codes/schema.json, for the same reason.

The canonical category order is declared below rather than discovered, and checked for set
equality against the meta-schema's category enum: a category added to the schema and not
placed in the order is a failure here, not a group silently rendered last. A reserved category
holds its place in the order and its subsection number, and is not in the meta-schema's enum:
no entry can use it until a later version defines it.

Two blocks in the document are generated: the register itself, and the table of affirmative
codes that answers "what does a PASS cite". Each sits between its own pair of markers and
nothing outside them is touched. The prose around them is written by hand and this tool never
rewrites it.

Usage:
    python tools/render_reason_codes.py            # verify the document matches the catalog
    python tools/render_reason_codes.py --write    # rewrite the generated block in place

Exit codes: 0 verified (or written), 1 verification failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs/specification/reason-codes/v2.0/catalog.json"
META_SCHEMA = ROOT / "docs/specification/reason-codes/schema.json"
SUMMARY_SCHEMA = ROOT / "docs/specification/schemas/verification_summary.schema.json"
ENTRY_SCHEMA = ROOT / "docs/specification/schemas/registry_entry.schema.json"
RECEIPT_SCHEMA = ROOT / "docs/specification/schemas/verification_receipt.schema.json"
DOCUMENT = ROOT / "docs/specification/reason-codes.md"

BEGIN_MARKER = "<!-- BEGIN GENERATED REGISTER -->"
END_MARKER = "<!-- END GENERATED REGISTER -->"
BEGIN_AFFIRMATIVE = "<!-- BEGIN GENERATED AFFIRMATIVE -->"
END_AFFIRMATIVE = "<!-- END GENERATED AFFIRMATIVE -->"
# The number of the section the register sits in; each category is a numbered subsection of it.
REGISTER_SECTION = "2"

# The order paragraphs appear in a composed narrative, and therefore the order the register
# is grouped in. It mirrors `_CANONICAL_CATEGORY_ORDER` in loquitur-verify-py
# (src/loquitur/verify/narrative.py). It is repeated here rather than
# imported because this repository must be readable and checkable on its own, with no
# implementation checked out; `check_category_order` below is what keeps the copy honest
# about the one property a copy can check locally, that it covers every category the
# schema allows.
CANONICAL_CATEGORY_ORDER: tuple[str, ...] = (
    "integrity",
    "coverage",
    "freshness",
    "conflict",
    "policy",
    "evidence",
    "offline",
    "anchoring",
    "materiality",
    "valuation_crosscheck",
    "authorization",
    "vocabulary",
)
# Categories whose name is reserved and that hold no code in this version (reason-codes.md
# section 3). Each keeps its place in the order, so that no later subsection is renumbered.
RESERVED_CATEGORIES: tuple[str, ...] = ("anchoring",)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _reason_code_enum(schema: dict, path: Path) -> list[str]:
    """Return the `reason_codes` item enum of a public schema."""
    try:
        return list(schema["properties"]["reason_codes"]["items"]["enum"])
    except (KeyError, TypeError) as exc:
        raise SystemExit(f"{path.relative_to(ROOT).as_posix()}: no reason_codes item enum ({exc})") from exc


def _meta_enum(meta: dict, field: str) -> list[str]:
    return list(meta["$defs"]["CatalogEntry"]["properties"][field]["enum"])


def collect_errors(
    catalog: dict, meta: dict, summary_enum: list[str], entry_enum: list[str], receipt_enum: list[str]
) -> list[str]:
    """Every disagreement that would make the register a false statement."""
    errors: list[str] = []
    entries = catalog["entries"]
    codes = set(entries)

    for code, entry in sorted(entries.items()):
        if entry.get("code") != code:
            errors.append(f"catalog entry {code!r} carries code {entry.get('code')!r}; they must be equal")

    for name, enum in (
        ("verification_summary", summary_enum),
        ("registry_entry", entry_enum),
        ("verification_receipt", receipt_enum),
    ):
        if len(enum) != len(set(enum)):
            dupes = sorted({value for value, n in Counter(enum).items() if n > 1})
            errors.append(f"{name}.reason_codes enum repeats: {dupes}")
        missing = sorted(codes - set(enum))
        extra = sorted(set(enum) - codes)
        if missing:
            errors.append(f"{name}.reason_codes enum omits catalog code(s): {missing}")
        if extra:
            errors.append(f"{name}.reason_codes enum carries code(s) absent from the catalog: {extra}")

    allowed_categories = set(_meta_enum(meta, "category"))
    allowed_severities = set(_meta_enum(meta, "severity"))
    for code, entry in sorted(entries.items()):
        if entry["category"] not in allowed_categories:
            errors.append(f"{code}: category {entry['category']!r} is outside the meta-schema enum")
        if entry["severity"] not in allowed_severities:
            errors.append(f"{code}: severity {entry['severity']!r} is outside the meta-schema enum")

    errors.extend(check_category_order(allowed_categories))
    return errors


def check_category_order(allowed_categories: set[str]) -> list[str]:
    """The declared order must cover exactly the categories the meta-schema allows."""
    errors: list[str] = []
    declared = set(CANONICAL_CATEGORY_ORDER) - set(RESERVED_CATEGORIES)
    if len(CANONICAL_CATEGORY_ORDER) != len(set(CANONICAL_CATEGORY_ORDER)):
        errors.append("CANONICAL_CATEGORY_ORDER repeats a category")
    if not set(RESERVED_CATEGORIES) <= set(CANONICAL_CATEGORY_ORDER):
        errors.append("a reserved category has no place in CANONICAL_CATEGORY_ORDER")
    if set(RESERVED_CATEGORIES) & allowed_categories:
        errors.append(f"reserved category(ies) allowed by the meta-schema: {sorted(set(RESERVED_CATEGORIES) & allowed_categories)}")
    unordered = sorted(allowed_categories - declared)
    unknown = sorted(declared - allowed_categories)
    if unordered:
        errors.append(f"category(ies) allowed by the meta-schema but absent from the canonical order: {unordered}")
    if unknown:
        errors.append(f"category(ies) in the canonical order but not allowed by the meta-schema: {unknown}")
    return errors


def render(catalog: dict, meta: dict) -> str:
    """Compose the generated block. Pure function of the catalog and the meta-schema."""
    entries = catalog["entries"]
    severities = _meta_enum(meta, "severity")  # meta-schema order: increasing severity
    by_category: dict[str, list[tuple[str, str]]] = {c: [] for c in CANONICAL_CATEGORY_ORDER}
    used = [c for c in CANONICAL_CATEGORY_ORDER if c not in RESERVED_CATEGORIES]
    for code, entry in entries.items():
        by_category[entry["category"]].append((code, entry["severity"]))
    for rows in by_category.values():
        rows.sort()

    total_by_severity = Counter(entry["severity"] for entry in entries.values())
    lines: list[str] = []
    lines.append(
        f"Vocabulary `{catalog['reason_code_vocabulary']}`, catalog version "
        f"`{catalog['catalog_version']}`: **{len(entries)} codes across "
        f"{len(used)} categories**."
    )
    lines.append("")
    lines.append("| Category | Codes | " + " | ".join(severities) + " |")
    lines.append("| --- | ---: | " + " | ".join("---:" for _ in severities) + " |")
    for category in used:
        rows = by_category[category]
        counts = Counter(severity for _, severity in rows)
        cells = " | ".join(str(counts.get(severity, 0)) for severity in severities)
        lines.append(f"| `{category}` | {len(rows)} | {cells} |")
    totals = " | ".join(f"**{total_by_severity.get(severity, 0)}**" for severity in severities)
    lines.append(f"| **Total** | **{len(entries)}** | {totals} |")
    lines.append("")

    for number, category in enumerate(CANONICAL_CATEGORY_ORDER, start=1):
        rows = by_category[category]
        if category in RESERVED_CATEGORIES:
            lines.append(f"### {REGISTER_SECTION}.{number} `{category}` — reserved")
            lines.append("")
            lines.append("The category name is reserved. It holds no code in this version (section 3).")
            lines.append("")
            continue
        lines.append(
            f"### {REGISTER_SECTION}.{number} `{category}` — {len(rows)} " + ("code" if len(rows) == 1 else "codes")
        )
        lines.append("")
        lines.append("| Code | Severity |")
        lines.append("| --- | --- |")
        for code, severity in rows:
            lines.append(f"| `{code}` | `{severity}` |")
        lines.append("")

    return "\n".join(lines).rstrip("\n")


def render_affirmative(catalog: dict, meta: dict) -> str:
    """Compose the affirmative-code block: the entries of least severity.

    Generated for the same reason the register is. This table is the answer to "what does a
    PASS cite", so a hand-typed copy of it going stale would misstate the one outcome a
    reader is most likely to act on. The description column is each entry's
    ``technical.headline`` without its final full stop, so the wording is sourced rather than
    editorial.
    """
    entries = catalog["entries"]
    affirmative_severity = _meta_enum(meta, "severity")[0]  # meta-schema order: least severe first
    rows = sorted(
        (
            (CANONICAL_CATEGORY_ORDER.index(entry["category"]), code, entry["category"], entry["technical"]["headline"].rstrip("."))
            for code, entry in entries.items()
            if entry["severity"] == affirmative_severity
        )
    )
    lines = [
        f"The register carries **{len(rows)} codes of severity `{affirmative_severity}`**. These are the",
        "affirmative ones: they record that a check succeeded rather than that something went wrong,",
        "and they are what a `PASS` cites. The description column is each entry's",
        "`technical.headline` from the catalog, without its final full stop.",
        "",
        "| Code | Category | What it records |",
        "| --- | --- | --- |",
    ]
    for _, code, category, headline in rows:
        lines.append(f"| `{code}` | `{category}` | {headline} |")
    return "\n".join(lines)


def splice(document: str, begin_marker: str, end_marker: str, block: str) -> str:
    begin = document.index(begin_marker)
    end = document.index(end_marker)
    if end < begin:
        raise SystemExit("markers are out of order in " + DOCUMENT.relative_to(ROOT).as_posix())
    head = document[: begin + len(begin_marker)]
    tail = document[end:]
    return head + "\n\n" + block + "\n\n" + tail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite the generated block in docs/specification/reason-codes.md",
    )
    args = parser.parse_args(argv)

    catalog = _load(CATALOG)
    meta = _load(META_SCHEMA)
    summary_enum = _reason_code_enum(_load(SUMMARY_SCHEMA), SUMMARY_SCHEMA)
    entry_enum = _reason_code_enum(_load(ENTRY_SCHEMA), ENTRY_SCHEMA)
    receipt_enum = _reason_code_enum(_load(RECEIPT_SCHEMA), RECEIPT_SCHEMA)

    errors = collect_errors(catalog, meta, summary_enum, entry_enum, receipt_enum)
    if errors:
        for error in errors:
            print("ERROR " + error, file=sys.stderr)
        print("the sources disagree; the register was not rendered", file=sys.stderr)
        return 1

    document = DOCUMENT.read_text(encoding="utf-8")
    blocks = (
        (BEGIN_MARKER, END_MARKER, render(catalog, meta)),
        (BEGIN_AFFIRMATIVE, END_AFFIRMATIVE, render_affirmative(catalog, meta)),
    )
    missing = [marker for begin, end, _ in blocks for marker in (begin, end) if marker not in document]
    if missing:
        print(
            "marker(s) missing from " + DOCUMENT.relative_to(ROOT).as_posix() + ": " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    rendered = document
    for begin, end, block in blocks:
        rendered = splice(rendered, begin, end, block)
    if args.write:
        if rendered == document:
            print("register already current: " + DOCUMENT.relative_to(ROOT).as_posix())
        else:
            DOCUMENT.write_text(rendered, encoding="utf-8", newline="\n")
            print("wrote " + DOCUMENT.relative_to(ROOT).as_posix())
        return 0

    if rendered != document:
        print(
            "ERROR the generated block(s) in "
            + DOCUMENT.relative_to(ROOT).as_posix()
            + " do not match the catalog; re-run with --write",
            file=sys.stderr,
        )
        return 1

    counts = Counter(entry["severity"] for entry in catalog["entries"].values())
    severities = ", ".join(f"{severity}={counts.get(severity, 0)}" for severity in _meta_enum(meta, "severity"))
    print(
        "reason-code register OK: "
        + str(len(catalog["entries"]))
        + " code(s) in "
        + str(len(CANONICAL_CATEGORY_ORDER) - len(RESERVED_CATEGORIES))
        + " category(ies) ["
        + severities
        + "]"
    )
    print(
        "catalog "
        + catalog["reason_code_vocabulary"]
        + " v"
        + catalog["catalog_version"]
        + ", verification_summary enum ("
        + str(len(summary_enum))
        + "), registry_entry enum ("
        + str(len(entry_enum))
        + ") and verification_receipt enum ("
        + str(len(receipt_enum))
        + ") agree; document block matches"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
