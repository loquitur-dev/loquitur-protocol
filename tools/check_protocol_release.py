"""Check this repository's release artifacts and the conformance archive they pin.

    python tools/check_protocol_release.py --root . [--require-siblings]

The release identities, the closed vocabularies and capability set, the oracle policy, each
profile's compatibility class and the normative prose digests are checked against this
repository's own files. The pinned conformance archive is checked by provenance, never by reading
it adversarially: `CONFORMANCE_LOCK.json` is read strictly; the archive is the one file under
`conformance/`, named after its corpus id, which is derived from its SHA-256; the archive is
byte for byte the canonical build of the members it holds (`tools/corpus_archive.py`), so any
byte the builder would not have written fails without being interpreted; its content manifest
lists every other member exactly; and its copies of this repository's normative files equal
them. When the corpus source checkout `loquitur-conformance` is beside this repository (required
with `--require-siblings` or LOQUITUR_REQUIRE_SIBLINGS), the archive must also equal the build
of that checkout's sources, byte for byte.

Nothing from the archive is executed. Whether a verifier reproduces the corpus's declared runs is
not decided here; `docs/specification/conformance-testing.md` section 7 says how it is measured.

Exit codes: 0 verified, 1 a check failed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# Plain imports of files beside this one, from this repository's own tools/, never from the
# archive under test.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_archive  # noqa: E402
from refresh_prose_digests import verify as verify_prose_digests  # noqa: E402

EXPECTED_RELEASE_SET = "loquitur-release-set-0.1.0"
EXPECTED_PROTOCOL_RELEASE = "loquitur-protocol-0.1.0"
EXPECTED_PROFILE = "independent-conformance-oracle-v1"
EXPECTED_ORACLE = "loquitur.independent_conformance_oracle.v1"
EXPECTED_STATUSES = ["pass", "warning", "review", "fail"]
EXPECTED_VERDICTS = ["PASS", "WARN", "REVIEW", "FAIL"]

LOCK = "CONFORMANCE_LOCK.json"
LOCK_SCHEMA = "loquitur.conformance_lock.v2"
LOCK_KEYS = frozenset(
    {
        "artifact",
        "authority_repository",
        "bytes",
        "consumption",
        "corpus_id",
        "expected_outcomes_mutable_by",
        "oracle_policy",
        "parent_release_set_id",
        "protocol_owner",
        "schema_version",
        "sha256",
        "verification_command",
    }
)
ARCHIVE_DIRECTORY = "conformance"
CORPUS_REPOSITORY = "loquitur-conformance"
REQUIRE_SIBLINGS_ENV = "LOQUITUR_REQUIRE_SIBLINGS"
BASELINE = "consumer-conformance-baseline.json"

# A release's conformance posture is one of two closed sets of status strings: one announces
# blocking consumer disagreements, the other announces none.
_DISAGREEMENT_STATUSES = {
    True: {"independent-conformance-oracle-active-known-consumer-disagreements-blocking"},
    False: {"independent-conformance-oracle-active-no-known-consumer-disagreements"},
}

# The phrasings that announce blocking disagreements in prose and non-claims entries.
_BLOCKING_DISAGREEMENT_PHRASES = (
    "disagreements-blocking",
    "nonconformance-remains-blocking",
    "disagreements remain release-blocking",
    "blocking work in the conformance baseline",
)


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _phrases_claiming_blocking(value: object) -> set[str]:
    """The blocking-disagreement phrases ``value`` carries, at any depth."""
    if isinstance(value, str):
        lowered = value.lower()
        return {phrase for phrase in _BLOCKING_DISAGREEMENT_PHRASES if phrase in lowered}
    if isinstance(value, list):
        return set().union(*(_phrases_claiming_blocking(item) for item in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(_phrases_claiming_blocking(item) for item in value.values())) if value else set()
    return set()


def _strict_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _compare_profile_sets(release: dict, corpus_manifest: dict) -> list[str]:
    """The release and the corpus it pins declare the same conformance profiles."""
    errors: list[str] = []
    release_ids = {profile.get("id") for profile in release.get("profiles", [])}
    corpus_ids = {profile.get("id") for profile in corpus_manifest.get("profiles", [])}
    if not release_ids or not corpus_ids:
        errors.append("a profile list is empty; the profile comparison would measure nothing")
        return errors
    only_release = sorted(release_ids - corpus_ids)
    only_corpus = sorted(corpus_ids - release_ids)
    if only_release:
        errors.append(f"PROTOCOL_RELEASE.json declares profiles the pinned corpus does not: {only_release}")
    if only_corpus:
        errors.append(f"the pinned corpus declares profiles PROTOCOL_RELEASE.json does not: {only_corpus}")
    return errors


def _check_profile_classes(root: Path, release: dict) -> list[str]:
    """Every release profile carries one explicit compatibility class from the closed catalog."""
    catalog_path = root / "docs/specification/compatibility-classes.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [
            f"docs/specification/compatibility-classes.json cannot be read ({type(exc).__name__}); "
            "no profile's compatibility_class was checked"
        ]
    entries = catalog.get("classes") if isinstance(catalog, dict) else None
    known = {
        entry["id"]
        for entry in (entries if isinstance(entries, list) else [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]
    }
    if not known:
        return [
            "docs/specification/compatibility-classes.json defines no compatibility class; "
            "the class check would measure nothing"
        ]
    errors: list[str] = []
    profiles = release.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        return ["PROTOCOL_RELEASE.json declares no profiles; no compatibility_class was checked"]
    seen: set[str] = set()
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            errors.append(f"PROTOCOL_RELEASE.json profile #{index} is not an object")
            continue
        profile_id = profile.get("id")
        if not isinstance(profile_id, str) or not profile_id:
            errors.append(f"PROTOCOL_RELEASE.json profile #{index} has no non-empty string id")
            continue
        if profile_id in seen:
            errors.append(f"PROTOCOL_RELEASE.json declares profile {profile_id} more than once")
        seen.add(profile_id)
        if "compatibility_class" not in profile:
            errors.append(f"profile {profile_id} has no explicit compatibility_class")
        elif profile["compatibility_class"] not in known:
            errors.append(
                f"profile {profile_id} declares compatibility_class {profile['compatibility_class']!r}, "
                "which docs/specification/compatibility-classes.json does not define"
            )
    return errors


def _check_registered_vocabularies(root: Path, release: dict) -> list[str]:
    """PROTOCOL_RELEASE.json names the meta-schema and one file per kind it closes, and the rule for
    an unknown and an invalid value (verification-vocabularies.md section 7). It names no version:
    a registration changes a vocabulary file and nothing here."""
    block = release.get("registered_vocabularies")
    if not isinstance(block, dict):
        return ["PROTOCOL_RELEASE.json declares no registered_vocabularies"]
    errors: list[str] = []
    expected_keys = {"files", "invalid_value", "kinds", "meta_schema", "unknown_value"}
    if set(block) != expected_keys:
        errors.append(f"registered_vocabularies holds exactly {sorted(expected_keys)}, not {sorted(block)}")
    if block.get("unknown_value") != "review" or block.get("invalid_value") != "contract-violation":
        errors.append("registered_vocabularies: an unknown value is a review and an invalid one a contract violation")
    meta_path = root / str(block.get("meta_schema"))
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        kinds = meta["properties"]["kind"]["enum"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return errors + [f"registered_vocabularies.meta_schema cannot be read ({type(exc).__name__})"]
    if block.get("kinds") != kinds:
        errors.append(f"registered_vocabularies.kinds is {block.get('kinds')!r}; the meta-schema closes kind to {kinds!r}")
    files = block.get("files") if isinstance(block.get("files"), dict) else {}
    if sorted(files) != sorted(kinds):
        errors.append(f"registered_vocabularies.files names {sorted(files)}, not one file per kind")
    for kind, relative in sorted(files.items()):
        try:
            document = json.loads((root / str(relative)).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"registered vocabulary {relative} cannot be read ({type(exc).__name__})")
            continue
        if not isinstance(document, dict) or document.get("kind") != kind:
            errors.append(f"registered vocabulary {relative} does not register the kind {kind}")
    return errors


def read_lock(root: Path) -> tuple[dict | None, list[str]]:
    """``CONFORMANCE_LOCK.json``, read strictly: exact keys, an archive named after its corpus id."""
    try:
        lock = json.loads((root / LOCK).read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except (OSError, ValueError) as exc:
        return None, [f"{LOCK} cannot be read as strict JSON ({exc})"]
    if not isinstance(lock, dict) or set(lock) != LOCK_KEYS:
        found = sorted(lock) if isinstance(lock, dict) else type(lock).__name__
        return None, [f"{LOCK} holds exactly the keys {sorted(LOCK_KEYS)}, not {found}"]
    errors: list[str] = []
    if lock["schema_version"] != LOCK_SCHEMA:
        errors.append(f"{LOCK} schema_version is not {LOCK_SCHEMA}")
    corpus_id = lock["corpus_id"]
    if not isinstance(corpus_id, str) or not corpus_archive.ID_PATTERN.fullmatch(corpus_id):
        errors.append(f"{LOCK} corpus_id is not {corpus_archive.ID_PREFIX} and 16 lowercase hexadecimal characters")
    elif lock["artifact"] != f"{ARCHIVE_DIRECTORY}/{corpus_id}.zip":
        errors.append(f"{LOCK} artifact is not exactly {ARCHIVE_DIRECTORY}/{corpus_id}.zip")
    if not isinstance(lock["bytes"], int) or isinstance(lock["bytes"], bool):
        errors.append(f"{LOCK} bytes is not an integer")
    digest = lock["sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or digest.strip("0123456789abcdef"):
        errors.append(f"{LOCK} sha256 is not 64 lowercase hexadecimal characters")
    elif isinstance(corpus_id, str) and corpus_id != corpus_archive.ID_PREFIX + digest[:16]:
        errors.append(f"{LOCK} corpus_id is not derived from its sha256")
    return (lock if not errors else None), errors


def read_pinned_archive(root: Path, lock: dict) -> tuple[bytes | None, list[str]]:
    """The bytes of the archive ``lock`` pins, and where they differ from what the lock records.

    The bytes are None when the archive is not a regular file.
    """
    artifact = root / lock["artifact"]
    if not artifact.is_file() or artifact.is_symlink():
        return None, [f"the pinned archive {lock['artifact']} is not a regular file"]
    data = artifact.read_bytes()
    errors: list[str] = []
    if len(data) != lock["bytes"]:
        errors.append("the pinned archive's size is not the size the lock declares")
    if hashlib.sha256(data).hexdigest() != lock["sha256"]:
        errors.append("the pinned archive's SHA-256 is not the digest the lock declares")
    if corpus_archive.corpus_id(data) != lock["corpus_id"]:
        errors.append("the pinned archive's corpus id is not derived from its bytes")
    return data, errors


def check_archive(root: Path, lock: dict, release: dict) -> tuple[dict[str, bytes] | None, list[str]]:
    """The pinned archive by provenance; returns its members when it is the canonical build."""
    errors: list[str] = []
    directory = root / ARCHIVE_DIRECTORY
    listing = sorted(entry.name for entry in directory.iterdir()) if directory.is_dir() else []
    expected_name = lock["artifact"].rsplit("/", 1)[-1]
    if listing != [expected_name]:
        errors.append(f"{ARCHIVE_DIRECTORY}/ holds {listing}, not exactly the pinned archive {expected_name}")
    data, found = read_pinned_archive(root, lock)
    errors.extend(found)
    if data is None:
        return None, errors
    try:
        members = corpus_archive.members_of(data)
    except corpus_archive.CanonicalArchiveError as exc:
        return None, errors + [f"the pinned archive is not the canonical build of its members: {exc}"]

    prefix = corpus_archive.PREFIX
    manifest_name = prefix + corpus_archive.MANIFEST
    if manifest_name not in members:
        return None, errors + [f"the pinned archive has no {corpus_archive.MANIFEST}"]
    try:
        manifest = json.loads(members[manifest_name].decode("utf-8"), object_pairs_hook=_strict_object)
    except ValueError as exc:
        return None, errors + [f"{corpus_archive.MANIFEST} cannot be read as strict JSON ({exc})"]
    others = {name[len(prefix) :]: content for name, content in members.items() if name != manifest_name}
    if manifest_bytes_expected(others, manifest) != members[manifest_name]:
        errors.append(f"{corpus_archive.MANIFEST} does not list exactly the archive's other members")
    vectors = [name for name in others if name.startswith("vectors/")]
    if not vectors:
        errors.append("the pinned archive carries no vectors")
    stray = sorted(name for name in others if not name.startswith(("vectors/", "protocol/")))
    if stray:
        errors.append(f"the pinned archive carries members outside vectors/ and protocol/: {stray}")
    for name, content in sorted(others.items()):
        if corpus_archive.ID_PREFIX.encode() in content and _names_a_corpus_id(content):
            errors.append(f"an archive member names a corpus id: {name}")

    copies = [("protocol/" + path, path) for path in corpus_archive.PROTOCOL_COPIES]
    schemas = sorted(path.name for path in (root / corpus_archive.SCHEMA_COPIES_DIRECTORY).glob("*.json"))
    carried = sorted(
        name[len(corpus_archive.VECTOR_SCHEMAS_DIRECTORY) :]
        for name in others
        if name.startswith(corpus_archive.VECTOR_SCHEMAS_DIRECTORY)
    )
    if schemas != carried:
        errors.append(f"the archive's vectors/schemas/ holds {carried}, this repository's schemas are {schemas}")
    copies += [
        (corpus_archive.VECTOR_SCHEMAS_DIRECTORY + name, corpus_archive.SCHEMA_COPIES_DIRECTORY + name)
        for name in schemas
    ]
    for copy, source in copies:
        path = root / source
        if not path.is_file():
            errors.append(f"normative artifact missing from this repository: {source}")
        elif others.get(copy) != path.read_bytes():
            errors.append(f"the archive's {copy} differs from this repository's {source}")
    errors.extend(_compare_profile_sets(release, manifest if isinstance(manifest, dict) else {}))
    return members, errors


def manifest_bytes_expected(others: dict[str, bytes], manifest: object) -> bytes | None:
    """The manifest the builder writes for ``others`` and ``manifest``'s profiles."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("profiles"), list):
        return None
    return corpus_archive.manifest_bytes(others, manifest["profiles"])


