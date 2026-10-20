from __future__ import annotations

import functools
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
VERIFIER = ROOT / "tools/verify_release_set.py"
POINTER = "RELEASE_SET_POINTER.json"
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


# The release set spans every repository, so these tests need the sibling checkouts beside
# this one. A single-repository clone, which is what CI gets and what a contributor gets,
# does not have them, and the verifier then reports every member as missing. That is the
# verifier working correctly on an incomplete workspace, not a defect, so the tests skip
# rather than fail.
#
# Skipping here would be dishonest on its own: a check that never runs is a check that does
# not exist. LOQUITUR_REQUIRE_SIBLINGS, set where every member is checked out, turns the same
# absence into a failure of the test.
#
# The manifest lists the members, and a repository it does not list is counted and never
# named, present or not. Skip unless EVERY member the manifest names is present, not merely
# more than one: this verifier compares pointers ACROSS the members the manifest names, and a
# subset, such as a release workspace with the published repositories, cannot answer the
# question. The verifier reports such a workspace as incomplete, correctly, and these tests
# are not the ones to assert it.
_MEMBERS = [p.name for p in WORKSPACE.iterdir() if p.is_dir() and (p / POINTER).is_file()] if WORKSPACE.is_dir() else []
_MANIFEST_MEMBERS = sorted(json.loads((ROOT / "release-set.json").read_text(encoding="utf-8")).get("members", {}))
_MISSING_MEMBERS = [name for name in _MANIFEST_MEMBERS if name not in _MEMBERS]


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_release_set", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PUBLISHED = sorted(_load_verifier().PUBLISHED_MEMBERS)
# The repositories of this workspace that carry a pointer and are not manifest members. Read
# from the checkout, so this file names none of them.
_OUTSIDE = sorted(set(_MEMBERS) - set(_MANIFEST_MEMBERS))
# Every repository checked out beside this one, pointer or not; read from the checkout too.
_SIBLINGS = (
    sorted(p.name for p in WORKSPACE.iterdir() if p.name.startswith("loquitur-") and p.is_dir())
    if WORKSPACE.is_dir()
    else []
)
# Every repository name that must never appear in output produced for a published layout.
UNPUBLISHED = sorted((set(_MANIFEST_MEMBERS) | set(_OUTSIDE) | set(_SIBLINGS)) - set(PUBLISHED))

# The skip reason is printed wherever this file runs, including in a published subset, so it
# follows the verifier's own rule: missing published members by name, the rest by count.
#
# A wrapper rather than a skipif mark, because a mark decides at import and cannot fail: under
# LOQUITUR_REQUIRE_SIBLINGS the same absence is a failure of the test, with the same reason.
def _needs_workspace(test):
    @functools.wraps(test)
    def guarded(*args, **kwargs):
        if _MISSING_MEMBERS:
            _absent(
                "release-set verification needs every repository the manifest names, in the parent "
                f"directory; missing {[n for n in _MISSING_MEMBERS if n in PUBLISHED]} and "
                f"{sum(1 for n in _MISSING_MEMBERS if n not in PUBLISHED)} unpublished member(s)."
            )
        return test(*args, **kwargs)

    return guarded


def run(workspace: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(VERIFIER), "--workspace", str(workspace), *args],
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def _clone_workspace(tmp_path: Path) -> Path:
    """Copy just the pointer files + manifest so the verifier has a full workspace."""
    dest = tmp_path / "ws"
    dest.mkdir()
    for repo in sorted(p for p in WORKSPACE.iterdir() if p.is_dir() and (p / POINTER).is_file()):
        (dest / repo.name).mkdir()
        shutil.copy2(repo / POINTER, dest / repo.name / POINTER)
    shutil.copy2(ROOT / "release-set.json", dest / "loquitur-protocol" / "release-set.json")
    return dest


@_needs_workspace
def test_release_set_pointers_and_manifest_are_coherent() -> None:
    # Complete by construction here, so absence of any member is a failure, not a warning.
    result = run(WORKSPACE, "--require-every-member")
    assert result.returncode == 0, result.stdout + result.stderr


