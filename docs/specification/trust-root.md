# Trust-registry root authentication

Status: normative.

This document specifies how a trust registry is authenticated against a trust root: the
exact bytes a root signs, the shape of the trust-root document, and the order in which a
verifier reaches its answer. [`verification-checks.md`](verification-checks.md) makes root
authentication part of the `authorization` check and [`threat-model.md`](threat-model.md) §5 states
the rule that governs it in RFC 2119 terms; this document specifies the construction, so that an
implementer builds the step that turns `REVIEW` into `PASS`, the one the whole trust argument rests
on, from the specification alone.

## 1. What root authentication answers, and what it does not

Pinning a root authenticates the trust-registry *document*. It establishes that a key the
verifier pinned out of band signed the registry it is being asked to rely on.

It does **not** establish that the root key belongs to any particular organization. That
binding is whatever process the operator used to obtain the root document, and the
protocol has no opinion about it. It does not verify a certificate chain: a root here is a
bare public key of a named key type with a validity window and a status, on a closed field set.

A root has no scope in this version. Its element names no `trust_registry_id`, no
`registry_operator_id` and no issuer, and no rule compares the trust registry a root authenticates,
or the issuers that registry lists, with anything the operator pinned. Every pinned root is
therefore authoritative for every `issuer_id`. An operator that pins the roots of two registry
operators in one document lets either of them authorize a key under an issuer the other governs,
and an entry signed with that key reaches `PASS`. An operator SHOULD pin in one trust-root document
only roots it trusts for every issuer it verifies, and SHOULD keep a separate trust-root document,
used in a separate run, for each registry operator whose authority it does not want to merge with
another's. Before it relies on a run, an operator can also check that the trust registry it
supplied carries the `trust_registry_id` and `registry_operator_id` it expects for the entry's
`issuer_id`. A scope member on a root is not part of this version: it changes the closed field set
of §3.

Read [`threat-model.md`](threat-model.md) §5 for why this matters. In short: without a pinned root,
the trust registry proves that *some* key signed the entry and that the registry *the verifier was
given* vouches for it. Whoever supplied that registry can make both true trivially.

## 2. The rule

A verifier that has no pinned trust root **MUST NOT** return `PASS` for a registry entry
verified against a trust registry. Absent a cause of `FAIL`, it **MUST** return `REVIEW`: a run
that fails for another reason, such as a revoked key or a broken link, is `FAIL` whether or not a
root is pinned ([`report-contract.md`](report-contract.md) §3).

Refusing is not accusing. The evidence may be perfect; the verifier cannot say who
vouches for the registry.

Gating is deliberately scoped to the case where roots were supplied. A caller who supplies
no roots sees at most `REVIEW`, not a refusal of everything: turning every unpinned exchange into a
failure would break every existing bilateral arrangement to close a hole those
callers never opened.

## 3. The trust-root document

Roots are supplied to the verifier **out of band**, as a document separate from the trust
registry they authenticate. A verifier **MUST NOT** read roots from the registry it is
authenticating: that is circular, and it is the defect root authentication exists to close.

The document is a JSON object with exactly three members, all required: `object_type`, exactly
`trust_root_document`; `schema_version`, the document's version identifier, exactly `v1` in this
version; and `roots`, a non-empty array. The top level is closed, as each element is: a document
that is not a JSON object, that lacks a member, that carries any other member, whose
`object_type` or `schema_version` is any other value, or whose array is empty or not an array, is
malformed and **MUST** be refused, not treated as "no roots pinned". This version defines no
other name for the array and no earlier version of the document: a document whose array is named
`trust_roots` is malformed.

`schema_version` is read before the rest of this section, under the version gate of
[`document-contracts.md`](document-contracts.md): a document whose `object_type` is
`trust_root_document` and whose `schema_version` is a well-formed identifier of another version,
such as `v2`, is an unsupported version ([`report-contract.md`](report-contract.md) §5.5, exit `4`)
and is not malformed; any other value, such as `2`, is malformed.

