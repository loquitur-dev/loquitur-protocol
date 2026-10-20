"""The normative artifacts are owned here, and the manifest that says so must be true.

docs/specification/README.md states in prose that this repository owns the schemas, the
reason-code catalog and the compatibility classes, and that every other copy is a mirror.
Prose is not a check. These tests are the check, and they are deliberately split the same
way the tool is: what can be verified from this repository alone always runs, and what
needs a sibling checkout skips when it is absent rather than pretending to have passed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
TOOL = ROOT / "tools/check_normative_mirrors.py"
MANIFEST = ROOT / "docs/specification/NORMATIVE_ARTIFACTS.json"
REQUIRE_SIBLINGS_ENV = "LOQUITUR_REQUIRE_SIBLINGS"


def _absent(message: str, required_message: str | None = None) -> None:
    """Skip for an absent sibling, or fail when the workspace says every sibling is here.

    A contributor with this repository alone should not be blocked by a checkout they do not
    have. A workspace that assembles every repository sets LOQUITUR_REQUIRE_SIBLINGS, and
    there the same absence is a failed checkout: skipping would report a check that did not
    run as one that passed. `required_message` is for a skip reason that must not name what
    is absent: the failure is reported only where every sibling is required, and may name it.
    """
    if os.environ.get(REQUIRE_SIBLINGS_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        pytest.fail(f"{REQUIRE_SIBLINGS_ENV} is set, but {required_message or message}")
    pytest.skip(message)


def run_tool(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.pop("LOQUITUR_REQUIRE_SIBLINGS", None)
    environment.update(env or {})
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**environment, "PYTHONIOENCODING": "utf-8"},
    )


def test_manifest_exists_and_declares_something() -> None:
    """An empty manifest satisfies every comparison, so emptiness is itself a failure."""
    assert MANIFEST.is_file(), "the normative artifacts manifest is missing; run the tool with --write"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["owner"] == "loquitur-protocol"
    assert manifest["artifacts"], "the manifest declares no artifacts; nothing would ever be compared"
    for artifact in manifest["artifacts"]:
        assert artifact["mirrors"], f"{artifact['path']} declares no mirror, so nothing follows it"


def test_manifest_matches_the_files_it_describes() -> None:
    """Self-consistency. This needs no sibling and must never skip."""
    result = run_tool()
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_mirror_matches_its_source() -> None:
    """The mirrors, when the siblings are here.

    Skips rather than fails when a sibling is absent: a contributor working on this
    repository alone should not be blocked by a checkout they do not have.
    LOQUITUR_REQUIRE_SIBLINGS, set where every sibling is checked out, is what turns this from
    documentation into a gate: for the tool it runs, and, since the variable is also read
    here, for this test's own skip.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    repositories = {m["repository"] for a in manifest["artifacts"] for m in a["mirrors"]}
    missing = sorted(name for name in repositories if not (WORKSPACE / name).is_dir())
    if missing:
        _absent("; ".join(_absent_sibling_message(name) for name in missing))
    result = run_tool(env={"LOQUITUR_REQUIRE_SIBLINGS": "1"})
    assert result.returncode == 0, result.stdout + result.stderr


def _absent_sibling_message(repository: str) -> str:
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_normative_mirrors", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.absent_sibling_message(repository)


def test_the_absent_conformance_note_claims_only_the_comparisons_the_release_gate_makes() -> None:
    """The note for an absent loquitur-conformance names exactly the artifacts it mirrors that the
    archive does not carry.

    The release gate compares the archive's copies with this repository for the files
    tools/corpus_archive.py places in it, and for no other. A note saying every mirrored artifact
    travels in the archive claims a comparison for a file the gate never reads.
    """
    import importlib.util

    loaded = {}
    for name, path in (("check_normative_mirrors", TOOL), ("corpus_archive", ROOT / "tools/corpus_archive.py")):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault(spec.name, module)
        spec.loader.exec_module(module)
        loaded[name] = module
    mirrors, archive = loaded["check_normative_mirrors"], loaded["corpus_archive"]
    mirrored = {rel for rel, copies in mirrors.OWNED if any(repo == "loquitur-conformance" for repo, _ in copies)}
    carried = set(archive.PROTOCOL_COPIES) | {
        rel for rel, _ in mirrors.OWNED if rel.startswith(archive.SCHEMA_COPIES_DIRECTORY)
    }
    absent = mirrored - carried
    assert mirrored & carried and absent, "the note would have nothing to tell apart"
    note = mirrors.ABSENT_SIBLING_NOTES["loquitur-conformance"]
    for rel in sorted(mirrored):
        assert (rel in note) == (rel in absent), (
            f"{rel}: the archive {'does not carry' if rel in absent else 'carries'} it, and the note "
            f"{'does not name' if rel in absent else 'names'} it"
        )


