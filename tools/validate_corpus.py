"""Validate a conformance corpus: the pinned archive, or an extraction of it.

    python tools/validate_corpus.py conformance/<corpus id>.zip
    python tools/validate_corpus.py ../corpus/loquitur-conformance

It checks what the corpus states about itself and nothing it would have to trust: the content
manifest lists every file exactly once with its size and SHA-256 and lists nothing else; every
profile names files the corpus carries and a compatibility class the protocol defines; every
declared run is well formed (a status, verdict and exit code `report-contract.md` pairs, reason and
error codes the reason-code catalog lists, inputs that lie under `vectors/` and exist, registered
vocabulary documents it names under `vectors/vocabularies/`); the schema fixtures, canonicalization
vectors, signature vectors, anchor-method vector, registered vocabulary fixtures and bundle seals
hold; and no file names a corpus id, since the archive never carries its own. Run inside a checkout of
loquitur-protocol, which it finds beside itself, it also checks that the corpus's copies of the
protocol's normative files equal this repository's. It runs no implementation: whether a verifier
reproduces the declared runs is what `conformance-testing.md` section 7 measures.

Given an archive, it first requires the archive to be the canonical build of its members
(`tools/corpus_archive.py`), then validates those members in a temporary directory.

Requires Python 3.11 or later, `jsonschema` and `cryptography`. Exit codes: 0 valid, 1 a check
failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_archive  # noqa: E402

MAX_SAFE_INTEGER = 2**53 - 1


SECP256K1_N = 115792089237316195423570985008687907852837564279074904382605163141518161494337


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utf16_sort_key(value: str) -> bytes:
    return value.encode("utf-16-be", "strict")


def reject_lone_surrogates(value: str) -> None:
    value.encode("utf-8", "strict")


def canonical_json(value: object) -> bytes:

    def render(item: object) -> str:
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, int) and (not isinstance(item, bool)):
            if abs(item) > MAX_SAFE_INTEGER:
                raise ValueError("integer outside safe range")
            return str(item)
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("non-finite number")
            if item.is_integer() and abs(item) > MAX_SAFE_INTEGER:
                raise ValueError("integer-valued number outside safe range")
            raise ValueError("non-integer numeric values require the independent ECMAScript JCS oracle profile")
        if isinstance(item, str):
            reject_lone_surrogates(item)
            return json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        if isinstance(item, list):
            return "[" + ",".join(render(x) for x in item) + "]"
        if isinstance(item, dict):
            if not all(isinstance(k, str) for k in item):
                raise ValueError("JSON object keys must be strings")
            keys = sorted(item, key=utf16_sort_key)
            return "{" + ",".join(render(k) + ":" + render(item[k]) for k in keys) + "}"
        raise ValueError(f"unsupported JSON type: {type(item).__name__}")

    return render(value).encode("utf-8")


AUTHORIZATION_STATUSES = (
    "AUTHORIZED_ACTIVE_KEY",
    "INVALID_REGISTRY_ENTRY",
    "INVALID_TRUST_REGISTRY",
    "ISSUER_NOT_FOUND",
    "ISSUER_KEY_NOT_FOUND",
    "TRUST_REGISTRY_AMBIGUOUS_KEY",
    "ISSUER_KEY_REVOKED",
    "ISSUER_KEY_SUSPENDED",
    "TRUST_REGISTRY_NOT_YET_EFFECTIVE",
    "TRUST_REGISTRY_EXPIRED",
    "ISSUER_KEY_NOT_YET_EFFECTIVE",
    "ISSUER_KEY_EXPIRED",
    "ISSUER_KEY_SCOPE_MISMATCH",
)


SIGNATURE_STATUSES = (
    "VALID_SIGNATURE",
    "MALFORMED_SIGNATURE",
    "UNSUPPORTED_SIGNING_PAYLOAD",
    "UNSUPPORTED_SIGNATURE_ALGORITHM",
    "SIGNATURE_KEY_MISMATCH",
    "SIGNATURE_INVALID",
)


def verify_declared_signature_statuses(root: Path, errors: list[str]) -> None:
    """Every status the signature vectors declare is one of section 8, and signature.json declares one.

    The migration vector declares errors rather than statuses (`signing-envelope-v2.md`): a
    status it does declare is still held to the vocabulary, and it need not declare one.
    """
    permitted = set(AUTHORIZATION_STATUSES) | set(SIGNATURE_STATUSES)
    for name in ("vectors/signature.json", "vectors/signature_payload_version.json"):
        document = json.loads((root / name).read_text(encoding="utf-8"))
        declared = {**document, **(document.get("expected") or {})}
        found = False
        for member, value in sorted(declared.items()):
            if not member.endswith("_status") or not isinstance(value, str):
                continue
            found = True
            if value not in permitted:
                errors.append(
                    f"{name} declares {member} {value!r}, which is no status of trust-registry-authorization.md section 8"
                )
        if not found and name == "vectors/signature.json":
            errors.append(f"{name} declares no signature status; the vocabulary rule would pass vacuously")


def verify_signature_vector(root: Path, errors: list[str]) -> None:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    except Exception as exc:
        errors.append(f"cryptography dependency unavailable: {exc}")
        return
    vector = json.loads((root / "vectors/signature.json").read_text(encoding="utf-8"))
    expected_prefix = b"LOQUITUR\x00REGISTRY_ENTRY\x00SIGNATURE\x00V2\x00"
    if bytes.fromhex(vector["domain_prefix_hex"]) != expected_prefix:
        errors.append("signature v2 domain prefix mismatch")
    if vector.get("payload_id") != "registry_entry_signing_payload_v2" or vector.get("payload_version") != 2:
        errors.append("signature v2 payload metadata mismatch")
    entry = dict(vector["signed_entry"])
    filtered = dict(entry)
    for field in ("signature", "anchor", "anchored_at"):
        filtered.pop(field, None)
    envelope = {
        "domain": "org.loquitur.protocol.registry-entry-signature",
        "envelope_schema": "loquitur.signing_envelope.v2",
        "envelope_version": 2,
        "payload": filtered,
        "payload_id": "registry_entry_signing_payload_v2",
        "payload_schema": "loquitur.registry_entry.v1",
        "signature_algorithm": "secp256k1_ecdsa_sha256",
    }
    if envelope != vector["signing_envelope"]:
        errors.append("signature v2 envelope mismatch")
    message = expected_prefix + canonical_json(envelope)
    if message.hex() != vector["signing_message_hex"]:
        errors.append("signature v2 exact message bytes mismatch")
    digest = "sha256:" + sha256_bytes(message)
    if digest != vector["signing_payload_sha256"]:
        errors.append("signature v2 payload hash mismatch")
    signature = bytes.fromhex(vector["signature_compact_hex"])
    if len(signature) != 64:
        errors.append("signature vector is not 64-byte compact encoding")
        return
    r = int.from_bytes(signature[:32], "big")
    sig_s = int.from_bytes(signature[32:], "big")
    if not (1 <= r < SECP256K1_N and 1 <= sig_s <= SECP256K1_N // 2):
        errors.append("signature vector violates r/s range or low-S")
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), bytes.fromhex(vector["public_key_hex"]))
    try:
        public.verify(encode_dss_signature(r, sig_s), message, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        errors.append("signature v2 vector does not verify independently")
    migration = json.loads((root / "vectors/signature_payload_version.json").read_text(encoding="utf-8"))
    errors.extend(migration_errors(migration))


def signing_message(entry: dict) -> bytes:
    """The v2 signing message of a registry entry (`signing-envelope-v2.md`)."""
    payload = {key: value for key, value in entry.items() if key not in ("signature", "anchor", "anchored_at")}
    envelope = {
        "domain": "org.loquitur.protocol.registry-entry-signature",
        "envelope_schema": "loquitur.signing_envelope.v2",
        "envelope_version": 2,
        "payload": payload,
        "payload_id": "registry_entry_signing_payload_v2",
        "payload_schema": "loquitur.registry_entry.v1",
        "signature_algorithm": "secp256k1_ecdsa_sha256",
    }
    return b"LOQUITUR\x00REGISTRY_ENTRY\x00SIGNATURE\x00V2\x00" + canonical_json(envelope)


ANCHOR_METHODS = "vectors/anchor-methods.json"
ANCHOR_METHOD_MEMBERS = frozenset({"schema_version", "public_key_hex", "signing_payload_sha256", "cases"})


def verify_anchor_methods(root: Path, errors: list[str]) -> None:
    """One signed entry has one `H`, with no anchor and under an anchor of each method.

    `anchor-commitment.md` section 1 binds whatever the method, and the anchor is outside the
    signing payload: every case's signing message has the declared digest, and the one signature
    every case carries verifies over it. The cases cover `anchor: null` and each method the
    corpus's baseline vocabulary registers, and each entry satisfies the registry-entry schema.
    """
    path = root / ANCHOR_METHODS
    if not path.is_file():
        return
    try:
        import jsonschema
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    except Exception as exc:
        errors.append(f"jsonschema or cryptography dependency unavailable: {exc}")
        return
    vector = json.loads(path.read_text(encoding="utf-8"))
    if set(vector) != ANCHOR_METHOD_MEMBERS:
        errors.append(f"{ANCHOR_METHODS} declares exactly {sorted(ANCHOR_METHOD_MEMBERS)}, not {sorted(vector)}")
        return
    schema = json.loads((root / "vectors/schemas/registry_entry.schema.json").read_text(encoding="utf-8"))
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), bytes.fromhex(vector["public_key_hex"]))
    methods = set()
    baseline = root / VOCABULARY_DIRECTORY / "baseline/anchoring_method.json"
    registered = set(json.loads(baseline.read_text(encoding="utf-8"))["values"]) if baseline.is_file() else set()
    for case in vector["cases"]:
        where = f"{ANCHOR_METHODS} case {case.get('id')!r}"
        entry = case.get("entry")
        if not isinstance(entry, dict):
            errors.append(f"{where}: carries no entry")
            continue
        for error in jsonschema.Draft202012Validator(schema).iter_errors(entry):
            errors.append(f"{where}: the entry breaks the registry-entry schema: {error.message}")
        anchor = entry.get("anchor")
        methods.add(None if anchor is None else anchor.get("method"))
        message = signing_message(entry)
        if "sha256:" + sha256_bytes(message) != vector["signing_payload_sha256"]:
            errors.append(f"{where}: the signing message's digest is not the declared H")
        signature = bytes.fromhex(entry["signature"]["signature"])
        r, s = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
        try:
            public.verify(encode_dss_signature(r, s), message, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            errors.append(f"{where}: the signature does not verify")
    expected = {None} | registered
    if not registered or methods != expected:
        errors.append(f"{ANCHOR_METHODS} covers {sorted(methods, key=str)}, not no anchor and each of {sorted(registered)}")
    signatures = {json.dumps(case.get("entry", {}).get("signature"), sort_keys=True) for case in vector["cases"]}
    if len(signatures) != 1:
        errors.append(f"{ANCHOR_METHODS}: the cases carry {len(signatures)} signatures, not the one signature of one entry")


# conformance-testing.md section 4.1: the registered vocabulary documents a run names, by kind.
VOCABULARY_KINDS = ("asset_type", "workflow", "anchoring_method")
VOCABULARY_DIRECTORY = "vectors/vocabularies"
VOCABULARY_META_SCHEMA = "protocol/docs/specification/registered-vocabularies/schema.json"
REFUSED_VOCABULARIES = "refused/"


def check_run_vocabularies(root: Path, case_id: str, case: dict, errors: list[str]) -> None:
    """A run's `vocabularies`: kinds of registered vocabulary to documents under vectors/vocabularies/."""
    if "vocabularies" not in case:
        return
    named = case["vocabularies"]
    if not isinstance(named, dict) or not named or not set(named) <= set(VOCABULARY_KINDS):
        errors.append(f"{case_id}: vocabularies maps one or more of {list(VOCABULARY_KINDS)} to a document")
        return
    for kind, relative in sorted(named.items()):
        if not isinstance(relative, str) or not relative.startswith("vocabularies/"):
            errors.append(f"{case_id}: the {kind} vocabulary is not a path under vectors/vocabularies/: {relative!r}")
        elif not (root / "vectors" / relative).is_file():
            errors.append(f"{case_id}: the {kind} vocabulary is missing: {relative}")


