"""tools/validate_corpus.py accepts the pinned corpus and refuses each defect planted in a copy of it."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from conftest import tool

ROOT = Path(__file__).resolve().parents[1]


validator = tool("validate_corpus")
ca = validator.corpus_archive


def _pinned() -> Path:
    lock = json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
    return ROOT / lock["artifact"]


@pytest.fixture(scope="module")
def pinned_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The pinned archive's members, written once and made read-only."""
    destination = tmp_path_factory.mktemp("pinned")
    for name, data in ca.members_of(_pinned().read_bytes()).items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        os.chmod(target, 0o444)
    return destination / ca.PREFIX.rstrip("/")


def _copy(shared: Path, destination: Path, changed: dict[str, bytes | None]) -> Path:
    """A tree of ``shared`` with ``changed`` written (None removes); other files are hard links."""
    for current, _, names in os.walk(shared):
        for name in names:
            source = Path(current) / name
            relative = source.relative_to(shared).as_posix()
            if relative in changed:
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(source, target)
            except OSError:
                shutil.copyfile(source, target)
    for relative, data in changed.items():
        if data is not None:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return destination


def _json(tree: Path, relative: str):
    return json.loads((tree / relative).read_text(encoding="utf-8"))


def _dump(value) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _with_manifest(tree: Path, edit) -> bytes:
    manifest = _json(tree, ca.MANIFEST)
    edit(manifest)
    return _dump(manifest)


def _migration() -> dict:
    """A migration vector of the shape signing-envelope-v2.md and the version gate require."""
    return {
        "automatic_fallback": False,
        "unknown_payload_entry": {"signature": {"payload_id": "registry_entry_signing_payload_v3", "payload_version": 3}},
        "unknown_payload_expected_error": {
            "code": "unsupported_version",
            "object": "signing_payload",
            "version": "registry_entry_signing_payload_v3/3",
        },
        "v2_metadata_stripped_entry": {"signature": {"algorithm": "secp256k1_ecdsa_sha256"}},
        "v2_metadata_stripped_expected_error": "registry_entry_contract_violation",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"earlier_payload_entry": {}},
        {"earlier_payload_status": "UNSUPPORTED_SIGNING_PAYLOAD"},
        {"opt_in_explicit_status": "VALID_SIGNATURE"},
        {"automatic_fallback": True},
        {"unknown_payload_expected_error": {"code": "unsupported_version", "object": "signing_payload", "version": "x"}},
        {"unknown_payload_entry": {"signature": {"payload_id": "registry_entry_signing_payload_v2", "payload_version": 2}}},
        {"unknown_payload_entry": {"signature": {"payload_id": "registry_entry_signing_payload_v3", "payload_version": True}}},
        {"v2_metadata_stripped_entry": {"signature": {"payload_id": "registry_entry_signing_payload_v2"}}},
        {"v2_metadata_stripped_expected_error": "unsupported_version"},
    ],
    ids=lambda change: next(iter(change)) + "=" + repr(next(iter(change.values())))[:40],
)
def test_a_migration_vector_that_declares_another_member_or_the_wrong_error_is_refused(change: dict) -> None:
    assert validator.migration_errors(_migration()) == []
    assert validator.migration_errors({**_migration(), **change}) != []


def _review() -> dict:
    return {
        "status": "OFFLINE_REVIEW",
        "verdict": "REVIEW",
        "exit_code": 2,
        "reason": "evaluation_time_not_provided",
        "errors": [],
        "trust_registry": {
            "authorization_status": "AUTHORIZED_ACTIVE_KEY",
            "signature_status": "VALID_SIGNATURE",
            "trust_registry_root_signature_status": "NO_PINNED_TRUST_ROOT",
        },
        "checks_requested": ["structure", "integrity", "link", "authorization"],
        "checks_established": ["structure", "integrity", "link"],
        "review_reasons": ["evaluation_time_not_provided", "trust_registry_root_not_pinned"],
        "evaluation_time": None,
    }