@_needs_workspace
def test_the_release_set_declares_no_branch_input_and_reports_none_unverifiable() -> None:
    """No pointer declares a branch input no copy carries, so a run reports nothing UNVERIFIABLE."""
    manifest = json.loads((ROOT / "release-set.json").read_text(encoding="utf-8"))
    assert manifest["branch_inputs_declared"] == 0
    assert manifest["unverifiable_branch_inputs"] == []
    assert manifest["branch_inputs_present"] is False
    for member in manifest["members"].values():
        assert member["branch_input_status"] == "not_declared"
        assert member["branch_input_artifact"] is None
    result = run(WORKSPACE)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "UNVERIFIABLE" not in result.stdout + result.stderr
    assert "NOTHING TO VERIFY" not in result.stdout + result.stderr
    assert "not-a-claim-that-a-branch-input-was-completed-or-verified" in manifest["non_claims"]


@_needs_workspace
def test_require_branch_inputs_fails_a_pointer_that_declares_none() -> None:
    result = run(WORKSPACE, "--require-branch-inputs")
    assert result.returncode == 1
    assert "NOTHING TO VERIFY" in result.stderr


@_needs_workspace
def test_a_declared_branch_input_that_is_absent_is_unverifiable_never_verified(tmp_path: Path) -> None:
    ws = _clone_workspace(tmp_path)
    pointer_path = ws / "loquitur-schemas" / POINTER
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    pointer["branch_input"] = {"artifact": "absent-input.zip", "bytes": 1, "kind": "k", "sha256": "0" * 64}
    pointer_path.write_text(json.dumps(pointer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert run(ws, "--write-manifest").returncode == 0
    manifest = json.loads((ws / "loquitur-protocol" / "release-set.json").read_text(encoding="utf-8"))
    assert manifest["branch_inputs_declared"] == 1
    assert manifest["unverifiable_branch_inputs"] == ["loquitur-schemas:absent-input.zip"]
    assert manifest["branch_inputs_present"] is False
    result = run(ws)
    assert result.returncode == 0
    assert "loquitur-schemas: branch input absent-input.zip is absent - UNVERIFIABLE" in result.stdout
    strict = run(ws, "--require-branch-inputs")
    assert strict.returncode == 1 and "UNVERIFIABLE" in strict.stderr


def test_a_declared_branch_input_that_is_absent_is_unverifiable_in_a_synthetic_release_set(
    tmp_path: Path,
) -> None:
    """The same path as above, on a release set made here, so that no checkout is needed.

    Two members, this repository's own pointer and a copy of it for a second repository: the
    second declares a branch input no file supplies. The test above needs every member of the
    real release set and is skipped without them; this one runs in any copy of this repository.
    """
    ws = tmp_path / "ws"
    own = json.loads((ROOT / POINTER).read_text(encoding="utf-8"))
    names = ("loquitur-protocol", "loquitur-schemas")
    for name in names:
        pointer = {**own, "repository": name}
        if name == "loquitur-schemas":
            pointer["branch_input"] = {"artifact": "absent-input.zip", "bytes": 1, "kind": "k", "sha256": "0" * 64}
        (ws / name).mkdir(parents=True)
        (ws / name / POINTER).write_text(json.dumps(pointer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    first = run(ws, "--write-manifest", *(arg for name in names for arg in ("--add-member", name)))
    assert first.returncode == 0, first.stdout + first.stderr
    manifest = json.loads((ws / "loquitur-protocol" / "release-set.json").read_text(encoding="utf-8"))
    assert sorted(manifest["members"]) == list(names)
    assert manifest["branch_inputs_declared"] == 1
    assert manifest["unverifiable_branch_inputs"] == ["loquitur-schemas:absent-input.zip"]
    assert manifest["branch_inputs_present"] is False
    result = run(ws)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "loquitur-schemas: branch input absent-input.zip is absent - UNVERIFIABLE" in result.stdout
    assert "(1 warning(s))" in result.stdout
    strict = run(ws, "--require-branch-inputs")
    assert strict.returncode == 1 and "UNVERIFIABLE" in strict.stderr


@_needs_workspace
def test_pointer_divergence_is_detected(tmp_path: Path) -> None:
    ws = _clone_workspace(tmp_path)
    assert run(ws).returncode == 0, "cloned workspace should verify before tampering"
    target = ws / "loquitur-verify-py" / POINTER
    data = json.loads(target.read_text(encoding="utf-8"))
    data["branch_id"] = "9.9.9"
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    result = run(ws)
    assert result.returncode == 1
    assert "disagree on branch_id" in result.stderr


@_needs_workspace
def test_pointer_hash_drift_is_detected(tmp_path: Path) -> None:
    ws = _clone_workspace(tmp_path)
    target = ws / "loquitur-schemas" / POINTER
    data = json.loads(target.read_text(encoding="utf-8"))
    data["repository_role"] = str(data.get("repository_role")) + "-tampered"
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    result = run(ws)
    assert result.returncode == 1
    assert "does not match manifest" in result.stderr


@_needs_workspace
def test_missing_manifest_is_detected(tmp_path: Path) -> None:
    ws = _clone_workspace(tmp_path)
    (ws / "loquitur-protocol" / "release-set.json").unlink()
    result = run(ws)
    assert result.returncode == 1
    assert "release manifest missing" in result.stderr


@_needs_workspace
def test_membership_is_the_manifests_and_a_repository_outside_it_is_counted_not_named(tmp_path: Path) -> None:
    """The manifest lists the members; a repository carrying a pointer outside it is counted.

    Two halves, because either alone passes vacuously. The members are the published
    repositories and the conformance corpus, which travels inside this one, and nothing else.
    A workspace that also holds pointers of repositories the manifest does not list (this
    workspace may, and so may a cross-repository job) verifies, says how many there are, and
    names none of them; a manifest regenerated there admits none of them either.
    """
    manifest = json.loads((ROOT / "release-set.json").read_text(encoding="utf-8"))
    assert set(manifest["members"]) == set(PUBLISHED) | {"loquitur-conformance"}

    ws = _clone_workspace(tmp_path)
    template = json.loads((ROOT / POINTER).read_text(encoding="utf-8"))
    planted = ["outside-one", "outside-two"]
    for name in planted:
        (ws / name).mkdir()
        (ws / name / POINTER).write_text(json.dumps(dict(template, repository=name)), encoding="utf-8")
    result = run(ws)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    count = len(planted) + len(_OUTSIDE)
    assert (
        f"{count} repository(ies) in this workspace carry a release-set pointer and are not manifest members"
        in result.stdout
    ), output
    assert not [name for name in planted + _OUTSIDE if name in output], output

    regenerated = run(ws, "--write-manifest")
    assert regenerated.returncode == 0, regenerated.stdout + regenerated.stderr
    written = json.loads((ws / "loquitur-protocol" / "release-set.json").read_text(encoding="utf-8"))
    assert written == manifest


@_needs_workspace
def test_a_member_joins_only_when_admitted_by_name(tmp_path: Path) -> None:
    ws = _clone_workspace(tmp_path)
    template = json.loads((ROOT / POINTER).read_text(encoding="utf-8"))
    (ws / "outside-one").mkdir()
    (ws / "outside-one" / POINTER).write_text(json.dumps(dict(template, repository="outside-one")), encoding="utf-8")
    refused = run(ws, "--write-manifest", "--add-member", "outside-none")
    assert refused.returncode == 1
    assert "outside-none: --add-member names no repository carrying a pointer here" in refused.stderr
    admitted = run(ws, "--write-manifest", "--add-member", "outside-one")
    assert admitted.returncode == 0, admitted.stdout + admitted.stderr
    written = json.loads((ws / "loquitur-protocol" / "release-set.json").read_text(encoding="utf-8"))
    assert set(written["members"]) == set(_MANIFEST_MEMBERS) | {"outside-one"}
    assert run(ws, "--add-member", "outside-one").returncode == 2


# --- published subsets -------------------------------------------------------------------
#
# A release workspace holds the published repositories side by side and nothing else. The
# verifier must pass such a layout and name, on stderr or anywhere else, no unpublished member
# it cannot find. These build the layouts from the real pointers and the real manifest.


def _subset_workspace(tmp_path: Path, names: list[str]) -> Path:
    dest = tmp_path / "ws"
    dest.mkdir()
    for name in names:
        (dest / name).mkdir()
        source = WORKSPACE / name / POINTER
        if source.is_file():
            shutil.copy2(source, dest / name / POINTER)
        else:
            # A directory with no pointer is still a directory in the layout; it must not
            # confuse the verifier either.
            (dest / name / "README.md").write_text("# " + name + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "release-set.json", dest / "loquitur-protocol" / "release-set.json")
    return dest


def _require_published_pointers() -> None:
    absent = [name for name in PUBLISHED if not (WORKSPACE / name / POINTER).is_file()]
    if absent:
        _absent(f"published repositories not checked out beside this one: {absent}")


def _assert_names_no_unpublished_repository(output: str) -> None:
    leaked = [name for name in UNPUBLISHED if name in output]
    assert not leaked, f"output for a published layout names unpublished repositories {leaked}:\n{output}"


PUBLISHED_SUBSETS = {
    "two": ["loquitur-protocol", "loquitur-schemas"],
    "three": ["loquitur-protocol", "loquitur-schemas", "loquitur-verify-py"],
    # The release workspace a publication produces: the published repositories.
    "four": ["loquitur-protocol", "loquitur-schemas", "loquitur-verify-py", "loquitur-verify-ts"],
    "five": ["loquitur-protocol", "loquitur-schemas", "loquitur-verify-py", "loquitur-verify-ts", "unrelated-directory"],
}


@pytest.mark.parametrize("size", sorted(PUBLISHED_SUBSETS))
def test_a_published_subset_verifies_and_names_nothing_unpublished(tmp_path: Path, size: str) -> None:
    _require_published_pointers()
    ws = _subset_workspace(tmp_path, PUBLISHED_SUBSETS[size])
    for extra in ((), ("--json",)):
        result = run(ws, *extra)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        _assert_names_no_unpublished_repository(output)
    assert "not published are not present in this workspace - NOT CHECKED" in run(ws).stdout


def test_a_subset_holding_an_unpublished_member_names_only_what_is_present(tmp_path: Path) -> None:
    """The published repositories plus one member that is not published.

    The member that plays the part is loquitur-conformance, the one manifest member that is
    not published.
    """
    _require_published_pointers()
    if not (WORKSPACE / "loquitur-conformance" / POINTER).is_file():
        # This skip fires precisely in the layouts that do not hold the repository, so its
        # reason must not name it.
        _absent(
            "an unpublished member this layout needs is not checked out",
            "loquitur-conformance, the unpublished member this layout needs, is not checked out",
        )
    ws = _subset_workspace(tmp_path, [*PUBLISHED, "loquitur-conformance"])
    result = run(ws)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    absent = [name for name in UNPUBLISHED if name != "loquitur-conformance"]
    assert not [name for name in absent if name in output], output
    # Non-vacuity: the present unpublished member is checked, so a pointer of it that no longer
    # matches the manifest fails the run by its name.
    pointer = ws / "loquitur-conformance" / POINTER
    pointer.write_bytes(pointer.read_bytes() + b" ")
    tampered = run(ws)
    assert tampered.returncode == 1
    assert "loquitur-conformance: pointer sha256" in tampered.stderr, tampered.stdout + tampered.stderr


def test_an_isolated_clone_is_a_usage_error_that_names_nothing(tmp_path: Path) -> None:
    ws = _subset_workspace(tmp_path, ["loquitur-protocol"])
    result = run(ws)
    output = result.stdout + result.stderr
    assert result.returncode == 2, output
    assert "fewer than two of them are present here" in result.stderr
    _assert_names_no_unpublished_repository(output)


def test_a_broken_published_member_still_fails_in_a_subset(tmp_path: Path) -> None:
    _require_published_pointers()
    ws = _subset_workspace(tmp_path, PUBLISHED_SUBSETS["three"])
    target = ws / "loquitur-schemas" / POINTER
    data = json.loads(target.read_text(encoding="utf-8"))
    data["repository_role"] = str(data.get("repository_role")) + "-tampered"
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    result = run(ws)
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "loquitur-schemas: pointer sha256" in result.stderr
    _assert_names_no_unpublished_repository(output)


def test_require_every_member_fails_a_subset_without_naming_unpublished_members(tmp_path: Path) -> None:
    _require_published_pointers()
    ws = _subset_workspace(tmp_path, PUBLISHED_SUBSETS["two"])
    result = run(ws, "--require-every-member")
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "loquitur-verify-py: manifest member is not present in this workspace" in result.stderr
    _assert_names_no_unpublished_repository(output)
