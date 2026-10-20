"""Read the requirements of the specification, and check the inventory that names them.

docs/traceability/requirements.json gives every requirement of the specification an identifier,
`REQ-<DOC>-<NNN>`, outside the prose: the identifiers are not written into the parts, so that
adding or correcting one changes no normative byte and no prose digest. A record is bound to the
text by a locator: an exact sentence of a section, or a row of a rule table that
docs/traceability/rule-tables.json lists, found by its natural key.

What counts as a requirement here (the inventory's `scope`, which introduction.md section 8.4 repeats):

- every sentence of a part that carries one of the key words MUST, MUST NOT, REQUIRED, SHALL or
  SHALL NOT, outside introduction.md section 4.1 (the key-word boilerplate) and outside fenced
  code; a sentence carrying SHOULD, SHOULD NOT, RECOMMENDED, NOT RECOMMENDED, MAY or OPTIONAL
  and none of those gets a record too, of kind `advisory`;
- every row of every table, numbered list or set of headings rule-tables.json lists.

A requirement stated in the indicative outside those tables binds as well (introduction.md section
4.2), and this inventory does not claim to list it: it cannot be found mechanically.

This module reads; it never writes the inventory. tools/propose_requirements.py proposes records
for a person to review, tools/render_requirements.py writes docs/traceability/README.md from the
inventory, and tests/test_requirements_inventory.py holds the invariants below.

The corpus a record's `coverage.corpus` names is the archive CONFORMANCE_LOCK.json pins, read with
tools/corpus_archive.py, or, when LOQUITUR_CORPUS_ROOTS names a corpus root (an extraction of an
archive, or a source tree built as the archive build builds one), the first root it names. No network is
used.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = "docs/specification"
INVENTORY = "docs/traceability/requirements.json"
RULE_TABLES = "docs/traceability/rule-tables.json"
RENDERED = "docs/traceability/README.md"
LOCK = "CONFORMANCE_LOCK.json"
ROOTS_ENV = "LOQUITUR_CORPUS_ROOTS"
INVENTORY_SCHEMA = "loquitur.requirements_inventory.v1"
RULE_TABLES_SCHEMA = "loquitur.rule_tables.v1"

# The parts, by file name, and the code of each identifier. A code is fixed by the file name, not
# by the part number, so that a part added to the document map moves no identifier.
DOC_CODES = {
    "introduction.md": "INT",
    "public-private-boundary.md": "PPB",
    "verification-checks.md": "CHK",
    "canonicalization-and-hashing.md": "CAN",
    "bundle-objects.md": "BND",
    "signing-envelope-v2.md": "SIG",
    "cryptographic-capabilities.md": "CRY",
    "registry-entry.md": "ENT",
    "registry-link.md": "LNK",
    "trust-registry-authorization.md": "TRA",
    "trust-root.md": "ROOT",
    "verification-vocabularies.md": "VOC",
    "reason-codes.md": "RC",
    "verdict-grounds.md": "VG",
    "report-contract.md": "RPT",
    "anchor-commitment.md": "ANC",
    "threat-model.md": "TM",
    "conformance-testing.md": "CT",
    "document-contracts.md": "DC",
}
BINDING_KEYWORDS = ("MUST NOT", "MUST", "REQUIRED", "SHALL NOT", "SHALL")
ADVISORY_KEYWORDS = ("SHOULD NOT", "SHOULD", "NOT RECOMMENDED", "RECOMMENDED", "MAY", "OPTIONAL")
# Sections that state no requirement although they carry the key words: the key-word boilerplate.
EXCLUDED_SECTIONS = {("introduction.md", "4.1")}
KINDS = ("keyword", "advisory", "row")
BINDS = ("verifier", "producer", "operator", "implementation", "document")
EXCLUSION_CLASSES = ("producer-side", "reserved", "host-dependent", "not-observable", "restatement", "governance")
STATUSES = ("active", "retired")
IDENTIFIER = re.compile(r"REQ-(?P<doc>[A-Z]+)-(?P<number>[0-9]{3})")
_SEPARATOR_ROW = re.compile(r"\s*\|(\s*:?-{3,}:?\s*\|)+\s*")
# A key word is a word of its own: REQUIRED inside the code REQUIRED_CLAIMS_PRESENT is not one.
_KEYWORD = {
    word: re.compile(r"(?<![A-Za-z0-9_])" + word.replace(" ", r"\s+") + r"(?![A-Za-z0-9_])")
    for word in BINDING_KEYWORDS + ADVISORY_KEYWORDS
}


def collapse(text: str) -> str:
    """Whitespace collapsed to single spaces, as a locator is compared."""
    return " ".join(text.split())


def keyword_of(sentence: str) -> tuple[str, str] | None:
    """(kind, the strongest key word) of a sentence, or None when it carries none.

    A key word counts only in capitals; one set in bold or in a code span means the same
    (introduction.md section 4.1).
    """
    plain = sentence.replace("*", "").replace("`", "")
    # A key word named in quotation marks, as the conventions name "MUST", is mentioned, not used.
    plain = re.sub(r'"(?:' + "|".join(BINDING_KEYWORDS + ADVISORY_KEYWORDS) + r')"', "", plain)
    for word in BINDING_KEYWORDS:
        if _KEYWORD[word].search(plain):
            return "keyword", word
    for word in ADVISORY_KEYWORDS:
        if _KEYWORD[word].search(plain):
            return "advisory", word
    return None


# ---- sections -------------------------------------------------------------------------------------


@dataclass
class Section:
    document: str
    id: str
    title: str
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def section_id(heading: str) -> str:
    """The identifier of a section, from its heading without the leading #'s.

    A numbered section is its number ("6", "4.1"); a section named by an identifier of its own is
    that identifier ("A1", "VG-1"); any other section is its title.
    """
    match = re.match(r"(?P<number>[0-9]+(?:\.[0-9]+)*)\.?\s", heading + " ")
    if match:
        return match.group("number")
    match = re.match(r"(?P<name>[A-Z]+-?[0-9]+)\s+[—-]", heading)
    if match:
        return match.group("name")
    return heading.strip()


def sections(document: str, text: str) -> list[Section]:
    """The sections of a part: the preamble before the first `## ` heading, then one per heading."""
    found = [Section(document, "preamble", "preamble")]
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and re.match(r"#{2,6} ", line):
            heading = line.lstrip("#").strip()
            found.append(Section(document, section_id(heading), heading))
            continue
        found[-1].lines.append(line)
    return found


def read_parts(root: Path = ROOT) -> dict[str, list[Section]]:
    return {name: sections(name, (root / SPECIFICATION / name).read_text(encoding="utf-8")) for name in DOC_CODES}


# ---- sentences ------------------------------------------------------------------------------------

_LIST_ITEM = re.compile(r"^\s*(?:[-*]|[0-9]+\.)\s+")
# A sentence ends at ".", "!" or "?" (after an optional closing quote, bracket or emphasis mark)
# followed by white space and a character that can begin a sentence. "e.g." and "i.e." never end
# one.
_SENTENCE_END = re.compile(r"(?<!\be\.g)(?<!\bi\.e)(?<=[.!?])(?:[\"')\]*]*)\s+(?=[A-Z`\"(\[*0-9])")


def paragraphs(section: Section) -> list[str]:
    """The prose of a section as paragraphs, each list item its own, whitespace collapsed.

    Fenced code and table rows are not prose. A block quote is prose with its marks removed.
    """
    out: list[list[str]] = []
    current: list[str] = []
    fenced = False

    def close() -> None:
        nonlocal current
        if current:
            out.append(current)
        current = []

    for raw in section.lines:
        if raw.startswith("```"):
            close()
            fenced = not fenced
            continue
        if fenced:
            continue
        line = raw
        if line.lstrip().startswith(">"):
            line = re.sub(r"^\s*>\s?", "", line)
        if not line.strip() or line.lstrip().startswith("|") or line.strip() == "---":
            close()
            continue
        if _LIST_ITEM.match(line):
            close()
            line = _LIST_ITEM.sub("", line, count=1)
        current.append(line.strip())
    close()
    return [collapse(" ".join(lines)) for lines in out]


def split_sentences(paragraph: str) -> list[str]:
    parts = []
    start = 0
    for match in _SENTENCE_END.finditer(paragraph):
        end = match.start() + len(match.group(0).rstrip())
        parts.append(paragraph[start:end].strip())
        start = match.end()
    parts.append(paragraph[start:].strip())
    return [part for part in parts if part]


@dataclass(frozen=True)
class Sentence:
    document: str
    section: str
    text: str
    kind: str
    keyword: str


def keyword_sentences(parts: dict[str, list[Section]]) -> list[Sentence]:
    """Every sentence of tier K: carries a key word, outside the excluded sections."""
    found = []
    for document, part in parts.items():
        for section in part:
            if (document, section.id) in EXCLUDED_SECTIONS:
                continue
            for paragraph in paragraphs(section):
                for sentence in split_sentences(paragraph):
                    marked = keyword_of(sentence)
                    if marked is not None:
                        found.append(Sentence(document, section.id, sentence, *marked))
    return found


def section_of(parts: dict[str, list[Section]], document: str, section: str) -> Section | None:
    matches = [s for s in parts.get(document, []) if s.id == section]
    return matches[0] if len(matches) == 1 else None


def section_prose(section: Section) -> str:
    return " ".join(paragraphs(section))


# ---- rule tables ----------------------------------------------------------------------------------


def _cells(line: str) -> list[str]:
    parts = re.split(r"(?<!\\)\|", line.strip())
    return [part.strip().replace("\\|", "|") for part in parts[1:-1]]


def tables_of(section: Section) -> list[tuple[list[str], list[list[str]]]]:
    lines = section.lines
    found = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("|") and index + 1 < len(lines) and _SEPARATOR_ROW.fullmatch(lines[index + 1]):
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


def _strip_code(cell: str) -> str:
    cell = cell.strip()
    if len(cell) >= 2 and cell.startswith("`") and cell.endswith("`") and cell.count("`") == 2:
        return cell[1:-1]
    return cell


def rule_rows(parts: dict[str, list[Section]], table: dict) -> list[str]:
    """The natural keys of the rows of one listed rule table, in document order.

    `kind` `table`: the rows of the one table of the section whose header is `header`, keyed by the
    cell of column `key` (a code span unwrapped). `kind` `list`: the items of the section's numbered
    list, keyed by their number. `kind` `headings`: the subsections of the section whose identifier
    matches `pattern`, keyed by that identifier.
    """
    document, kind = table["document"], table["kind"]
    if kind == "headings":
        pattern = re.compile(table["pattern"])
        return [s.id for s in parts[document] if pattern.fullmatch(s.id)]
    section = section_of(parts, document, table["section"])
    if section is None:
        raise ValueError(f"{table['id']}: {document} has no single section {table['section']}")
    if kind == "list":
        return [m.group(1) for m in (re.match(r"^([0-9]+)\.\s", line) for line in section.lines) if m]
    matching = [rows for header, rows in tables_of(section) if header == table["header"]]
    if len(matching) != 1:
        raise ValueError(
            f"{table['id']}: {document} section {table['section']} has {len(matching)} tables headed {table['header']}"
        )
    column = table["header"].index(table["key"])
    return [_strip_code(row[column]) for row in matching[0]]


def unlisted_keyword_cells(parts: dict[str, list[Section]], tables: dict) -> list[tuple[str, str, str]]:
    """Cells of tables rule-tables.json does not list that use a binding key word.

    A cell that quotes another document (a key word inside quotation marks, as the rows of
    document-contracts.md cite their sources) does not use it.
    """
    listed = {(t["document"], t["section"], tuple(t["header"])) for t in tables["tables"] if t["kind"] == "table"}
    found = []
    for document, part in parts.items():
        for section in part:
            for header, rows in tables_of(section):
                if (document, section.id, tuple(header)) in listed:
                    continue
                for row in rows:
                    for cell in row:
                        unquoted = re.sub(r'"[^"]*"', "", cell.replace("**", ""))
                        marked = keyword_of(unquoted)
                        if marked is not None and marked[0] == "keyword":
                            found.append((document, section.id, cell))
    return found


def read_rule_tables(root: Path = ROOT) -> dict:
    return json.loads((root / RULE_TABLES).read_text(encoding="utf-8"))


def read_inventory(root: Path = ROOT) -> dict:
    return json.loads((root / INVENTORY).read_text(encoding="utf-8"))


# ---- the corpus -----------------------------------------------------------------------------------

# The declaration files of the corpus that conformance-testing.md section 6 makes binding, and how a
# case of each is named after "#": a run name, or the `id`, `name` or `fixture` of a case.
BINDING_DECLARATIONS = (
    "verify.json",
    "additional-negatives/expected.json",
    "bundles/manifest.json",
    "schema-negative/manifest.json",
    "schema-valid/expected.json",
    "canonicalization.json",
    "canonicalization_unicode.json",
    "jcs-numeric.json",
    "signature.json",
    "signature_payload_version.json",
    "summary-checks/expected.json",
)


def _case_names(value: object) -> set[str]:
    names: set[str] = set()
    lists = (
        [value]
        if isinstance(value, list)
        else [v for v in value.values() if isinstance(v, list)]
        if isinstance(value, dict)
        else []
    )
    for items in lists:
        for item in items:
            if isinstance(item, dict):
                for key in ("id", "name", "fixture"):
                    if isinstance(item.get(key), str):
                        names.add(item[key])
                        break
    return names


def corpus_entries(files: dict[str, bytes]) -> set[str]:
    """Every binding name a coverage entry may cite: `FILE` for a whole binding file and `FILE#CASE`.

    `files` maps a path under `vectors/` to its bytes.
    """
    entries: set[str] = set()
    for name in BINDING_DECLARATIONS:
        if name not in files:
            continue
        value = json.loads(files[name].decode("utf-8"))
        entries.add(name)
        cases = set(value) if name == "verify.json" else _case_names(value)
        entries.update(f"{name}#{case}" for case in cases)
    return entries


def corpus_files(root: Path = ROOT) -> tuple[str, dict[str, bytes]]:
    """(where the corpus was read, its files under vectors/ by path).

    The first root LOQUITUR_CORPUS_ROOTS names, when it is set; else the archive
    CONFORMANCE_LOCK.json pins.
    """
    roots = [part for part in os.environ.get(ROOTS_ENV, "").split(os.pathsep) if part.strip()]
    if roots:
        base = Path(roots[0]) / "vectors"
        files = {
            path.relative_to(base).as_posix(): path.read_bytes()
            for path in base.rglob("*")
            if path.is_file() and path.relative_to(base).as_posix() in BINDING_DECLARATIONS
        }
        return str(Path(roots[0])), files
    if str(root / "tools") not in sys.path:
        sys.path.insert(0, str(root / "tools"))
    import corpus_archive

    lock = json.loads((root / LOCK).read_text(encoding="utf-8"))
    members = corpus_archive.members_of((root / lock["artifact"]).read_bytes())
    prefix = corpus_archive.PREFIX + "vectors/"
    files = {
        name[len(prefix) :]: data
        for name, data in members.items()
        if name.startswith(prefix) and name[len(prefix) :] in BINDING_DECLARATIONS
    }
    return lock["artifact"], files


# ---- the invariants -------------------------------------------------------------------------------


def _active(inventory: dict) -> list[dict]:
    return [record for record in inventory["requirements"] if record["status"] == "active"]


def record_problems(inventory: dict) -> list[str]:
    """Each record has the members, values and identifier form the inventory defines."""
    problems = []
    for record in inventory["requirements"]:
        rid = record.get("id", "?")
        match = IDENTIFIER.fullmatch(rid)
        if match is None:
            problems.append(f"{rid}: not an identifier REQ-<DOC>-<NNN>")
            continue
        document = record.get("document")
        if DOC_CODES.get(document) != match.group("doc"):
            problems.append(f"{rid}: the code does not name {document}")
        if record.get("kind") not in KINDS:
            problems.append(f"{rid}: kind {record.get('kind')!r}")
        if record.get("binds") not in BINDS:
            problems.append(f"{rid}: binds {record.get('binds')!r}")
        if record.get("status") not in STATUSES:
            problems.append(f"{rid}: status {record.get('status')!r}")
        if record.get("status") == "retired" and not record.get("retired_in"):
            problems.append(f"{rid}: retired without retired_in")
        exclusion = record.get("exclusion")
        if exclusion is not None and (exclusion.get("class") not in EXCLUSION_CLASSES or not exclusion.get("reason")):
            problems.append(f"{rid}: an exclusion needs a class of {EXCLUSION_CLASSES} and a reason")
        coverage = record.get("coverage", {})
        if sorted(coverage) != ["corpus", "static", "suites"]:
            problems.append(f"{rid}: coverage names {sorted(coverage)}")
        locator = record.get("locator", {})
        if record.get("kind") == "row" and locator.get("kind") != "row":
            problems.append(f"{rid}: a row record needs a row locator")
        if record.get("kind") != "row" and locator.get("kind") != "sentence":
            problems.append(f"{rid}: a sentence record needs a sentence locator")
    return problems


def identifier_problems(inventory: dict) -> list[str]:
    """Identifiers are unique and contiguous per code from 001: none deleted, none reused."""
    problems = []
    by_code: dict[str, list[int]] = {}
    seen: set[str] = set()
    for record in inventory["requirements"]:
        rid = record["id"]
        if rid in seen:
            problems.append(f"{rid} is used twice")
        seen.add(rid)
        match = IDENTIFIER.fullmatch(rid)
        if match:
            by_code.setdefault(match.group("doc"), []).append(int(match.group("number")))
    for code, numbers in sorted(by_code.items()):
        if sorted(numbers) != list(range(1, len(numbers) + 1)):
            problems.append(f"REQ-{code}: the numbers are not 001 to {len(numbers):03d} with none missing")
    return problems


def locator_problems(inventory: dict, parts: dict[str, list[Section]], tables: dict) -> list[str]:
    """Every active locator resolves exactly once in the section, or table, it names."""
    problems = []
    table_rows = {table["id"]: rule_rows(parts, table) for table in tables["tables"]}
    for record in _active(inventory):
        locator = record["locator"]
        rid = record["id"]
        if locator["kind"] == "row":
            rows = table_rows.get(locator["table"])
            if rows is None:
                problems.append(f"{rid}: no listed table {locator['table']}")
            elif rows.count(locator["key"]) != 1:
                problems.append(
                    f"{rid}: table {locator['table']} has {rows.count(locator['key'])} rows keyed {locator['key']!r}"
                )
            continue
        section = section_of(parts, record["document"], record["section"])
        if section is None:
            problems.append(f"{rid}: {record['document']} has no single section {record['section']}")
            continue
        count = section_prose(section).count(collapse(locator["text"]))
        if count != 1:
            problems.append(
                f"{rid}: its sentence occurs {count} times in {record['document']} section {record['section']}"
            )
    return problems


def claim_problems(inventory: dict, parts: dict[str, list[Section]], tables: dict) -> list[str]:
    """Every sentence of tier K and every row of every listed table is claimed by exactly one active record."""
    problems = []
    active = _active(inventory)
    for sentence in keyword_sentences(parts):
        claimed = [
            r["id"]
            for r in active
            if r["locator"]["kind"] == "sentence"
            and r["document"] == sentence.document
            and r["section"] == sentence.section
            and collapse(r["locator"]["text"]) in sentence.text
        ]
        if len(claimed) != 1:
            problems.append(
                f"{sentence.document} section {sentence.section}: {len(claimed)} records claim the sentence"
                f" {sentence.text[:90]!r}{' (' + ', '.join(claimed) + ')' if claimed else ''}"
            )
    for document, section, cell in unlisted_keyword_cells(parts, tables):
        problems.append(
            f"{document} section {section}: a table rule-tables.json does not list carries a key word: {cell[:90]!r}"
        )
    for table in tables["tables"]:
        for key in rule_rows(parts, table):
            claimed = [
                r["id"]
                for r in active
                if r["locator"]["kind"] == "row" and r["locator"]["table"] == table["id"] and r["locator"]["key"] == key
            ]
            if len(claimed) != 1:
                problems.append(f"table {table['id']} row {key!r}: {len(claimed)} records claim it")
    return problems


def coverage_problems(inventory: dict, entries: set[str], where: str) -> list[str]:
    """Every corpus entry exists, as a binding declaration, in the corpus read."""
    problems = []
    for record in _active(inventory):
        for entry in record["coverage"]["corpus"]:
            if entry not in entries:
                problems.append(f"{record['id']}: {entry} is not a binding declaration of {where}")
    return problems


def gap_problems(inventory: dict) -> list[str]:
    """A binding record is covered, excluded, or listed as not tested with its known limit."""
    problems = []
    for record in _active(inventory):
        if record["kind"] == "advisory":
            continue
        coverage, exclusion = record["coverage"], record["exclusion"]
        known = record.get("known_limit")
        if not any(coverage.values()) and exclusion is None and not known:
            problems.append(f"{record['id']}: no coverage, no exclusion and no known limit")
        if known and (any(coverage.values()) or exclusion is not None):
            problems.append(f"{record['id']}: a known limit is for a record with no coverage and no exclusion")
    return problems


def floor_problems(inventory: dict) -> list[str]:
    covered = sum(1 for record in _active(inventory) if record["coverage"]["corpus"])
    floor = inventory["corpus_covered_floor"]
    if covered < floor:
        return [f"{covered} active records have corpus coverage, fewer than the floor {floor}"]
    return []


def classify(record: dict) -> str:
    """Where a record stands for the list of rules without a vector.

    `vector`: the corpus covers it. `excluded`: an exclusion says why no vector can. `suites`:
    tested only in an implementation's suite or by a static check here. `untested`: none of these,
    and listed as a known limit. `advisory`: a SHOULD or MAY, with no obligation.
    """
    if record["kind"] == "advisory":
        return "advisory"
    if record["coverage"]["corpus"]:
        return "vector"
    if record["exclusion"] is not None:
        return "excluded"
    if record["coverage"]["static"] or record["coverage"]["suites"]:
        return "suites"
    return "untested"


def suite_problems(inventory: dict, workspace: Path) -> tuple[list[str], list[str]]:
    """(problems, absent repositories) for `coverage.suites` and `coverage.static` entries.

    A suite entry is `<repository>:<path>` or `<repository>:<path>::<test name>`; a static entry is a
    path of this repository with the same optional test name. The file must exist and, when a test
    is named, define it.
    """
    problems: list[str] = []
    absent: set[str] = set()
    for record in _active(inventory):
        cited = [("loquitur-protocol:" + entry) for entry in record["coverage"]["static"]] + list(
            record["coverage"]["suites"]
        )
        for entry in cited:
            repository, _, rest = entry.partition(":")
            path, _, test = rest.partition("::")
            base = ROOT if repository == "loquitur-protocol" else workspace / repository
            if not base.is_dir():
                absent.add(repository)
                continue
            target = base / path
            if not target.is_file():
                problems.append(f"{record['id']}: {entry} names no file")
                continue
            if test and test not in target.read_text(encoding="utf-8"):
                problems.append(f"{record['id']}: {entry} names no test {test}")
    return problems, sorted(absent)


def all_problems(root: Path = ROOT) -> list[str]:
    inventory, tables, parts = read_inventory(root), read_rule_tables(root), read_parts(root)
    where, files = corpus_files(root)
    return (
        record_problems(inventory)
        + identifier_problems(inventory)
        + locator_problems(inventory, parts, tables)
        + claim_problems(inventory, parts, tables)
        + coverage_problems(inventory, corpus_entries(files), where)
        + gap_problems(inventory)
        + floor_problems(inventory)
    )


def summary(inventory: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in _active(inventory):
        counts[classify(record)] = counts.get(classify(record), 0) + 1
    return counts


def iter_records(inventory: dict) -> Iterable[dict]:
    return iter(inventory["requirements"])


if __name__ == "__main__":
    found = all_problems()
    for problem in found:
        print(problem)
    print(f"requirements inventory: {len(found)} problems; {summary(read_inventory())}")
    raise SystemExit(1 if found else 0)
