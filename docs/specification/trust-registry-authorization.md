# Issuer authorization against a trust registry (the `authorization` check)

Status: normative.

This document specifies how a verifier decides, in the `authorization` check, that the key which
signed a registry entry is authorized by a trust registry: which instant judges the key, what each
lifecycle state and validity window means, what makes a trust registry contradict itself, how the
key is found, the order in which the conditions are evaluated, the signature step that follows, and
the statuses each outcome reports. Section 10 lists what a trust registry may carry, and
[`verification-checks.md`](verification-checks.md) names the property the check answers; this
document states what those members mean and how a verifier reaches each status.
[`trust-root.md`](trust-root.md) specifies the separate question of whether the trust registry
itself is authentic.

## 1. Inputs and preconditions

The check reads the registry entry, the trust registry, and optionally an evaluation time
supplied by the operator and a trust-root document ([`trust-root.md`](trust-root.md) §3). Every JSON
document is loaded under the input-strictness rules of
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md).

A verifier evaluates a trust registry only when a registry entry was supplied, the entry
satisfies its contract and its link holds ([`registry-link.md`](registry-link.md) §7). Beside an
entry or a link that fails, the trust registry reaches no conclusion. A trust registry supplied
without a registry entry cannot be honored, and is not read. A trust registry the host fails to read
is not evaluated either: no row of §6 is a finding about bytes nobody read, and the run reports the
host failure `trust_registry_read_failed` with `trust_registry` `null`
([`report-contract.md`](report-contract.md) §5.3). Row 1 of §6 is a fact about what was read, or
about a path at which something that is not a regular file is found; nothing found at the trust
registry's path refuses the run as a whole ([`report-contract.md`](report-contract.md) §5.3,
`input_not_found`).

## 2. The evaluation time

A key is authorized, or not, at an instant, and the choice of instant decides the outcome. The
evaluation time is the operator's, and only the operator's.

- The operator supplies it: on a command line as `--evaluation-time`, in a library as
  `evaluation_time` (Python) or `evaluationTime` (TypeScript), and the report states it as
  `evaluation_time` ([`report-contract.md`](report-contract.md) §2). It **MUST** be a calendar
  instant of the form `YYYY-MM-DDTHH:MM:SSZ`
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness"); a
  verifier refuses any other value before evaluating anything
  ([`report-contract.md`](report-contract.md) §4).
- **Issuer dates never decide authorization.** The entry's `effective_at`, `issued_at` and
  `anchored_at` are written by the party being verified ([`threat-model.md`](threat-model.md) §6),
  and no verifier reads any of them as a time at which to judge a key, a registry or a root.
- **Without an evaluation time, authorization is not established.** The trust registry is still
  evaluated, with every row of §6 that does not read the time; rows 9 to 12 are not evaluated, and
  neither are rows 9 and 10 of [`trust-root.md`](trust-root.md) §5. When that evaluation does not
  fail, the run is `OFFLINE_REVIEW` with the review reason `evaluation_time_not_provided`, never a
  usage error. A revoked or suspended key, a contract that does not hold, a key that is not found or
  is out of scope, and a signature that does not verify fail the run whether or not a time was
  supplied: a coherently revoked key is revoked at every instant.

**No other source.** This version of the protocol defines no time-stamp token and no other
attestation of time: a time that a third party attests to a signature is not yet defined, and
the operator's evaluation time is the only time a verifier reads.

Instants are compared as UTC seconds. The same evaluation time is the time of root
authentication ([`trust-root.md`](trust-root.md) §5).

| case | operator evaluation time | key window holds it | outcome |
| --- | --- | --- | --- |
| `operator-time` | `2026-05-20T00:00:00Z` | yes | authorization judged at `2026-05-20T00:00:00Z` |
| `no-time-active-key` | none | not judged | `OFFLINE_REVIEW`, `evaluation_time_not_provided` |
| `no-time-revoked-key` | none | not judged | `OFFLINE_FAIL`, `ISSUER_KEY_REVOKED` |
| `operator-time-key-expired` | one second after the key's `expires_at` | no | `OFFLINE_REVIEW`, `issuer_key_outside_validity_window` |

