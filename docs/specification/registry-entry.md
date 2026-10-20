# Registry entry

Status: normative.

A registry entry is the primary public commitment object.

## 1. Purpose

A registry entry lets a verifier identify that a verification receipt was committed with declared
issuer identity, policy identity, reason-code outcome, and manifest/receipt commitment material.

## 2. Expected public fields

The public model is centered on these field families:

- registry and receipt identifiers;
- issuer and issuer-key identifiers;
- asset type and workflow category;
- subject reference hash;
- manifest and receipt hashes;
- policy identifier and version;
- verdict posture;
- reason-code vocabulary and reason codes;
- issuance timestamp;
- privacy/disclosure posture;
- optional signature material;
- optional anchor reference material: the anchoring method, the system that carries the record, and
  the anchor reference.

## 3. Strict privacy rule

A registry entry must not include raw evidence, full bundles, canonical input payloads,
valuation/NAV values, private document metadata, private asset identifiers, unrestricted storage
URLs, secrets, or backend internals.

**No personal data in public identifiers.** An identifier of a registry entry (`registry_entry_id`,
`receipt_id`, `issuer_id`, `issuer_key_id`, `policy_id`, `subject_ref_hash`) MUST NOT carry
personal data. An entry and every copy of it stay in public logs and dossiers and cannot be
withdrawn.

**Identifiers are random or opaque.** `registry_entry_id` and `receipt_id` MUST be random or
otherwise opaque, and MUST NOT be derived from `bundle_id` or from any other value of the private
bundle: an identifier derived from the bundle would let anyone who guesses the bundle confirm the
guess ([`public-private-boundary.md`](public-private-boundary.md)).

## 4. Subject reference hash

`subject_ref_hash` identifies the subject of the entry (an asset, a fund, a property) without
naming it. It MUST NOT be derivable from a public or guessable identifier: a registry entry is
public and cannot be withdrawn, so a value that anyone could compute from an ISIN, a cadastral
reference or a fund name would let anyone test whether a subject is in the registry and link its
whole public history. It is built as:

```text
subject_ref_hash = "sha256:" || lowercase-hex( SHA-256( P || salt || JCS({"id": id, "scheme": scheme}) ) )
```

- `P` is the domain prefix, the 24 ASCII bytes `LOQUITUR 00 SUBJECT_REF 00 V1 00`, hex
  `4c4f515549545552005355424a4543545f52454600563100`. Like the signing prefixes, it is an opaque
  domain-separation tag ([`signing-envelope-v2.md`](signing-envelope-v2.md)).
- `salt` is 32 bytes from a cryptographically secure random generator, held secret by the issuer.
- `scheme` names the kind of identifier (for example an identifier scheme of a vertical) and `id`
  is the identifier under it, both strings; `JCS` is RFC 8785
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md)).

The value is stable for one subject and one salt, so every entry about that subject under that
salt is linkable in public; an issuer that needs entries of a series not to be linkable uses a
different salt for each series. The opening, the object `{"id": id, "salt": <64 lowercase hex>,
"scheme": scheme}`, is private: when the issuer gives it to a relying party, it travels in the
bundle as the member `subject_ref_opening.json`, declared in `manifest.files` like any other
member. No check of this version reads the opening or recomputes the value; a verifier treats
`subject_ref_hash` as a digest of the form
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §2 fixes.

A run therefore says nothing about `subject_ref_opening.json`. Its digest in `manifest.files` shows
only that the bundle carries the file, not that it opens the entry's `subject_ref_hash`: an opening
that names another subject, or that is not an object of the form above, verifies the same way. A
check of the opening would read it as a closed object with exactly the members `id`, `salt` and
`scheme`, `salt` being 64 lowercase hexadecimal characters and `id` and `scheme` strings, recompute
the value by the construction above and compare it with the entry's `subject_ref_hash`. This version
defines no such check and no reason code for its failure. A relying party that relies on the subject
an opening names SHOULD recompute the value itself and compare it with the entry's
`subject_ref_hash` first.

| `scheme` | `id` | `salt` (hex) | `subject_ref_hash` |
| --- | --- | --- | --- |
| `example` | `subject-0001` | `000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f` | `sha256:8cd0973fe7841d9ba5788ae768fd6ba3fbdc44c3d7b6f1167a42af335fed70b4` |

The JCS bytes in that row are `{"id":"subject-0001","scheme":"example"}`.

## 5. Interpretation limits

A registry entry can support a public proof-of-commitment workflow. It does not by itself prove
source-document truth, issuer legal status, valuation correctness, regulatory status, or final
settlement on any external network.

## 6. Surface representations (intentional, not drift)

The same logical fact is represented differently on the **receipt/pipeline surface** and the
**registry/public surface**. These differences are intentional and stable for 0.1.0:

