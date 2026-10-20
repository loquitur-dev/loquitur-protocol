from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import release_gate

ROOT = Path(__file__).resolve().parents[1]
gate = release_gate()
ca = gate.corpus_archive
IGNORED = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".venv", "venv")


def run(root: Path, *arguments: str):
    """The gate over ``root``, as a command."""
    command = [sys.executable, str(root / "tools/check_protocol_release.py"), "--root", str(root), *arguments]
    env = {key: value for key, value in os.environ.items() if key != gate.REQUIRE_SIBLINGS_ENV}
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(command, text=True, env=env, encoding="utf-8", capture_output=True, check=False)


def _lock() -> dict:
    return json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))


def _copy(tmp_path: Path) -> Path:
    """A copy of this repository, alone in its directory, so no corpus source checkout is beside it."""
    target = tmp_path / "alone" / "loquitur-protocol"
    shutil.copytree(ROOT, target, ignore=IGNORED)
    return target


def _install(target: Path, data: bytes) -> None:
    """Replace the pinned archive of ``target`` with ``data`` and repoint the lock at it, name and all."""
    lock_path = target / "CONFORMANCE_LOCK.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    (target / lock["artifact"]).unlink()
    identity = ca.corpus_id(data)
    lock.update(
        artifact=f"conformance/{identity}.zip",
        bytes=len(data),
        corpus_id=identity,
        sha256=hashlib.sha256(data).hexdigest(),
    )
    (target / lock["artifact"]).write_bytes(data)
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _members() -> dict[str, bytes]:
    return ca.members_of((ROOT / _lock()["artifact"]).read_bytes())


def test_protocol_release_and_embedded_conformance_pass() -> None:
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _lock()["corpus_id"] in result.stdout


def test_unclassified_changes_are_breaking() -> None:
    release = json.loads((ROOT / "PROTOCOL_RELEASE.json").read_text(encoding="utf-8"))
    assert release["conformance"]["compatibility_class_default"] == "breaking"


def test_signing_envelope_v2_is_canonical_and_no_earlier_payload_is_defined() -> None:
    release = json.loads((ROOT / "PROTOCOL_RELEASE.json").read_text(encoding="utf-8"))
    v2 = next(x for x in release["profiles"] if x["id"] == "registry-entry-signing-envelope-v2")
    assert release["wire_semantic_change"] is False
    assert v2["status"] == "canonical"
    assert v2["compatibility_class"] == "breaking"
    # The protocol defines no earlier signing payload (document-contracts.md, "Version gate"), so
    # no profile, policy file or opt-in describes one.
    assert not [x["id"] for x in release["profiles"] if "legacy" in x["id"]], release["profiles"]
    assert not (ROOT / "SIGNING_MIGRATION_POLICY.json").exists()


def test_protocol_0_1_cryptographic_capability_set_is_closed() -> None:
    capability = json.loads((ROOT / "CRYPTOGRAPHIC_CAPABILITIES.json").read_text(encoding="utf-8"))
    assert capability["profile_id"] == "loquitur.crypto_capabilities.v0.1"
    assert [x["id"] for x in capability["signature_algorithms"]] == ["secp256k1_ecdsa_sha256"]
    assert capability["trust_registry_key_types"] == ["secp256k1"]
    assert [x["id"] for x in capability["reserved_not_supported"]] == ["ed25519"]
    # The documents admit any well-formed identifier; the verifier's allowlist answers
    # UNSUPPORTED_SIGNATURE_ALGORITHM at the signature step, so Ed25519 is accepted by the schemas
    # and verified by nothing.
    assert capability["reserved_not_supported"][0]["schema_acceptance"] is True
    assert capability["reserved_not_supported"][0]["verification"] is False
    assert capability["automatic_fallback"] is False
    assert capability["unknown_algorithm_policy"] == "reject"