## 3. The trust registry's contract

A trust registry satisfies its contract when it is a JSON object that satisfies
`schemas/trust_registry.schema.json`, every instant it carries is a calendar instant, used or
not, its free strings are not empty, and it does not contradict itself. Its free strings are
`signature.key_id` and, in every trust entry, `issuer_display_name`, `issuer_key_id`, and `notes`
and `revocation_reason` when they are strings: each has a code point outside the whitespace set W
([`bundle-objects.md`](bundle-objects.md)), whether or not the entry is the one the registry entry
names. `signature.signature` is not among them: its form is judged by
[`trust-root.md`](trust-root.md) when a root authenticates the registry. Each element of a trust
entry's `allowed_asset_types` and `allowed_workflows` is an identifier, `^[a-z0-9][a-z0-9_]{0,63}$`,
and an element that is not one breaks the contract
([`verification-vocabularies.md`](verification-vocabularies.md) §7). A trust registry contradicts
itself, and is malformed, when any of these holds for the registry or for **any** of its trust
entries, not only the one the registry entry names:

- a trust entry with status `active` carries a `revoked_at` or a `revocation_reason` that is not
  `null`;
- a trust entry with status `suspended` carries a `revoked_at` or a `revocation_reason` that is
  not `null`: a suspension is reversible and a revocation is not, so an entry that records both
  says two things about one key;
- a trust entry with status `revoked` carries no `revoked_at`, or a `null` one;
- a trust entry's `effective_from` is later than its `expires_at`;
- the registry's `effective_at` is later than its `expires_at`;
- the registry's `issued_at` is later than its `expires_at`: a registry cannot be issued after it
  expires.

Contradictory trust material is refused rather than read one way or the other. Two cases are not
contradictions. A registry issued before it takes effect is issued in advance, and is valid. A
window whose bounds are equal is a window of one second, and is valid; a trust root's window, by
contrast, must be non-empty ([`trust-root.md`](trust-root.md) §3). Nor are two trust entries that
carry one public key under different labels, whatever their statuses: the registry keeps its
contract, and a registry entry that names either of them stops at row 6 of §6, as §5 states.

| case | trust registry | contract holds |
| --- | --- | --- |
| `active-with-revoked-at` | an `active` entry with `revoked_at` `"2026-05-01T00:00:00Z"` | no |
| `active-with-revocation-reason` | an `active` entry with `revocation_reason` `"compromised"` | no |
| `suspended-with-revoked-at` | a `suspended` entry with `revoked_at` `"2026-05-01T00:00:00Z"` | no |
| `suspended-with-revocation-reason` | a `suspended` entry with `revocation_reason` `"compromised"` | no |
| `revoked-without-revoked-at` | a `revoked` entry with `revoked_at` `null` | no |
| `key-window-inverted` | an entry with `effective_from` later than its `expires_at` | no |
| `key-window-one-second` | an entry with `effective_from` equal to its `expires_at` | yes |
| `registry-window-inverted` | `effective_at` later than `expires_at` | no |
| `registry-issued-after-expiry` | `issued_at` later than `expires_at` | no |
| `registry-issued-in-advance` | `issued_at` earlier than `effective_at` | yes |
| `second-entry-contradicts` | the authorized entry is coherent; a second entry is `active` with a `revoked_at` | no |
| `entry-issuer-key-id-blank` | an entry with `issuer_key_id` `" "` | no |
| `entry-display-name-blank` | an entry with `issuer_display_name` `"\u00a0"` | no |
| `entry-notes-blank` | an entry with `notes` `"\u3000"` | no |
| `entry-revocation-reason-blank` | a `revoked` entry with a `revoked_at` and `revocation_reason` `" "` | no |
| `signature-key-id-blank` | `signature.key_id` `"\t"` | no |
| `entry-notes-zero-width-space` | an entry with `notes` `"\u200b"` | yes |