def _gate() -> dict:
    return {
        "status": "UNSUPPORTED_VERSION",
        "verdict": None,
        "exit_code": 4,
        "reason": "unsupported_version",
        "errors": ["unsupported_version"],
        "trust_registry": None,
        "checks_requested": ["structure", "integrity"],
        "checks_established": [],
        "review_reasons": [],
        "evaluation_time": None,
        "unsupported_version": {"object": "manifest", "version": "loquitur.bundle.v2"},
    }


def _host() -> dict:
    return {
        "status": "HOST_FAILURE",
        "verdict": None,
        "exit_code": 5,
        "reason": "input_not_found",
        "errors": ["input_not_found"],
        "trust_registry": None,
        "checks_requested": ["structure", "integrity"],
        "checks_established": [],
        "review_reasons": [],
        "evaluation_time": None,
    }


def _declaration_errors(expected: dict) -> list[str]:
    errors: list[str] = []
    validator._check_declared_outcome("case", "", expected, errors)
    return errors


@pytest.mark.parametrize(
    "base,change",
    [
        (_review, {"checks_requested": ["integrity", "structure", "link", "authorization"]}),
        (_review, {"checks_requested": ["structure", "integrity", "authorization", "link"]}),
        (_review, {"checks_established": ["structure", "link"]}),
        (_review, {"review_reasons": ["trust_registry_root_not_pinned", "evaluation_time_not_provided"]}),
        (_review, {"review_reasons": ["evaluation_time_not_provided", "evaluation_time_not_provided"]}),
        (_review, {"review_reasons": ["not_a_review_reason"]}),
        (_review, {"reason": "trust_registry_root_not_pinned"}),
        (_review, {"evaluation_time": "2026-05-10"}),
        (_review, {"verdict": None}),
        (_review, {"unsupported_version": {"object": "manifest", "version": "loquitur.bundle.v2"}}),
        (_review, {"checks_evaluated": ["structure"]}),
        (_gate, {"verdict": "FAIL"}),
        (_gate, {"exit_code": 1}),
        (_gate, {"checks_established": ["structure"]}),
        (_gate, {"unsupported_version": {"object": "envelope", "version": "v2"}}),
        (_gate, {"unsupported_version": {"object": "manifest"}}),
        (_gate, {"review_reasons": ["bundle_extra_files"]}),
        (_host, {"exit_code": 1}),
        (_host, {"errors": ["no_such_code"]}),
    ],
    ids=lambda value: value.__name__.strip("_") if callable(value) else repr(value)[:60],
)
def test_a_declaration_outside_the_outcome_table_or_its_members_is_refused(base, change: dict) -> None:
    """report-contract.md sections 3 and 5.5, read from conformance-testing.md section 4.1."""
    assert _declaration_errors(base()) == []
    assert _declaration_errors({**base(), **change}) != []


def test_a_gate_declaration_without_its_object_and_version_is_refused() -> None:
    declaration = _gate()
    del declaration["unsupported_version"]
    assert _declaration_errors(declaration) != []


def test_the_reason_surface_reads_every_compared_member() -> None:
    report = {
        "status": "UNSUPPORTED_VERSION",
        "verdict": None,
        "exit_code": 4,
        "outcome": {"reason": "unsupported_version"},
        "errors": [{"code": "unsupported_version", "object": "trust_registry", "version": "v2"}],
        "trust_registry": None,
        "checks_requested": ["structure", "integrity", "link", "authorization"],
        "checks_established": [],
        "review_reasons": [],
        "evaluation_time": "2026-05-10T00:00:00Z",
    }
    surface = validator.reason_surface(report)
    assert surface["unsupported_version"] == {"object": "trust_registry", "version": "v2"}
    assert surface["evaluation_time"] == "2026-05-10T00:00:00Z"
    assert surface["checks_requested"] == report["checks_requested"]
    assert _declaration_errors({k: v for k, v in surface.items()}) == []


@pytest.fixture(scope="module")
def pinned_validation() -> tuple[list[str], dict]:
    """validate() of the pinned archive against this checkout, run once for the module."""
    return validator.validate(_pinned(), ROOT)


def test_the_pinned_archive_is_valid(pinned_validation: tuple[list[str], dict]) -> None:
    errors, summary = pinned_validation
    assert errors == []
    assert summary["corpus_id"] == json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))["corpus_id"]
    assert summary["declared_runs"] > 0