def _vocabulary_errors(document: object, meta: dict) -> list[str]:
    """Every way ``document`` breaks `verification-vocabularies.md` section 6."""
    import jsonschema

    found = [error.message for error in jsonschema.Draft202012Validator(meta).iter_errors(document)]
    if found or not isinstance(document, dict):
        return found or ["not an object"]

    def version(text: str) -> tuple[int, ...]:
        return tuple(int(part) for part in text.split("."))

    for value, entry in document["values"].items():
        if version(entry["since"]) > version(document["version"]):
            found.append(f"values/{value}: since is later than version")
        if ("asset_types" in entry) != (document["kind"] == "workflow"):
            found.append(f"values/{value}: asset_types is present exactly when kind is workflow")
        for member in ("title", "profile"):
            text = entry.get(member)
            if isinstance(text, str) and not text.strip(WHITESPACE_W):
                found.append(f"values/{value}/{member} is empty under W")
    return found


# The whitespace set W of bundle-objects.md.
WHITESPACE_W = "".join(
    chr(point)
    for point in [*range(0x09, 0x0E), *range(0x1C, 0x20), 0x20, 0x85, 0xA0, 0x1680, *range(0x2000, 0x200B)]
    + [0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF]
)


def verify_vocabulary_fixtures(root: Path, errors: list[str]) -> None:
    """The corpus's registered vocabularies hold section 6, and each refused one is refused.

    A document outside `refused/` satisfies the meta-schema the archive carries and the rules
    the schema cannot state, and is named after the kind it registers; `baseline/` holds one
    document of every kind. A document under `refused/` is named by a run that declares a
    refusal, and is refused where a run names it: it breaks section 6, is not strict JSON, or
    is named for a kind it does not register.
    """
    directory = root / VOCABULARY_DIRECTORY
    if not directory.is_dir():
        return
    try:
        import jsonschema  # noqa: F401
    except Exception as exc:
        errors.append(f"jsonschema dependency unavailable: {exc}")
        return
    meta_path = root / VOCABULARY_META_SCHEMA
    if not meta_path.is_file():
        errors.append(f"the corpus carries registered vocabularies and no {VOCABULARY_META_SCHEMA}")
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    baseline = sorted(path.stem for path in (directory / "baseline").glob("*.json"))
    if baseline != sorted(VOCABULARY_KINDS):
        errors.append(f"{VOCABULARY_DIRECTORY}/baseline/ holds {baseline}, not one document of each kind")
    runs = json.loads((root / "vectors/verify.json").read_text(encoding="utf-8")).values()
    uses: dict[str, list[tuple[str, bool]]] = {}
    for run in runs:
        for kind, relative in (run.get("vocabularies") or {}).items():
            refused = declares_a_refusal(run.get("expected"))
            uses.setdefault(relative, []).append((kind, refused))
    for path in sorted(directory.rglob("*.json")):
        relative = path.relative_to(root / "vectors").as_posix()
        under = path.relative_to(directory).as_posix()
        try:
            document = json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_strict_object)
        except ValueError:
            document = None
        if not under.startswith(REFUSED_VOCABULARIES):
            if document is None:
                errors.append(f"{relative} is not strict JSON")
                continue
            found = _vocabulary_errors(document, meta)
            errors.extend(f"{relative}: {error}" for error in found)
            if not found and document["kind"] != path.stem:
                errors.append(f"{relative} registers the kind {document['kind']}, not the one it is named after")
            continue
        named = uses.get(relative, [])
        if not named:
            errors.append(f"{relative} is a refused vocabulary no run names")
        for kind, refused in named:
            if not refused:
                errors.append(f"{relative} is named for {kind} by a run that does not declare a refusal")
            elif document is not None and not _vocabulary_errors(document, meta) and document.get("kind") == kind:
                errors.append(f"{relative} is named for {kind} and is a valid document of that kind")