def _names_a_corpus_id(content: bytes) -> bool:
    needle = corpus_archive.ID_PREFIX.encode()
    index = content.find(needle)
    while index != -1:
        tail = content[index + len(needle) : index + len(needle) + 16]
        if len(tail) == 16 and all(byte in b"0123456789abcdef" for byte in tail):
            return True
        index = content.find(needle, index + 1)
    return False


def check_source_rebuild(root: Path, lock: dict, require: bool) -> tuple[list[str], list[str]]:
    """The pinned archive equals the build of the corpus source checkout beside this repository.

    Returns the errors and the notes to print.
    """
    source = root.parent / CORPUS_REPOSITORY
    if not (source / corpus_archive.PROFILES_SOURCE).is_file():
        message = f"{CORPUS_REPOSITORY} is not beside this repository, so the archive was not rebuilt from its sources"
        return ([message] if require else []), ([] if require else ["note: " + message])
    try:
        rebuilt = corpus_archive.build_from_sources(source, root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"the archive could not be rebuilt from {CORPUS_REPOSITORY} ({type(exc).__name__}: {exc})"], []
    if hashlib.sha256(rebuilt).hexdigest() != lock["sha256"]:
        return [
            f"the build of {CORPUS_REPOSITORY}'s sources is {corpus_archive.corpus_id(rebuilt)}, "
            f"not the pinned {lock['corpus_id']}: the sources changed without rebuilding the archive"
        ], []
    return [], []


