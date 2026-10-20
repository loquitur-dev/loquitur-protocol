"""Link every reference to a specification document to its file, and check that each one is linked.

The documents under docs/specification/ cite one another as "`report-contract.md` section 5.3".
On a host that renders Markdown, such as GitHub, a reader can follow a citation only when the
document name is a link. This tool turns each backtick reference to a document of that folder
into a relative link to the file, `[`report-contract.md`](report-contract.md)`, and leaves the
section number as text: a file-level link survives a heading change, and a renderer that knows
the section anchors adds the deep link itself, so no anchor is written into the source.

What is linked: a code span whose whole content is the file name of a Markdown document in
docs/specification/, outside fenced code blocks and outside headings. A code span that names a
file of another folder, such as `GOVERNANCE.md`, is left as it is.

    python tools/link_specification_references.py          link every reference in place
    python tools/link_specification_references.py --check  list the references that are not linked

Exit codes: 0 written or verified, 1 verification failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

SPECIFICATION = "docs/specification"

# A code span of one document name, not already the text of a link, and not part of a longer
# span: no backtick or opening bracket before it, no backtick or "](" after it.
_REFERENCE = re.compile(r"(?<![`\[])`([A-Za-z0-9][A-Za-z0-9._-]*\.md)`(?![`\]])")
_LINKED = re.compile(r"\[`([A-Za-z0-9][A-Za-z0-9._-]*\.md)`\]\(([^)\s]*)\)")
_FENCE = re.compile(r"^\s*(```|~~~)")


def documents(root: Path) -> set[str]:
    """The file names of the Markdown documents of the specification folder."""
    return {path.name for path in (root / SPECIFICATION).glob("*") if path.suffix.lower() == ".md" and path.is_file()}


def _prose_lines(text: str):
    """(index, line) of every line outside fenced code blocks that is not a heading."""
    fenced = False
    for index, line in enumerate(text.split("\n")):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced or line.startswith("#"):
            continue
        yield index, line


def link(text: str, names: set[str]) -> str:
    """``text`` with every unlinked reference to a document in ``names`` linked to its file."""
    lines = text.split("\n")
    for index, line in _prose_lines(text):
        lines[index] = _REFERENCE.sub(
            lambda match: f"[`{match.group(1)}`]({match.group(1)})" if match.group(1) in names else match.group(0),
            line,
        )
    return "\n".join(lines)


def problems(text: str, names: set[str]) -> list[str]:
    """Each reference to a document in ``names`` that is not linked, or linked to another target."""
    found = []
    for index, line in _prose_lines(text):
        for match in _REFERENCE.finditer(line):
            if match.group(1) in names:
                found.append(f"line {index + 1}: `{match.group(1)}` is not linked")
        for match in _LINKED.finditer(line):
            if match.group(1) in names and match.group(2) != match.group(1):
                found.append(f"line {index + 1}: `{match.group(1)}` links to {match.group(2)}, not to its file")
    return found


def check(root: Path) -> list[str]:
    """Every unlinked or mislinked reference in the specification folder, by file."""
    names = documents(root)
    errors = []
    for name in sorted(names):
        text = (root / SPECIFICATION / name).read_text(encoding="utf-8")
        errors.extend(f"{SPECIFICATION}/{name} {problem}" for problem in problems(text, names))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--check", action="store_true", help="list the references that are not linked and write nothing"
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.check:
        errors = check(root)
        for error in errors:
            print(error)
        if errors:
            print("run python tools/link_specification_references.py to link them")
            return 1
        print("specification references OK: every reference to a specification document is linked")
        return 0
    names = documents(root)
    changed = 0
    for name in sorted(names):
        path = root / SPECIFICATION / name
        text = path.read_text(encoding="utf-8")
        linked = link(text, names)
        if linked != text:
            path.write_bytes(linked.encode("utf-8"))
            changed += 1
    print(f"linked the references in {changed} document(s) of {SPECIFICATION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