SIGNING_PAYLOAD_ID = re.compile(r"registry_entry_signing_payload_v[1-9][0-9]{0,8}")


# conformance-testing.md section 4.2: everything the signing-payload vector declares.
PAYLOAD_VECTOR_MEMBERS = frozenset(
    {
        "schema_version",
        "automatic_fallback",
        "unknown_payload_entry",
        "unknown_payload_expected_error",
        "v2_metadata_stripped_entry",
        "v2_metadata_stripped_expected_error",
    }
)


def migration_errors(migration: object) -> list[str]:
    """What `vectors/signature_payload_version.json` must declare (`signing-envelope-v2.md`, `document-contracts.md`).

    No earlier signing payload is defined, so nothing falls back and the vector declares no outcome
    beside the two below: its members are a closed set. An entry whose signature names a
    well-formed later payload is an unsupported version of the signing payload (version gate 7),
    and an entry stripped of `payload_id` and `payload_version` breaks the entry's contract.
    """
    if not isinstance(migration, dict):
        return ["the migration vector is not a JSON object"]
    errors: list[str] = []
    if migration.get("automatic_fallback") is not False:
        errors.append("the migration vector must forbid automatic fallback")
    undeclared = sorted(set(migration) - PAYLOAD_VECTOR_MEMBERS)
    if undeclared:
        errors.append(f"the migration vector declares members outside its closed set: {undeclared}")
    signature = (migration.get("unknown_payload_entry") or {}).get("signature") or {}
    payload_id, payload_version = signature.get("payload_id"), signature.get("payload_version")
    well_formed = (
        isinstance(payload_id, str)
        and SIGNING_PAYLOAD_ID.fullmatch(payload_id) is not None
        and isinstance(payload_version, int)
        and not isinstance(payload_version, bool)
        and 1 <= payload_version <= 999999999
    )
    if not well_formed or (payload_id, payload_version) == ("registry_entry_signing_payload_v2", 2):
        errors.append("unknown_payload_entry does not name a well-formed unsupported signing payload")
    else:
        expected = {"code": "unsupported_version", "object": "signing_payload", "version": f"{payload_id}/{payload_version}"}
        if migration.get("unknown_payload_expected_error") != expected:
            errors.append(f"unknown_payload_expected_error is not {expected}")
    stripped = (migration.get("v2_metadata_stripped_entry") or {}).get("signature")
    if not isinstance(stripped, dict) or "payload_id" in stripped or "payload_version" in stripped:
        errors.append("v2_metadata_stripped_entry does not carry a signature stripped of payload_id and payload_version")
    if migration.get("v2_metadata_stripped_expected_error") != "registry_entry_contract_violation":
        errors.append("v2_metadata_stripped_expected_error is not registry_entry_contract_violation")
    return errors


def verify_canonicalization(root: Path, errors: list[str]) -> None:
    data = json.loads((root / "vectors/canonicalization.json").read_text(encoding="utf-8"))
    for case in data["canonicalize_ok"]:
        actual = canonical_json(case["input"])
        if actual.decode("utf-8") != case["canonical_utf8"]:
            errors.append(f"canonical UTF-8 mismatch: {case['name']}")
        if actual.hex() != case["canonical_hex"]:
            errors.append(f"canonical hex mismatch: {case['name']}")
        if "sha256:" + sha256_bytes(actual) != case["sha256"]:
            errors.append(f"canonical digest mismatch: {case['name']}")
    for case in data["canonicalize_reject"]:
        try:
            canonical_json(case["input"])
        except ValueError:
            pass
        else:
            errors.append(f"reject vector accepted: {case['name']}")
    unicode_cases = json.loads((root / "vectors/canonicalization_unicode.json").read_text(encoding="utf-8"))
    for case in unicode_cases:
        actual = canonical_json(case["value"])
        if actual.hex() != case["canonical_utf8_hex"]:
            errors.append(f"unicode canonicalization mismatch: {case['name']}")
    verify_jcs_numeric(root, errors)


def verify_jcs_numeric(root: Path, errors: list[str]) -> None:
    data = json.loads((root / "vectors/jcs-numeric.json").read_text(encoding="utf-8"))
    for spelling in data["reject"]:
        try:
            value = json.loads(spelling)
        except ValueError:
            continue
        try:
            canonical_json(value)
        except ValueError:
            pass
        else:
            errors.append(f"jcs-numeric reject vector accepted: {spelling}")
    for case in data["cases"]:
        if "value" not in case:
            continue
        if float(case["value"]).is_integer() and abs(case["value"]) > MAX_SAFE_INTEGER:
            errors.append(f"jcs-numeric case declares a serialization input strictness rule 2 refuses: {case['id']}")


def verify_schema_fixtures(root: Path, errors: list[str]) -> None:
    try:
        import jsonschema
    except Exception as exc:
        errors.append(f"jsonschema dependency unavailable: {exc}")
        return
    expected = json.loads((root / "vectors/schema-valid/expected.json").read_text(encoding="utf-8"))
    for case in expected["cases"]:
        fixture = json.loads((root / "vectors/schema-valid" / case["fixture"]).read_text(encoding="utf-8"))
        schema = json.loads((root / "vectors/schemas" / case["schema"]).read_text(encoding="utf-8"))
        try:
            jsonschema.Draft202012Validator(schema).validate(fixture)
        except Exception as exc:
            errors.append(f"schema-valid fixture rejected: {case['fixture']}: {exc}")