- **Hash fields.** The receipt carries `manifest_sha256`, and the registry_entry carries
  `manifest_hash` and `receipt_hash`, all in the self-describing form `sha256:<64 lowercase hex>`
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §2). The field names differ
  by surface; a consumer must not assume one field name across both surfaces.
- **Policy version.** The receipt and verification_summary represent `policy_version` as a monotonic
  integer (pipeline ordering). The registry_entry represents the same policy version as a semver
  string (`MAJOR.MINOR.PATCH`) for public, human-readable citation. Map between them via
  `policy_id`. The receipt's `policy_pack_sha256` is opaque in this version: the specification
  defines no policy pack, and nothing is inferred from the value. One narrow comparison is normative
  and is not such an assumption: a verifier comparing a registry entry against a receipt MUST
  require the entry's `MAJOR` to equal the receipt's integer `policy_version`, and MUST treat a
  mismatch as a failure. Nothing else about the two forms may be inferred from their types. Whether
  a `MAJOR` exists is decided by the form of the whole string under the pattern of
  [`registry-link.md`](registry-link.md) §4, a leading zero in any group meaning none; the values of
  `MINOR` and `PATCH` carry no comparison meaning.
- **Verdict vs status.** The registry surface uses an uppercase `verdict`
  (`PASS · WARN · REVIEW · FAIL`); the pipeline surface uses a lowercase `status`
  (`pass · warning · review · fail`). The two vocabularies correspond one to one, so the
  mapping between them is total and a consumer never has to handle a status with no verdict;
  there is no status `unknown` (the resolution of `LCP-0008` that `docs/change-proposals.md`
  records). Link
  verification maps each of the four receipt statuses to its registry verdict before any
  comparison, exactly and with no aliases; a status outside the closed set maps to nothing
  and the comparison fails. Consumers compare mapped verdicts, never raw strings.
- **Reason-code vocabulary field.** The registry_entry names the pinned vocabulary
  `reason_code_catalog_version`; the receipt and the verification_summary name the same fact,
  with the same `const` value `loquitur.reason_codes.v1`, `reason_code_vocabulary_version`.
  All three are required. The two names are frozen for 0.1.0: the registry name is in the
  conformance corpus under a digest and in the TypeScript declarations `loquitur-verify-ts`
  generates from the schemas, so renaming it
  would trade a naming inconsistency for drift across those artifacts. Read the field by
  surface, never by assuming one name spans both.
- **Anchor method field.** The registry_entry names how an anchor is carried in `anchor.method`,
  an identifier of the registered vocabulary `anchoring_method`, and the system that carries the
  record in `anchor.system`, a free string; the receipt records what a pipeline observed in
  `anchor_type`, `anchor_provider` and `network`, unconstrained nullable strings. The registry
  surface fixes a grammar because it is the public commitment; the receipt surface is open because
  it records an observation. The asymmetry is not strictness: neither
  `anchor.method` nor `anchor.system` is a field [`anchor-commitment.md`](anchor-commitment.md)
  makes normative, while `anchor.anchor_reference`, the only field the anchoring rule binds, is
  constrained to a non-empty string and no more, because what it must reference may be `H` directly
  or a structure over digests, and because the lexical form of a reference depends on the method and
  the system. That constraint, and the form of `anchor.system`, tighten when the `anchoring` check
  is defined, not before.

## 7. Link verification

How a verifier decides that a registry entry refers to the bundle in hand is specified in
[`registry-link.md`](registry-link.md): every comparison and its operands, what is and is not
normalized, the three values of the result, and what the verdict an entry commits to does to the
run. The same document states the rule that binds an entry's verdict to its reason codes.

## 8. Signature version

Issuance MUST use `registry_entry_signing_payload_v2` with `payload_version: 2` as defined in
[`signing-envelope-v2.md`](signing-envelope-v2.md). This protocol defines no earlier signing
payload: a signature object that carries neither `payload_id` nor `payload_version` breaks the
entry's contract, and a well-formed later payload version is an unsupported version
([`document-contracts.md`](document-contracts.md), "Version gate").

## 9. Values from registered vocabularies

`asset_type`, `workflow` and `anchor.method` take their values from the registered vocabularies of
[`verification-vocabularies.md`](verification-vocabularies.md) §5. The schema holds each to the
identifier grammar and to nothing more, so an entry may name a value that a later version of a
vocabulary registers. A verifier that does not hold the value reports the review reason
`vocabulary_value_unknown` for `asset_type` and `workflow`, and nothing for `anchor.method`
([`verification-vocabularies.md`](verification-vocabularies.md) §7).

An issuer SHOULD name only registered values. An entry that names a value no vocabulary registers
is a review for every verifier until the value is registered, and it stays public under that value,
because an entry cannot be withdrawn.