A trust-root document the host fails to read is neither malformed nor "no roots pinned": nothing
about it was read. The run reports the host failure `trust_root_read_failed`
([`report-contract.md`](report-contract.md) §5.3), and root authentication is not evaluated: a trust
registry that holds reports `ROOT_SIGNATURE_NOT_EVALUATED`. A path that names no regular file is
refused as a malformed document is ([`report-contract.md`](report-contract.md) §4).

Each element is an object on a **closed** field set:

| field | type | required | meaning |
| --- | --- | --- | --- |
| `key_id` | string, not empty | yes | matched against the trust registry's `signature.key_id` |
| `key_type` | string | yes | the key type, an identifier matching `^[a-z0-9][a-z0-9_]{0,63}$` ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4) |
| `public_key_hex` | string | yes | the public key, lowercase hexadecimal; for `secp256k1` the uncompressed SEC1 point, `04 \|\| X \|\| Y`, 130 lowercase hex characters |
| `not_before` | string | yes | UTC instant, exactly `YYYY-MM-DDTHH:MM:SSZ` |
| `not_after` | string | yes | UTC instant, same form |
| `status` | string | no | `active` (default) or `revoked` |

A member the table does not name is a rejection, not an extension point. An unexpected
field could carry an assumption the verifier silently ignores, which is how a permissive
parser becomes a trust hole.

Further constraints, each of which **MUST** be enforced:

- `key_type` matches `^[a-z0-9][a-z0-9_]{0,63}$`. A well-formed key type the verifier does not
  support is not a document-validity rule: the root is well formed, and a trust registry it would
  authenticate reaches `UNSUPPORTED_SIGNATURE_ALGORITHM` (§5, row 11).
- `public_key_hex` is lowercase hexadecimal of even length, from 2 to 1024 characters, matching
  `^([0-9a-f]{2}){1,512}$`; when `key_type` is `secp256k1` it matches `^04[0-9a-f]{128}$`. It is
  not lower-cased first. This is a check on the *encoding*. Whether the point lies on the curve is
  **not** a document-validity rule: a root whose key is off the curve is well formed, no signature
  verifies under it, and a trust registry it would authenticate reaches `ROOT_SIGNATURE_INVALID`
  (§5, row 12). The distinction matters because the two lead to different outcomes: a malformed
  document is refused, with exit `64` on a command line and an error of the host language from a
  library, and a failed verification is a verdict. An implementation that moved the check forward
  would refuse where a conforming one reports a verdict.
- `not_before` and `not_after` match `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$`
  and are calendar instants ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md),
  "Input strictness", rule 8). No offset forms, no fractional seconds, no February 30 and no
  second 60.
- `not_after` is strictly later than `not_before`. An empty or inverted window is
  malformed, not merely unsatisfiable. The windows of a trust registry and of its entries follow
  a different rule in this version: equal bounds are a valid window of one second there
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §3). A root whose
  `not_before` equals its `not_after` is malformed; a trust-registry window with equal bounds is
  not.
