"""The normative prose is bound by digest, and both release gates enforce the binding.

NORMATIVE_ARTIFACTS.json binds the JSON artifacts only, so a rewrite of the `bundle_id` row of
bundle-objects.md would leave every release artifact unchanged and every gate green without a
second binding. docs/specification/PROSE_DIGESTS.json binds the Markdown, tools/refresh_prose_digests.py
generates it, and tools/check_protocol_release.py and tools/check_normative_mirrors.py both
refuse a list that does not match the prose.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from conftest import tool

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "docs/specification/PROSE_DIGESTS.json"
GENERATOR = ROOT / "tools/refresh_prose_digests.py"
GATES = {
    "release": ["tools/check_protocol_release.py", "--root", "."],
    "mirrors": ["tools/check_normative_mirrors.py"],
}


def _generator():
    return tool("refresh_prose_digests")


def _copy_repository(tmp_path: Path) -> Path:
    target = tmp_path / "loquitur-protocol"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".venv", "venv"))
    return target


def _run_gate(copy: Path, gate: str) -> subprocess.CompletedProcess[str]:
    """The gate in ``copy``."""
    environment = dict(os.environ)
    # A copy has no siblings beside it; the mirror half skips, the prose half must not.
    environment.pop("LOQUITUR_REQUIRE_SIBLINGS", None)
    command = [sys.executable, *GATES[gate]]
    return subprocess.run(
        command,
        cwd=copy,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**environment, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )


def test_the_list_binds_every_normative_prose_file_and_nothing_else() -> None:
    """Anti-vacuity: a list that names nothing, or misses a document, binds nothing."""
    document = json.loads(LIST.read_text(encoding="utf-8"))
    assert document["schema_version"] == "loquitur.prose_digests.v1"
    listed = [entry["path"] for entry in document["files"]]
    expected = sorted(
        {
            p.relative_to(ROOT).as_posix()
            for p in (ROOT / "docs/specification").rglob("*")
            if p.suffix.lower() == ".md" and p.is_file()
        }
        | {"GOVERNANCE.md", "PROTOCOL_RELEASE.json", "docs/change-proposals.md"}
    )
    assert listed == expected
    assert len(listed) >= 20, listed
    assert "docs/specification/bundle-objects.md" in listed
    assert "docs/specification/README.md" in listed
    # The authoritative register of change proposals is bound as the specification is.
    assert "docs/change-proposals.md" in listed
    assert _generator().verify(ROOT) == []


def test_the_list_stays_outside_the_normative_artifacts_and_the_archive() -> None:
    """In NORMATIVE_ARTIFACTS.json the release gate would compare README.md with another repository's."""
    assert LIST.is_file(), "the prose digest list is missing"
    artifacts = json.loads((ROOT / "docs/specification/NORMATIVE_ARTIFACTS.json").read_text(encoding="utf-8"))
    paths = [artifact["path"] for artifact in artifacts["artifacts"]]
    assert not [p for p in paths if p.endswith(".md") or p.endswith("PROSE_DIGESTS.json")], paths
    lock = json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(ROOT / lock["artifact"]) as archive:
        assert not [n for n in archive.namelist() if n.endswith("PROSE_DIGESTS.json")]


def test_the_generator_check_passes_on_this_repository() -> None:
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "normative prose OK" in result.stdout


def test_a_byte_flip_in_any_listed_file_is_refused(tmp_path: Path) -> None:
    """Every listed file, one at a time, restored between flips."""
    generator = _generator()
    listed = [entry["path"] for entry in json.loads(LIST.read_text(encoding="utf-8"))["files"]]
    copy = tmp_path / "prose"
    for rel in [*listed, "docs/specification/PROSE_DIGESTS.json"]:
        (copy / rel).parent.mkdir(parents=True, exist_ok=True)
        (copy / rel).write_bytes((ROOT / rel).read_bytes())
    assert generator.verify(copy) == []
    undetected = []
    for rel in listed:
        original = (copy / rel).read_bytes()
        (copy / rel).write_bytes(bytes([original[0] ^ 0x01]) + original[1:])
        errors = generator.verify(copy)
        if not any(error.startswith(rel + " is ") for error in errors):
            undetected.append(rel)
        (copy / rel).write_bytes(original)
    assert not undetected, undetected
    assert generator.verify(copy) == []


def test_an_unlisted_normative_markdown_file_is_refused(tmp_path: Path) -> None:
    generator = _generator()
    copy = _copy_repository(tmp_path)
    (copy / "docs/specification/reason-codes/unlisted-note.md").write_text("# Unlisted\n", encoding="utf-8")
    errors = generator.verify(copy)
    assert any(
        error.endswith("nothing binds its bytes: docs/specification/reason-codes/unlisted-note.md") for error in errors
    ), errors