def test_main_exits_zero_on_the_pinned_archive_and_one_on_a_non_canonical_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pinned_validation: tuple[list[str], dict]
) -> None:
    # main() on the pinned archive is validate() of it against this checkout, which the fixture has
    # already run: the call is answered from it, and its arguments are checked.
    real = validator.validate
    calls = []

    def validate(corpus: Path, protocol: Path | None):
        calls.append((corpus, protocol))
        if (corpus, protocol) == (_pinned().resolve(), ROOT.resolve()):
            return pinned_validation
        return real(corpus, protocol)

    monkeypatch.setattr(validator, "validate", validate)
    assert validator.main([str(_pinned())]) == 0
    assert calls == [(_pinned().resolve(), ROOT.resolve())]
    altered = tmp_path / "altered.zip"
    altered.write_bytes(_pinned().read_bytes() + b"\x00")
    assert validator.main([str(altered)]) == 1


def _manifest_errors(tree: Path) -> list[str]:
    errors: list[str] = []
    validator.check_manifest(tree, errors)
    return errors


def test_the_pinned_manifest_and_profiles_hold(pinned_tree: Path) -> None:
    assert _manifest_errors(pinned_tree) == []
    errors: list[str] = []
    validator.check_no_corpus_id(pinned_tree, errors)
    validator.check_protocol_copies(pinned_tree, ROOT, errors)
    assert errors == []


@pytest.mark.parametrize(
    "plant",
    [
        "unlisted-file",
        "changed-vector",
        "removed-vector",
        "duplicate-key",
        "listed-twice",
        "missing-profile-file",
        "unknown-class",
        "extra-manifest-key",
    ],
)
def test_manifest_defects_are_refused(pinned_tree: Path, tmp_path: Path, plant: str) -> None:
    verify = pinned_tree / "vectors/verify.json"
    changes: dict[str, bytes | None] = {
        "unlisted-file": {"vectors/extra.json": b"{}\n"},
        "changed-vector": {"vectors/verify.json": verify.read_bytes() + b" "},
        "removed-vector": {"vectors/verify.json": None},
        "duplicate-key": {ca.MANIFEST: (pinned_tree / ca.MANIFEST).read_bytes().replace(b"{", b'{"profiles": [], ', 1)},
        "listed-twice": {ca.MANIFEST: _with_manifest(pinned_tree, lambda m: m["files"].append(m["files"][0]))},
        "missing-profile-file": {
            ca.MANIFEST: _with_manifest(pinned_tree, lambda m: m["profiles"][0]["files"].append("vectors/absent.json"))
        },
        "unknown-class": {
            ca.MANIFEST: _with_manifest(pinned_tree, lambda m: m["profiles"][0].update(compatibility_class="nope"))
        },
        "extra-manifest-key": {ca.MANIFEST: _with_manifest(pinned_tree, lambda m: m.update(corpus_id="x"))},
    }[plant]
    tree = _copy(pinned_tree, tmp_path / "corpus", changes)
    assert _manifest_errors(tree)


def test_a_file_naming_a_corpus_id_is_refused(pinned_tree: Path, tmp_path: Path) -> None:
    data = (pinned_tree / "vectors/verify.json").read_bytes() + b" loquitur-conformance-0123456789abcdef"
    tree = _copy(pinned_tree, tmp_path / "corpus", {"vectors/verify.json": data})
    errors: list[str] = []
    validator.check_no_corpus_id(tree, errors)
    assert errors == ["vectors/verify.json names a corpus id"]


@pytest.mark.parametrize("copy", ["protocol/" + ca.PROTOCOL_COPIES[0], "vectors/schemas/registry_entry.schema.json"])
def test_a_protocol_copy_that_differs_is_refused(pinned_tree: Path, tmp_path: Path, copy: str) -> None:
    tree = _copy(pinned_tree, tmp_path / "corpus", {copy: (pinned_tree / copy).read_bytes() + b"\n"})
    errors: list[str] = []
    validator.check_protocol_copies(tree, ROOT, errors)
    assert errors and copy in errors[0]


def _first_case_with(document: dict, key: str) -> str:
    return next(name for name, case in document.items() if isinstance(case, dict) and key in case)


