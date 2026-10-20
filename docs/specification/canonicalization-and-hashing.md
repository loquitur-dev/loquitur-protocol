# Canonicalization and hashing

Status: normative.

This document is the binding description of the canonicalization and
hash-construction profile. A verifier that follows it reproduces the same bytes,
the same digests and the same accept/reject decisions as any other that does, on
the same inputs. The reference packages and the conformance vectors illustrate the
profile; where they and this text disagree, this text is the protocol.

## 1. Canonical JSON profile

Verification surfaces canonicalize JSON values with **RFC 8785 (JSON
Canonicalization Scheme, JCS)** and encode the result as UTF-8 bytes.

Profile constraints on top of RFC 8785:

- Integers outside the JavaScript safe range (absolute value greater than
  2^53 − 1) are rejected as a canonicalization error rather than silently
  re-encoded. Objects in the protocol surfaces below do not legitimately
  contain such values.
- Floating-point values are serialized exactly as RFC 8785 prescribes. The
  protocol object family avoids floats almost everywhere, but not entirely, and
  the exception is small enough to name in full: `coverage_summary.coverage`
  carries `required_pct` and `recommended_pct`, and `change_summary` carries
  `mark_delta_k` and `mark_delta_pct`, all typed `number`, with shipped examples
  such as `100.0` and `0.0914`. Those four fields are the whole of it. Nothing on a signed surface
  is a float (the registry-entry signing surface described below is string-valued throughout), which
  is the property this section needs.

The registry-entry signing surface in `loquitur-schemas` canonicalizes with
RFC 8785 through the same implementation `loquitur-verify` uses, and applies the
same acceptance filter. There is no second profile: RFC 8785 is the only
canonical form this protocol defines, and no minimal-separator variant of it is
accepted anywhere. Because both packages call one implementation, their output is
byte-identical to RFC 8785. Implementers should treat RFC 8785 as the normative
profile.

## 2. Digest and notation

All digests are **SHA-256**. A digest names its algorithm wherever a JSON document carries it.

Two notations are in use, by surface:

- **Every digest inside a JSON document** is self-describing: the label `sha256`, a colon and
  the 64 lowercase hexadecimal characters of the digest, `sha256:<64 hex>`, matching
  `^sha256:[a-f0-9]{64}$`. That holds for the values of the `files` map of `manifest.json`,
  for `ih` of `p1.json`, for the envelope's `bundle_manifest_sha256` and `p1_sha256`, for the
  receipt's `manifest_sha256`, `p1_sha256` and `policy_pack_sha256`, for the verification
  summary's `policy_pack_sha256`, and for the registry entry's `manifest_hash`, `receipt_hash` and
  `subject_ref_hash`.
- **A digest sidecar file** (`manifest.sha256`, `p1.sha256`, `envelope.sha256`) is not JSON. It
  holds exactly the 64 lowercase hexadecimal characters of the digest and no other byte; its
  algorithm is fixed by the bundle version ([`bundle-objects.md`](bundle-objects.md) §2).

A digest is compared as the whole string, label included, with `sha256:` followed by the
lowercase hexadecimal form of the recomputed digest, by exact equality of code units. Nothing is
removed, trimmed or case-folded first: `SHA256:<hex>`, an uppercase digest and a bare 64-hex value
are each a value that equals no digest, and a document whose contract types the member as a
digest is refused for it. The comparison is the one §7 defines.

The set of digest labels is closed for each version of each object, and is `sha256` alone in this
version. Another label, such as `sha512`, is not a digest this version defines: it breaks the
contract of the object that carries it. Adding a label is a change of that object's version
([`document-contracts.md`](document-contracts.md), "Version gate").

## 3. Hash constructions, by artifact