def test_an_absent_conformance_repository_is_not_presented_as_a_prerequisite(tmp_path: Path) -> None:
    """What a reader of a published copy sees: this repository alone, and no conformance repository.

    "is not checked out" alone would read as something the reader lacks. Both the tool's SKIP
    line and this module's skip reason say that loquitur-conformance is not published and that
    the archive carries its copies of what the corpus reads. Read from the output of a separate tool run and a
    separate pytest run in a scratch layout, not from the strings.
    """
    protocol = _scratch_protocol(tmp_path)
    (protocol / "tests").mkdir()
    (protocol / "tests" / "test_normative_mirrors.py").write_bytes(Path(__file__).read_bytes())
    note = "loquitur-conformance is not checked out beside this repository; it is not published"

    tool = _run_scratch(protocol)
    assert tool.returncode == 0, tool.stdout + tool.stderr
    assert "SKIP  " + note in tool.stdout, tool.stdout

    environment = dict(os.environ)
    environment.pop("LOQUITUR_REQUIRE_SIBLINGS", None)
    environment.pop("PYTEST_ADDOPTS", None)
    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-rs",
            "-p",
            "no:cacheprovider",
            "tests/test_normative_mirrors.py::test_every_mirror_matches_its_source",
        ],
        cwd=protocol,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**environment, "PYTHONIOENCODING": "utf-8"},
    )
    output = tests.stdout + tests.stderr
    assert "1 skipped" in output, output
    assert note in output, output
    assert "the archive in conformance/ carries its copies" in output, output


def test_a_diverging_mirror_is_rejected(tmp_path: Path) -> None:
    """The gate must fail when a mirror drifts, or it is decoration.

    Verified against a copied workspace rather than the real one: a test that mutates a
    sibling repository to prove a point can leave it mutated when it fails.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    artifact = next(a for a in manifest["artifacts"] if a["mirrors"][0]["repository"] == "loquitur-schemas")
    mirror_rel = artifact["mirrors"][0]["path"]
    source = WORKSPACE / "loquitur-schemas" / mirror_rel
    if not source.is_file():
        _absent("loquitur-schemas is not checked out")

    workspace = tmp_path / "workspace"
    (workspace / "loquitur-protocol").mkdir(parents=True)
    for rel in ("tools", "docs"):
        _copytree(ROOT / rel, workspace / "loquitur-protocol" / rel)
    _copy_prose_outside_docs(workspace / "loquitur-protocol")
    target = workspace / "loquitur-schemas" / mirror_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes() + b"\n")

    result = subprocess.run(
        [sys.executable, str(workspace / "loquitur-protocol/tools/check_normative_mirrors.py")],
        cwd=workspace / "loquitur-protocol",
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        encoding="utf-8",
    )
    assert result.returncode == 1, "a diverging mirror was accepted:\n" + result.stdout + result.stderr
    assert "mirror must follow the source" in (result.stdout + result.stderr)


def _copytree(src: Path, dst: Path) -> None:
    import shutil

    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def _scratch_protocol(tmp_path: Path) -> Path:
    """A copy of this repository's tools, docs and vocabularies inside an otherwise empty workspace."""
    protocol = tmp_path / "workspace" / "loquitur-protocol"
    protocol.mkdir(parents=True)
    # vocabularies/ holds the registered vocabularies, artifacts this repository owns outside docs/.
    for rel in ("tools", "docs", "vocabularies"):
        _copytree(ROOT / rel, protocol / rel)
    _copy_prose_outside_docs(protocol)
    return protocol