def test_ed25519_reintroduction_is_rejected(tmp_path: Path) -> None:
    target = _copy(tmp_path)
    path = target / "CRYPTOGRAPHIC_CAPABILITIES.json"
    capability = json.loads(path.read_text(encoding="utf-8"))
    capability["trust_registry_key_types"].append("ed25519")
    path.write_text(json.dumps(capability, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run(target)
    assert result.returncode == 1
    assert "key type" in result.stdout.lower()
    # The archive's copy of the file does not equal it, and that is reported too.
    assert "protocol/CRYPTOGRAPHIC_CAPABILITIES.json differs" in result.stdout


def test_verification_vocabularies_are_closed() -> None:
    vocab = json.loads((ROOT / "VERIFICATION_VOCABULARIES.json").read_text(encoding="utf-8"))
    assert vocab["verification_statuses"] == ["pass", "warning", "review", "fail"]
    assert vocab["registry_verdicts"] == ["PASS", "WARN", "REVIEW", "FAIL"]
    assert vocab["closed_status_vocabulary"] is True
    # There is no `unknown` status (the resolution of LCP-0008 that docs/change-proposals.md
    # records): it would resolve to no registry verdict.
    assert "unknown" not in vocab["verification_statuses"]
    assert "unknown" not in vocab["status_to_registry_verdict"]
    assert set(vocab["status_to_registry_verdict"]) == set(vocab["verification_statuses"])
    assert all(v is not None for v in vocab["status_to_registry_verdict"].values())
    assert set(vocab["status_to_registry_verdict"].values()) == set(vocab["registry_verdicts"])


def test_schema_types_profile_is_source_api_breaking_not_wire_breaking() -> None:
    release = json.loads((ROOT / "PROTOCOL_RELEASE.json").read_text(encoding="utf-8"))
    profile = next(x for x in release["profiles"] if x["id"] == "schema-generated-types-v1")
    assert release["wire_semantic_change"] is False
    assert profile["compatibility_class"] == "source-api-breaking"


def test_independent_oracle_policy_is_fail_closed() -> None:
    policy = json.loads((ROOT / "CONFORMANCE_ORACLE_POLICY.json").read_text(encoding="utf-8"))
    assert policy["policy_id"] == "loquitur.independent_conformance_oracle.v1"
    assert "cross-implementation agreement is necessary but never sufficient" in policy["principles"]
    assert "unexpected disagreements fail closed" in policy["principles"]
    assert policy["wire_semantic_change"] is False


def test_every_release_artifact_points_at_the_lock_and_none_repeats_the_pin() -> None:
    release = json.loads((ROOT / "PROTOCOL_RELEASE.json").read_text(encoding="utf-8"))
    authority = json.loads((ROOT / "CONFORMANCE_AUTHORITY.json").read_text(encoding="utf-8"))
    public = json.loads((ROOT / "public_spec_manifest.json").read_text(encoding="utf-8"))
    assert release["conformance"]["lock_path"] == "CONFORMANCE_LOCK.json"
    assert authority["canonical_corpus"] == {"lock_path": "CONFORMANCE_LOCK.json", "repository": "loquitur-conformance"}
    assert public["conformance_lock"] == "CONFORMANCE_LOCK.json"
    assert public["release_set_id"] == "loquitur-release-set-0.1.0"
    assert public["protocol_release_id"] == "loquitur-protocol-0.1.0"
    pinned = _lock()["corpus_id"]
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT).as_posix()
        if not path.is_file() or relative.startswith((".git/", ".venv/", "venv/")) or "__pycache__" in relative:
            continue
        if relative in {"CONFORMANCE_LOCK.json", "CHANGELOG.md"} or relative.startswith("conformance/"):
            continue
        assert pinned not in path.read_bytes().decode("utf-8", "replace"), f"{relative} repeats the corpus id"


def test_the_gate_never_executes_code_from_the_artifact_it_validates() -> None:
    """No execution primitive is reachable from the gate or the builder it imports."""
    for name in ("tools/check_protocol_release.py", "tools/corpus_archive.py"):
        source = (ROOT / name).read_text(encoding="utf-8")
        body = "\n".join(line for line in source.splitlines() if not line.strip().startswith("#"))
        for primitive in ("import subprocess", "subprocess.", "exec(", "eval(", "importlib", "__import__"):
            assert primitive not in body, f"{name} must not be able to execute anything: found {primitive!r}"


# --- provenance ---------------------------------------------------------------------------------


def _offsets(size: int) -> list[int]:
    """Offsets spread over the whole archive, and every byte of its last 64."""
    return sorted({*range(0, size, max(1, size // 48)), *range(max(0, size - 64), size)})


def test_a_one_byte_change_anywhere_in_the_pinned_archive_is_refused() -> None:
    data = (ROOT / _lock()["artifact"]).read_bytes()
    accepted = []
    for offset in _offsets(len(data)):
        changed = bytearray(data)
        changed[offset] ^= 0x01
        try:
            ca.members_of(bytes(changed))
        except ca.CanonicalArchiveError:
            continue
        accepted.append(offset)
    assert accepted == []


@pytest.mark.parametrize("offset", ["first", "middle", "last"])
def test_the_gate_refuses_a_one_byte_change_even_with_the_lock_repointed(tmp_path: Path, offset: str) -> None:
    data = bytearray((ROOT / _lock()["artifact"]).read_bytes())
    position = {"first": 0, "middle": len(data) // 2, "last": len(data) - 1}[offset]
    data[position] ^= 0x01
    target = _copy(tmp_path)
    _install(target, bytes(data))
    result = run(target)
    assert result.returncode == 1, result.stdout
    assert "is not the canonical build of its members" in result.stdout


def test_an_archive_with_a_byte_appended_is_refused_by_the_lock(tmp_path: Path) -> None:
    target = _copy(tmp_path)
    artifact = target / _lock()["artifact"]
    artifact.write_bytes(artifact.read_bytes() + b"\x00")
    result = run(target)
    assert result.returncode == 1
    assert "size is not the size the lock declares" in result.stdout
    assert "SHA-256 is not the digest the lock declares" in result.stdout


def _rebuilt(edit) -> bytes:
    members = _members()
    edit(members)
    return ca.build(members)


MANIFEST = ca.PREFIX + ca.MANIFEST
VERIFY = ca.PREFIX + "vectors/verify.json"


@pytest.mark.parametrize(
    ("case", "edit", "message"),
    [
        (
            "changed-vector",
            lambda m: m.__setitem__(VERIFY, m[VERIFY] + b" "),
            "does not list exactly the archive's other members",
        ),
        (
            "added-member",
            lambda m: m.__setitem__(ca.PREFIX + "vectors/extra.json", b"{}\n"),
            "does not list exactly the archive's other members",
        ),
        (
            "member-outside-the-layout",
            lambda m: m.__setitem__(ca.PREFIX + "tools/run.py", b""),
            "members outside vectors/ and protocol/",
        ),
        ("no-manifest", lambda m: m.pop(MANIFEST), "has no conformance-manifest.json"),
        (
            "self-reference",
            lambda m: m.__setitem__(VERIFY, m[VERIFY] + ca.corpus_id(b"x").encode()),
            "an archive member names a corpus id: vectors/verify.json",
        ),
        (
            "protocol-copy-differs",
            lambda m: m.__setitem__(ca.PREFIX + "protocol/" + ca.PROTOCOL_COPIES[0], b"{}\n"),
            "differs from this repository's",
        ),
        (
            "no-vectors",
            lambda m: [m.pop(name) for name in [n for n in m if n.startswith(ca.PREFIX + "vectors/")]],
            "carries no vectors",
        ),
    ],
)
def test_a_canonical_archive_that_is_not_the_corpus_is_refused(tmp_path: Path, case: str, edit, message: str) -> None:
    target = _copy(tmp_path)
    _install(target, _rebuilt(edit))
    result = run(target)
    assert result.returncode == 1, result.stdout
    assert message in result.stdout, result.stdout


def _write_lock(target: Path, edit) -> None:
    path = target / "CONFORMANCE_LOCK.json"
    lock = json.loads(path.read_text(encoding="utf-8"))
    edit(lock)
    path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")


@pytest.mark.parametrize(
    ("case", "edit", "message"),
    [
        ("extra-key", lambda lock: lock.update(note="x"), "holds exactly the keys"),
        ("missing-key", lambda lock: lock.pop("consumption"), "holds exactly the keys"),
        ("upper-case", lambda lock: lock.update(artifact=lock["artifact"].upper()), "artifact is not exactly"),
        ("dot-slash", lambda lock: lock.update(artifact="./" + lock["artifact"]), "artifact is not exactly"),
        (
            "backslash",
            lambda lock: lock.update(artifact=lock["artifact"].replace("/", "\\")),
            "artifact is not exactly",
        ),
        ("trailing-dot", lambda lock: lock.update(artifact=lock["artifact"] + "."), "artifact is not exactly"),
        ("other-id", lambda lock: lock.update(corpus_id=ca.corpus_id(b"x")), "not derived from its sha256"),
        ("old-schema", lambda lock: lock.update(schema_version="loquitur.conformance_lock.v1"), "schema_version"),
    ],
)
def test_the_lock_is_read_strictly(tmp_path: Path, case: str, edit, message: str) -> None:
    target = _copy(tmp_path)
    _write_lock(target, edit)
    result = run(target)
    assert result.returncode == 1, result.stdout
    assert message in result.stdout, result.stdout


def test_a_duplicate_key_in_the_lock_is_refused(tmp_path: Path) -> None:
    target = _copy(tmp_path)
    path = target / "CONFORMANCE_LOCK.json"
    path.write_text(path.read_text(encoding="utf-8").replace("{", '{\n  "bytes": 0,', 1), encoding="utf-8")
    result = run(target)
    assert result.returncode == 1
    assert "duplicate key" in result.stdout


def test_a_second_file_in_the_archive_directory_is_refused(tmp_path: Path) -> None:
    target = _copy(tmp_path)
    (target / "conformance/other.zip").write_bytes(b"")
    result = run(target)
    assert result.returncode == 1
    assert "not exactly the pinned archive" in result.stdout


def _sibling_sources(tmp_path: Path) -> tuple[Path, Path]:
    """A workspace of a copy of this repository and a corpus source checkout built from the pinned members."""
    workspace = tmp_path / "ws"
    protocol = workspace / "loquitur-protocol"
    shutil.copytree(ROOT, protocol, ignore=IGNORED)
    source = workspace / gate.CORPUS_REPOSITORY
    members = _members()
    for name, data in members.items():
        relative = name[len(ca.PREFIX) :]
        if relative.startswith("vectors/"):
            (source / relative).parent.mkdir(parents=True, exist_ok=True)
            (source / relative).write_bytes(data)
    profiles = json.loads(members[MANIFEST])["profiles"]
    (source / ca.PROFILES_SOURCE).write_text(json.dumps({"profiles": profiles}), encoding="utf-8")
    return protocol, source


def test_the_archive_equals_the_build_of_its_sources_and_refuses_sources_that_moved(tmp_path: Path) -> None:
    protocol, source = _sibling_sources(tmp_path)
    passed = run(protocol, "--require-siblings")
    assert passed.returncode == 0, passed.stdout
    vector = source / "vectors/verify.json"
    vector.write_bytes(vector.read_bytes() + b" ")
    moved = run(protocol, "--require-siblings")
    assert moved.returncode == 1
    assert "the sources changed without rebuilding the archive" in moved.stdout


def test_an_absent_source_checkout_fails_only_when_siblings_are_required(tmp_path: Path) -> None:
    target = _copy(tmp_path)
    assert run(target).returncode == 0
    required = run(target, "--require-siblings")
    assert required.returncode == 1
    assert "is not beside this repository" in required.stdout


# --- profiles and classes -------------------------------------------------------------------------


def _edit_release_profiles(target: Path, edit) -> None:
    path = target / "PROTOCOL_RELEASE.json"
    release = json.loads(path.read_text(encoding="utf-8"))
    release["profiles"] = edit(release["profiles"])
    path.write_text(json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_a_profile_the_corpus_does_not_declare_is_rejected(tmp_path: Path) -> None:
    target = _copy(tmp_path)
    _edit_release_profiles(
        target,
        lambda profiles: (
            profiles
            + [{"compatibility_class": "source-api-breaking", "id": "undeclared-profile-v1", "status": "current"}]
        ),
    )
    result = run(target)
    assert result.returncode == 1
    assert "declares profiles the pinned corpus does not" in result.stdout
    assert "undeclared-profile-v1" in result.stdout


def test_a_profile_the_release_does_not_declare_is_rejected(tmp_path: Path) -> None:
    target = _copy(tmp_path)
    _edit_release_profiles(target, lambda profiles: [p for p in profiles if p["id"] != "registry-link-v1"])
    result = run(target)
    assert result.returncode == 1
    assert "declares profiles PROTOCOL_RELEASE.json does not" in result.stdout
    assert "registry-link-v1" in result.stdout


def _replace_profile(profiles: list[dict], profile_id: str, edit) -> list[dict]:
    return [edit(dict(p)) if p["id"] == profile_id else p for p in profiles]


def _without_class(profile: dict) -> dict:
    profile.pop("compatibility_class")
    return profile


def _empty_class_catalog(target: Path) -> None:
    path = target / "docs/specification/compatibility-classes.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["classes"] = []
    path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8", newline="\n")


_CLASS_CASES = {
    "unknown-class": (
        lambda t: _edit_release_profiles(
            t,
            lambda ps: _replace_profile(
                ps, "canonical-json-v1", lambda p: {**p, "compatibility_class": "not-a-real-compatibility-class"}
            ),
        ),
        "profile canonical-json-v1 declares compatibility_class 'not-a-real-compatibility-class', "
        "which docs/specification/compatibility-classes.json does not define",
    ),
    "null-class": (
        lambda t: _edit_release_profiles(
            t, lambda ps: _replace_profile(ps, "registry-link-v1", lambda p: {**p, "compatibility_class": None})
        ),
        "profile registry-link-v1 declares compatibility_class None",
    ),
    "absent-class": (
        lambda t: _edit_release_profiles(t, lambda ps: _replace_profile(ps, "offline-verification-v1", _without_class)),
        "profile offline-verification-v1 has no explicit compatibility_class",
    ),
    "duplicate-profile": (
        lambda t: _edit_release_profiles(
            t, lambda ps: ps + [dict(next(p for p in ps if p["id"] == "canonical-json-v1"))]
        ),
        "PROTOCOL_RELEASE.json declares profile canonical-json-v1 more than once",
    ),
    "empty-id": (
        lambda t: _edit_release_profiles(
            t, lambda ps: ps + [{"compatibility_class": "wire-exact", "id": "", "status": "current"}]
        ),
        "has no non-empty string id",
    ),
    "empty-catalog": (
        _empty_class_catalog,
        "docs/specification/compatibility-classes.json defines no compatibility class",
    ),
}


@pytest.mark.parametrize("case", sorted(_CLASS_CASES))
def test_a_profile_without_a_catalogued_compatibility_class_is_rejected(tmp_path: Path, case: str) -> None:
    target = _copy(tmp_path)
    mutate, message = _CLASS_CASES[case]
    mutate(target)
    result = run(target)
    assert result.returncode == 1, result.stdout + result.stderr
    assert message in result.stdout, result.stdout


def test_a_status_announcing_blocking_disagreements_is_checked_against_the_phrases(tmp_path: Path) -> None:
    target = _copy(tmp_path)
    path = target / "public_spec_manifest.json"
    public = json.loads(path.read_text(encoding="utf-8"))
    public["release_posture"] += "; disagreements remain release-blocking"
    path.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    result = run(target)
    assert result.returncode == 1
    assert "disagreements remain release-blocking" in result.stdout