## 4. Lifecycle states and validity windows

A trust entry's `status` is one of three values, and the status alone decides whether the key
may authorize anything:

| status | meaning | may authorize |
| --- | --- | --- |
| `active` | the key is in service | yes, at an instant inside both windows and within its scope |
| `suspended` | the key is withheld, reversibly | never, whatever the instant |
| `revoked` | the key's authority was withdrawn | never, whatever the instant |

A revoked entry carries `revoked_at` (§3). The instant it records, and `revocation_reason`, are
not compared with the evaluation time: a coherent revoked entry is revoked at every instant.

Two windows apply, and both include their bounds. The trust registry is in effect at an instant
`t` when `effective_at` ≤ `t` ≤ `expires_at`; a trust entry's key is in effect at `t` when
`effective_from` ≤ `t` ≤ `expires_at`.

| case | evaluation time | authorized |
| --- | --- | --- |
| `key-effective-from-equal` | equal to the entry's `effective_from` | yes |
| `key-expires-at-equal` | equal to the entry's `expires_at` | yes |
| `registry-effective-at-equal` | equal to the registry's `effective_at` | yes |
| `registry-expires-at-equal` | equal to the registry's `expires_at` | yes |
| `key-expires-at-one-second-after` | one second after the entry's `expires_at` | no, and the run is `OFFLINE_REVIEW` (§9) |

A revoked or suspended key is reported as such even when the registry copy is stale: its status
is evaluated before the registry's window (§6), so a revocation signal is never lost to the age
of the copy that carries it.

## 5. Finding the key, and its scope