| Artifact | Bytes hashed |
| --- | --- |
| Manifest digest (`manifest.sha256` sidecar) | RFC 8785 canonical bytes of the parsed `manifest.json` object |
| Manifest file entries (`files` map) | Raw bytes of each listed bundle file. A `files` map that names `manifest.json` or `manifest.sha256` is a rejection ([`bundle-objects.md`](bundle-objects.md) §2). A key that is not a portable member name ([`bundle-objects.md`](bundle-objects.md) §2), an absolute or traversing name included, fails the manifest's file check, and the member it names is not read. |
| P1 digest (`p1.sha256` sidecar) | RFC 8785 canonical bytes of the parsed `p1.json` object, subject to a maximum-size guard |
| P1 input hash (`ih` field of `p1.json`) | RFC 8785 canonical bytes of the input payload. If `p1.ik` is a list of strings, the payload is the object `{key: canonical-input-value-or-null for each key in ik}` (a key listed in `ik` but absent from the canonical input maps to JSON `null`); the order of `ik` does not affect the result, since JCS sorts object keys. If `ik` is absent, the payload is the entire canonical-input object; a present `ik`, `null` included, that is not a non-empty array of distinct strings is a rejection. `ik`, when present, MUST be a NON-EMPTY array of strings: `ik: []` is vacuously a list of strings, so a reader following the sentence above would compute `JCS({})` and commit to a projection of nothing, and the reference verifier rejects the bundle instead. An empty `ik` is a rejection. |
| Envelope digest (`envelope.sha256` sidecar) | RFC 8785 canonical bytes of the parsed `envelope_env1.json` object; the envelope additionally links `bundle_id`, the manifest digest and the P1 digest, and those links must match the digests the bundle commits to. A link holds only when the object it names parsed, satisfied its closed contract and matched its sidecar; a link to a manifest or P1 that failed any of these is `false` ([`bundle-objects.md`](bundle-objects.md) §4). |
| Receipt hash (registry-entry field `receipt_hash`) | RFC 8785 canonical bytes of the complete verification-receipt object |
| Registry-entry signing message v2 | Fixed binary domain prefix followed by RFC 8785 canonical bytes of the closed envelope defined in [`signing-envelope-v2.md`](signing-envelope-v2.md); payload excludes `signature`, `anchor`, and `anchored_at` |
| Trust-registry root signing message v1 | Fixed binary domain prefix followed by RFC 8785 canonical bytes of the closed envelope defined in [`trust-root.md`](trust-root.md); payload excludes `signature` only. A distinct prefix from the registry-entry signing message v2, so a signature made for one construction cannot verify as the other |

A verifier that cannot reproduce a declared digest must fail closed: digest
mismatches are integrity failures, and a missing canonical-input file makes
the input hash unverifiable, never a silent pass.

What a check that could not be performed reports, how it differs from a check that failed, and how
the per-check results and the other conditions decide the report status are stated in
[`bundle-objects.md`](bundle-objects.md) §6 and [`report-contract.md`](report-contract.md) §3.

## 4. Signature scheme (registry entries)

The same curve, encoding and low-s rule govern the trust-registry root signature; only
the message differs. See [`trust-root.md`](trust-root.md).

The normative capability set is defined by
[`cryptographic-capabilities.md`](cryptographic-capabilities.md) and
`CRYPTOGRAPHIC_CAPABILITIES.json`. Protocol release 0.1 supports only secp256k1 ECDSA with SHA-256.

**Algorithm agility.** A signature names its algorithm, and a key names its key type, as
identifiers matching `^[a-z0-9][a-z0-9_]{0,63}$`. The documents admit any identifier of that
form; which pairs of algorithm and key type a verifier accepts is a closed allowlist the verifier
holds, never a value the input chooses. In this version the allowlist is exactly the pair
(`secp256k1_ecdsa_sha256`, `secp256k1`). A well-formed identifier outside the allowlist is not a
contract violation: it reaches the signature step and yields `UNSUPPORTED_SIGNATURE_ALGORITHM`
([`trust-registry-authorization.md`](trust-registry-authorization.md) §6,
[`trust-root.md`](trust-root.md) §5).

- Algorithm identifier: `secp256k1_ecdsa_sha256`; key type `secp256k1`.
- Message and hash: SHA-256 is applied exactly once. The ECDSA hash value `e` is the 32-byte
  SHA-256 digest of the exact domain-separated v2 signing message defined in
  [`signing-envelope-v2.md`](signing-envelope-v2.md); that is the same as ECDSA with SHA-256 over
  the signing message bytes. The digest is never hashed again, and a signature over the digest
  hashed a second time does not verify.
- Curve: secp256k1. Public keys are uncompressed SEC1 points
  (`04 || X || Y`, 130 hex characters); `X` and `Y` are each below the field prime `p`, and the
  point lies on the curve. An encoding with a coordinate at or above `p` is not a public key,
  even when it reduces to a point on the curve.
- Scalars: `r` and `s` are each in `[1, n-1]`, where `n` is the group order.
- Signature encoding: `r || s` as 128 lowercase hex characters
  (64 hex per scalar).
- **Low-s rule**: signatures with `s` greater than `n/2` are rejected on
  verification; conforming signers normalize `s` to the low value.
  This specification does not require deterministic nonces (RFC 6979) of a
  signer, and verifiers must not assume any nonce-generation scheme
  ([`cryptographic-capabilities.md`](cryptographic-capabilities.md) §5).
- The signature object's `key_id` must equal the entry's `issuer_key_id`,
  and trust evaluation (issuer status, validity windows, asset-type and
  workflow scopes) is a separate layer specified in
  [`trust-registry-authorization.md`](trust-registry-authorization.md); a valid signature alone does
  not establish trust.

## 5. Verdict vocabularies across surfaces

Two related but distinct vocabularies exist by design:

- Verification receipts carry a lowercase `status` produced by the
  verification pipeline (for example `pass`).
- Registry entries carry the uppercase commitment verdict enum
  `PASS | WARN | REVIEW | FAIL`, constrained by the published schema.

Link verification ([`registry-link.md`](registry-link.md) §4) bridges the two by mapping each of the
four receipt statuses onto its registry verdict before comparison. The mapping is exact and total
over the closed set; a status outside it maps to nothing and the comparison fails rather than
proceeding on a guess. Implementations must compare mapped verdicts, not raw strings.

The mapping is not a normalization, and it has no aliases: a receipt whose status is
`passed`, `ok`, `success` or any other value outside the closed set maps to no verdict, and
the comparison fails. In a verification run that comparison is not reached: the receipt's contract,
whose schema closes `status` to the four values, refuses such a receipt first. The rule is stated
for an interface that compares a receipt and an entry on its own, and as defence in depth.

## 6. Input strictness

Every JSON document a verifier reads MUST satisfy the following rules when it is
loaded: each JSON member of a bundle (`manifest.json`, `p1.json`, `canonical_input.json`,
the envelope and `verification_receipt.json`) and each document the caller supplies (the
registry entry, the trust registry and the trust-root document). The rules apply to the whole
document, member names included, whether or not a digest or a projection later reads the part
that breaks them. Conforming implementations MUST reject violating documents before
canonicalization; silent repair (for example last-wins duplicate resolution or
precision-lossy number coercion) is non-conforming. A document that breaks a rule is present
and unreadable, and is refused as [`bundle-objects.md`](bundle-objects.md) and
[`report-contract.md`](report-contract.md) §5.3 state.

These rules align the protocol's JSON input with I-JSON (RFC 7493) under RFC 8785, and the two
reference verifiers apply them identically.

**Numbers are IEEE 754 binary64 values.** A JSON number is read as the binary64 value nearest to
the number it spells, ties to even: the value RFC 8785 serializes. Every rule below and every
comparison this protocol makes reads that value. A number whose nearest binary64 value is
infinite, such as `1e400`, breaks rule 3; one whose value is an integer beyond the safe range,
such as `1.5e300`, breaks rule 2.

**No excess precision.** A number is valid only when the decimal value it spells equals the
decimal value of the RFC 8785 serialization of its nearest binary64 value. A number that names
more precision or a smaller magnitude than binary64 holds is invalid, rather than rounded: the
document is refused, not repaired. So `0.1`, `1.0`, `1e0`, `1E2` and `-0` are valid (their
serializations are `0.1`, `1`, `1`, `100` and `0`, which spell the same decimal values), while
`2.0000000000000001` (whose nearest binary64 value serializes as `2`), `4.9e-325` (which
underflows to `0`) and `9007199254740992.5` are invalid. The coercion this section forbids
includes reading `9007199254740993` as the neighboring binary64 value `9007199254740992` and
accepting it.

**Exponent forms.** An exponent, `e` or `E` followed by an optional `+` or `-` and one or more
digits, is a valid spelling of a number, and the number is read by the two paragraphs above:
`1E2` is the valid number `100`, `1e-7` the valid number `1e-7`.

1. **No duplicate member names.** A JSON object MUST NOT contain two members
   with the same name after escape decoding (`"a"` and `"\u0061"` are the same
   name). Duplicate names make the committed value parser-dependent. Aligned
   with I-JSON (RFC 7493, section 2.3).
2. **Safe-integer range, by value.** Any number whose value, its binary64 value
   above, is an integer with magnitude greater than 2^53 - 1 is invalid regardless
   of spelling (digit form or exponent form). This value-based rule keeps every
   canonical form re-parseable and re-canonicalizable by any conforming
   implementation (round-trip closure) and matches the RFC 8785 / ECMAScript
   interoperability range.
3. **Finite numbers only.** `NaN`, `Infinity`, and `-Infinity` are invalid at
   parse time.
4. **Unicode scalar values only.** Every string, and every member name, MUST
   consist solely of Unicode scalar values: an unpaired surrogate (a code point
   in `U+D800` to `U+DFFF` that is not part of a valid pair) is invalid at parse
   time.