def test_an_unknown_reason_code_in_a_declared_run_is_refused(pinned_tree: Path, tmp_path: Path) -> None:
    runs = _json(pinned_tree, "vectors/verify.json")
    name = _first_case_with(runs, "expected")
    runs[name]["expected"]["reason"] = "not_a_catalogued_reason"
    tree = _copy(pinned_tree, tmp_path / "corpus", {"vectors/verify.json": _dump(runs)})
    errors: list[str] = []
    validator.verify_expected_outcomes(tree, errors)
    assert errors


def test_a_refused_run_that_records_informative_checks_is_refused(pinned_tree: Path, tmp_path: Path) -> None:
    """conformance-testing.md section 4.1: a refused invocation has no report, so no per-check results."""
    runs = _json(pinned_tree, "vectors/verify.json")
    for run in runs.values():
        if validator.declares_a_refusal(run.get("expected")):
            run.pop("informative_checks", None)
    tree = _copy(pinned_tree, tmp_path / "clean", {"vectors/verify.json": _dump(runs)})
    errors: list[str] = []
    validator.verify_expected_outcomes(tree, errors)
    assert not [error for error in errors if "informative_checks" in error], errors
    name = next(
        name
        for name, run in runs.items()
        if "informative_checks" in run and isinstance(run.get("expected"), dict) and "report" not in run["expected"]
    )
    runs[name]["expected"] = {"exit_code": 64, "report": None}
    tree = _copy(pinned_tree, tmp_path / "planted", {"vectors/verify.json": _dump(runs)})
    errors = []
    validator.verify_expected_outcomes(tree, errors)
    assert [error for error in errors if name in error and "informative_checks" in error], errors


def test_a_declared_run_whose_input_is_absent_is_refused(pinned_tree: Path, tmp_path: Path) -> None:
    runs = _json(pinned_tree, "vectors/verify.json")
    name = _first_case_with(runs, "input")
    runs[name]["input"] = "inputs/absent.zip"
    tree = _copy(pinned_tree, tmp_path / "corpus", {"vectors/verify.json": _dump(runs)})
    errors: list[str] = []
    validator.verify_expected_outcomes(tree, errors)
    assert errors


def test_an_input_that_names_nothing_is_the_question_only_where_the_run_says_so(
    pinned_tree: Path, tmp_path: Path
) -> None:
    """conformance-testing.md section 4.1: a run whose input names nothing lists `input` under
    not_a_regular_file, and the verifier reports input_not_found. Declared, the absence is the
    question; declared over a path that names something, the declaration is false."""
    runs = _json(pinned_tree, "vectors/verify.json")
    name = _first_case_with(runs, "input")
    present = runs[name]["input"]
    runs[name]["input"] = "inputs/names_nothing"
    runs[name]["not_a_regular_file"] = ["input"]
    tree = _copy(pinned_tree, tmp_path / "corpus", {"vectors/verify.json": _dump(runs)})
    errors: list[str] = []
    validator.verify_expected_outcomes(tree, errors)
    assert not [error for error in errors if name in error and "input" in error], errors
    runs[name]["input"] = present
    tree = _copy(pinned_tree, tmp_path / "corpus-present", {"vectors/verify.json": _dump(runs)})
    errors = []
    validator.verify_expected_outcomes(tree, errors)
    assert f"verify case {name}: declares that its input names nothing, and it names something" in errors


def test_a_wrong_canonical_form_is_refused(pinned_tree: Path, tmp_path: Path) -> None:
    vectors = _json(pinned_tree, "vectors/canonicalization.json")
    vectors["canonicalize_ok"][0]["sha256"] = "sha256:" + "0" * 64
    tree = _copy(pinned_tree, tmp_path / "corpus", {"vectors/canonicalization.json": _dump(vectors)})
    errors: list[str] = []
    validator.verify_canonicalization(tree, errors)
    assert errors


def test_a_signature_that_does_not_verify_is_refused(pinned_tree: Path, tmp_path: Path) -> None:
    vector = _json(pinned_tree, "vectors/signature.json")
    signature = vector["signature_compact_hex"]
    vector["signature_compact_hex"] = signature[:-2] + ("00" if signature[-2:] != "00" else "01")
    tree = _copy(pinned_tree, tmp_path / "corpus", {"vectors/signature.json": _dump(vector)})
    errors: list[str] = []
    validator.verify_signature_vector(tree, errors)
    assert errors