def check_posture(root: Path, release: dict, pointer: dict, documents: dict[str, dict]) -> list[str]:
    """The release's status strings name a recognized conformance posture, and the posture agrees
    with the consumer baseline of the corpus source checkout when it is beside this repository."""
    errors: list[str] = []
    baseline_path = root.parent / CORPUS_REPOSITORY / BASELINE
    baseline = None
    if baseline_path.is_file():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        if (
            baseline.get("unexpected_disagreement_policy") != "fail"
            or baseline.get("unreviewed_disappearance_policy") != "fail"
        ):
            errors.append("consumer disagreement baseline is not fail-closed")
        if baseline.get("expected_disagreements") is None:
            errors.append("consumer disagreement baseline does not declare expected_disagreements")
            baseline = None
        elif not baseline["expected_disagreements"] and baseline.get("status") != "no-known-consumer-nonconformance":
            errors.append("empty disagreement baseline without an explicit no-known-consumer-nonconformance status")
    for name, document in (("PROTOCOL_RELEASE.json", release), ("RELEASE_SET_POINTER.json", pointer)):
        status = document.get("status")
        if status not in _DISAGREEMENT_STATUSES[True] | _DISAGREEMENT_STATUSES[False]:
            errors.append(f"{name} status is {status!r}, which is not a recognized conformance posture")
        elif baseline is not None:
            has_disagreements = bool(baseline["expected_disagreements"])
            if status not in _DISAGREEMENT_STATUSES[has_disagreements]:
                errors.append(
                    f"{name} status is {status!r}; the baseline records "
                    f"{len(baseline['expected_disagreements'])} expected disagreement(s) and it announces the opposite"
                )
    announces_none = all(document.get("status") in _DISAGREEMENT_STATUSES[False] for document in (release, pointer))
    if announces_none:
        for name, document in documents.items():
            for phrase in sorted(_phrases_claiming_blocking(document)):
                errors.append(f"{name} says {phrase!r} while the release announces no known consumer disagreements")
    return errors