The registry entry names its issuer and key by `issuer_id` and `issuer_key_id`. A verifier finds
the trust entries whose `issuer_id` equals the entry's, and among them those whose
`issuer_key_id` equals the entry's. Both comparisons, and the key comparisons of rows 18 and 19 of
§6, are exact equality of code units: nothing is trimmed, case-folded or normalised, so keys that
differ only in letter case or in Unicode normalisation form do not match. The comparison is the
one [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7 defines.

- No trust entry carries the issuer: the issuer is not found.
- Trust entries carry the issuer and none carries the key: the key is not found.
- More than one trust entry carries both: the key is ambiguous. That holds whatever their
  statuses and whatever their order. A pair listed twice has no well-defined authority, and
  resolving it by position would let an `active` duplicate listed first authorize a key revoked
  in the second. The same `issuer_key_id` under another `issuer_id` is still not a label
  duplicate; whether the two carry one key is the point comparison below. Ambiguous entries differ
  in some other member: an exact copy of a trust entry is already refused by the trust registry's
  contract (§6, row 3).
- The trust entry found shares its point with another trust entry of the registry: the key is
  ambiguous as well. That holds whatever the statuses, the issuers and the key types of the two
  entries.

A trust entry is found by its labels, and its key is then compared with the key of every other trust
entry of the registry, so a status reaches the key material and not only the label that carries it.

The **point** of a `public_key_hex` is the secp256k1 point it encodes in SEC1, whatever the
`key_type` beside it. A value encodes a point when it is either a compressed encoding, `02` or `03`
followed by the 32-byte X, or an uncompressed one, `04` followed by the 32-byte X and the 32-byte Y;
X and Y are integers below the field prime p; the point (X, Y) lies on the curve, where for a
compressed encoding Y is the one of the two roots whose parity the prefix names (`02` even, `03`
odd); and the point is not the point at infinity. A
value that encodes no point, of any other length or prefix, or off the curve, has no point and
shares none. Two values share a point when both encode one and the two points are equal, so the
compressed and the uncompressed encodings of one key share it. [`trust-root.md`](trust-root.md) §5
compares pinned roots by the same definition.

When a trust registry lists one public key in two trust entries, under two `issuer_key_id` values of
one issuer or under two issuers, one `revoked` and the other `active`, an entry that names the
active pair stops at row 6 of §6 with `TRUST_REGISTRY_AMBIGUOUS_KEY`: the revocation of the other
pair is not lost to the label that carries the key. The rule reads only the trust entry found: two
other trust entries that share a point with each other leave an entry that names neither
unaffected, and the registry keeps its contract (§3). A trust-registry operator SHOULD NOT list one
public key in more than one trust entry.

The key's scope is its two allow-lists. The entry is within scope when its `asset_type` is an
element of `allowed_asset_types` **and** its `workflow` is an element of `allowed_workflows`, by
exact equality. An empty list allows nothing. Exact equality here, and in §11, is the comparison of
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7.

The comparison is the same whether or not the vocabulary the verifier holds registers the values
([`verification-vocabularies.md`](verification-vocabularies.md) §7): a value the verifier does not
know is in scope when an allow-list holds it, and out of scope when none does. No element stands for
every value (§11).

## 6. Evaluation order and statuses

A verifier **MUST** evaluate the conditions below in this order and stop at the first that holds,
reporting its `authorization_status` and `signature_status`. A `signature_status` of `null` means
the signature step was not reached. Two implementations that check the same conditions in a
different order report different facts about the same documents, so the order is normative.
Rows 9 to 12 are evaluated only when an evaluation time was supplied (§2). The last column is the
effect on the run (§9).

| # | condition | `authorization_status` | `signature_status` | effect |
| --- | --- | --- | --- | --- |
| 1 | the trust registry cannot be read: what its path names is not a regular file, or its document is not strict JSON or is not an object | `INVALID_TRUST_REGISTRY` | `null` | failure |
| 2 | the registry entry breaks its contract ([`registry-link.md`](registry-link.md) §2) | `INVALID_REGISTRY_ENTRY` | `null` | failure |
| 3 | the trust registry breaks its contract (§3) | `INVALID_TRUST_REGISTRY` | `null` | failure |
| 4 | no trust entry carries the entry's `issuer_id` | `ISSUER_NOT_FOUND` | `null` | failure |
| 5 | no trust entry of the issuer carries the entry's `issuer_key_id` | `ISSUER_KEY_NOT_FOUND` | `null` | failure |
| 6 | more than one trust entry of the issuer carries it, or the trust entry found shares its point (§5) with another trust entry of the registry, whatever the statuses, the issuers and the key types of the entries | `TRUST_REGISTRY_AMBIGUOUS_KEY` | `null` | failure |
| 7 | the trust entry's `status` is `revoked` | `ISSUER_KEY_REVOKED` | `null` | failure |
| 8 | the trust entry's `status` is `suspended` | `ISSUER_KEY_SUSPENDED` | `null` | failure |
| 9 | the evaluation time is earlier than the registry's `effective_at` | `TRUST_REGISTRY_NOT_YET_EFFECTIVE` | `null` | review: `trust_registry_not_current` |
| 10 | the evaluation time is later than the registry's `expires_at` | `TRUST_REGISTRY_EXPIRED` | `null` | review: `trust_registry_not_current` |
| 11 | the evaluation time is earlier than the trust entry's `effective_from` | `ISSUER_KEY_NOT_YET_EFFECTIVE` | `null` | review: `issuer_key_outside_validity_window` |
| 12 | the evaluation time is later than the trust entry's `expires_at` | `ISSUER_KEY_EXPIRED` | `null` | review: `issuer_key_outside_validity_window` |
| 13 | the entry's `asset_type` or `workflow` is outside the key's scope (§5) | `ISSUER_KEY_SCOPE_MISMATCH` | `null` | failure |
| 14 | the entry carries no signature object: `signature` is absent, `null` or not an object | `AUTHORIZED_ACTIVE_KEY` | `MALFORMED_SIGNATURE` | failure |
| 15 | the signature names a payload other than `registry_entry_signing_payload_v2` version `2` | `AUTHORIZED_ACTIVE_KEY` | `UNSUPPORTED_SIGNING_PAYLOAD` | failure |
| 16 | the pair of the signature's `algorithm` and the trust entry's `key_type` is not in the verifier's allowlist ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4) | `AUTHORIZED_ACTIVE_KEY` | `UNSUPPORTED_SIGNATURE_ALGORITHM` | failure |
| 17 | the signature's value is not a string of exactly 128 lowercase hexadecimal characters | `AUTHORIZED_ACTIVE_KEY` | `MALFORMED_SIGNATURE` | failure |
| 18 | the signature's `key_id` is not the trust entry's `issuer_key_id` | `AUTHORIZED_ACTIVE_KEY` | `SIGNATURE_KEY_MISMATCH` | failure |
| 19 | the entry's `issuer_key_id` is not the trust entry's `issuer_key_id` | `AUTHORIZED_ACTIVE_KEY` | `SIGNATURE_KEY_MISMATCH` | failure |
| 20 | the signature does not verify | `AUTHORIZED_ACTIVE_KEY` | `SIGNATURE_INVALID` | failure |
| — | otherwise | `AUTHORIZED_ACTIVE_KEY` | `VALID_SIGNATURE` | holds |

A report never reaches row 2: an entry that breaks its contract fails the `link` check first
([`registry-link.md`](registry-link.md) §2), the authorization check is not evaluated, and the
report's `trust_registry` is `null`. `INVALID_REGISTRY_ENTRY` is what an interface that evaluates
authorization on its own reports for such an entry.

Points in that table that are load-bearing:

**The windows come before the scope (rows 9 to 12 before 13).** A registry or a key outside its
window stops the evaluation at a review, and a scope that would also fail is not reached. The
catalog gives the codes of those rows, `AUTHORIZATION_TRUST_MATERIAL_OUTSIDE_VALIDITY_WINDOW`,
`AUTHORIZATION_ISSUER_KEY_NOT_YET_EFFECTIVE` and `AUTHORIZATION_ISSUER_KEY_EXPIRED`, the severity
`review`, the outcome a run that stops there reaches, so that a published object citing one of
them does not say `fail` for what the run left open.

**Authorization comes before the signature (rows 1 to 13 before 14 to 20).** An unauthorized key
reports no signature status at all, rather than the outcome of a check that was never the
question.

**Key status before the registry's window, and the registry's window before the key's (7 and 8
before 9 and 10, before 11 and 12).** A revoked key behind a stale registry copy is reported as
revoked (§4). A registry that is not in effect answers nothing about any key in it, whatever that
key's own window says.

