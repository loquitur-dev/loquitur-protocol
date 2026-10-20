"""Sentences of the specification that must agree with the contracts they describe.

Each test holds one sentence of the prose against the rule, schema or report member it speaks
of, so that a correction made before publication cannot come undone unnoticed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = ROOT / "docs" / "specification"


def _text(name: str) -> str:
    return (SPECIFICATION / name).read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    return text[begin : text.index(end, begin + len(start))]


def _sentences(text: str) -> list[str]:
    return [" ".join(part.split()) for part in re.split(r"(?<=[.:])\s+(?=[A-Z`])", text)]


def test_rule_11_is_not_illustrated_by_a_run_that_carries_an_error() -> None:
    """A committed FAIL over a link that holds carries an error, so rule 1 names it, not rule 11."""
    text = _text("report-contract.md")
    errors = _between(text, "### 5.3 `errors`", "### 5.4 ")
    assert re.search(r"^\| `registry_entry_verdict_fail` \|", errors, re.M)
    reason = _between(text, "### 5.2 `outcome.reason`", "### 5.3 `errors`")
    eleven = [sentence for sentence in _sentences(reason) if "named by rule 11" in sentence]
    assert eleven, "section 5.2 no longer says which runs rule 11 names"
    for sentence in eleven:
        assert "commits `FAIL`" not in sentence, sentence
        assert "carries no error" in sentence, sentence
    assert "`registry_entry_verdict_fail` (§5.3), so rule 1 names it" in " ".join(reason.split())


def _key_type(schema: object) -> list[dict]:
    found = []
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "key_type" and isinstance(value, dict):
                found.append(value)
            found.extend(_key_type(value))
    elif isinstance(schema, list):
        for value in schema:
            found.extend(_key_type(value))
    return found


def test_section_10_places_the_key_type_restriction_in_the_verifier_not_the_schemas() -> None:
    """The schemas admit any well-formed key type; the verifier refuses the unsupported ones at row 16."""
    schema = json.loads((SPECIFICATION / "schemas" / "trust_registry.schema.json").read_text(encoding="utf-8"))
    [key_type] = _key_type(schema)
    assert "enum" not in key_type and "const" not in key_type
    capabilities = json.loads((ROOT / "CRYPTOGRAPHIC_CAPABILITIES.json").read_text(encoding="utf-8"))
    [ed25519] = [entry for entry in capabilities["reserved_not_supported"] if entry["id"] == "ed25519"]
    assert ed25519["schema_acceptance"] is True and ed25519["verification"] is False

    section = " ".join(_between(_text("trust-registry-authorization.md"), "## 10. ", "### 10.1 ").split())
    assert "invalid under the 0.1 schemas" not in section
    assert "closed to `secp256k1`" not in section
    assert "The 0.1 schemas admit any well-formed key-type identifier, `ed25519` included" in section
    assert "(§6, row 16) with `UNSUPPORTED_SIGNATURE_ALGORITHM`" in section


def test_the_online_posture_is_reserved_and_promises_no_registry_view_or_anchors() -> None:
    """Section 4.1 defines no online procedure: anchoring is reserved and no service is defined."""
    text = _text("verification-checks.md")
    online = " ".join(_between(text, "### 4.1 Online verification", "### 4.2 ").split())
    assert online.startswith("### 4.1 Online verification Status: reserved and not defined in this version.")
    for phrase in ("public registry view", "anchor references", "queries"):
        assert phrase not in online, phrase
    assert "public registry view" not in text
    assert "this version defines two of them: offline and link verification" in " ".join(text.split())


def test_the_specification_claims_no_nonce_scheme_for_signing() -> None:
    """No repository signs with deterministic nonces throughout, so the text claims no scheme."""
    text = " ".join(_text("canonicalization-and-hashing.md").split())
    assert "Reference signing uses deterministic nonces" not in text
    assert "This specification does not require deterministic nonces (RFC 6979) of a signer" in text
    assert "verifiers must not assume any nonce-generation scheme" in text


def test_the_operator_minimum_reading_names_only_normative_report_members() -> None:
    """Section 10, item 5 of the threat model names members every conforming verifier reports."""
    contract = _between(_text("report-contract.md"), "## 2. Normative and informative members", "## 3. ")
    normative = set(re.findall(r"^\| `([^`]+)` \|[^\n]*\| normative", contract, re.M))
    assert {"outcome.reason", "trust_registry.authorization_status"} <= normative
    operator = _between(_text("threat-model.md"), "## 10. ", "## 11. ")
    item = _between(operator, "5. **Read more than the exit code.**", "\n6. ")
    item = re.sub(r"\[`[^`]+`\]\([^)]+\)", "", item)
    named = set(re.findall(r"`([^`]+)`", item))
    assert named, "item 5 names no member"
    assert named <= normative, sorted(named - normative)
    assert "registry.status" not in named


def _corpus_member(name: str) -> bytes:
    import zipfile

    lock = json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(ROOT / lock["artifact"]) as archive:
        return archive.read(f"loquitur-conformance/{name}")


def test_revocation_is_stated_to_reach_the_key_material() -> None:
    """One public key under two labels is ambiguous, and the prose says so where it matters."""
    roots = json.loads(_corpus_member("vectors/trust-roots/other_revoked_root.json"))["roots"]
    by_key: dict[str, set[str]] = {}
    for root in roots:
        by_key.setdefault(root["public_key_hex"], set()).add(root.get("status", "active"))
    assert {"active", "revoked"} in by_key.values(), "other_revoked_root no longer shares one key"
    runs = json.loads(_corpus_member("vectors/verify.json"))
    run = runs["authorization_root_other_root_revoked"]
    assert run["trust_root"] == "trust-roots/other_revoked_root.json"
    assert run["expected"]["verdict"] == "FAIL"
    assert run["expected"]["trust_registry"]["trust_registry_root_signature_status"] == "AMBIGUOUS_ROOT_KEY"
    # The point is compared whatever the key type, and for a trust entry whatever the issuer and
    # the encoding (trust-registry-authorization.md section 5).
    root_shared = runs["authorization_root_other_key_type_shared_point"]["expected"]["trust_registry"]
    assert root_shared["trust_registry_root_signature_status"] == "AMBIGUOUS_ROOT_KEY"
    for name in (
        "authorization_dup_other_issuer_same_key",
        "authorization_shared_key_entry_names_the_revoked_label",
        "authorization_shared_key_entry_names_the_compressed_label",
    ):
        assert runs[name]["expected"]["trust_registry"]["authorization_status"] == "TRUST_REGISTRY_AMBIGUOUS_KEY", name

    root_text = " ".join(_between(_text("trust-root.md"), "## 3. ", "## 4. ").split())
    assert "Roots are told apart by `key_id`, never by key." not in root_text
    assert (
        "A root is found by its `key_id`, and its key is then compared with the key of every other pinned root."
        in root_text
    )
    assert "the case `other-revoked` is one, since `root-9` there carries `N`'s key" in root_text
    authorization = " ".join(_between(_text("trust-registry-authorization.md"), "## 5. ", "## 6. ").split())
    assert "A trust entry is found by its labels, never by its key." not in authorization
    assert "so a status reaches the key material and not only the label that carries it" in authorization
    threat = " ".join(_between(_text("threat-model.md"), "## 15. ", "## 16. ").split())
    assert "marks the key `revoked`, every entry signed with it fails" not in threat
    assert "marks the key `revoked` in every trust entry that carries it, every entry signed" in threat
    assert "**One key under two labels.** A status reaches the key material, not only a label" in threat


def test_pinned_roots_are_stated_to_have_no_scope() -> None:
    """A root names no issuer or operator, so the prose warns that co-pinned roots merge authority."""
    contract = _between(_text("trust-root.md"), "## 3. ", "## 4. ")
    fields = re.findall(r"^\| `([a-z_]+)` \| [^|]+ \| (?:yes|no) \|", contract, re.M)
    assert fields == ["key_id", "key_type", "public_key_hex", "not_before", "not_after", "status"], fields
    first = " ".join(_between(_text("trust-root.md"), "## 1. ", "## 2. ").split())
    assert "A root has no scope in this version." in first
    assert "Every pinned root is therefore authoritative for every `issuer_id`." in first
    threat = " ".join(_between(_text("threat-model.md"), "## 5. ", "## 6. ").split())
    assert "**Pinned roots have no scope.**" in threat


def test_the_envelope_metadata_is_stated_to_be_unauthenticated() -> None:
    """Nothing the issuer signs commits to the envelope, so its non-link members are not issuer-authorized."""
    entry = json.loads((SPECIFICATION / "schemas" / "registry_entry.schema.json").read_text(encoding="utf-8"))
    assert not [name for name in entry["properties"] if "envelope" in name], "the entry now commits to the envelope"
    section = " ".join(_between(_text("bundle-objects.md"), "## 4. `envelope_env1.json`", "## 5. ").split())
    assert "**The envelope is authenticated by nothing.**" in section
    assert (
        "A relying party MUST NOT treat a member of the envelope other than its three links as authorized by the issuer"
        in section
    )
    adversary = " ".join(_between(_text("threat-model.md"), "### A3 ", "### A4 ").split())
    assert "The envelope is the same case inside the bundle." in adversary


def test_the_subject_reference_opening_is_stated_to_be_unchecked() -> None:
    """No check reads subject_ref_opening.json in 0.1, and the prose says what a check would do."""
    catalogs = (SPECIFICATION / "reason-codes").rglob("*.json")
    assert not [path for path in catalogs if "subject_ref" in path.read_text(encoding="utf-8").lower()]
    section = " ".join(_between(_text("registry-entry.md"), "## 4. ", "## 5. ").split())
    assert "No check of this version reads the opening or recomputes the value" in section
    assert "A run therefore says nothing about `subject_ref_opening.json`." in section
    assert "This version defines no such check and no reason code for its failure." in section


def test_the_report_is_stated_not_to_name_its_trust_material() -> None:
    """No normative report member identifies the trust registry or root, and the prose says so."""
    contract = _between(_text("report-contract.md"), "## 2. Normative and informative members", "## 3. ")
    normative = set(re.findall(r"^\| `([^`]+)` \|[^\n]*\| normative", contract, re.M))
    for member in ("trust_registry_id", "registry_version", "issued_at", "registry_operator_id"):
        assert not [name for name in normative if member in name], member
    flat = " ".join(contract.split())
    assert "No normative member names the trust material a run rested on." in flat
    freshness = " ".join(_between(_text("threat-model.md"), "## 16. ", "## 17. ").split())
    assert "Nor does a report name the trust registry or the root it rested on" in freshness


def test_the_preview_limitations_list_the_known_protocol_limits() -> None:
    """Each limit the specification states for 0.1 is also on the preview limitations page."""
    page = " ".join((ROOT / "docs" / "preview-limitations.md").read_text(encoding="utf-8").split())
    section = page[page.index("## Known limitations of the protocol in release 0.1") :]
    for heading in (
        "**Pinned roots have no scope.**",
        "**The envelope is not authenticated.**",
        "**The subject reference opening is not checked.**",
        "**A report does not name its trust material.**",
    ):
        assert heading in section, heading
    assert "**Revocation reaches a label, not a key.**" not in section
