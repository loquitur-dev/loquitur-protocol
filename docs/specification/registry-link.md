# Registry-entry link verification (the `link` check)

Status: normative.

This document specifies the `link` check: how a verifier decides that a registry entry refers
to the bundle in hand. It names every comparison, the operands of each, what is and is not
normalized before comparing, how the comparisons combine into one result, and what the verdict the
entry commits to does to the run. [`registry-entry.md`](registry-entry.md) states three of the
comparisons (the policy version by `MAJOR`, the status-to-verdict mapping, the two names of the
vocabulary field), and [`verification-checks.md`](verification-checks.md) names two digests; this
document states every comparison, the order and duplicates of reason codes, and the three values of
the link result.

## 1. Inputs

The check reads three things: the registry entry the caller supplies, the bundle's
`verification_receipt.json`, and the results of the bundle layers the entry and the receipt
point at ([`bundle-objects.md`](bundle-objects.md)). Every JSON document is loaded under the
input-strictness rules of [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md)
before anything is compared.

A verifier **MUST** perform every check of §3, **MUST** combine them as §5 states, and **MUST
NOT** compare any operand in a form other than the one §4 fixes.

## 2. The two documents and their contracts

**The registry entry** satisfies its contract when it is a JSON object that satisfies
`schemas/registry_entry.schema.json`, every one of its instants is a calendar instant
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness"), its free
strings are not empty, and its verdict is the verdict its reason codes derive.

**Not empty** has the meaning [`bundle-objects.md`](bundle-objects.md) gives it: a string with at
least one code point outside the whitespace set W. The entry's free strings are `issuer_key_id`,
`policy_id`, `signature.key_id`, `anchor.anchor_reference` and `anchor.system`, the last three when
the object that carries them is present. The schema asks only for one character (`minLength` 1), so
a value made only of spaces satisfies it; an entry whose `issuer_key_id` or `policy_id` is such a
value names no key and no policy, and it breaks its contract in the `link` and `authorization`
checks alike, and so does an entry whose signature names no key or whose anchor names no system or
reference, whether or not a check reads them. Every other string member of the entry is held by the
schema to a pattern, an enumeration or a constant that no string of W matches. W decides emptiness
only: a value that is not empty is compared as written (§4).

| member | value | contract holds |
| --- | --- | --- |
| `issuer_key_id` | `"demo-key-2"` | yes |
| `issuer_key_id` | `" demo-key-2"` | yes |
| `issuer_key_id` | `" "` | no |
| `issuer_key_id` | `"\u00a0\t"` | no |
| `policy_id` | `"loquitur.policy.property.demo"` | yes |
| `policy_id` | `"\u3000"` | no |
| `policy_id` | `"\u200b"` | yes |
| `signature.key_id` | `" "` | no |
| `anchor.system` | `"eip155:1"` | yes |
| `anchor.system` | `"\u3000"` | no |
| `anchor.anchor_reference` | `"\u00a0"` | no |

The values in that table are written as JSON strings.

`asset_type` and `workflow` of the entry, `anchor.method`, and `asset_type` of the receipt are
identifiers, held to `^[a-z0-9][a-z0-9_]{0,63}$` by the schemas: any identifier satisfies the
contract, and whether the verifier's vocabulary registers it is judged after the contract
([`verification-vocabularies.md`](verification-vocabularies.md) §7). An unknown `asset_type` or
`workflow` is a review reason, and changes no comparison of §4.

**The verdict an entry's reason codes derive** is fixed by the rules VG-1 to VG-4 of
[`verdict-grounds.md`](verdict-grounds.md), read with `registry_entry.verdict` in place of
`verification_summary.status` and the verdict column of the severity-to-status map in place of
the status column:

- VG-1: `reason_codes` cites at least one code, and no code twice;
- VG-2: every cited code is in the catalog;
- VG-3: the verdict equals the verdict mapped from the highest severity among the cited codes:
  `info` to `PASS`, `warn` to `WARN`, `review` to `REVIEW`, `fail` to `FAIL`;
- VG-4: a `PASS` cites at least one code of severity `info`.

Equality, not a floor: a verdict less severe than its grounds and a verdict more severe than
them both break the contract. VG-5 to VG-7 do not apply, because an entry carries neither
`key_checks` nor `reason_context`. The schema already holds VG-1 and VG-2 (`minItems`,
`uniqueItems` and the `enum` of the items); VG-3 and VG-4 are held here.