**The key's window before its scope (11 and 12 before 13).**

**A window outside the evaluation time is a question, not a failure (rows 9 to 12).** No time
attested to the signature exists in this version, so a verifier cannot tell a key used outside its
window from a key used inside it and judged later. A registry or key window that does not hold the
operator's evaluation time leaves authorization not established, and the run is `OFFLINE_REVIEW`.
Revocation and suspension are not windows: they fail the run at every time.

**The signature step follows the model of [`trust-root.md`](trust-root.md) §5.**
`MALFORMED_SIGNATURE` is a matter of form only: no signature object (row 14), or a value that is not
128 lowercase hexadecimal characters (row 17). The payload, the algorithm and the form are checked
before the key identifiers, as a root signature's algorithm and form come before its key lookup.
**The allowlist is the verifier's (row 16).** The entry and the trust registry admit any well-formed
algorithm and key-type identifier; a pair the verifier does not support reaches this row, whatever
the documents say about themselves. Everything that is well formed and does not verify is
`SIGNATURE_INVALID` (row 20): a public key that is not of the form of its key type (for `secp256k1`,
not an uncompressed point `^04[a-f0-9]{128}$`, a coordinate not below the field prime, or a point
off the curve), a payload that cannot be canonicalized, `r` or `s` equal to zero or not below the
group order, `s` above half the group order
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4), and a signature over
other bytes.