- `status` is one of `active` or `revoked`. Any other value is malformed.
- `key_id` is not empty in the sense of [`bundle-objects.md`](bundle-objects.md): it has at least
  one code point outside the whitespace set W. Wherever a `key_id` is matched (§5, rows 6 and 7),
  the comparison is exact equality of code units: nothing is trimmed, case-folded or normalized, and
  two identifiers that differ only in letter case or in Unicode normalization form are different
  keys. Every member is of the type the table gives it, as written: a `key_id` of `9` is not the
  string `"9"`, and nothing is converted before it is checked. The comparison is the one
  [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7 defines.

**The whole document is validated when it is read.** A verifier **MUST** validate the
trust-root document against this section when it reads it, before it evaluates any row of §5:
the document itself, and every element of its array, whatever the element's `key_id` and
whether or not the trust registry names it. A document that breaks this section anywhere is
malformed, and a malformed document is refused as a whole. It is never evaluated in part, and no
status of §5 reports it: those statuses are facts about a trust registry measured against a
well-formed set of roots, so the refusal comes before every one of them, including those that
would otherwise hold first, such as `MALFORMED_SIGNATURE` or `UNKNOWN_ROOT_KEY`.

- A command line refuses a malformed document with exit `64` and no report
  ([`report-contract.md`](report-contract.md) §4), whatever the bundle, the registry entry and the
  trust registry hold.
- A library interface that accepts trust roots, as a document or as roots already built from
  one, refuses a set that has any root breaking this section with an error of the host language,
  before it evaluates any row of §5 or reads any evidence, and returns no report.

In the first table `R` stands for a well-formed root and `H` for the two members
`"object_type":"trust_root_document","schema_version":"v1"`. The second table starts from the
document `{H,"roots":[N]}`, where `N` is a well-formed root whose `key_id` the trust registry's
`signature.key_id` names and whose window holds the evaluation time. A case either changes one
member of `N`, or adds a second root, `root-9`: a copy of `N` whose `key_id` is `root-9`, with
the change applied to it, so that `root-9` carries `N`'s key unless the case gives it another. A `value` of absent removes the member; a `member` of — replaces the
whole element with the value. The trust registry is signed by `N`, or differs from that as the
column says.

| document | document is |
| --- | --- |
| `{H,"roots":[R]}` | well-formed |
| `{"object_type":"trust_root_document","schema_version":"v2","roots":[R]}` | an unsupported version |
| `{"object_type":"trust_root_document","schema_version":"2","roots":[R]}` | malformed |
| `{"object_type":"trust_roots","schema_version":"v1","roots":[R]}` | malformed |
| `{"schema_version":"v1","roots":[R]}` | malformed |
| `{"roots":[R]}` | malformed |
| `{H,"trust_roots":[R]}` | malformed |
| `{H,"roots":[]}` | malformed |
| `{H,"roots":R}` | malformed |
| `{H}` | malformed |
| `{}` | malformed |
| `[R]` | malformed |
| `{H,"roots":[R],"trust_roots":[R]}` | malformed |
| `{H,"roots":[R],"version":1}` | malformed |

| case | root | member | value | trust registry | outcome |
| --- | --- | --- | --- | --- | --- |
| `well-formed` | — | — | — | signed by `N` | `ROOT_SIGNATURE_VALID` |
| `well-formed-signature-form` | — | — | — | signature not lowercase hex | `MALFORMED_SIGNATURE` |
| `well-formed-unknown-key` | — | — | — | names a key no root has | `UNKNOWN_ROOT_KEY` |
| `well-formed-altered` | — | — | — | altered after signing | `ROOT_SIGNATURE_INVALID` |
| `named-revoked` | `N` | `status` | `"revoked"` | signed by `N` | `ROOT_KEY_REVOKED` |
| `other-revoked` | `root-9` | `status` | `"revoked"` | signed by `N` | `AMBIGUOUS_ROOT_KEY` |
| `named-status` | `N` | `status` | `"suspended"` | signed by `N` | refused |
| `named-status-signature-form` | `N` | `status` | `"suspended"` | signature not lowercase hex | refused |
| `other-status` | `root-9` | `status` | `"suspended"` | signed by `N` | refused |
| `other-status-unknown-key` | `root-9` | `status` | `"suspended"` | names a key no root has | refused |
| `other-status-null` | `root-9` | `status` | `null` | signed by `N` | refused |
| `other-public-key` | `root-9` | `public_key_hex` | `"04AB"` | signed by `N` | refused |
| `other-no-key-type` | `root-9` | `key_type` | absent | signed by `N` | refused |
| `other-key-type-form` | `root-9` | `key_type` | `"Ed25519"` | signed by `N` | refused |
| `other-key-type-unsupported` | `root-9` | `key_type`, `public_key_hex` | `"ed25519"`, and a key of its own that shares no point with `N`'s | signed by `N` | `ROOT_SIGNATURE_VALID` |
| `other-key-type-shared-point` | `root-9` | `key_type` | `"ed25519"`, `root-9` still carrying `N`'s key | signed by `N` | `AMBIGUOUS_ROOT_KEY` |
| `named-key-type-unsupported` | `N` | `key_type` | `"ed25519"` | signed by `N` | `UNSUPPORTED_SIGNATURE_ALGORITHM` |
| `named-key-id-case` | `N` | `key_id` | `N`'s `key_id` in upper case | signed by `N` | `UNKNOWN_ROOT_KEY` |
| `other-unknown-member` | `root-9` | `comment` | `"spare"` | signed by `N` | refused |
| `other-no-not-after` | `root-9` | `not_after` | absent | signed by `N` | refused |
| `other-inverted-window` | `root-9` | `not_after` | `"0001-01-01T00:00:00Z"` | signed by `N` | refused |
| `other-february-30` | `root-9` | `not_before` | `"2026-02-30T00:00:00Z"` | signed by `N` | refused |
| `other-key-id-number` | `root-9` | `key_id` | `9` | signed by `N` | refused |
| `other-key-id-blank` | `root-9` | `key_id` | `"\ufeff"` | signed by `N` | refused |
| `other-not-an-object` | `root-9` | — | `"root-9"` | signed by `N` | refused |

The values in these tables are written as JSON. An outcome of `refused` is the refusal of the
invocation, before any evidence is read: exit `64` on a command line and an error of the host
language from a library, as above.

A root is found by its `key_id`, and its key is then compared with the key of every other pinned
root. A document that lists one public key under two `key_id` values is well formed, so it is
accepted when it is read: the case `other-revoked` is one, since `root-9` there carries `N`'s key.
A trust registry whose `signature.key_id` names either of those roots stops at row 7 of §5 with
`AMBIGUOUS_ROOT_KEY`, whatever the statuses and the key types of the two. The comparison matters
because the trust registry's `signature.key_id` is outside the bytes a root signs (§4): were roots
told apart by `key_id` alone, whoever holds a trust registry signed under a revoked `key_id` could
rewrite it to name an active one carrying the same key, without any private key, and the registry
would reach `ROOT_SIGNATURE_VALID`. Two roots share a key when their `public_key_hex` values share
a point, as [`trust-registry-authorization.md`](trust-registry-authorization.md) §5 defines it:
the compressed and the uncompressed encodings of one secp256k1 key share it, and a value that
encodes no point shares none. An operator SHOULD NOT list one public key under more than one
`key_id`.

Example:

```json
{
  "object_type": "trust_root_document",
  "schema_version": "v1",
  "roots": [
    {
      "key_id": "root-1",
      "key_type": "secp256k1",
      "public_key_hex": "04ab...",
      "not_before": "2020-01-01T00:00:00Z",
      "not_after": "2030-01-01T00:00:00Z",
      "status": "active"
    }
  ]
}
```

A conforming verifier ships **no** pinned roots by default. Populating the set is a
governance act that follows key generation, and a default that passed when nothing was
pinned would convert a truthful "not verified" into a false "verified".

## 4. Exact signing message

The message a root signs over a trust registry is:

```text
ASCII/hex prefix:
LOQUITUR 00 TRUST_REGISTRY 00 ROOT_SIGNATURE 00 V1 00

followed immediately by:
RFC 8785 canonical UTF-8 bytes of the root signing envelope object.
```

The prefix bytes are:

```text
4c4f5155495455520054525553545f524547495354525900524f4f545f5349474e415455524500563100
```

The closed root signing envelope is:

```json
{
  "domain": "org.loquitur.protocol.trust-registry-root-signature",
  "envelope_schema": "loquitur.trust_registry_root_signing_envelope.v1",
  "envelope_version": 1,
  "payload": { "...": "the trust registry without its signature member" },
  "payload_schema": "loquitur.trust_registry.v1",
  "signature_algorithm": "secp256k1_ecdsa_sha256"
}
```

`payload` is the trust-registry object with the member `signature` removed and nothing
else removed. A signature cannot cover itself. No other member is excluded. In particular, unlike
the registry-entry construction in [`signing-envelope-v2.md`](signing-envelope-v2.md), there is no
`anchor` or `anchored_at` exclusion here, because a trust registry carries neither.

The root signs:

```text
SHA-256(prefix || JCS(envelope))
```

SHA-256 is applied exactly once, as
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4 states: the 32-byte digest
above is the ECDSA hash value, which is the same as ECDSA with SHA-256 over the signing message
bytes, and the digest is never hashed again.

The envelope keys above are already in JCS order; a conforming implementation
does not depend on that, since RFC 8785 sorts them.

The prefix and the `domain`, `envelope_schema` and `payload_schema` strings are opaque
domain-separation tags. They name no domain and claim nothing about who controls one; they are
compared as bytes, and their only job is to make the message of one construction differ from the
message of every other.

### 4.1 Domain-separation invariant

A signature created for the registry-entry envelope of
[`signing-envelope-v2.md`](signing-envelope-v2.md), for another envelope version, another payload
schema or another signature algorithm **MUST NOT** verify here. The fixed prefix and the canonical
envelope both bind the context. The two prefixes are distinct byte strings and neither is a prefix
of the other.

### 4.2 Signature encoding

The trust registry's own `signature` member is an object declaring:

```json
{
  "algorithm": "secp256k1_ecdsa_sha256",
  "key_id": "<the pinned root's key_id>",
  "signature": "<compact-low-S-r||s-hex>"
}
```

`signature` is `r || s` as exactly 128 lowercase hex characters. The low-S rule of
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4 applies unchanged: a
signature whose `s` exceeds `n/2` is rejected on verification.

The algorithm is an identifier matching `^[a-z0-9][a-z0-9_]{0,63}$`; in protocol release 0.1
the verifier's allowlist holds only `secp256k1_ecdsa_sha256` with key type `secp256k1`; see
[`cryptographic-capabilities.md`](cryptographic-capabilities.md).

## 5. Evaluation order, and the status vocabulary

The time the decision is evaluated against is the operator's evaluation time
([`trust-registry-authorization.md`](trust-registry-authorization.md) §2), never read from the
system clock and never taken from a date the issuer wrote: a trust decision that depends on "now"
cannot be replayed or audited. Without an evaluation time, rows 9 and 10 are not evaluated, and
authorization is not established
([`trust-registry-authorization.md`](trust-registry-authorization.md) §2).

The roots were validated as a whole when they were read (§3): a malformed set was refused then,
and the rows below are evaluated only against a well-formed one. A verifier **MUST** reach its
answer in this order, returning at the first condition that holds. The order is normative, not an
implementation detail: two implementations that check the same conditions in a different order
report different facts about the same document.

| # | condition | status | effect |
| --- | --- | --- | --- |
| 1 | no root is pinned | `NO_PINNED_TRUST_ROOT` | review: `trust_registry_root_not_pinned` |
| 2 | the trust registry is not an object | `MALFORMED_TRUST_REGISTRY` | failure |
| 3 | it carries no `signature` object | `MALFORMED_SIGNATURE` | failure |
| 4 | `signature.algorithm` is in no pair of the verifier's allowlist | `UNSUPPORTED_SIGNATURE_ALGORITHM` | failure |
| 5 | `signature.signature` is not 128 lowercase hex characters | `MALFORMED_SIGNATURE` | failure |
| 6 | no pinned root has this `key_id` | `UNKNOWN_ROOT_KEY` | failure |
| 7 | more than one pinned root has this `key_id`, or the matched root shares its point ([`trust-registry-authorization.md`](trust-registry-authorization.md) §5) with another pinned root | `AMBIGUOUS_ROOT_KEY` | failure |
| 8 | the matched root's `status` is `revoked` | `ROOT_KEY_REVOKED` | failure |
| 9 | the evaluation time precedes `not_before` | `ROOT_KEY_NOT_YET_VALID` | review: `trust_root_outside_validity_window` |
| 10 | the evaluation time follows `not_after` | `ROOT_KEY_EXPIRED` | review: `trust_root_outside_validity_window` |
| 11 | the pair of `signature.algorithm` and the matched root's `key_type` is not in the verifier's allowlist | `UNSUPPORTED_SIGNATURE_ALGORITHM` | failure |
| 12 | the signature does not verify | `ROOT_SIGNATURE_INVALID` | failure |
| — | otherwise | `ROOT_SIGNATURE_VALID` | holds |

Both bounds of a root's window belong to it: an evaluation time equal to `not_before` or to
`not_after` is inside the window.

A report never reaches row 2 or row 3. A trust registry that is not an object stops authorization at
row 1 of [`trust-registry-authorization.md`](trust-registry-authorization.md) §6, and one that
carries no `signature` object breaks the trust registry's contract, whose schema requires the
member, and stops it at row 3 there; the root is then reported `ROOT_SIGNATURE_NOT_EVALUATED`.
`MALFORMED_TRUST_REGISTRY` and `MALFORMED_SIGNATURE` are what an interface that authenticates a
trust registry on its own reports for such documents.

Three points in that table are load-bearing and are stated rather than left to be
inferred:

**Revocation is checked before the validity window (8 before 9 and 10).** A root revoked
inside a lapsed window **MUST** be reported as revoked. The remedies differ, and losing a
revocation signal to a date-arithmetic detail is the failure this ordering exists to
prevent.

**`AMBIGUOUS_ROOT_KEY` is not `UNKNOWN_ROOT_KEY` (7, not 6).** Two pinned roots sharing a
`key_id` have no well-defined authority, and the key is manifestly *known*: it matched twice.
Reporting that as unknown would leave the truth surviving only in free text. Two pinned roots
sharing a point have no well-defined authority either: a status given to one of them would reach a
`key_id` and not the key, and row 7 holds before the revocation of row 8 is read, so a root revoked
under one `key_id` is not authoritative under another.

**A run that never reached root authentication reports `ROOT_SIGNATURE_NOT_EVALUATED`.**
That is a different fact from `NO_PINNED_TRUST_ROOT`, and collapsing the two recreates
precisely the ambiguity root authentication was written to remove.

## 6. Effect on the verdict

When roots are supplied and the registry fails to authenticate, the **verdict** changes, not merely
a note. A report that says `FAIL` in its detail and `PASS` in its headline is honest in the channel
nobody reads and wrong in the two an integrator consumes.

| roots supplied | root authentication | verdict |
| --- | --- | --- |
| no | — | `REVIEW`, with the review reason `trust_registry_root_not_pinned` |
| yes | stops at a row whose effect is a failure | `FAIL` |
| yes | stops at row 9 or 10: the matched root's window does not hold the evaluation time | `REVIEW`, with the review reason `trust_root_outside_validity_window` |
| yes | `ROOT_SIGNATURE_VALID` | no downgrade from this step; `PASS` if everything else holds and an evaluation time was supplied |

A root window that does not hold the operator's evaluation time is a question rather than a
failure for the reason [`trust-registry-authorization.md`](trust-registry-authorization.md) §6 gives
for a key's window: no time attested to the registry's signature exists in this version.

## 7. What an operator must do that no verifier can

Obtaining the root document through a channel the issuer does not control is the
operator's problem entirely, and no flag makes it. [`threat-model.md`](threat-model.md) §10 states
the rest.