def test_a_valid_fixture_the_schema_rejects_is_refused(pinned_tree: Path, tmp_path: Path) -> None:
    case = _json(pinned_tree, "vectors/schema-valid/expected.json")["cases"][0]
    tree = _copy(pinned_tree, tmp_path / "corpus", {"vectors/schema-valid/" + case["fixture"]: b"[]\n"})
    errors: list[str] = []
    validator.verify_schema_fixtures(tree, errors)
    assert errors


def test_a_document_whose_bytes_are_not_utf8_is_read_by_the_walks_without_stopping_them(pinned_tree: Path) -> None:
    """The corpus carries vector documents that are not UTF-8, and both walks over vectors/ step
    past them. A walk catching only the JSON decoder's error stops at the first one instead."""

    def utf8(path: Path) -> bool:
        try:
            path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True

    assert not all(utf8(path) for path in (pinned_tree / "vectors").rglob("*.json") if path.is_file()), (
        "no vector document has bytes outside UTF-8; the walks' guards hold nothing"
    )
    source = (ROOT / "tools/validate_corpus.py").read_text(encoding="utf-8")
    guard = "except ValueError:\n            # Not JSON"
    weakened_source = source.replace(guard, guard.replace("ValueError", "json.JSONDecodeError"))
    assert weakened_source.count("except json.JSONDecodeError:") - source.count("except json.JSONDecodeError:") == 2
    weakened = type(validator)("validate_corpus_weakened")
    weakened.__file__ = str(ROOT / "tools/validate_corpus.py")
    exec(compile(weakened_source, weakened.__file__, "exec"), weakened.__dict__)
    assert validator.validate_tree(pinned_tree, ROOT) == []
    errors = weakened.validate_tree(pinned_tree, ROOT)
    assert any("UnicodeDecodeError" in error for error in errors), errors


def test_an_integer_past_the_digit_limit_is_read_by_the_walks_without_stopping_them(
    pinned_tree: Path, tmp_path: Path
) -> None:
    """A strict-parsing vector may hold an integer of thousands of digits, which json.loads refuses
    with a ValueError that is neither a decoding error nor a UTF-8 one; both walks step past it."""
    planted = "vectors/strict-parsing/planted_integer_5000_digits.json"
    tree = _copy(pinned_tree, tmp_path / "tree", {planted: b'{"anchor":' + b"7" * 5000 + b"}"})
    source = (ROOT / "tools/validate_corpus.py").read_text(encoding="utf-8")
    guard = "except ValueError:\n            # Not JSON"
    weakened_source = source.replace(
        guard, guard.replace("ValueError", "(json.JSONDecodeError, UnicodeDecodeError)")
    )
    assert weakened_source != source
    weakened = type(validator)("validate_corpus_digits_weakened")
    weakened.__file__ = str(ROOT / "tools/validate_corpus.py")
    exec(compile(weakened_source, weakened.__file__, "exec"), weakened.__dict__)
    for check in ("verify_expected_outcomes", "verify_vector_declared_digests"):
        errors: list[str] = []
        getattr(validator, check)(tree, errors)
        assert not any("digits" in error for error in errors), errors
        stopped: list[str] = []
        try:
            getattr(weakened, check)(tree, stopped)
        except ValueError as exc:
            stopped.append(str(exc))
        assert any("digits" in error for error in stopped), (check, stopped)