5. **Pattern anchoring is ECMA-262.** A `pattern` in the published schemas is an
   ECMA-262 regular expression, applied without the `m` flag, and `$` therefore asserts
   the ABSOLUTE end of the string. An implementation whose regular-expression engine lets
   `$` also match before a final newline (Python's `re` is the common case) MUST NOT
   accept a value carrying that trailing newline. The schemas spell the anchor `$`, which
   every engine accepts, the non-backtracking engines that refuse a negative look-ahead
   included, and this rule supplies the strict reading.

6. **Nesting depth at most 64.** A scalar has depth 0; an empty array or object has depth 1;
   a non-empty array or object has depth one more than the deepest of its members. A document
   of depth 64 is valid, and one of depth 65 or more is invalid. Brackets inside a string do not
   count. The limit is decided without recursion and in time linear in the document's length,
   so no host stack, recursion limit or backtracking decides the outcome; a string that is never
   terminated makes the document not JSON, whatever its depth.
7. **UTF-8, exactly.** A document's bytes are decoded as UTF-8 with no replacement: invalid
   UTF-8 is invalid, and so is a leading byte-order mark (the bytes `EF BB BF`). U+FEFF inside a
   string is a scalar value like any other and is valid there.
8. **Instants are calendar instants.** Every string that a published schema, or
   [`trust-root.md`](trust-root.md) §3, holds to the instant form `YYYY-MM-DDTHH:MM:SSZ` names a
   real UTC second of the proleptic Gregorian calendar: the year is 0001 or later, the day exists in
   its month (February 29 only in a leap year), the hour is at most 23, the minute at most 59 and
   the second at most 59, so a leap second written as `60` is invalid. The rule applies to every
   instant of the registry entry, the trust registry, the verification receipt and the trust-root
   document, used or not, whenever the document is loaded and whichever checks the run requests; a
   document that breaks it breaks its contract. The evaluation time the operator supplies is held to
   the same rule.

| instant | calendar instant |
| --- | --- |
| `2026-05-10T00:00:00Z` | yes |
| `2024-02-29T12:00:00Z` | yes |
| `2026-12-31T23:59:59Z` | yes |
| `2026-02-29T12:00:00Z` | no |
| `2026-02-30T00:00:00Z` | no |
| `2026-04-31T00:00:00Z` | no |
| `2026-04-29T12:00:60Z` | no |
| `0000-01-01T00:00:00Z` | no |
| `2000-02-29T00:00:00Z` | yes |
| `1900-02-29T00:00:00Z` | no |
| `2100-02-29T00:00:00Z` | no |

9. **No noncharacters.** Every string, and every member name, MUST NOT contain a Unicode
   noncharacter: U+FDD0 to U+FDEF, and each code point whose last four hexadecimal digits are
   FFFE or FFFF (66 code points in all), whether it is written as the character itself or as an
   escape (`\uFDD0`, `\uFFFF`, or the pair `\uD83F\uDFFE` for U+1FFFE). Aligned with I-JSON
   (RFC 7493, section 2.1).

> Note (intentional profile). Rule 2 is applied *by value*, so it also rejects
> large floats written in scientific notation (for example `1e21`, `1.79e308`) whose
> magnitude is an integer beyond 2^53 - 1. This is deliberately stricter than
> raw RFC 8785 (which would canonicalize them): for a financial-evidence
> protocol every committed quantity must sit in the exactly-representable
> range. The restriction is enforced identically across all implementations,
> so it never causes a cross-implementation divergence.

## 7. Comparing strings

Unless a rule of this specification names another comparison, two strings are equal when, and
only when, their UTF-8 encodings are the same sequence of bytes. Every string a verifier compares
is a sequence of Unicode scalar values (§6, rule 4), so this is the same as equality of code points
and as equality of UTF-16 code units, and an implementation may compare in any of these forms; the
phrase "exact equality of code units" in the other parts means this comparison. Nothing is trimmed,
case-folded or normalized (no NFC, NFD, NFKC or NFKD) before a comparison: two strings that differ
only in letter case, in normalization form or in a compatibility variant of a character are
different. The whitespace set W of [`bundle-objects.md`](bundle-objects.md) decides only whether a
string is empty; it never changes a compared string.

These rules name another comparison, and there are no others:

- member names of a bundle are also compared with each of the letters `A` to `Z` read as its
  lower-case letter, and no other character folded, to find names that conflict, to find a
  `files` key that is `manifest.json` or `manifest.sha256`, and to find a segment that is a Windows
  reserved device name ([`bundle-objects.md`](bundle-objects.md) §2);
- a path whose root is a named pipe is recognized in any ASCII letter case
  ([`report-contract.md`](report-contract.md) §5.3);
- an instant is compared as the UTC second it names
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §2);
- a number is compared as its binary64 value (§6);
- a registry entry's `policy_version` is compared with a receipt's as
  [`registry-link.md`](registry-link.md) §4 reads it, and two lists of reason codes as the multisets
  that section names.

This specification defines no order of strings other than the order in which RFC 8785 sorts member
names. No normative member of a report depends on the order in which a verifier lists or visits
strings, and a comparison of two lists as multisets gives the same answer whatever order sorts
them.

A length a schema states (`minLength`, `maxLength`) counts Unicode scalar values; a length this
specification states in bytes counts the bytes of the UTF-8 encoding.