| verdict | reason codes | grounds hold |
| --- | --- | --- |
| `PASS` | `["INTEGRITY_OK"]` | yes |
| `PASS` | `["INTEGRITY_OK","FRESHNESS_OK"]` | yes |
| `WARN` | `["INTEGRITY_OK","FRESHNESS_WARNING"]` | yes |
| `REVIEW` | `["INTEGRITY_OK","NEEDS_REVIEW"]` | yes |
| `FAIL` | `["INTEGRITY_OK","INTEGRITY_OFFLINE_FAIL"]` | yes |
| `PASS` | `["AUTHORIZATION_ISSUER_KEY_REVOKED"]` | no |
| `PASS` | `["FRESHNESS_WARNING"]` | no |
| `WARN` | `["INTEGRITY_OK"]` | no |
| `REVIEW` | `["FRESHNESS_WARNING"]` | no |
| `FAIL` | `["INTEGRITY_OK"]` | no |

**The receipt** satisfies its contract when it is a JSON object that satisfies
`schemas/verification_receipt.schema.json`, every one of its instants is a calendar instant, and
its free strings are not empty: `bundle_id`, `policy_id` and `verification_mode`, and `asset_id`,
`network`, `anchor_provider` and `anchor_type` when they are strings, each have a code point
outside W. The empty string has no code point at all, so `""` breaks the contract in each of
them, as a value made only of W does; the schema's `minLength` says the same for the empty string.

The rules VG-3 and VG-4 do not bind the receipt: its `status` is not compared with the verdict
its own `reason_codes` would derive, and a receipt whose status is milder or harsher than its
codes satisfies its contract. What the receipt's status must agree with is the entry's verdict,
through the comparison `status_verdict` of §3.

## 3. The comparisons

Each comparison is a check with one of three results: it holds, it does not hold, or it could
not be evaluated because an operand is missing. A **hard** check holds only when it was
evaluated and held; a hard check that could not be evaluated fails the link like one that did
not hold.

| check | hard | registry-entry operand | other operand | holds when |
| --- | --- | --- | --- | --- |
| `registry_entry_contract` | yes | the entry | none | the entry satisfies its contract (§2) |
| `verification_receipt_contract` | yes | none | the receipt | the receipt satisfies its contract (§2) |
| `manifest_hash` | yes | `manifest_hash` (§4) | the manifest digest (§4) | equal |
| `receipt_manifest_sha256` | yes | none | the receipt's `manifest_sha256`, against the manifest digest | equal |
| `receipt_hash` | yes | `receipt_hash` | the digest of the RFC 8785 canonical bytes of the whole receipt | equal |
| `receipt_bundle_id` | yes | none | the receipt's `bundle_id`, against the manifest's `bundle_id` | equal, and the manifest's `bundle_id` is a string with a code point outside W ([`bundle-objects.md`](bundle-objects.md) §2) |
| `receipt_p1_sha256` | yes | none | the receipt's `p1_sha256`, against the digest of the P1 that satisfied its contract, its size bound and its sidecar, whatever its canonical input (`ih`) check found | the receipt's value is `null` or absent, or it equals the digest of a P1 that satisfied its contract, its size bound and its sidecar; a P1 that was refused, failed its sidecar or was not evaluated has no digest, and a value the receipt names does not hold against it |
| `policy_id` | yes | `policy_id` | the receipt's `policy_id` | equal |
| `policy_version` | yes | the `MAJOR` of `policy_version` (§4) | the receipt's `policy_version`, as an integer (§4) | equal |
| `reason_code_catalog_version` | yes | `reason_code_catalog_version` | the receipt's `reason_code_vocabulary_version` | equal |
| `reason_codes` | yes | `reason_codes` | the receipt's `reason_codes` | equal as multisets (§4) |
| `asset_type` | yes | `asset_type` | the receipt's `asset_type` | equal |
| `status_verdict` | no | `verdict` | the receipt's `status`, mapped to a verdict (§4) | equal |

`workflow`, `issuer_id`, `issuer_key_id` and the entry's instants take part in no comparison
of the `link` check. An entry's `receipt_id` is not compared either: the receipt schema has no
member to compare it with. Nor is the receipt's `policy_pack_sha256`: in this version it is an
opaque value, and nothing is inferred from it.

## 4. What is compared, exactly

Every string is compared by exact equality of its code units. Nothing is trimmed, nothing is
case-folded, and no Unicode normalization is applied. The whitespace set W of
[`bundle-objects.md`](bundle-objects.md) decides only whether a value is empty; it never changes a
compared value. The operands below are derived before comparing, and nothing else is. The comparison
of strings is the one [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7
defines.

- **Digests are compared whole.** Every digest operand of §3 is spelled `sha256:` followed by
  64 lowercase hexadecimal characters
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §2), on both sides, and is
  compared as the whole string with `sha256:` followed by the recomputed digest. Nothing is removed
  first. A value in any other spelling equals no digest, and the check does not hold.