Four rows cannot be reached in a bundle verification, because an earlier step already refuses what
they test: row 2 (the trust registry is evaluated only when the registry entry satisfies its
contract and its link holds, [`report-contract.md`](report-contract.md) §5.4), row 15 (the version
gate of the signing payload, [`document-contracts.md`](document-contracts.md), "Version gate", and
the entry's contract fix the payload), row 17 (the entry's contract holds `signature.signature` to
128 lowercase hexadecimal characters, so a malformed value is `registry_entry_contract_violation`
first) and row 19 (the key was found by that identifier). They are stated because they fix the
answer of a verifier that evaluates authorization or the signature step on its own, and because
their position fixes the answer when two conditions hold together.

This protocol defines no earlier signing payload. A signature object that carries neither
`payload_id` nor `payload_version` breaks the entry's contract, and no verifier offers an option
that verifies it.

The signature is verified over the message of [`signing-envelope-v2.md`](signing-envelope-v2.md)
with the trust entry's `public_key_hex`;
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4 fixes the curve, the
encoding and the low-S rule.

## 7. Root authentication

When the evaluation reaches `VALID_SIGNATURE`, the verifier authenticates the trust registry
against the trust roots, in the order and with the statuses of [`trust-root.md`](trust-root.md) §5,
at the evaluation time of §2. A run that stopped at any row of §6 reports the root status
`ROOT_SIGNATURE_NOT_EVALUATED`; it did not reach the question, which is a different fact from
`NO_PINNED_TRUST_ROOT`.

## 8. Vocabularies

**Authorization status**, closed:

| `authorization_status` |
| --- |
| `AUTHORIZED_ACTIVE_KEY` |
| `INVALID_REGISTRY_ENTRY` |
| `INVALID_TRUST_REGISTRY` |
| `ISSUER_NOT_FOUND` |
| `ISSUER_KEY_NOT_FOUND` |
| `TRUST_REGISTRY_AMBIGUOUS_KEY` |
| `ISSUER_KEY_REVOKED` |
| `ISSUER_KEY_SUSPENDED` |
| `TRUST_REGISTRY_NOT_YET_EFFECTIVE` |
| `TRUST_REGISTRY_EXPIRED` |
| `ISSUER_KEY_NOT_YET_EFFECTIVE` |
| `ISSUER_KEY_EXPIRED` |
| `ISSUER_KEY_SCOPE_MISMATCH` |

**Signature status**, closed:

| `signature_status` |
| --- |
| `VALID_SIGNATURE` |
| `MALFORMED_SIGNATURE` |
| `UNSUPPORTED_SIGNING_PAYLOAD` |
| `UNSUPPORTED_SIGNATURE_ALGORITHM` |
| `SIGNATURE_KEY_MISMATCH` |
| `SIGNATURE_INVALID` |

**Root signature status**: the statuses of [`trust-root.md`](trust-root.md) §5, and
`ROOT_SIGNATURE_NOT_EVALUATED`.

A report carries no other summary of these statuses.

## 9. Effect on the run

The trust registry holds for a run when the authorization status is `AUTHORIZED_ACTIVE_KEY` and
the signature status is `VALID_SIGNATURE`. Otherwise the evaluation stopped at a row of §6, and
the row's effect decides: a failure makes the run `OFFLINE_FAIL`, and a review makes it at least
`OFFLINE_REVIEW` with the review reason the row names. When it holds, root authentication decides
as [`trust-root.md`](trust-root.md) §6 states: no root supplied, `OFFLINE_REVIEW`; roots supplied
whose authentication fails, `OFFLINE_FAIL`; a root window that does not hold the evaluation time,
`OFFLINE_REVIEW`; roots that authenticate the registry, no downgrade. Without an evaluation time, a
registry that holds and roots that do not fail still leave the run `OFFLINE_REVIEW` (§2).