def recursively_collect_reason_codes(value: object, result: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "reason_codes" and isinstance(item, list):
                result.update(x for x in item if isinstance(x, str))
            recursively_collect_reason_codes(item, result)
    elif isinstance(value, list):
        for item in value:
            recursively_collect_reason_codes(item, result)


INTAKES = ("archive", "directory_only")


DECLARABLE_INTAKES = ("any",) + INTAKES


# report-contract.md section 3.3, in the order of its table: review_reasons lists them in this order.
REVIEW_REASONS = (
    "registry_entry_verdict_requires_review",
    "verification_receipt_not_provided",
    "evaluation_time_not_provided",
    "trust_registry_not_current",
    "issuer_key_outside_validity_window",
    "trust_root_outside_validity_window",
    "trust_registry_root_not_pinned",
    "bundle_reserved_member",
    "container_extra_files",
    "bundle_extra_files",
    "canonical_input_not_provided",
    "envelope_not_provided",
    "offline_review_required",
    "vocabulary_value_unknown",
)


# The checks of verification-checks.md, in their dependency order.
CHECKS = ("structure", "integrity", "link", "authorization")


# The objects a version gate names (document-contracts.md, "Version gate").
VERSIONED_OBJECTS = (
    "trust_root_document",
    "manifest",
    "verification_receipt",
    "reason_code_vocabulary",
    "registry_entry",
    "signing_payload",
    "trust_registry",
)


INSTANT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


REASONS_WITHOUT_AN_ERROR = frozenset(REVIEW_REASONS) | frozenset(
    {
        "local_integrity_registry_link_and_trust_checks_passed",
        "local_integrity_and_registry_link_checks_passed",
        "local_integrity_checks_passed",
        "trust_registry_verification_failed",
        "registry_link_verification_failed",
        "manifest_integrity_failed",
        "p1_integrity_failed",
        "envelope_integrity_or_link_failed",
        "offline_verification_failed",
    }
)


ERROR_CODES = (
    "input_not_found",
    "invalid_zip",
    "archive_unsafe_member",
    "archive_safety_limit",
    "bundle_root_invalid",
    "archive_load_failed",
    "unsupported_input",
    "filesystem_error",
    "bundle_inventory_failed",
    "bundle_member_name_invalid",
    "unsafe_bundle_member",
    "manifest_verification_failed",
    "manifest_read_failed",
    "p1_verification_failed",
    "p1_read_failed",
    "envelope_verification_failed",
    "envelope_incomplete",
    "envelope_read_failed",
    "verification_receipt_contract_violation",
    "registry_link_verification_failed",
    "registry_entry_contract_violation",
    "registry_entry_verdict_fail",
    "registry_link_read_failed",
    "trust_registry_requires_registry_entry",
    "trust_registry_requires_valid_registry_entry",
    "trust_registry_read_failed",
    "trust_root_read_failed",
    "trust_registry_root_not_authenticated",
    "unsupported_version",
    "internal_error",
)


L3_STATUSES = ("authorization_status", "signature_status", "trust_registry_root_signature_status")


OUTCOME_TUPLES = {
    ("OFFLINE_OK", "PASS", 0),
    ("OFFLINE_FAIL", "FAIL", 1),
    ("OFFLINE_REVIEW", "REVIEW", 2),
    ("INTERNAL_ERROR", None, 3),
    ("UNSUPPORTED_VERSION", None, 4),
    ("HOST_FAILURE", None, 5),
}


# The members a declared outcome may carry (conformance-testing.md section 4.1).
OUTCOME_MEMBERS = frozenset(
    {
        "status",
        "verdict",
        "exit_code",
        "reason",
        "errors",
        "trust_registry",
        "checks_requested",
        "checks_established",
        "review_reasons",
        "evaluation_time",
        "unsupported_version",
    }
)


REFUSAL_EXIT_CODE = 64


# conformance-testing.md section 4.1: what a run exercises, and the rules a summary run names.
SURFACES = ("verify", "summary")
VERDICT_GROUNDS_RULES = ("VG-1", "VG-2", "VG-3", "VG-4", "VG-5", "VG-6", "VG-7")
SUMMARY_RUNS = "vectors/summary-checks/expected.json"


def check_verify_run_members(case_id: str, case: dict, errors: list[str]) -> None:
    """A verification run's `surface`, `expected_command_line` and `informative_checks`
    (conformance-testing.md section 4.1)."""
    if case.get("surface", "verify") != "verify":
        errors.append(f"{case_id}: a run of this file exercises the surface verify, not {case.get('surface')!r}")
    # A refused invocation has no report, so it has no per-check results to record.
    if "informative_checks" in case and declares_a_refusal(case.get("expected")):
        errors.append(f"{case_id}: declares a refused invocation, which has no report, and records informative_checks")
    if "expected_command_line" in case:
        _check_declared_outcome(case_id, " [command line]", case["expected_command_line"], errors)
        if case["expected_command_line"] == case.get("expected"):
            errors.append(f"{case_id}: declares the same answer for a command line, so it declares no expected_command_line")


def summary_run_errors(case: object) -> list[str]:
    """What one summary run must declare (conformance-testing.md section 4.1)."""
    if not isinstance(case, dict):
        return ["a summary run is not a JSON object"]
    where = f"summary run {case.get('id')!r}"
    errors: list[str] = []
    if case.get("surface") != "summary":
        errors.append(f"{where}: surface is not summary")
    if not isinstance(case.get("summary"), str):
        errors.append(f"{where}: names no summary document")
    named = sorted(
        set(case) & {"bundle", "input", "registry_entry", "trust_registry", "trust_root", "evaluation_time", "vocabularies"}
    )
    if named:
        errors.append(f"{where}: names inputs of a verification run: {named}")
    expected = case.get("expected")
    rules = expected.get("violated_rules") if isinstance(expected, dict) else None
    if not isinstance(expected, dict) or sorted(expected) != ["violated_rules"] or not isinstance(rules, list):
        errors.append(f"{where}: expected is not exactly {{'violated_rules': [...]}}")
        return errors
    if any(rule not in VERDICT_GROUNDS_RULES for rule in rules) or rules != sorted(set(rules), key=VERDICT_GROUNDS_RULES.index):
        errors.append(f"{where}: violated_rules is not a list of VG-1 to VG-7 in rule order, once each: {rules!r}")
    elif any(rule in rules for rule in ("VG-1", "VG-2")) and len(rules) != 1:
        errors.append(f"{where}: a violation of VG-1 or VG-2 stops the check, so it is the only rule listed: {rules!r}")
    return errors


def verify_summary_runs(root: Path, errors: list[str]) -> None:
    path = root / SUMMARY_RUNS
    if not path.is_file():
        return
    cases = json.loads(path.read_text(encoding="utf-8")).get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{SUMMARY_RUNS}: declares no cases")
        return
    for case in cases:
        errors.extend(summary_run_errors(case))
        if isinstance(case, dict) and isinstance(case.get("summary"), str) and not (root / "vectors" / case["summary"]).is_file():
            errors.append(f"summary run {case.get('id')!r}: summary missing: {case['summary']}")


def declares_a_refusal(expected: object) -> bool:
    return isinstance(expected, dict) and "report" in expected and (expected["report"] is None)


def _check_declared_outcome(case_id: str, label: str, expected: object, errors: list[str]) -> None:
    where = f"declared outcome {case_id}{label}"
    if not isinstance(expected, dict):
        errors.append(f"{where}: not an object")
        return
    if declares_a_refusal(expected):
        extra = sorted(set(expected) - {"exit_code", "report"})
        if extra:
            errors.append(f"{where}: declares a refused invocation, which has no report, beside {extra}")
        if expected.get("exit_code") != REFUSAL_EXIT_CODE:
            errors.append(
                f"{where}: declares a refused invocation with exit code {expected.get('exit_code')!r}, and report-contract.md section 4 gives it {REFUSAL_EXIT_CODE}"
            )
        return
    unknown = sorted(set(expected) - OUTCOME_MEMBERS)
    if unknown:
        errors.append(f"{where}: declares members outside the normative surface: {unknown}")
    triple = (expected.get("status"), expected.get("verdict"), expected.get("exit_code"))
    if triple not in OUTCOME_TUPLES:
        errors.append(f"{where}: invalid status, verdict and exit code: {triple}")
    codes = expected.get("errors")
    if not isinstance(codes, list) or any(code not in ERROR_CODES for code in codes):
        errors.append(f"{where}: errors is not a list of report-contract.md section 5.3 codes: {codes!r}")
        return
    if len(set(codes)) != len(codes):
        errors.append(f"{where}: the same error code appears twice: {codes}")
    positions = [ERROR_CODES.index(code) for code in codes]
    if positions != sorted(positions):
        errors.append(f"{where}: the error codes are not in the order of the section 5.3 table: {codes}")
    reason = expected.get("reason")
    if codes:
        if reason != codes[0]:
            errors.append(
                f"{where}: the run carries an error, so section 5.2 rule 1 names its first code {codes[0]!r}, not {reason!r}"
            )
    elif reason not in REASONS_WITHOUT_AN_ERROR:
        errors.append(f"{where}: outcome.reason {reason!r} is outside the closed vocabulary of section 5.2")
    trust = expected.get("trust_registry", _ABSENT)
    if trust is _ABSENT:
        errors.append(f"{where}: does not say whether the trust registry was evaluated")
    elif trust is not None:
        if not isinstance(trust, dict) or sorted(trust) != sorted(L3_STATUSES):
            errors.append(f"{where}: an evaluated trust registry declares exactly the three statuses of section 5.4")
    _check_declared_report_members(where, expected, codes, errors)


def _check_declared_report_members(where: str, expected: dict, codes: list, errors: list[str]) -> None:
    """The members report-contract.md sections 3.2, 3.3 and 5.5 add, where a run declares them."""
    requested = expected.get("checks_requested", _ABSENT)
    established = expected.get("checks_established", _ABSENT)
    if requested is not _ABSENT and (
        not isinstance(requested, list) or requested[:2] != list(CHECKS[:2]) or requested != [c for c in CHECKS if c in requested]
    ):
        errors.append(f"{where}: checks_requested is not structure and integrity followed by checks in their order: {requested!r}")
    if established is not _ABSENT:
        prefix = requested if isinstance(requested, list) else list(CHECKS)
        if not isinstance(established, list) or established != prefix[: len(established)]:
            errors.append(f"{where}: checks_established is not a prefix of the checks requested: {established!r}")
        elif expected.get("status") == "OFFLINE_OK" and established != prefix:
            errors.append(f"{where}: an OFFLINE_OK run establishes every check it requested (section 3.2)")
        elif expected.get("verdict") is None and established:
            errors.append(f"{where}: a run whose status is not an evidence outcome establishes no check (section 3.2)")
    reasons = expected.get("review_reasons", _ABSENT)
    if reasons is not _ABSENT:
        if not isinstance(reasons, list) or any(r not in REVIEW_REASONS for r in reasons):
            errors.append(f"{where}: review_reasons is not a list of section 3.3 reasons: {reasons!r}")
        elif [REVIEW_REASONS.index(r) for r in reasons] != sorted({REVIEW_REASONS.index(r) for r in reasons}):
            errors.append(f"{where}: review_reasons is not in the order of the section 3.3 table, once each: {reasons}")
        elif expected.get("status") == "OFFLINE_REVIEW" and (not reasons or expected.get("reason") != reasons[0]):
            errors.append(f"{where}: an OFFLINE_REVIEW run names its first review reason as outcome.reason (section 5.2)")
        elif expected.get("status") in ("OFFLINE_OK", "UNSUPPORTED_VERSION", "INTERNAL_ERROR") and reasons:
            errors.append(f"{where}: a {expected.get('status')} run holds no review reason")
    when = expected.get("evaluation_time", _ABSENT)
    if when is not _ABSENT and when is not None and not (isinstance(when, str) and INSTANT.fullmatch(when)):
        errors.append(f"{where}: evaluation_time is neither null nor one instant YYYY-MM-DDTHH:MM:SSZ: {when!r}")
    gate = expected.get("unsupported_version", _ABSENT)
    if gate is not _ABSENT:
        if (
            not isinstance(gate, dict)
            or sorted(gate) != ["object", "version"]
            or gate.get("object") not in VERSIONED_OBJECTS
            or not isinstance(gate.get("version"), str)
        ):
            errors.append(f"{where}: unsupported_version declares an object of the gate table and its version: {gate!r}")
        if codes != ["unsupported_version"]:
            errors.append(f"{where}: declares unsupported_version without the run's only error unsupported_version")
    elif codes == ["unsupported_version"]:
        errors.append(f"{where}: declares the error unsupported_version without the object and version it names")


_ABSENT = object()


def reason_surface(report: dict) -> dict:
    trust = report.get("trust_registry")
    gate = next((error for error in report.get("errors") or [] if error.get("code") == "unsupported_version"), None)
    return {
        "status": report.get("status"),
        "verdict": report.get("verdict"),
        "exit_code": report.get("exit_code"),
        "reason": (report.get("outcome") or {}).get("reason"),
        "errors": [error.get("code") for error in report.get("errors") or []],
        "trust_registry": None if trust is None else {name: trust.get(name) for name in L3_STATUSES},
        "checks_requested": report.get("checks_requested"),
        "checks_established": report.get("checks_established"),
        "review_reasons": report.get("review_reasons"),
        "evaluation_time": report.get("evaluation_time"),
        "unsupported_version": None if gate is None else {"object": gate.get("object"), "version": gate.get("version")},
    }


def reference_outcome(case: dict, intake: str) -> dict | None:
    by_intake = case.get("expected_by_intake")
    if isinstance(by_intake, dict):
        value = by_intake.get(intake)
        return value if isinstance(value, dict) else None
    expected = case.get("expected")
    if not isinstance(expected, dict):
        return None
    declared = case.get("intake")
    if declared in ("any", intake):
        return expected
    return None


def additional_negative_cases(root: Path) -> dict[str, dict]:
    document = json.loads((root / "vectors/additional-negatives/expected.json").read_text(encoding="utf-8"))
    return {f"additional-negatives/expected.json:{case['id']}": case for case in document["cases"]}


DECLARED_REASON_CODE_NEGATIVES = {
    "bundles/receipt_reason_code_nul_joined_bundle/verification_receipt.json": "two reason codes joined by a NUL, where the entry beside it cites them separately",
    "bundles/receipt_reason_code_padded_bundle/verification_receipt.json": "a reason code with a space on each side, which is compared as written",
    "bundles/receipt_reason_code_unknown_bundle/verification_receipt.json": "a receipt citing a code outside the closed vocabulary, which its contract refuses",
    "entry-contract/entry_reason_codes_unknown.json": "an entry citing a code outside the closed vocabulary, refused at the link check",
    "entry-contract/authorization_entry_reason_codes_unknown.json": "an entry citing a code outside the closed vocabulary, refused at the authorization check",
    "summary-checks/a_code_the_catalog_does_not_define.json": "a summary citing a code outside the closed vocabulary, which breaks VG-2",
}


DECLARED_UNSEALED_LINKS = {
    "envelope_manifest_digest_not_lowercase_bundle": (
        "bundle_manifest_sha256",
        "this bundle's manifest digest in upper case, which is not 64 lowercase hexadecimal characters",
    ),
    "envelope_p1_digest_wrong_length_bundle": (
        "p1_sha256",
        "this bundle's P1 digest one character short, which is not 64 characters",
    ),
    "envelope_bundle_id_not_a_string_bundle": (
        "bundle_id",
        "this bundle's identifier inside a container, which is not converted to a string",
    ),
}


def verify_bundle_seals(root: Path, errors: list[str]) -> None:
    declared = json.loads((root / "vectors/bundles/manifest.json").read_text(encoding="utf-8"))["cases"]
    bundles = sorted({root / "vectors/bundles" / case["bundle"] for case in declared})
    if not bundles:
        errors.append("vectors/bundles/manifest.json declares no bundle; the seal rule would pass vacuously")
        return
    for bundle in bundles:
        manifest_path = bundle / "manifest.json"
        if not manifest_path.is_file():
            errors.append(f"bundle seal: {bundle.name} has no manifest.json")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bundle_id = manifest.get("bundle_id")
        # The sidecars carry the bare digest; every JSON document carries it with its label
        # (canonicalization-and-hashing.md section 2).
        manifest_digest = "sha256:" + (bundle / "manifest.sha256").read_text(encoding="utf-8").strip()
        envelope_path = bundle / "envelope_env1.json"
        if envelope_path.is_file():
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
            deviation = DECLARED_UNSEALED_LINKS.get(bundle.name, (None, ""))[0]
            if envelope.get("bundle_id") != bundle_id and deviation != "bundle_id":
                errors.append(
                    f"bundle seal: {bundle.name}/envelope_env1.json seals bundle_id {envelope.get('bundle_id')!r}, not {bundle_id!r}"
                )
            if envelope.get("bundle_manifest_sha256") != manifest_digest and deviation != "bundle_manifest_sha256":
                errors.append(
                    f"bundle seal: {bundle.name}/envelope_env1.json links a manifest digest that is not this bundle's manifest"
                )
            p1_sidecar = bundle / "p1.sha256"
            p1_digest = "sha256:" + p1_sidecar.read_text(encoding="utf-8").strip() if p1_sidecar.is_file() else None
            if p1_digest is not None:
                if envelope.get("p1_sha256") != p1_digest and deviation != "p1_sha256":
                    errors.append(
                        f"bundle seal: {bundle.name}/envelope_env1.json links a P1 digest that is not this bundle's P1"
                    )
            if deviation is not None:
                sealed = {"bundle_id": bundle_id, "bundle_manifest_sha256": manifest_digest, "p1_sha256": p1_digest}[
                    deviation
                ]
                if envelope.get(deviation) == sealed:
                    errors.append(
                        f"bundle seal: {bundle.name}/envelope_env1.json is declared to deviate in {deviation} and seals this bundle correctly"
                    )
            envelope_sidecar = (bundle / "envelope.sha256").read_text(encoding="utf-8").strip()
            if envelope_sidecar != hashlib.sha256(canonical_json(envelope)).hexdigest():
                errors.append(f"bundle seal: {bundle.name}/envelope.sha256 does not match its envelope")
        receipt_path = bundle / "verification_receipt.json"
        if receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("bundle_id") != bundle_id:
                errors.append(
                    f"bundle seal: {bundle.name}/verification_receipt.json declares bundle_id {receipt.get('bundle_id')!r}, not {bundle_id!r}"
                )
            if receipt.get("manifest_sha256") != manifest_digest:
                errors.append(
                    f"bundle seal: {bundle.name}/verification_receipt.json cites a manifest digest that is not this bundle's manifest"
                )


DOCUMENT_INPUTS = ("registry_entry", "trust_registry", "trust_root")


NOT_A_REGULAR_FILE = "not_a_regular_file"


def check_document_paths(root: Path, case_id: str, case: dict, errors: list[str]) -> None:
    declared = case.get(NOT_A_REGULAR_FILE, [])
    named = {field for field in DOCUMENT_INPUTS + ("input",) if case.get(field)}
    if not isinstance(declared, list) or not set(declared) <= named:
        errors.append(
            f"{case_id}: {NOT_A_REGULAR_FILE} lists only inputs the run names, out of {list(DOCUMENT_INPUTS) + ['input']}"
        )
        return
    for field in DOCUMENT_INPUTS:
        if not case.get(field):
            continue
        path = root / "vectors" / str(case[field])
        if field in declared:
            if path.is_file():
                errors.append(
                    f"{case_id}: declares that its {field} path names no regular file, and it names one: {case[field]}"
                )
        elif not path.is_file():
            errors.append(f"{case_id}: {field} missing: {case[field]}")


def verify_expected_outcomes(root: Path, errors: list[str]) -> None:
    verify_data = json.loads((root / "vectors/verify.json").read_text(encoding="utf-8"))
    for case_id, case in verify_data.items():
        named = [field for field in ("bundle", "input") if case.get(field)]
        if len(named) != 1:
            errors.append(f"verify case {case_id}: names exactly one of bundle or input, not {named}")
        elif "bundle" in named:
            bundle = root / "vectors/bundles" / str(case["bundle"])
            if not bundle.is_dir():
                errors.append(f"verify case bundle missing: {case_id}: {bundle.name}")
        else:
            # conformance-testing.md section 4.1: an input that names nothing is the run's question
            # only where the run says so, and then nothing may be there.
            source = root / "vectors" / str(case["input"])
            absent = "input" in (case.get(NOT_A_REGULAR_FILE) or [])
            if absent and (source.exists() or source.is_symlink()):
                errors.append(f"verify case {case_id}: declares that its input names nothing, and it names something")
            elif not absent and not source.exists():
                errors.append(f"verify case input missing: {case_id}: {case['input']}")
        check_document_paths(root, f"verify case {case_id}", case, errors)
        check_run_vocabularies(root, f"verify case {case_id}", case, errors)
        check_verify_run_members(f"verify case {case_id}", case, errors)
        by_intake = case.get("expected_by_intake")
        if (case.get("expected") is None) == (by_intake is None):
            errors.append(
                f"verify case {case_id}: declares exactly one of expected (with intake) or expected_by_intake"
            )
            continue
        if by_intake is None:
            intake = case.get("intake")
            if intake not in DECLARABLE_INTAKES:
                errors.append(f"verify case {case_id}: intake {intake!r} is not one of {list(DECLARABLE_INTAKES)}")
            _check_declared_outcome(case_id, "", case["expected"], errors)
        else:
            if "intake" in case:
                errors.append(f"verify case {case_id}: declares an outcome per intake, so it names no single intake")
            if not isinstance(by_intake, dict) or sorted(by_intake) != sorted(INTAKES):
                errors.append(f"verify case {case_id}: expected_by_intake declares exactly {list(INTAKES)}")
                continue
            for intake in INTAKES:
                _check_declared_outcome(case_id, f" [{intake}]", by_intake[intake], errors)
            if by_intake[INTAKES[0]] == by_intake[INTAKES[1]]:
                errors.append(
                    f"verify case {case_id}: declares the same outcome under both intakes, so it is not intake-dependent and names one intake instead"
                )
    bundle_cases = json.loads((root / "vectors/bundles/manifest.json").read_text(encoding="utf-8"))["cases"]
    for case in bundle_cases:
        case_id = f"bundles/manifest.json:{case['id']}"
        if not (root / "vectors/bundles" / str(case.get("bundle"))).is_dir():
            errors.append(f"{case_id}: names no bundle directory")
        if case.get("intake") not in DECLARABLE_INTAKES:
            errors.append(f"{case_id}: intake {case.get('intake')!r} is not one of {list(DECLARABLE_INTAKES)}")
        check_document_paths(root, case_id, case, errors)
        check_run_vocabularies(root, case_id, case, errors)
        check_verify_run_members(case_id, case, errors)
        _check_declared_outcome(case_id, "", case.get("expected"), errors)
    for case_id, case in additional_negative_cases(root).items():
        check_document_paths(root, case_id, case, errors)
        check_run_vocabularies(root, case_id, case, errors)
        check_verify_run_members(case_id, case, errors)
        if not (root / "vectors/bundles" / str(case.get("bundle"))).is_dir():
            errors.append(f"{case_id}: names no bundle directory")
        if case.get("intake") not in DECLARABLE_INTAKES:
            errors.append(f"{case_id}: intake {case.get('intake')!r} is not one of {list(DECLARABLE_INTAKES)}")
        _check_declared_outcome(case_id, "", case.get("expected"), errors)
    verify_summary_runs(root, errors)
    catalog_root = root / "protocol/docs/specification/reason-codes"
    catalog_candidates = sorted(catalog_root.glob("v*/catalog.json"))
    if len(catalog_candidates) != 1:
        errors.append(
            f"expected exactly one reason-code catalog version in the corpus, found {[p.parent.name for p in catalog_candidates]}"
        )
        return errors
    catalog = json.loads(catalog_candidates[0].read_text(encoding="utf-8"))
    known = set(catalog["entries"])
    used: set[str] = set()
    declared_negatives: set[str] = set()
    for path in (root / "vectors").rglob("*.json"):
        if not path.is_file():
            continue
        if "schema-negative" in path.parts:
            continue
        relative = path.relative_to(root / "vectors").as_posix()
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            # Not JSON, not UTF-8 (both ValueError), or an integer past the interpreter's digit
            # limit: a strict-parsing vector the walks have nothing to read in.
            continue
        if relative in DECLARED_REASON_CODE_NEGATIVES:
            declared_negatives.add(relative)
            own: set[str] = set()
            recursively_collect_reason_codes(document, own)
            if not own - known:
                errors.append(
                    f"{relative} is declared to carry a reason code the catalog does not list, and carries none: {DECLARED_REASON_CODE_NEGATIVES[relative]}"
                )
            continue
        recursively_collect_reason_codes(document, used)
    for relative in sorted(set(DECLARED_REASON_CODE_NEGATIVES) - declared_negatives):
        errors.append(
            f"{relative} is declared to carry a reason code the catalog does not list, and is not a document of this corpus"
        )
    unknown = sorted(used - known)
    if unknown:
        errors.append(f"vectors use unknown reason codes: {unknown}")


def _collect_enums_with_value(value: object, target: str, result: list[list[object]]) -> None:
    if isinstance(value, dict):
        enum = value.get("enum")
        if isinstance(enum, list) and target in enum:
            result.append(enum)
        for child in value.values():
            _collect_enums_with_value(child, target, result)
    elif isinstance(value, list):
        for child in value:
            _collect_enums_with_value(child, target, result)


IDENTIFIER_GRAMMAR = "^[a-z0-9][a-z0-9_]{0,63}$"


def verify_cryptographic_capabilities(root: Path, errors: list[str]) -> None:
    vector = json.loads((root / "vectors/cryptographic_capabilities.json").read_text(encoding="utf-8"))
    capability = json.loads((root / "protocol/CRYPTOGRAPHIC_CAPABILITIES.json").read_text(encoding="utf-8"))
    expected = vector["expected"]
    algorithms = [item["id"] for item in capability["signature_algorithms"]]
    if algorithms != expected["signature_algorithms"]:
        errors.append("capability signature algorithm mismatch")
    if capability["trust_registry_key_types"] != expected["trust_registry_key_types"]:
        errors.append("capability trust key type mismatch")
    if capability.get("unknown_algorithm_policy") != "reject" or capability.get("automatic_fallback") is not False:
        errors.append("capability fail-closed policy mismatch")
    reserved = [item["id"] for item in capability.get("reserved_not_supported", [])]
    if reserved != expected["reserved_not_supported"]:
        errors.append("reserved algorithm set mismatch")
    registry_schema = json.loads((root / "vectors/schemas/registry_entry.schema.json").read_text(encoding="utf-8"))
    trust_schema = json.loads((root / "vectors/schemas/trust_registry.schema.json").read_text(encoding="utf-8"))
    # The schemas admit any well-formed identifier and name no allowlist: the verifier's own closed
    # allowlist decides at the signature step (canonicalization-and-hashing.md, algorithm agility).
    def grammar_only(node: dict, where: str) -> None:
        if node.get("pattern") != IDENTIFIER_GRAMMAR or "enum" in node or "const" in node:
            errors.append(f"{where} is not the identifier grammar alone: {node}")

    registry_branches = registry_schema["properties"]["signature"]["oneOf"]
    for branch in registry_branches:
        props = branch.get("properties", {})
        if "algorithm" in props:
            grammar_only(props["algorithm"], f"registry signature algorithm ({branch.get('title')})")
    entry = trust_schema["properties"]["entries"]["items"]
    grammar_only(entry["properties"]["key_type"], "trust registry key_type")
    grammar_only(trust_schema["properties"]["signature"]["properties"]["algorithm"], "trust registry signature algorithm")
    for case in vector["positive_cases"]:
        if case.get("accepted") is not True:
            errors.append(f"positive capability case is not accepted: {case.get('id')}")
    for case in vector["negative_cases"]:
        if case.get("accepted") is not False:
            errors.append(f"negative capability case is not rejected: {case.get('id')}")


def _enum_from_schema(schema: dict[str, object], property_name: str) -> list[str] | None:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return None
    prop = properties.get(property_name)
    if not isinstance(prop, dict):
        return None
    enum = prop.get("enum")
    if not isinstance(enum, list) or not all(isinstance(value, str) for value in enum):
        return None
    return list(enum)


def verify_vector_declared_digests(root: Path, errors: list[str]) -> None:
    for vector_path in sorted((root / "vectors").rglob("*.json")):
        if not vector_path.is_file():
            continue
        try:
            document = json.loads(vector_path.read_text(encoding="utf-8"))
        except ValueError:
            # Not JSON, not UTF-8 (both ValueError), or an integer past the interpreter's digit
            # limit: a strict-parsing vector the walks have nothing to read in.
            continue
        name = vector_path.relative_to(root).as_posix()

        def check(node: object, name: str = name) -> None:
            if isinstance(node, list):
                for item in node:
                    check(item)
                return
            if not isinstance(node, dict):
                return
            for key, value in node.items():
                if key.endswith("_sha256") and isinstance(value, str):
                    declared_path = node.get(f"{key[: -len('_sha256')]}_path")
                    if not isinstance(declared_path, str):
                        continue
                    target = root / declared_path
                    if not target.is_file():
                        errors.append(f"{name}: {key} names a file the corpus does not carry: {declared_path}")
                    elif sha256_file(target) != value:
                        errors.append(f"{name}: {key} does not match {declared_path}")
                else:
                    check(value)

        check(document)


def _strict_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _corpus_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for current, directories, names in os.walk(root):
        directories.sort()
        for name in names:
            path = Path(current) / name
            files[path.relative_to(root).as_posix()] = path
    return files


def check_manifest(root: Path, errors: list[str]) -> dict | None:
    """The content manifest lists every other file exactly, and its profiles name what exists."""
    path = root / corpus_archive.MANIFEST
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except (OSError, ValueError) as exc:
        errors.append(f"{corpus_archive.MANIFEST} cannot be read as strict JSON ({exc})")
        return None
    if not isinstance(manifest, dict) or set(manifest) != {"files", "profiles", "schema_version"}:
        errors.append(f"{corpus_archive.MANIFEST} holds exactly files, profiles and schema_version")
        return None
    if manifest["schema_version"] != corpus_archive.MANIFEST_SCHEMA:
        errors.append(f"unknown manifest schema_version {manifest['schema_version']!r}")
    present = _corpus_files(root)
    present.pop(corpus_archive.MANIFEST, None)
    listed: set[str] = set()
    for entry in manifest["files"] if isinstance(manifest["files"], list) else []:
        if not isinstance(entry, dict) or set(entry) != {"bytes", "path", "sha256"}:
            errors.append(f"malformed manifest file entry: {entry!r}")
            continue
        name = entry["path"]
        if name in listed:
            errors.append(f"the manifest lists {name} twice")
            continue
        listed.add(name)
        file = present.get(name)
        if file is None:
            errors.append(f"the manifest lists a file the corpus does not carry: {name}")
            continue
        data = file.read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            errors.append(f"{name} does not hold the size and digest the manifest lists")
    for name in sorted(set(present) - listed):
        errors.append(f"the corpus carries a file the manifest does not list: {name}")
    classes_path = root / "protocol/docs/specification/compatibility-classes.json"
    try:
        known = {entry["id"] for entry in json.loads(classes_path.read_text(encoding="utf-8"))["classes"]}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"protocol/docs/specification/compatibility-classes.json cannot be read ({exc})")
        known = set()
    seen: set[str] = set()
    profiles = manifest["profiles"] if isinstance(manifest["profiles"], list) else []
    if not profiles:
        errors.append("the manifest declares no profile")
    for profile in profiles:
        if not isinstance(profile, dict) or set(profile) != {"compatibility_class", "files", "id"}:
            errors.append(f"malformed profile: {profile!r}")
            continue
        if profile["id"] in seen:
            errors.append(f"profile {profile['id']} is declared twice")
        seen.add(profile["id"])
        if profile["compatibility_class"] not in known:
            errors.append(f"profile {profile['id']} declares an unknown compatibility class")
        for name in profile["files"]:
            if name not in present:
                errors.append(f"profile {profile['id']} names a file the corpus does not carry: {name}")
    return manifest