def verify(root: Path, require_siblings: bool = False) -> tuple[list[str], list[str]]:
    """Every error found in the release at ``root``, and the notes to print; no errors when it passes."""
    errors: list[str] = []
    required = [
        "PROTOCOL_RELEASE.json",
        "CONFORMANCE_AUTHORITY.json",
        LOCK,
        "CONFORMANCE_ORACLE_POLICY.json",
        "public_spec_manifest.json",
        "VERIFICATION_VOCABULARIES.json",
        "CRYPTOGRAPHIC_CAPABILITIES.json",
        "RELEASE_SET_POINTER.json",
    ]
    for name in required:
        if not (root / name).is_file():
            errors.append(f"missing required protocol release file: {name}")
    if errors:
        return errors, []
    release = json.loads((root / "PROTOCOL_RELEASE.json").read_text(encoding="utf-8"))
    authority = json.loads((root / "CONFORMANCE_AUTHORITY.json").read_text(encoding="utf-8"))
    public = json.loads((root / "public_spec_manifest.json").read_text(encoding="utf-8"))
    oracle_policy = json.loads((root / "CONFORMANCE_ORACLE_POLICY.json").read_text(encoding="utf-8"))
    vocab = json.loads((root / "VERIFICATION_VOCABULARIES.json").read_text(encoding="utf-8"))
    capability = json.loads((root / "CRYPTOGRAPHIC_CAPABILITIES.json").read_text(encoding="utf-8"))
    pointer = json.loads((root / "RELEASE_SET_POINTER.json").read_text(encoding="utf-8"))

    # PROTOCOL_RELEASE.json repeats the vocabularies VERIFICATION_VOCABULARIES.json owns.
    mirrored = release.get("verification_vocabularies") or {}
    for field in ("verification_statuses", "registry_verdicts", "unknown_status_policy"):
        if mirrored.get(field) != vocab.get(field):
            errors.append(
                f"verification vocabulary mirror drift in PROTOCOL_RELEASE.json: {field} is "
                f"{mirrored.get(field)!r} but the owner artifact says {vocab.get(field)!r}"
            )
    if mirrored.get("path") != "VERIFICATION_VOCABULARIES.json":
        errors.append("the vocabulary mirror does not name the artifact it mirrors")

    if release.get("release_set_id") != EXPECTED_RELEASE_SET:
        errors.append("unexpected release-set identity")
    if release.get("protocol_release_id") != EXPECTED_PROTOCOL_RELEASE:
        errors.append("unexpected protocol-release identity")
    if release.get("wire_semantic_change") is not False:
        errors.append("this release must preserve wire semantics")
    conformance = release.get("conformance", {})
    if conformance.get("compatibility_class_default") != "breaking":
        errors.append("unclassified changes must default to breaking")
    # The corpus is named in one place, the lock; every other artifact points at the lock.
    for name, value in (
        ("PROTOCOL_RELEASE.json conformance.lock_path", conformance.get("lock_path")),
        (
            "CONFORMANCE_AUTHORITY.json canonical_corpus.lock_path",
            authority.get("canonical_corpus", {}).get("lock_path"),
        ),
        ("public_spec_manifest.json conformance_lock", public.get("conformance_lock")),
    ):
        if value != LOCK:
            errors.append(f"{name} does not name {LOCK}")
    if (
        "corpus_id" in conformance
        or "conformance_corpus_id" in public
        or set(authority.get("canonical_corpus", {}))
        - {
            "lock_path",
            "repository",
        }
    ):
        errors.append(f"a release artifact repeats a pin that only {LOCK} holds")
    if (
        public.get("release_set_id") != EXPECTED_RELEASE_SET
        or public.get("protocol_release_id") != EXPECTED_PROTOCOL_RELEASE
    ):
        errors.append("public specification identity is stale")
    if oracle_policy.get("policy_id") != EXPECTED_ORACLE:
        errors.append("independent oracle policy identity mismatch")
    if oracle_policy.get("wire_semantic_change") is not False:
        errors.append("oracle policy must not claim wire change")
    principles = set(oracle_policy.get("principles") or [])
    for required_principle in (
        "normative expected outcomes may not be generated solely by an implementation under test",
        "cross-implementation agreement is necessary but never sufficient",
        "unexpected disagreements fail closed",
    ):
        if required_principle not in principles:
            errors.append(f"oracle policy principle missing: {required_principle}")
    if vocab.get("verification_statuses") != EXPECTED_STATUSES:
        errors.append("verification status vocabulary drift")
    if vocab.get("registry_verdicts") != EXPECTED_VERDICTS:
        errors.append("registry verdict vocabulary drift")
    # There is no `unknown` status (the resolution of LCP-0008 that docs/change-proposals.md
    # records): the mapping is total over the vocabulary, and `unknown` is on neither side.
    mapping = vocab.get("status_to_registry_verdict", {})
    if "unknown" in mapping or "unknown" in (vocab.get("verification_statuses") or []):
        errors.append("the vocabulary carries an unknown status, which the four-value vocabulary excludes")
    if sorted(mapping) != sorted(EXPECTED_STATUSES) or any(v is None for v in mapping.values()):
        errors.append("status to registry verdict mapping is not total over the vocabulary")
    if [item.get("id") for item in capability.get("signature_algorithms", [])] != ["secp256k1_ecdsa_sha256"]:
        errors.append("signature algorithm capability drift")
    if capability.get("trust_registry_key_types") != ["secp256k1"]:
        errors.append("trust registry key type capability drift")
    if capability.get("unknown_algorithm_policy") != "reject" or capability.get("automatic_fallback") is not False:
        errors.append("cryptographic capability policy is not fail-closed")
    if [item.get("id") for item in capability.get("reserved_not_supported", [])] != ["ed25519"]:
        errors.append("Ed25519 reservation mismatch")
    profile = next((x for x in release.get("profiles", []) if x.get("id") == EXPECTED_PROFILE), None)
    if (
        not profile
        or profile.get("compatibility_class") != "semantic-exact"
        or profile.get("status") != "canonical-blocking-oracle"
    ):
        errors.append("independent oracle conformance profile missing or misclassified")
    errors.extend(_check_profile_classes(root, release))
    errors.extend(_check_registered_vocabularies(root, release))
    errors.extend(verify_prose_digests(root))
    errors.extend(
        check_posture(
            root,
            release,
            pointer,
            {
                "PROTOCOL_RELEASE.json": release,
                "RELEASE_SET_POINTER.json": pointer,
                "CONFORMANCE_ORACLE_POLICY.json": oracle_policy,
                "public_spec_manifest.json": public,
            },
        )
    )

    notes: list[str] = []
    lock, lock_errors = read_lock(root)
    errors.extend(lock_errors)
    if lock is None:
        return errors, notes
    members, archive_errors = check_archive(root, lock, release)
    errors.extend(archive_errors)
    if members is not None:
        rebuild_errors, notes = check_source_rebuild(root, lock, require_siblings)
        errors.extend(rebuild_errors)
    return errors, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="the loquitur-protocol checkout to check (default: the one this tool is in)",
    )
    parser.add_argument(
        "--require-siblings",
        action="store_true",
        help=f"fail when {CORPUS_REPOSITORY} is not beside this repository (also set by {REQUIRE_SIBLINGS_ENV})",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors, notes = verify(root, args.require_siblings or _truthy(REQUIRE_SIBLINGS_ENV))
    if errors:
        for error in errors:
            print(error)
        return 1
    release = json.loads((root / "PROTOCOL_RELEASE.json").read_text(encoding="utf-8"))
    lock = json.loads((root / LOCK).read_text(encoding="utf-8"))
    print(f"protocol release ownership OK: {release['protocol_release_id']}, corpus {lock['corpus_id']}")
    for note in notes:
        print(note)
    print(
        "note: this checks the release artifacts, and that the pinned archive is the canonical build of "
        "its members with an exact content manifest and copies of this repository's normative files. "
        "It does not run any verifier over the corpus; tools/validate_corpus.py checks the corpus's "
        "own declarations."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