The `authorization` check is established when the trust registry holds at the operator's
evaluation time and roots authenticate it at that time ([`report-contract.md`](report-contract.md)
§3.2). It establishes that the registry handed to the verifier authorizes the key that signed the
entry, for that scope, at that time. It does not establish that the registry is authentic unless a
root authenticated it, that the key was in its window when the entry was signed, or that the issuer
identifier names any real-world party ([`threat-model.md`](threat-model.md) §5, §6 and §8).

## 10. The trust registry

A trust registry is a versioned issuer/key authorization object.

A protocol 0.1 verifier accepts one trust-registry `key_type`, `secp256k1`. The 0.1 schemas admit
any well-formed key-type identifier, `ed25519` included, so the restriction is the verifier's
allowlist and not the schemas: a signature whose key is of any other type is refused at the
signature step (§6, row 16) with `UNSUPPORTED_SIGNATURE_ALGORITHM`, not as an invalid trust
registry. Ed25519 is not a protocol 0.1 capability; see [`cryptographic-capabilities.md`](cryptographic-capabilities.md) §2 and §3.

### 10.1 Purpose

The trust registry describes which issuer/key pairs are allowed for specific asset types and
workflows, as the authorization order of this document evaluates them. The asset types and workflows
are values of the registered vocabularies, which the profiles of the verticals define
([`verification-vocabularies.md`](verification-vocabularies.md) §5).

### 10.2 Public-safe content

A trust registry may include:

- issuer identifier;
- issuer display name or public label;
- issuer key identifier;
- public key material;
- key type;
- key lifecycle status;
- allowed asset types and workflows;
- effective and revocation timestamps;
- required signature object.

### 10.3 Forbidden content

A trust registry must not include private keys, seed phrases, signing secrets, KYC/AML records,
investor records, private asset data, document contents, valuation data, or private evidence
material.

### 10.4 Authorization

What a trust registry authorizes is specified in sections 2 to 9 of this document: the instant
that judges a key, the meaning of each lifecycle status and validity window, what makes a trust
registry contradict itself, how an issuer's key is found and scoped, the order of evaluation, the
signature step, and the statuses each outcome reports.

### 10.5 Root authentication

The `signature` object above is verified against a trust root supplied out of band. The
exact signing message, the closed shape of the trust-root document, the evaluation order
and the status vocabulary are specified in [`trust-root.md`](trust-root.md). This section defines
what a trust registry *is*; that document defines how one is authenticated.

### 10.6 Interpretation limits

A trust registry that satisfies its contract authorizes a key only in the terms of
[`trust-registry-authorization.md`](trust-registry-authorization.md), and it is authentic only when
a root pinned out of band authenticates it ([`trust-root.md`](trust-root.md)). Neither establishes
that an issuer identifier names a real-world party, that the copy in hand is the current one, or
that any deployment policy approves the issuer.

## 11. Scope across verticals

A trust registry may serve verticals the verifier does not know, and scope works for any number of
them. The allow-lists are compared by exact equality (§5), so:

- an entry whose `asset_type` and `workflow` are in the allow-lists is in scope, whether or not the
  verifier's vocabularies register them; an unknown value then makes the run a review, through the
  review reason `vocabulary_value_unknown`
  ([`verification-vocabularies.md`](verification-vocabularies.md) §7), and never a failure;
- an entry whose `asset_type` or `workflow` is in no allow-list is out of scope:
  `ISSUER_KEY_SCOPE_MISMATCH`, whatever the verifier's vocabularies hold, so an unknown value never
  masks a scope failure;
- an element of an allow-list that the verifier's vocabulary does not register is not a finding: a
  registry may authorize a key for a vertical a verifier does not support.

There is no wildcard. No element, such as `*` or `all`, stands for every asset type or every
workflow, and the identifier grammar cannot write one: a wildcard would widen the authority of every
key that carries it each time a vertical is registered, without a change to the registry its root
signed.