def check_no_corpus_id(root: Path, errors: list[str]) -> None:
    """No file names a corpus id: the id is derived from the archive's bytes and is never inside them."""
    needle = corpus_archive.ID_PREFIX.encode("ascii")
    for name, path in sorted(_corpus_files(root).items()):
        data = path.read_bytes()
        index = data.find(needle)
        while index != -1:
            if re.fullmatch(rb"[0-9a-f]{16}", data[index + len(needle) : index + len(needle) + 16]):
                errors.append(f"{name} names a corpus id")
                break
            index = data.find(needle, index + 1)


def check_protocol_copies(root: Path, protocol: Path, errors: list[str]) -> None:
    """The corpus's copies of the protocol's normative files equal the files of ``protocol``."""
    pairs = [("protocol/" + path, path) for path in corpus_archive.PROTOCOL_COPIES]
    schemas = protocol / corpus_archive.SCHEMA_COPIES_DIRECTORY
    expected_schemas = sorted(path.name for path in schemas.glob("*.json"))
    carried_schemas = sorted(path.name for path in (root / corpus_archive.VECTOR_SCHEMAS_DIRECTORY).glob("*.json"))
    if expected_schemas != carried_schemas:
        errors.append(f"vectors/schemas/ carries {carried_schemas}, the protocol defines {expected_schemas}")
    pairs += [
        (corpus_archive.VECTOR_SCHEMAS_DIRECTORY + name, corpus_archive.SCHEMA_COPIES_DIRECTORY + name)
        for name in expected_schemas
        if name in carried_schemas
    ]
    for copy, source in pairs:
        try:
            equal = (root / copy).read_bytes() == (protocol / source).read_bytes()
        except OSError as exc:
            errors.append(f"{copy} cannot be compared with {source} ({type(exc).__name__})")
            continue
        if not equal:
            errors.append(f"{copy} differs from loquitur-protocol {source}")