def test_a_markdown_file_with_an_upper_case_suffix_is_bound_on_every_host(tmp_path: Path) -> None:
    """The suffix is compared in lower case, not by a glob whose case rule is the filesystem's."""
    generator = _generator()
    copy = _copy_repository(tmp_path)
    (copy / "docs/specification/reason-codes/UPPER-NOTE.MD").write_text("# Upper\n", encoding="utf-8")
    assert "docs/specification/reason-codes/UPPER-NOTE.MD" in generator.covered_paths(copy)
    errors = generator.verify(copy)
    assert any(
        error.endswith("nothing binds its bytes: docs/specification/reason-codes/UPPER-NOTE.MD") for error in errors
    ), errors


def test_a_changed_byte_of_the_change_proposal_register_is_refused(tmp_path: Path) -> None:
    generator = _generator()
    copy = _copy_repository(tmp_path)
    assert generator.verify(copy) == []
    path = copy / "docs/change-proposals.md"
    data = path.read_bytes()
    assert b"| `LCP-0005` | breaking |" in data
    path.write_bytes(data.replace(b"| `LCP-0005` | breaking |", b"| `LCP-0005` | governance-only |", 1))
    errors = generator.verify(copy)
    assert any(error.startswith("docs/change-proposals.md is ") for error in errors), errors


def test_a_hand_edited_list_is_refused(tmp_path: Path) -> None:
    """Right digests in another form, and a list emptied to nothing, are both refused."""
    generator = _generator()
    copy = _copy_repository(tmp_path)
    path = copy / "docs/specification/PROSE_DIGESTS.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(
        json.dumps({**document, "files": document["files"][::-1]}, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    assert any("different form" in error for error in generator.verify(copy))
    path.write_text(json.dumps({**document, "files": []}, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert any("lists no files" in error for error in generator.verify(copy))
    path.unlink()
    assert any("is missing" in error for error in generator.verify(copy))


@pytest.mark.parametrize("gate", sorted(GATES))
def test_both_gates_refuse_a_changed_normative_sentence(tmp_path: Path, gate: str) -> None:
    """A rewrite of one row: `bundle_id` typed as an integer, with nothing else touched."""
    copy = _copy_repository(tmp_path)
    assert _run_gate(copy, gate).returncode == 0
    path = copy / "docs/specification/bundle-objects.md"
    data = path.read_bytes()
    assert b"string with a code point outside W" in data
    path.write_bytes(data.replace(b"string with a code point outside W", b"integer", 1))
    result = _run_gate(copy, gate)
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "docs/specification/bundle-objects.md is " in output, output


@pytest.mark.parametrize("gate", sorted(GATES))
def test_both_gates_refuse_any_changed_byte_of_the_release_file(
    tmp_path: Path, gate: str
) -> None:
    """PROTOCOL_RELEASE.json, one byte at a time: a non-claim, the owner, indentation, the last newline.

    The release gate reads some of its fields, and none of these; without the binding, each
    change would pass both gates.
    """
    copy = _copy_repository(tmp_path)
    path = copy / "PROTOCOL_RELEASE.json"
    original = path.read_bytes()
    positions = {
        "non-claim": original.index(b"not-a-release-candidate") + len("not-a-release-candidat"),
        "owner": original.index(b"loquitur-protocol-governance") + len("loquitur-protocol-governanc"),
        "indentation": original.index(b'\n  "approval_rule"') + 1,
        "last newline": len(original) - 1,
    }
    replacement = {"non-claim": b"f", "owner": b"f", "indentation": b"\t", "last newline": b" "}
    assert _run_gate(copy, gate).returncode == 0
    passed = []
    for name, index in positions.items():
        mutated = original[:index] + replacement[name] + original[index + 1 :]
        assert len(mutated) == len(original) and mutated != original
        path.write_bytes(mutated)
        result = _run_gate(copy, gate)
        if result.returncode != 1 or "PROTOCOL_RELEASE.json is " not in result.stdout + result.stderr:
            passed.append(name)
        path.write_bytes(original)
    assert not passed, passed
    assert _run_gate(copy, gate).returncode == 0


@pytest.mark.parametrize("gate", sorted(GATES))
def test_both_gates_refuse_an_unlisted_normative_markdown_file(
    tmp_path: Path, gate: str
) -> None:
    copy = _copy_repository(tmp_path)
    (copy / "docs/specification/unlisted-normative-note.md").write_text(
        "# Unlisted\n\nStatus: normative.\n", encoding="utf-8"
    )
    result = _run_gate(copy, gate)
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "nothing binds its bytes: docs/specification/unlisted-normative-note.md" in output, output
