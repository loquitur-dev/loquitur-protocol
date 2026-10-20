"""The normative documents state the rules of offline-verification-v1 and no sentence contradicting them.

Each row names a normative document, a sentence that contradicts the verifier contract
(reject rather than normalize, identical outcomes in both reference verifiers), and the
sentence that states the rule. The document does not carry the first and does carry the
second: a contradicting sentence teaches an implementer the behavior both verifiers refuse.
Whitespace is compared as one space, so rewrapping a paragraph does not fail the test;
changing its words does.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

RULES = [
    (
        "no-v1-signing-message-in-the-protocol",
        "docs/specification/trust-registry-authorization.md",
        "the signature is verified over the legacy signing message",
        "This protocol defines no earlier signing payload. A signature object that carries neither",
    ),
    (
        "v1-opt-in-outside-conformance",
        "docs/specification/conformance-testing.md",
        "bind an implementation that offers that opt-in",
        # The denial is stated of the corpus, which carries no `*_explicit_status` member.
        "The corpus declares no outcome for a legacy opt-in",
    ),
    (
        "signing-envelope-defines-no-v1-message",
        "docs/specification/signing-envelope-v2.md",
        "Historical verification requires an explicit migration-only opt-in.",
        "This specification defines no signing payload before v2, and so no legacy payload to migrate from.",
    ),
    (
        "reason-rules-name-only-a-failed-layer",
        "docs/specification/report-contract.md",
        "Rule 15 therefore also names a failed run whose P1 layer is `OFFLINE_REVIEW`",
        "Each names a layer whose outcome is `OFFLINE_FAIL`, and never a layer that is only `OFFLINE_REVIEW`:",
    ),
    (
        "registry-entry-hash-fields-compared-exactly",
        "docs/specification/canonicalization-and-hashing.md",
        "Verifiers normalize by stripping the optional `sha256:` prefix and lower-casing before comparison",
        "Nothing is removed, trimmed or case-folded first: `SHA256:<hex>`, an uppercase digest and a bare 64-hex "
        "value are each a value that equals no digest,",
    ),
    (
        "sidecar-holds-exactly-64-bytes",
        "docs/specification/bundle-objects.md",
        "and nothing that changes its value",
        "A sidecar file holds exactly the 64 lowercase hexadecimal characters of the digest and no other byte, "
        "not even a newline.",
    ),
    (
        "trust-root-public-key-not-lower-cased",
        "docs/specification/trust-root.md",
        "after lower-casing",
        "when `key_type` is `secp256k1` it matches `^04[0-9a-f]{128}$`. It is not lower-cased first.",
    ),
    (
        "trust-root-row-5-lowercase",
        "docs/specification/trust-root.md",
        "| 5 | `signature.signature` is not 128 hex characters |",
        "| 5 | `signature.signature` is not 128 lowercase hex characters | `MALFORMED_SIGNATURE` |",
    ),
    (
        "ik-fallback-only-when-absent",
        "docs/specification/canonicalization-and-hashing.md",
        "If `ik` is absent or not a string list",
        "If `ik` is absent, the payload is the entire canonical-input object; a present `ik`, `null` included, "
        "that is not a non-empty array of distinct strings is a rejection.",
    ),
    (
        "manifest-self-declaration-malformed",
        "docs/specification/canonicalization-and-hashing.md",
        "entry is excluded from its own `files` map",
        "A `files` map that names `manifest.json` or `manifest.sha256` is a rejection (`bundle-objects.md` §2).",
    ),
    (
        "envelope-links-to-verified-objects-hashing",
        "docs/specification/canonicalization-and-hashing.md",
        "Implementations differ in how they obtain those digests",
        "a link to a manifest or P1 that failed any of these is `false` (`bundle-objects.md` §4).",
    ),
    (
        "receipt-validated-when-present",
        "docs/specification/bundle-objects.md",
        "the envelope and the receipt are checked against their own digests",
        "a present receipt is validated against its closed schema in every run and against the registry entry by "
        "the `link` check.",
    ),
    (
        "p1-bound-is-1024",
        "docs/specification/bundle-objects.md",
        "a verifier **MUST** impose some finite bound",
        "The bound is 1024 bytes of canonical form; a verifier **MUST** fail closed when it is exceeded.",
    ),
    (
        "envelope-links-to-verified-objects",
        "docs/specification/bundle-objects.md",
        "Implementations may differ in how they obtain those digests",
        "A link holds only when the object it names parsed, satisfied its closed contract and matched its sidecar; "
        "a link to a manifest or P1 that failed any of these is `false`.",
    ),
    (
        "archive-limits-are-the-bounds",
        "docs/specification/bundle-objects.md",
        "an implementation **MAY** choose different finite bounds",
        "These values are the bounds: a verifier **MUST** apply them, and applies the per-member bound to a "
        "directory bundle as well.",
    ),
    (
        "archive-ratio-has-no-floor",
        "docs/specification/threat-model.md",
        "ratio 100 above a 1 MiB floor",
        "a compression ratio of 100:1 for every member whatever its size",
    ),
    (
        "receipt-schema-at-structure",
        "docs/specification/verification-checks.md",
        "applied to those three bundle files. A member",
        "applied to those three bundle files, and to `verification_receipt.json` whenever it is present, against "
        "`schemas/verification_receipt.schema.json` and the rules of `document-contracts.md` §8 that the schema does "
        "not carry.",
    ),
    (
        "vg-1-duplicate-terminates",
        "docs/specification/verdict-grounds.md",
        "If the document cites nothing, there is no severity to compute and no code to match context against. "
        "Report `reason_codes` absent and stop.",
        "1. **VG-1.** If `reason_codes` is absent, empty or carries a duplicate, report the VG-1 violation and stop.",
    ),
    (
        "json-nesting-limit-64",
        "docs/specification/threat-model.md",
        "nesting deep enough to exhaust the interpreter stack",
        "and nesting deeper than 64 levels.",
    ),
    (
        "not-implemented-capabilities-per-run",
        "docs/specification/threat-model.md",
        "### A reporting discrepancy, stated rather than hidden",
        "`not_implemented_capabilities` is computed per run: `trust_registry_root_signature_verification` is omitted "
        "exactly when a pinned root verified the trust registry in that run.",
    ),
    (
        "not-implemented-capabilities-row-not-stale",
        "docs/specification/threat-model.md",
        "this list entry is stale",
        "The entry is omitted in a run where a pinned root verified the trust registry; see the note below.",
    ),
    (
        "registry-entry-verdict-equality-settled",
        "docs/specification/verdict-grounds.md",
        "Whether equality or the floor binds `registry_entry.verdict` is **not settled** here.",
        "**Equality, not a floor, for the entry as for the summary.** An entry whose verdict is less severe than "
        "its grounds and an entry whose verdict is more severe both break the entry's contract.",
    ),
    (
        "reason-code-severity-is-an-equality",
        "docs/specification/reason-codes.md",
        "The rule is a floor and not an equality.",
        "The rule is an equality and not a floor.",
    ),
    (
        "narrative-renderer-does-not-skip-unknown-codes",
        "docs/specification/reason-codes.md",
        "The reference renderer therefore skips an individual code its own catalog does not carry",
        "does not skip a code its own catalog does not carry",
    ),
    (
        "trust-registry-interpretation-limits",
        "docs/specification/trust-registry-authorization.md",
        "does not automatically mean that every issuer is approved for production use",
        "A trust registry that satisfies its contract authorizes a key only in the terms of "
        "`trust-registry-authorization.md`",
    ),
    (
        "verifier-report-bound-by-the-report-contract",
        "docs/specification/verdict-grounds.md",
        "| a verifier's local report | the verifying tool, for its own reader | **neither** |",
        "| a verifier's local report | the verifying tool, for its own reader | `report-contract.md`, and not these rules |",
    ),
    (
        "status-rule-names-its-scope",
        "docs/specification/bundle-objects.md",
        "The report status follows from those results, in this order:",
        "Over the checks of the bundle layers, the report status follows from those results, in this order:",
    ),
    (
        "bundle-id-empty-means-only-w",
        "docs/specification/bundle-objects.md",
        "| `bundle_id` | string, non-empty after trimming | yes |",
        "| `bundle_id` | string with a code point outside W | yes |",
    ),
    (
        "input-strictness-covers-every-document",
        "docs/specification/canonicalization-and-hashing.md",
        "Canonical input MUST satisfy the following parse-level rules.",
        "Every JSON document a verifier reads MUST satisfy the following rules when it is loaded:",
    ),
    (
        "transparency-no-withheld-code-claimed",
        "docs/specification/verification-checks.md",
        "RFC 6962 inclusion and consistency code exists in `loquitur-schemas`",
        "no reference package computes or verifies any of them.",
    ),
    (
        "transparency-anchoring-cryptographic-parts-are-local",
        "docs/specification/verification-checks.md",
        "**`transparency` and `anchoring` cannot be offline**, because both ask about something that happened elsewhere.",
        "**`transparency` and `anchoring` cannot be completed offline.** Their cryptographic parts can be checked from "
        "local files",
    ),
    (
        "trust-root-document-validated-whole-when-read",
        "docs/specification/trust-root.md",
        "| 8 | the matched root is malformed under §3 | refusal; the document is invalid |",
        "The roots were validated as a whole when they were read (§3): a malformed set was refused then,",
    ),
    (
        "trust-root-document-top-level-closed",
        "docs/specification/trust-root.md",
        "`trust_roots` is accepted as an alternative name for the same array.",
        "The top level is closed, as each element is: a document that is not a JSON object, that lacks a member, "
        "that carries any other member,",
    ),
    (
        "no-time-stamp-token-source-in-the-run",
        "docs/specification/trust-registry-authorization.md",
        "when the evaluation instant was taken from a time-stamp token, the token binds the digest",
        "This version of the protocol defines no time-stamp token and no other attestation of time",
    ),
    (
        "no-time-stamp-token-policy-binds-a-verifier",
        "docs/specification/threat-model.md",
        "MUST be reproduced by any verifier that adds a backend",
        "defines its source, its binding to the evidence and its authority pinning in this specification",
    ),
    (
        "trust-root-key-id-not-empty-under-w",
        "docs/specification/trust-root.md",
        "| `key_id` | string, non-empty | yes |",
        "`key_id` is not empty in the sense of `bundle-objects.md`: it has at least one code point outside "
        "the whitespace set W.",
    ),
    (
        "security-scope-per-run",
        "SECURITY.md",
        "listed in `not_implemented_capabilities` in every verification report",
        "Trust-registry root-signature verification is implemented and in scope.",
    ),
    (
        "no-time-stamp-seam-in-the-reference-implementation",
        "docs/specification/threat-model.md",
        "keeps an RFC 3161 seam outside the protocol",
        "The reference implementation carries no time-stamp code: no token parser, no pinned",
    ),
    (
        "non-finite-number-cell-names-the-code-and-the-member",
        "docs/specification/threat-model.md",
        "| `non_finite_json_number:NaN` |",
        "| `p1_verification_failed:non_finite_json_number:NaN:canonical_input.json` |",
    ),
    (
        "envelope-missing-field-cell-names-both-members",
        "docs/specification/threat-model.md",
        "`envelope_missing_field:*`",
        "`envelope_missing_field:bundle_manifest_sha256`, `envelope_missing_field:p1_sha256`",
    ),
    (
        # --tsa-token is not an option of this version: a command line refuses it as an unknown
        # option (report-contract.md section 4.1), with exit 64 and no report.
        "tsa-token-cell-records-the-unknown-option",
        "docs/specification/threat-model.md",
        "refusal: no token source in version 0.1",
        "| `--tsa-token` | any token bytes | exit 64, no report |",
    ),
    (
        "the-entry-nested-strings-are-free-strings",
        "docs/specification/registry-link.md",
        "The strings nested in `signature` and `anchor` are not held to this rule",
        "The entry's free strings are `issuer_key_id`, `policy_id`, `signature.key_id`, `anchor.anchor_reference` and `anchor.system`",
    ),
    (
        "empty-files-map-is-a-rule-of-its-own",
        "docs/specification/bundle-objects.md",
        "that is a consequence of §1 rather than a rule of its own",
        "A `files` map with no member makes the manifest's file check `false`",
    ),
    (
        "unsupported-input-covers-a-kind-the-verifier-does-not-read",
        "docs/specification/report-contract.md",
        "| `unsupported_input` | the input exists and is neither a directory nor a regular file |",
        "| `unsupported_input` | content | the input exists and is neither a directory nor a regular file, or is of "
        "a kind the verifier does not read (a verifier without archive intake given a regular file) |",
    ),
    (
        "invalid-zip-is-the-row-of-a-verifier-with-archive-intake",
        "docs/specification/report-contract.md",
        "| `invalid_zip` | the input is a file that is not a readable ZIP archive |",
        "| `invalid_zip` | content | the verifier reads ZIP archives and the input is a regular file that is not a "
        "readable ZIP archive |",
    ),
    (
        "bundle-root-invalid-holds-without-archive-intake",
        "docs/specification/report-contract.md",
        "§5.3 that refuse a ZIP archive never hold for it",
        "`bundle_root_invalid` is not one of them: its condition also names a directory input with no "
        "`manifest.json`, and that half holds for this verifier as for any other.",
    ),
    (
        "hostile-table-scoped-to-its-archive-rows",
        "docs/specification/threat-model.md",
        "a verifier reading directory bundles only never meets these inputs",
        "the rows whose input is an archive bind only a verifier that has it",
    ),
]


# A reference to another specification document is a link to its file, [`x.md`](x.md). The link is
# markup: the tests read the text a reader sees, the document name in a code span.
DOCUMENT_LINK = re.compile(r"\[`([^`\]]+\.md)`\]\(\1\)")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


@pytest.mark.parametrize(("row", "document", "contradiction", "rule"), RULES, ids=[c[0] for c in RULES])
def test_the_document_states_the_rule_and_not_its_contradiction(
    row: str, document: str, contradiction: str, rule: str
) -> None:
    text = _flat(DOCUMENT_LINK.sub(r"`\1`", (ROOT / document).read_text(encoding="utf-8")))
    assert _flat(contradiction) not in text, f"{document} contradicts the rule: {contradiction!r}"
    assert _flat(rule) in text, f"{document} does not state the rule: {rule!r}"