def declared_runs(root: Path) -> int:
    """The number of declared runs: `verify.json`, the additional negatives and the bundle runs."""
    verify = json.loads((root / "vectors/verify.json").read_text(encoding="utf-8"))
    bundles = json.loads((root / "vectors/bundles/manifest.json").read_text(encoding="utf-8"))["cases"]
    return len(verify) + len(additional_negative_cases(root)) + len(bundles)


def validate_tree(root: Path, protocol: Path | None) -> list[str]:
    """Every error found in the extracted corpus at ``root``; an empty list when it is valid."""
    errors: list[str] = []
    if check_manifest(root, errors) is None:
        return errors
    check_no_corpus_id(root, errors)
    if protocol is not None:
        check_protocol_copies(root, protocol, errors)
    for check in (
        verify_bundle_seals,
        verify_canonicalization,
        verify_jcs_numeric,
        verify_signature_vector,
        verify_anchor_methods,
        verify_vocabulary_fixtures,
        verify_declared_signature_statuses,
        verify_schema_fixtures,
        verify_cryptographic_capabilities,
        verify_expected_outcomes,
        verify_vector_declared_digests,
    ):
        try:
            check(root, errors)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors.append(f"{check.__name__} could not complete ({type(exc).__name__}: {exc})")
    return errors