def test_a_reason_code_outside_the_catalog_is_refused_unless_its_document_is_declared(
    pinned_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every declared reason-code negative still carries a code the catalog does not list, and
    removing one declaration makes the validator report that document's code."""
    catalog = set(_json(pinned_tree, "protocol/docs/specification/reason-codes/v2.0/catalog.json")["entries"])
    assert validator.DECLARED_REASON_CODE_NEGATIVES
    for relative in validator.DECLARED_REASON_CODE_NEGATIVES:
        used: set[str] = set()
        validator.recursively_collect_reason_codes(_json(pinned_tree, "vectors/" + relative), used)
        assert used - catalog, f"{relative} is declared and carries only cataloged codes"
    errors: list[str] = []
    validator.verify_expected_outcomes(pinned_tree, errors)
    assert errors == []
    relative = sorted(validator.DECLARED_REASON_CODE_NEGATIVES)[0]
    monkeypatch.delitem(validator.DECLARED_REASON_CODE_NEGATIVES, relative)
    validator.verify_expected_outcomes(pinned_tree, errors)
    assert any(error.startswith("vectors use unknown reason codes") for error in errors), errors


def _summary_run(**change) -> dict:
    run = {"id": "s", "surface": "summary", "summary": "summary-checks/s.json", "expected": {"violated_rules": ["VG-5"]}}
    return {**run, **change}


@pytest.mark.parametrize(
    "change",
    [
        {"surface": "verify"},
        {"summary": None},
        {"bundle": "link_valid_bundle"},
        {"expected": {"violated_rules": ["VG-8"]}},
        {"expected": {"violated_rules": ["VG-6", "VG-5"]}},
        {"expected": {"violated_rules": ["VG-1", "VG-3"]}},
        {"expected": {"violated_rules": ["VG-5"], "status": "OFFLINE_OK"}},
    ],
    ids=lambda change: next(iter(change)) + "=" + repr(next(iter(change.values())))[:40],
)
def test_a_summary_run_outside_the_run_format_is_refused(change: dict) -> None:
    assert validator.summary_run_errors(_summary_run()) == []
    assert validator.summary_run_errors(_summary_run(expected={"violated_rules": []})) == []
    assert validator.summary_run_errors(_summary_run(**change)) != []


def test_a_command_line_answer_is_held_to_the_outcome_table_and_must_differ() -> None:
    run = {"expected": _host(), "expected_command_line": {"exit_code": 64, "report": None}}
    errors: list[str] = []
    validator.check_verify_run_members("r", run, errors)
    assert errors == []
    for planted in ({"exit_code": 63, "report": None}, _host()):
        errors = []
        validator.check_verify_run_members("r", {**run, "expected_command_line": planted}, errors)
        assert errors, planted
    errors = []
    validator.check_verify_run_members("r", {**run, "surface": "summary"}, errors)
    assert errors


def test_a_run_names_registered_vocabularies_by_kind_under_vectors_vocabularies(tmp_path: Path) -> None:
    """conformance-testing.md section 4.1: `vocabularies` maps kinds to documents under vectors/vocabularies/."""
    (tmp_path / "vectors/vocabularies/extended").mkdir(parents=True)
    (tmp_path / "vectors/vocabularies/extended/asset_type.json").write_text("{}", encoding="utf-8")
    good = {"vocabularies": {"asset_type": "vocabularies/extended/asset_type.json"}}
    errors: list[str] = []
    validator.check_run_vocabularies(tmp_path, "run", good, errors)
    assert errors == []
    for bad in (
        {"vocabularies": {}},
        {"vocabularies": {"vessel_type": "vocabularies/extended/asset_type.json"}},
        {"vocabularies": {"asset_type": "bundles/asset_type.json"}},
        {"vocabularies": {"workflow": "vocabularies/extended/workflow.json"}},
        {"vocabularies": ["vocabularies/extended/asset_type.json"]},
    ):
        errors = []
        validator.check_run_vocabularies(tmp_path, "run", bad, errors)
        assert errors, bad


def test_the_vocabulary_rules_are_those_of_section_6() -> None:
    meta = json.loads((ROOT / "docs/specification/registered-vocabularies/schema.json").read_text(encoding="utf-8"))
    document = json.loads((ROOT / "vocabularies/workflow.json").read_text(encoding="utf-8"))
    assert validator._vocabulary_errors(document, meta) == []
    later = json.loads(json.dumps(document))
    later["values"]["fund_nav_update"]["since"] = "2.0.0"
    assert validator._vocabulary_errors(later, meta)
    missing = json.loads(json.dumps(document))
    del missing["values"]["fund_nav_update"]["asset_types"]
    assert validator._vocabulary_errors(missing, meta)
    blank = json.loads(json.dumps(document))
    blank["values"]["fund_nav_update"]["title"] = "\u2028"
    assert validator._vocabulary_errors(blank, meta)
