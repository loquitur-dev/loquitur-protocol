"""Citations of a reference implementation by definition name, resolved in a sibling checkout.

Several documents cite a reference implementation as `<module>.py::<name>`: a function, class or
constant defined at the top level of that module, or its docstring as `__doc__`. The modules are
not part of this repository. A citation by line is only true of one commit, which the published
copies of these repositories do not carry; a definition name stays resolvable in any checkout that
still defines it.

These helpers find the citations in a document and the definitions in a module's source, with the
source text of each definition, so that a test can require both that the definition exists and that
it still does what the document cites it for. A sibling that is not checked out skips the calling
test, and fails it instead when LOQUITUR_REQUIRE_SIBLINGS is set.

Not a test module: pytest collects test_*.py, and this is imported by them.
"""

from __future__ import annotations

import ast
import os
import re
import tomllib
from pathlib import Path

import pytest

CITATION = re.compile(r"`([A-Za-z0-9_]+\.py)::([A-Za-z_][A-Za-z0-9_]*)`")
# A release a citation note names: release `0.1.0` of `loquitur-verify-py`.
RELEASE = re.compile(r"release `(\d+\.\d+\.\d+)` of `(loquitur-[a-z-]+)`")
# The repositories a citation note may name. Each is checked out beside this one under
# its own name, so the name in the note is the directory to read.
CITED_REPOSITORIES = frozenset({"loquitur-verify-py", "loquitur-schemas"})
WORKSPACE = Path(__file__).resolve().parents[2]


def unavailable(message: str) -> None:
    """Skip for an absent sibling, or fail when the workspace requires every sibling."""
    __tracebackhide__ = True
    if os.environ.get("LOQUITUR_REQUIRE_SIBLINGS", "").strip().lower() in {"1", "true", "yes", "on"}:
        pytest.fail(f"LOQUITUR_REQUIRE_SIBLINGS is set, but {message}")
    pytest.skip(message)


def releases(text: str) -> list[tuple[str, str]]:
    """Every release ``text`` names, as (repository, version), in order."""
    return [(repository, version) for version, repository in RELEASE.findall(" ".join(text.split()))]


def checked_out_version(repository: str) -> str:
    """The version of the ``repository`` checkout beside this one, from its pyproject.toml.

    A published copy of a cited repository carries one release, and this is the version it
    declares, so a note that names a release is checked against the source it cites.
    """
    if repository not in CITED_REPOSITORIES:
        raise AssertionError(f"{repository} is not a repository a citation note may name")
    pyproject = WORKSPACE / repository / "pyproject.toml"
    if not pyproject.is_file():
        unavailable(f"{pyproject.parent} is not checked out beside this repository")
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


def citations(text: str) -> list[tuple[str, str]]:
    """Every `<module>.py::<name>` citation of ``text``, in order, repeats included."""
    return CITATION.findall(text)


def definitions(module: Path) -> dict[str, str]:
    """The top-level definitions of ``module``, each with its source text, and ``__doc__``."""
    if not module.is_file():
        unavailable(f"{module} is not checked out beside this repository")
    source = module.read_text(encoding="utf-8")
    tree = ast.parse(source)
    found = {"__doc__": ast.get_docstring(tree) or ""}
    for node in tree.body:
        segment = ast.get_source_segment(source, node) or ""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found[node.name] = segment
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = segment
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found[node.target.id] = segment
    return found
