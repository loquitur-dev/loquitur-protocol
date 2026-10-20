"""The two pages a first-time reader navigates by name every file they would look for.

docs/README.md is the table of contents of the specification, and docs/maintainers/REPOSITORY_LAYOUT.md is the
map of the tree. A specification page the table of contents omits is one an implementer may never
open, and a tracked file the map omits is one a reader cannot place. Both lists are hand-written,
so these tests derive what they must name from the files themselves.

The table of contents and the document map of introduction.md section 3 give the same parts, in
the same order, with the same kinds, and each kind is the status line its document opens with.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READING_ORDER = ROOT / "docs" / "README.md"
INTRODUCTION = ROOT / "docs" / "specification" / "introduction.md"
LAYOUT = ROOT / "docs" / "maintainers" / "REPOSITORY_LAYOUT.md"

# Directories the layout names as a whole rather than file by file, each with the line that names
# it. A file under one of them is accounted for by that line.
NAMED_AS_A_WHOLE = {
    "tests/": "tests/",
    "docs/traceability/": "traceability/",
    "docs/specification/schemas/": "schemas/",
    "docs/specification/reason-codes/": "reason-codes/",
    "docs/specification/registered-vocabularies/": "registered-vocabularies/",
    "vocabularies/": "vocabularies/",
    "conformance/": "loquitur-conformance-*.zip",
}
# The prose specification, which the layout names by pattern and docs/README.md names page by page.
SPECIFICATION_PAGES = re.compile(r"docs/specification/[^/]+\.md")
# The status lines a specification document may open with (introduction.md section 4.3).
STATUS_LINES = (
    "Status: normative.",
    "Status: informative.",
    "Status: reserved.",
    "Status: normative appendix, adds no rule.",
)


def _tracked() -> list[str]:
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout
    return sorted(name for name in listing.split("\0") if name)


def _layout_tree(text: str) -> str:
    match = re.search(r"```text\n(.*?)```", text, re.DOTALL)
    assert match, "docs/maintainers/REPOSITORY_LAYOUT.md has no tree block"
    return match.group(1)


def unnamed_in_reading_order(pages: list[str], reading_order: str) -> list[str]:
    """The specification pages docs/README.md does not name, as `specification/<page>`."""
    named = set(re.findall(r"`(specification/[^`]+\.md)`", reading_order))
    return [page for page in pages if page.removeprefix("docs/") not in named]


def unplaced_in_layout(tracked: list[str], layout: str) -> list[str]:
    """The tracked files the layout's tree neither names nor covers by a directory or pattern."""
    tree = _layout_tree(layout)
    entries = set(re.findall(r"[─]\s(\S+)", tree))
    missing = []
    for path in tracked:
        if SPECIFICATION_PAGES.fullmatch(path):
            continue
        if any(path.startswith(directory) for directory in NAMED_AS_A_WHOLE):
            continue
        if path.rsplit("/", 1)[-1] not in entries:
            missing.append(path)
    return missing


def test_the_table_of_contents_names_every_specification_page() -> None:
    pages = [path for path in _tracked() if SPECIFICATION_PAGES.fullmatch(path)]
    assert len(pages) >= 20, f"only {len(pages)} specification pages found; the check is thin"
    missing = unnamed_in_reading_order(pages, READING_ORDER.read_text(encoding="utf-8"))
    assert not missing, f"docs/README.md does not name {missing}"


def test_the_layout_places_every_tracked_file() -> None:
    layout = LAYOUT.read_text(encoding="utf-8")
    tree = _layout_tree(layout)
    for directory, line in NAMED_AS_A_WHOLE.items():
        assert line in tree, f"the layout covers {directory} as a whole but does not name it ({line!r})"
    tracked = _tracked()
    assert len(tracked) > 50, f"only {len(tracked)} tracked files found; the check is thin"
    missing = unplaced_in_layout(tracked, layout)
    assert not missing, f"docs/maintainers/REPOSITORY_LAYOUT.md does not place {missing}"


def test_an_omission_is_reported() -> None:
    """The two rules report a page or a file the lists leave out, so a pass above means something."""
    reading_order = READING_ORDER.read_text(encoding="utf-8")
    assert unnamed_in_reading_order(["docs/specification/bundle-objects.md"], reading_order) == []
    trimmed = reading_order.replace("`specification/bundle-objects.md`", "")
    assert unnamed_in_reading_order(["docs/specification/bundle-objects.md"], trimmed) == [
        "docs/specification/bundle-objects.md"
    ]
    layout = LAYOUT.read_text(encoding="utf-8")
    assert unplaced_in_layout(["requirements-dev.txt", "tests/test_x.py"], layout) == []
    assert unplaced_in_layout(["requirements-dev.txt"], layout.replace("requirements-dev.txt", "")) == [
        "requirements-dev.txt"
    ]


def _parts(text: str, link: bool) -> list[tuple[str, str, str]]:
    """(part, document, kind) of each row of the first table of ``text`` whose header begins with Part."""
    rows = []
    table = False
    for line in text.splitlines():
        if line.startswith("| Part | Document | Kind |"):
            table = True
            continue
        if table and line.startswith("| ---"):
            continue
        if table and line.startswith("|"):
            part, document, kind = (cell.strip() for cell in line.strip("|").split("|")[:3])
            if link:
                match = re.fullmatch(r"\[`specification/([^`]+)`\]\(specification/\1\)", document)
                assert match, f"docs/README.md does not link the part {part}: {document}"
            else:
                match = re.search(r"`([^`]+\.md)`", document)
                assert match, f"introduction.md names no document for part {part}: {document}"
            rows.append((part, match.group(1), kind))
        elif table:
            break
    return rows


def test_the_table_of_contents_is_the_document_map() -> None:
    contents = _parts(READING_ORDER.read_text(encoding="utf-8"), link=True)
    document_map = _parts(INTRODUCTION.read_text(encoding="utf-8"), link=False)
    assert len(contents) >= 20, f"only {len(contents)} parts found; the check is thin"
    assert contents == document_map, "docs/README.md and introduction.md section 3 give different parts"
    pages = sorted(
        path.removeprefix("docs/specification/") for path in _tracked() if SPECIFICATION_PAGES.fullmatch(path)
    )
    assert sorted(document for _, document, _ in contents) == pages


def test_every_specification_document_opens_with_its_status_line() -> None:
    kinds = {document: kind for _, document, kind in _parts(INTRODUCTION.read_text(encoding="utf-8"), link=False)}
    for path in _tracked():
        if not SPECIFICATION_PAGES.fullmatch(path):
            continue
        lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("# ") and lines[1] == "", f"{path} does not open with its title"
        assert lines[2] in STATUS_LINES, f"{path} does not open with a status line: {lines[2]!r}"
        assert sum(line in STATUS_LINES for line in lines) == 1, f"{path} has more than one status line"
        name = path.removeprefix("docs/specification/")
        assert lines[2] == "Status: " + kinds[name] + ".", f"{path} opens with {lines[2]!r}, the map says {kinds[name]}"