def _copy_prose_outside_docs(protocol: Path) -> None:
    """The tool also checks the prose digest list, which binds GOVERNANCE.md and PROTOCOL_RELEASE.json beside docs/."""
    for rel in ("GOVERNANCE.md", "PROTOCOL_RELEASE.json"):
        (protocol / rel).write_bytes((ROOT / rel).read_bytes())


def _run_scratch(protocol: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.pop("LOQUITUR_REQUIRE_SIBLINGS", None)
    return subprocess.run(
        [sys.executable, str(protocol / "tools/check_normative_mirrors.py"), *args],
        cwd=protocol,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**environment, "PYTHONIOENCODING": "utf-8"},
    )


def _edit_manifest(protocol: Path, edit) -> None:
    path = protocol / "docs/specification/NORMATIVE_ARTIFACTS.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    edit(manifest)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def test_a_hand_edited_mirror_declaration_is_rejected(tmp_path: Path) -> None:
    """A mirror pointed at this repository's own file, with the real mirror diverged, is refused.

    The mirror half follows whatever the manifest says, so it would compare the protocol's file
    with itself and never read the diverged loquitur-schemas copy; the hand edit of the manifest
    is what fails.
    """
    protocol = _scratch_protocol(tmp_path)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    artifact = next(a for a in manifest["artifacts"] if a["mirrors"][0]["repository"] == "loquitur-schemas")
    diverged = tmp_path / "workspace" / "loquitur-schemas" / artifact["mirrors"][0]["path"]
    diverged.parent.mkdir(parents=True, exist_ok=True)
    diverged.write_bytes((ROOT / artifact["path"]).read_bytes() + b"\n")

    def point_at_self(document: dict) -> None:
        for entry in document["artifacts"]:
            if entry["path"] == artifact["path"]:
                entry["mirrors"] = [{"repository": "loquitur-protocol", "path": artifact["path"]}]

    _edit_manifest(protocol, point_at_self)
    result = _run_scratch(protocol)
    output = result.stdout + result.stderr
    assert result.returncode == 1, "a hand-edited mirror declaration was accepted:\n" + output
    assert artifact["path"] + ": manifest field 'mirrors'" in output


def test_a_hand_edited_byte_count_is_rejected(tmp_path: Path) -> None:
    protocol = _scratch_protocol(tmp_path)

    def wrong_bytes(document: dict) -> None:
        document["artifacts"][0]["bytes"] += 1

    _edit_manifest(protocol, wrong_bytes)
    result = _run_scratch(protocol)
    output = result.stdout + result.stderr
    assert result.returncode == 1, "a hand-edited byte count was accepted:\n" + output
    assert "manifest field 'bytes'" in output


def test_a_diverging_change_proposal_schema_mirror_is_rejected(tmp_path: Path) -> None:
    """One byte of drift in either copy of the change-proposal schema fails the binding."""
    protocol = _scratch_protocol(tmp_path)
    source = ROOT / "docs/specification/change-proposal.schema.json"
    mirror = tmp_path / "workspace" / "loquitur-conformance" / "governance" / "change-proposal.schema.json"
    mirror.parent.mkdir(parents=True)
    mirror.write_bytes(source.read_bytes() + b"\n")
    result = _run_scratch(protocol)
    output = result.stdout + result.stderr
    assert result.returncode == 1, "a diverging change-proposal schema mirror was accepted:\n" + output
    assert "loquitur-conformance:governance/change-proposal.schema.json" in output
    assert "mirror must follow the source" in output


def test_an_undeclared_normative_json_file_is_rejected(tmp_path: Path) -> None:
    """A JSON file under docs/specification/ that OWNED does not declare fails: discovery backs the list."""
    protocol = _scratch_protocol(tmp_path)
    newcomer = protocol / "docs/specification/schemas/undeclared_object.schema.json"
    newcomer.write_text('{"$schema": "https://json-schema.org/draft/2020-12/schema"}\n', encoding="utf-8")
    result = _run_scratch(protocol)
    output = result.stdout + result.stderr
    assert result.returncode == 1, "an undeclared normative JSON file was accepted:\n" + output
    assert "not declared in OWNED" in output
    assert "docs/specification/schemas/undeclared_object.schema.json" in output