- **The manifest digest** is `sha256:` followed by the SHA-256 of the RFC 8785 canonical bytes of
  `manifest.json` as the verifier loaded it. It is the recomputed digest, not the content of
  `manifest.sha256`: a sidecar that does not match fails the manifest layer, not these checks. There
  is no manifest digest when `manifest.json` or `manifest.sha256` is not a regular member, or
  `manifest.json` cannot be loaded or canonicalized; the checks that read it do not hold.
- **The policy version.** The entry's `policy_version` is read as `MAJOR.MINOR.PATCH`,
  optionally followed by `-` and a pre-release label: the whole string matches
  `^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[A-Za-z0-9_.-]+)?$`, and `MAJOR` is the
  decimal value of the first group. Whether a `MAJOR` exists is decided by the form of the whole
  string: a version with a leading zero in any group has no `MAJOR`, although the schema's pattern
  admits it, and the check does not hold. The values of `MINOR`, `PATCH` and the pre-release label
  take no part in the comparison. The receipt's `policy_version` is a JSON number whose value is an
  integer, under the canonical numeric model of
  [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §6: `1`, `1.0` and `1e0`
  are the same integer. The two
  are compared as decimal text: the check holds when `MAJOR`, as written, is the same string as the
  receipt's integer written in decimal without a sign or leading zero. `MAJOR` is never converted to
  a number first, so its length, whatever it is, cannot make a verifier fail: a `MAJOR` of 4401
  digits is a string that equals no receipt integer, and the check does not hold.
- **The status mapping.** The receipt's `status` maps exactly, with no alias, to a verdict:
  `pass` to `PASS`, `warning` to `WARN`, `review` to `REVIEW`, `fail` to `FAIL`
  ([`registry-entry.md`](registry-entry.md)). A value outside those four maps to nothing.
- **Reason codes as a multiset.** The two arrays are compared as sorted sequences with every
  element kept: the order of the codes carries no meaning, and their multiplicity does. A code
  cited twice is already a contract violation of either document (§2), and it is not collapsed
  into one before any check sees it.

| case | field | registry entry | receipt | link holds |
| --- | --- | --- | --- | --- |
| `policy-version-major-equal` | `policy_version` | `"1.9.3"` | `1` | yes |
| `policy-version-pre-release` | `policy_version` | `"1.0.0-rc.1"` | `1` | yes |
| `policy-version-receipt-float` | `policy_version` | `"1.0.0"` | `1.0` | yes |
| `policy-version-receipt-exponent` | `policy_version` | `"1.0.0"` | `1e0` | yes |
| `policy-version-leading-zero` | `policy_version` | `"01.0.0"` | `1` | no |
| `policy-version-major-differs` | `policy_version` | `"2.0.0"` | `1` | no |
| `policy-version-major-very-long` | `policy_version` | `"1"` followed by 4400 `"0"`, then `".0.0"` | `1` | no |
| `policy-id-leading-space` | `policy_id` | `" loquitur.policy.property.demo"` | `"loquitur.policy.property.demo"` | no |
| `policy-id-same-space-both` | `policy_id` | `" loquitur.policy.property.demo"` | `" loquitur.policy.property.demo"` | yes |
| `policy-id-case` | `policy_id` | `"Loquitur.policy.property.demo"` | `"loquitur.policy.property.demo"` | no |
| `reason-codes-order` | `reason_codes` | `["INTEGRITY_OK","FRESHNESS_OK"]` | `["FRESHNESS_OK","INTEGRITY_OK"]` | yes |
| `reason-codes-subset` | `reason_codes` | `["INTEGRITY_OK","FRESHNESS_OK"]` | `["INTEGRITY_OK"]` | no |
| `reason-codes-duplicate` | `reason_codes` | `["INTEGRITY_OK","INTEGRITY_OK"]` | `["INTEGRITY_OK","INTEGRITY_OK"]` | no |
| `asset-type-differs` | `asset_type` | `"fund_nav"` | `"property"` | no |
| `status-maps-to-verdict` | `status` | `"WARN"` | `"warning"` | yes |
| `status-verdict-spelling` | `status` | `"PASS"` | `"PASS"` | no |
| `status-verdict-differ` | `status` | `"PASS"` | `"review"` | no |
| `manifest-hash-exact` | `manifest_hash` | `"sha256:<manifest digest>"` | none | yes |
| `manifest-hash-uppercase-digest` | `manifest_hash` | `"sha256:<MANIFEST DIGEST>"` | none | no |
| `manifest-hash-uppercase-prefix` | `manifest_hash` | `"SHA256:<manifest digest>"` | none | no |
| `manifest-hash-no-prefix` | `manifest_hash` | `"<manifest digest>"` | none | no |
| `receipt-manifest-sha256-no-prefix` | `manifest_sha256` | none | `"<manifest digest>"` | no |

In that table a value is written as JSON text; for `status` the registry-entry column is the
entry's `verdict` and the receipt column the receipt's `status`. `<manifest digest>` stands for
the 64 lowercase hexadecimal characters of the manifest digest, and `<MANIFEST DIGEST>` for the
same characters in upper case. Every other member of both documents is left as a valid pair,
and where a case changes a verdict the reason codes of both documents move with it, so that the
entry's grounds (§2) still hold.

## 5. The link result

The link **holds** when every hard check holds and no check was evaluated and failed to hold.
It is **unresolved** when every hard check holds, no check failed, and a check that is not hard
could not be evaluated. Otherwise it **does not hold**. Behind the two contracts of §2,
`status_verdict` is always evaluated, so a link either holds or does not.

The report's `registry_link` result has three values. In a run that reads a bundle, the rows
are read in order, and the first whose condition holds gives the value: a link whose input is
absent is `null` whatever else holds ([`bundle-objects.md`](bundle-objects.md) §6).

| `registry_link` | when |
| --- | --- |
| `null` | no registry entry was supplied; the bundle carries no `verification_receipt.json`; something that is not a regular file is found at the entry's path; or the host fails to read a document the link reads |
| `false` | otherwise, when the entry document is not strict JSON or is not an object (JSON `null` included); the receipt is not strict JSON, is not an object or breaks any part of its contract (§2: the schema, its instants and its free strings); the entry breaks its contract; or the link does not hold |
| `true` | the link holds |

A run that refuses its input as a whole ([`report-contract.md`](report-contract.md) §5.3) reads no
bundle, and the table does not apply to it: the link is refused with the input, and its
`registry_link` is `false` when a registry entry was supplied and `null` when none was
([`bundle-objects.md`](bundle-objects.md) §6).

`null` when a registry entry was supplied is not a pass: `link` was requested and is not
established. What the run is depends on why it is `null`. A bundle that carries no
`verification_receipt.json` has nothing the entry can be linked to, which is a question and not
a finding: the run is at least `OFFLINE_REVIEW`, with the review reason
`verification_receipt_not_provided` ([`report-contract.md`](report-contract.md) §3.3). An entry path
that names no regular file is refused (`registry_link_verification_failed`, `OFFLINE_FAIL`), and a
host that fails to read a document is a host failure (`registry_link_read_failed`). A link that does
not hold makes the run `OFFLINE_FAIL`. An unresolved link makes it at least `OFFLINE_REVIEW`.

## 6. The committed verdict

The link asks whether the entry and the receipt agree, and they can agree on `FAIL`. Once the
registry entry satisfies its contract (§2), in the `link` and `authorization` checks alike, the
verdict it commits to bounds the run, whatever the link result:

| entry verdict | effect on the run |
| --- | --- |
| `PASS` | none |
| `WARN` | at least `OFFLINE_REVIEW` |
| `REVIEW` | at least `OFFLINE_REVIEW` |
| `FAIL` | `OFFLINE_FAIL` |

The link result is not changed by it: an entry and a receipt that agree on `FAIL` are a link
that holds, over evidence the issuer published as rejected. An entry that breaks its contract
commits nothing, and its verdict has no effect of its own.

## 7. The trust registry beside the link

A trust registry is evaluated only when a registry entry was supplied, satisfies its contract
and its link holds. A link holds only over a receipt that satisfies the whole of its contract
(§2), its free strings included: beside a receipt whose free string is made only of W, the link
does not hold and the trust registry is not evaluated. In a run that reads a bundle, beside an entry
that breaks its contract, or a link that does not hold or is `null`, the trust registry reaches no
conclusion, whether or not it satisfies its own contract: the report's `trust_registry` result is
`null`, no signature is evaluated, and the report's `registry_signature` result is `UNSUPPORTED`. A
trust registry supplied without a registry entry cannot be honored, and it is not read.

A run that refuses its input as a whole evaluates no trust registry either. Its trust registry is
refused with the input: the report's `trust_registry` result is `false` when a registry entry and
a trust registry were supplied, and `registry_signature` is `UNSUPPORTED`
([`bundle-objects.md`](bundle-objects.md) §6).

## 8. What the `link` check does not establish

The check establishes that the entry commits to this bundle's manifest and receipt. It does not
evaluate the entry's signature, the issuer's authority or whether the entry was published: an
interceptor who rewrites the bundle and the entry consistently produces a link that holds
([`threat-model.md`](threat-model.md), adversary A3). Those questions belong to the `authorization`
check and to the reserved checks after it.