def validate(path: Path, protocol: Path | None) -> tuple[list[str], dict]:
    """Validate the archive or extracted corpus at ``path``; returns the errors and a summary."""
    if path.is_file():
        data = path.read_bytes()
        try:
            members = corpus_archive.members_of(data)
        except corpus_archive.CanonicalArchiveError as exc:
            return [f"{path.name} is not a canonical corpus archive: {exc}"], {}
        with tempfile.TemporaryDirectory(prefix="corpus-") as scratch:
            for name, content in members.items():
                target = Path(scratch) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            errors, summary = validate(Path(scratch) / corpus_archive.PREFIX.rstrip("/"), protocol)
        summary["corpus_id"] = corpus_archive.corpus_id(data)
        return errors, summary
    errors = validate_tree(path, protocol)
    summary: dict = {"files": len(_corpus_files(path))}
    if not errors:
        summary["declared_runs"] = declared_runs(path)
    return errors, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", type=Path, help="the corpus archive, or the root of an extraction of it")
    parser.add_argument(
        "--protocol",
        type=Path,
        default=None,
        help="a loquitur-protocol checkout whose normative files the copies must equal "
        "(default: the checkout this tool sits in)",
    )
    args = parser.parse_args(argv)
    protocol = args.protocol or Path(__file__).resolve().parents[1]
    if not (protocol / "docs/specification/NORMATIVE_ARTIFACTS.json").is_file():
        protocol = None
    if not args.corpus.exists():
        print(f"no such file or directory: {args.corpus}", file=sys.stderr)
        return 2
    errors, summary = validate(args.corpus.resolve(), protocol.resolve() if protocol else None)
    for error in errors:
        print(error)
    if errors:
        return 1
    print("corpus OK: " + json.dumps(summary, sort_keys=True))
    if protocol is None:
        print("note: no loquitur-protocol checkout was found, so the protocol copies were not compared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
