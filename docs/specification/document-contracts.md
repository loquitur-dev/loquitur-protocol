# Member contracts of the documents a verifier loads

Status: normative appendix, adds no rule.

This document lists, for every document a verifier loads, every member at every depth: whether it
is required, its JSON type, the values it may take, values it may not, and what a run reports when
it is broken. It is the completeness surface of the closed contracts the other documents define:
[`bundle-objects.md`](bundle-objects.md) for the three bundle objects, the published schemas for the
receipt, the registry entry and the trust registry, and [`trust-root.md`](trust-root.md) for the
trust-root document.

Those rules are complete only when read together with three JSON Schemas and four other
documents. This appendix states the answer per member, so that two implementers do not assemble
different answers without either contradicting a sentence.

**It adds no rule of its own.** Every row cites the sentence, or the schema keyword, that states
it, in its last column. Where a row and the rule it cites differ, the cited rule is the protocol
and the row is a defect of this appendix.

Three suites hold the tables, and each holds a different part of them. This repository's
`tests/test_document_contracts.py` holds each row against the rule the row cites: that the
citation is a sentence of the document it names, or the schema keyword at the pointer it names;
that in a schema-backed section the `required`, `type` and `value` cells are the schema's own
keywords; that in a prose-backed section the `required` and `type` cells are what the declaring
document's own table states, so that no member row is held by nothing; that no member of a
closed field set or of a schema is missing a row; and that every outcome, of a member row, a
case or an input, is a value of [`report-contract.md`](report-contract.md). The reference verifiers
`loquitur-verify-py` and `loquitur-verify-ts` read the same tables and run them against themselves:
the mutation a row describes must carry that row's outcome, and a case must carry its own.
`loquitur-verify-py` runs §11, §12 and §15 through its command line, which must exit 64 and print no
report, because a trust-root document, a registered vocabulary document and a refused invocation
yield no report; `loquitur-verify-ts` runs §11 and §15 through its library, which must refuse the
document with an error of the host language before it reads any evidence
([`report-contract.md`](report-contract.md) §4). What a suite runs, it holds: a row those runs do
not honor fails them rather than standing as prose.

How far each suite reaches is not described here. It is §14, in numbers the three suites read
from that section and compare with the cases they run, so that a coverage this appendix claims
and a suite does not have fails a build rather than standing as prose.

## 1. How to read a row

| column | meaning |
| --- | --- |
| member | the member's path in its document; `[i]` stands for every element of an array |
| required | whether the document is refused when the member is absent |
| type | the JSON types the member may have; `bytes` for a file that is not JSON |
| value | what the member's value must be, beyond its type |
| refused | example values that break the row, written as JSON; a verifier refuses each |
| outcome | what a run reports when the row is broken (§2) |
| rule | the sentence, or the schema keyword, that states the row |

A member that is `required` and absent has its row's outcome. A member that is not required may
be absent, and a member whose type includes `null` may be `null`: both are accepted, and a
verifier that refuses either is wrong. A row whose type is `bytes` describes a file rather than a
member, and what its absence means is a row of its section's case table.

A row's outcome is the outcome of one mutation of a valid baseline: a bundle, registry entry, trust
registry or trust-root document that breaks no row of its section, changed in the row's member
alone. Every digest that commits to the changed document, a sidecar, a manifest declaration or a
link, is recomputed over the changed bytes, so that the row's member is the only thing broken. A
row of a sidecar itself is the exception: the sidecar under test is not recomputed.

A case table, headed `case`, `outcome` and `rule`, carries what is not the mutation of one
member: a document that is not an object at all, a file that is absent, a bound on the whole
document. Every case is named and executed by the verifiers' suites.

Three refused values stand for bytes rather than JSON, and appear only for a member of type
`bytes`: `<upper>` is the correct digest in upper case, `<newline>` the correct digest followed
by a newline, and `<other>` the digest of something else.

A rule cell names either a document and a sentence of it, quoted, or a schema file and the JSON
pointer of the keyword. A member the table does not name is refused by the closed field set of
its document, which each section states.

The `refused` column is a sample, never the whole set: a value of another type, or outside the
stated value rule, is refused whether or not it appears there.

**The `type` column is a rule, not a description.** A value whose JSON type the cell does not
admit is refused with the row's outcome, and a value whose JSON type it admits is not refused for
its type. `-` in the `value` column means the row states no rule beyond its type, and a row that
says so accepts every value of every type it admits.

Two checks hold the column together, and it takes both, because a cell can fail the reader in
two directions. **The cell is held to the rule it cites.** This repository's test reads the type
the citation gives (the keyword of the schema for §8 to §10, the type column of
[`bundle-objects.md`](bundle-objects.md) §2, §3 and §4 for §3, §4 and §7, of
[`trust-root.md`](trust-root.md) §3 for the fields of §11, and, for a row that describes a document
as a whole rather than a field of one, the one JSON type the quoted sentence names) and fails when
the cell is not that type. Widening a cell therefore contradicts the rule the row itself names.
**The cell is run.** The verifiers' suites read the cell rather than the `refused` examples and run
one value of every JSON type it refuses, which must carry the row's outcome, and, where the `value`
cell is `-`, one value of every type it admits, which must be accepted; each row asserts that it
compared at least one value, so a cell that refuses nothing fails rather than passing over an empty
loop. What is counted there is the set of types the cell refuses, not the `refused` column of
examples: emptying that column removes examples rather than comparisons, which is why it is a sample
and the cell is the rule. A `bytes` cell admits no JSON type, and its row is run the same way: the
canonical form of a value of each JSON type, written as the whole file, carries the row's outcome.

Both checks are about the `type` column, so they reach the rows that have one: the member rows
of §3 to §11. The case tables, and the input rows of §12, state forms rather than JSON types,
have no `type` cell to hold, and are run through their own tables. A `bytes` row names no JSON
type, so what states its contract is the sentence its `rule` cell quotes rather than a source
table, and what runs it is the `refused` column beside it and the `bytes` run above. How many
rows each check reaches, and which suite runs which section, is §14.

**Absence and `null`.** For a member whose type includes `null`, an absent member and a `null`
one are the same, and both are accepted when the member is not required.

**`integer` and `-` in the `required` column.** An `integer` cell admits a JSON number whose value
is an integer under the canonical numeric model of
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §6: `2` and `2.0` are the same
integer, and `true` is not an integer. `-` in the `required` column means the
row states no requirement of its own: whether the member must be present is stated by the row of the
document, or of the parent member, that carries it.

### 1.1 Version gate

Every versioned object carries a closed version identifier, and a verifier reads it **before**
the object's contract, after input strictness. When the object is a JSON object, its type member
(where the table names one) is the known value, and its version member is well formed under the
table's grammar, the gate decides: the supported value continues to the contract, and any other
well-formed value **fires** the gate, an unsupported version
([`report-contract.md`](report-contract.md) §5.5, exit `4`). When any of those does not hold, the
gate does not fire, and the object's contract refuses the identifier as it refuses any other value:
a malformed identifier stays a refusal. No option of any verifier changes what a fired gate reports.

| # | object | known type | version member | supported | well formed |
| --- | --- | --- | --- | --- | --- |
| 1 | `trust_root_document` | `object_type` is `trust_root_document` | `schema_version` | `v1` | `^v[1-9][0-9]{0,8}$` |
| 2 | `manifest` | the member `manifest.json` | `schema_version` | `loquitur.bundle.v1` | `^loquitur\.bundle\.v[1-9][0-9]{0,8}$` |
| 3 | `verification_receipt` | `object_type` is `verification_receipt` | `schema_version` | `v2` | `^v[1-9][0-9]{0,8}$` |
| 4 | `reason_code_vocabulary` | the receipt, as in 3 | `reason_code_vocabulary_version` | `loquitur.reason_codes.v1` | `^loquitur\.reason_codes\.v[1-9][0-9]{0,8}$` |
| 5 | `registry_entry` | `object_type` is `registry_entry` | `schema_version` | `v1` | `^v[1-9][0-9]{0,8}$` |
| 6 | `reason_code_vocabulary` | the entry, as in 5 | `reason_code_catalog_version` | `loquitur.reason_codes.v1` | as in 4 |
| 7 | `signing_payload` | the entry, as in 5, whose `signature` is an object | `signature.payload_id` and `signature.payload_version` | `registry_entry_signing_payload_v2` and `2` | `payload_id` matches `^registry_entry_signing_payload_v[1-9][0-9]{0,8}$` and `payload_version` is an integer from 1 to 999999999 |
| 8 | `trust_registry` | `object_type` is `trust_registry` | `schema_version` | `v1` | `^v[1-9][0-9]{0,8}$` |

The gates are evaluated in the order of the table, each when the run reads its object: the
trust-root document when the invocation is read, the manifest and the receipt when the bundle is
read, the entry when the link reads it, and the trust registry when it is evaluated. The first
gate that fires stops the run. A signing payload whose two members are both the supported values
continues; any other well-formed pair fires gate 7, so `registry_entry_signing_payload_v3` with
`3`, and `registry_entry_signing_payload_v2` with `3`, are unsupported versions.

Extending a closed enumeration of an object, adding a member to its closed field set or changing
a rule of its contract changes the object's version identifier: an object of one version means
one thing. A value registered in a registered vocabulary extends no closed enumeration and changes
no version identifier: the members it governs admit every identifier
([`verification-vocabularies.md`](verification-vocabularies.md) §9). This version of the protocol
defines exactly the supported values above, and no earlier version of any object.

## 2. Outcomes

Each row's outcome is one of these. `status`, `verdict`, `exit_code`, `outcome.reason` and the
error codes are the normative report surface of [`report-contract.md`](report-contract.md) §2.

| outcome | `status` | `verdict` | `outcome.reason` | `errors` | exit | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `manifest-layer` | `OFFLINE_FAIL` | `FAIL` | `manifest_integrity_failed` | none | `1` | [`report-contract.md`](report-contract.md) "failed its manifest layer: the sidecar, a declared file or the closed contract did not hold" |
| `manifest-refused` | `OFFLINE_FAIL` | `FAIL` | `manifest_verification_failed` | `manifest_verification_failed` | `1` | [`report-contract.md`](report-contract.md) "`manifest.json` is not a regular member, is not strict JSON" |
| `p1-refused` | `OFFLINE_FAIL` | `FAIL` | `p1_verification_failed` | `p1_verification_failed` | `1` | [`report-contract.md`](report-contract.md) "P1 breaks its closed contract" |
| `p1-layer` | `OFFLINE_FAIL` | `FAIL` | `p1_integrity_failed` | none | `1` | [`report-contract.md`](report-contract.md) "failed its P1 layer" |
| `envelope-layer` | `OFFLINE_FAIL` | `FAIL` | `envelope_integrity_or_link_failed` | none | `1` | [`report-contract.md`](report-contract.md) "failed its envelope layer" |
| `envelope-refused` | `OFFLINE_FAIL` | `FAIL` | `envelope_verification_failed` | `envelope_verification_failed` | `1` | [`report-contract.md`](report-contract.md) "the envelope and `envelope.sha256` are both present and the envelope is not strict JSON" |
| `envelope-incomplete` | `OFFLINE_FAIL` | `FAIL` | `envelope_incomplete` | `envelope_incomplete` | `1` | [`report-contract.md`](report-contract.md) "exactly one of `envelope_env1.json` and `envelope.sha256` is present" |
| `unsupported-version` | `UNSUPPORTED_VERSION` | `null` | `unsupported_version` | `unsupported_version` | `4` | [`report-contract.md`](report-contract.md) "fires when an object of a known type carries a well-formed version identifier other than the one this version supports" |
| `receipt-refused` | `OFFLINE_FAIL` | `FAIL` | `verification_receipt_contract_violation` | `verification_receipt_contract_violation` | `1` | [`report-contract.md`](report-contract.md) "`verification_receipt.json` is present and is not strict JSON" |
| `entry-refused` | `OFFLINE_FAIL` | `FAIL` | `registry_entry_contract_violation` | `registry_entry_contract_violation` | `1` | [`report-contract.md`](report-contract.md) "the registry entry and the receipt are both objects, and the entry breaks its contract" |
| `entry-unreadable` | `OFFLINE_FAIL` | `FAIL` | `registry_link_verification_failed` | `registry_link_verification_failed` | `1` | [`report-contract.md`](report-contract.md) "its document is not strict JSON or is not an object" |
| `trust-refused` | `OFFLINE_FAIL` | `FAIL` | `trust_registry_verification_failed` | none | `1` | [`trust-registry-authorization.md`](trust-registry-authorization.md) "the trust registry breaks its contract" |
| `input-refused` | none | none | none | none | `64` | [`report-contract.md`](report-contract.md) "Exit 64 is a refusal of the invocation." |
| `input-absent` | `OFFLINE_REVIEW` | `REVIEW` | `canonical_input_not_provided` | none | `2` | [`report-contract.md`](report-contract.md) "the canonical input is absent and the manifest does not declare it" |
| `bundle-extra-files` | `OFFLINE_REVIEW` | `REVIEW` | `bundle_extra_files` | none | `2` | [`report-contract.md`](report-contract.md) "the bundle carries an undeclared member that is not at a reserved name" |
| `envelope-absent` | `OFFLINE_REVIEW` | `REVIEW` | `envelope_not_provided` | none | `2` | [`report-contract.md`](report-contract.md) "the bundle carries neither the envelope nor its sidecar" |

`trust-refused` also reports the authorization statuses `INVALID_TRUST_REGISTRY`, `signature_status`
`null` and `trust_registry_root_signature_status` `ROOT_SIGNATURE_NOT_EVALUATED`
([`trust-registry-authorization.md`](trust-registry-authorization.md) §6 row 3, §7).

`input-refused` is the outcome of a command line. A library interface has no exit code, and
[`report-contract.md`](report-contract.md) §4 states what it does with each of these inputs: an
input it refuses is refused with an error of the host language, and no report is returned; a trust
registry without a registry entry is not refused that way, and the report it returns is the one
[`report-contract.md`](report-contract.md) §4 states for it.

In a run that reads a bundle, an entry that is not strict JSON, is not an object or breaks its
contract also makes the report's `registry_link` result `false` when the bundle carries a
`verification_receipt.json`, and `null` when it carries none, since a link whose input is absent
is `null`; a trust registry is then not evaluated at all ([`registry-link.md`](registry-link.md) §5
and §7). Both are stated there and are not repeated per row. A run that refuses its input as a whole
reports its per-check results as [`bundle-objects.md`](bundle-objects.md) §6 states, whatever entry
is supplied beside it.

## 3. `manifest.json`

The closed field set of [`bundle-objects.md`](bundle-objects.md) §2. A member outside it, or a row
below broken, fails the manifest layer.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `bundle_id` | yes | `string` | a code point outside W | `7` `""` `" "` `null` `true` | `manifest-layer` | [`bundle-objects.md`](bundle-objects.md) "A `bundle_id` that is not a string, or that is made only of code points in W, is a rejection in its own right" |
| `files` | yes | `object` | every key is a portable member name and no two keys conflict; every value is the digest `sha256:<64 lowercase hex>` of that member's bytes; a map with no member fails the file check | `[]` `"x"` `7` `null` `{}` | `manifest-layer` | [`bundle-objects.md`](bundle-objects.md) "A `files` map with no member makes the manifest's file check `false`" |
| `nonce` | yes | `string` | exactly 64 lowercase hexadecimal characters, `^[0-9a-f]{64}$` | `7` `null` `""` `"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` | `manifest-layer` | [`bundle-objects.md`](bundle-objects.md) "`nonce` is exactly 64 lowercase hexadecimal characters, matching `^[0-9a-f]{64}$`, and any other value is a rejection of the manifest." |
| `schema_version` | yes | `string` | exactly `loquitur.bundle.v1`, read first under the version gate (§1) | `7` `null` `[]` `" "` `"bundle-v1"` `"manifest.fixture.v1"` | `manifest-layer` | [`bundle-objects.md`](bundle-objects.md) "any other value, such as `bundle-v1`, is a rejection of the manifest" |

A key of `files` that names a member the bundle does not carry, and a value that is not the
digest of the member it names, fail the same layer (`manifest-layer`): the manifest declared a
file the bundle does not hold as declared.

The file check and completeness are two rules, and the last two cases below separate them. A map
with no member fails the file check, so the run fails its manifest layer. A map that declares
some of the bundle's members leaves the file check holding, and the members it does not declare
make the run `OFFLINE_REVIEW`, the same outcome as a file added beside an intact bundle.

| case | outcome | rule |
| --- | --- | --- |
| `manifest-not-an-object` | `manifest-refused` | [`report-contract.md`](report-contract.md) "`manifest.json` is not a regular member, is not strict JSON" |
| `manifest-schema-version-is-a-later-version` | `unsupported-version` | [`bundle-objects.md`](bundle-objects.md) "a well-formed identifier of another version, such as `loquitur.bundle.v2`, is an unsupported version (exit `4`)" |
| `manifest-declares-a-member-the-bundle-does-not-carry` | `manifest-layer` | [`bundle-objects.md`](bundle-objects.md) "A member `manifest.files` declares that is not present makes the manifest file check `false`." |
| `manifest-declares-a-digest-that-is-not-the-members` | `manifest-layer` | [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Raw bytes of each listed bundle file" |
| `manifest-files-map-is-empty` | `manifest-layer` | [`bundle-objects.md`](bundle-objects.md) "A `files` map with no member makes the manifest's file check `false`" |
| `manifest-files-map-declares-some-of-the-members` | `bundle-extra-files` | [`bundle-objects.md`](bundle-objects.md) "An undeclared member does not make the file check `false`; it yields `OFFLINE_REVIEW` under §1, whatever the size of the map." |

## 4. `p1.json`

The closed field set of [`bundle-objects.md`](bundle-objects.md) §3. A member outside it, or a row
below broken, is `p1-refused`: the P1 contract is checked before the digest it commits to.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `s` | yes | `string` | exactly `p1` | `"p2"` `1` `null` `"P1"` | `p1-refused` | [`bundle-objects.md`](bundle-objects.md) "exactly `p1`" |
| `v` | yes | `integer` | `1` is the only supported version; `1` and `1.0` are the same value | `2` `"1"` `true` `null` | `p1-refused` | [`bundle-objects.md`](bundle-objects.md) "So is a missing or unsupported `v`" |
| `ih` | yes | `string` | the digest `sha256:<64 lowercase hex>` | `7` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `"sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"` `"SHA256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `null` | `p1-refused` | [`bundle-objects.md`](bundle-objects.md) "`ih` is a digest of the form `sha256:<64 lowercase hex>`" |
| `ik` | no | `array` | a non-empty array of distinct strings, each with a code point outside W | `[]` `null` `"external_mark"` `[1]` `["a","a"]` `{}` `[" "]` | `p1-refused` | [`bundle-objects.md`](bundle-objects.md) "**`ik`, when present, MUST be a non-empty array of distinct strings, each with a code point outside W.**" |

An `ih` that is well formed and is not the digest of the projection is a different fact: the
input-hash check was performed and did not hold, which is `p1-layer`.

| case | outcome | rule |
| --- | --- | --- |
| `p1-not-an-object` | `p1-refused` | [`report-contract.md`](report-contract.md) "`p1.json` is not a regular member, is not strict JSON" |
| `p1-over-the-canonical-size-bound` | `p1-refused` | [`bundle-objects.md`](bundle-objects.md) "The bound is 1024 bytes of canonical form; a verifier **MUST** fail closed when it is exceeded." |
| `p1-ih-is-not-the-digest-of-the-projection` | `p1-layer` | [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "A verifier that cannot reproduce a declared digest must fail closed" |
| `p1-absent` | `p1-refused` | [`report-contract.md`](report-contract.md) "`p1.json` is not a regular member" |

## 5. `canonical_input.json`

The canonical input has no member contract: it is the payload the projection of §4 reads, and any
JSON object is one.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| the document | no | `object` | any JSON object | `[1,2]` `"x"` `5` `null` `true` | `p1-refused` | [`bundle-objects.md`](bundle-objects.md) "exceeds the per-member bound or is not a JSON object refuses the P1 layer" |

Absence is decided by the manifest, not by the file: a canonical input the manifest declares and
the bundle does not carry is `manifest-layer`, and one the manifest never declared is
`input-absent`.

| case | outcome | rule |
| --- | --- | --- |
| `canonical-input-declared-and-absent` | `manifest-layer` | [`bundle-objects.md`](bundle-objects.md) "deleting `canonical_input.json` from a bundle whose manifest declares it yields `FAIL`" |
| `canonical-input-undeclared-and-absent` | `input-absent` | [`bundle-objects.md`](bundle-objects.md) "A bundle whose manifest never declared a canonical input yields `REVIEW`" |

## 6. The digest sidecars

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `manifest.sha256` | yes | bytes | exactly the 64 lowercase hexadecimal characters of the manifest digest | `<upper>` `<newline>` `<other>` | `manifest-layer` | [`bundle-objects.md`](bundle-objects.md) "A sidecar file holds exactly the 64 lowercase hexadecimal characters of the digest and no other byte, not even a newline." |
| `p1.sha256` | yes | bytes | exactly the 64 lowercase hexadecimal characters of the P1 digest | `<upper>` `<newline>` `<other>` | `p1-layer` | [`bundle-objects.md`](bundle-objects.md) "A sidecar file holds exactly the 64 lowercase hexadecimal characters of the digest and no other byte, not even a newline." |
| `envelope.sha256` | yes | bytes | exactly the 64 lowercase hexadecimal characters of the envelope digest | `<upper>` `<newline>` `<other>` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "A sidecar file holds exactly the 64 lowercase hexadecimal characters of the digest and no other byte, not even a newline." |

Required means required beside the object it commits to: a bundle that carries neither the
envelope nor its sidecar is `OFFLINE_REVIEW`, and either one without the other is refused with
the error `envelope_incomplete` ([`bundle-objects.md`](bundle-objects.md) §4 and §6). `p1.sha256` is
required whether or not the manifest declares it.

| case | outcome | rule |
| --- | --- | --- |
| `manifest-sidecar-absent` | `manifest-refused` | [`report-contract.md`](report-contract.md) "`manifest.sha256` is not a regular member" |
| `p1-sidecar-absent` | `p1-layer` | [`bundle-objects.md`](bundle-objects.md) "A bundle without `p1.sha256` fails the P1 layer whether or not its manifest declares it" |
| `envelope-sidecar-absent` | `envelope-incomplete` | [`bundle-objects.md`](bundle-objects.md) "A bundle that carries exactly one of `envelope_env1.json` and `envelope.sha256` refuses its envelope layer with the error `envelope_incomplete`" |
| `envelope-absent-sidecar-present` | `envelope-incomplete` | [`bundle-objects.md`](bundle-objects.md) "A bundle that carries exactly one of `envelope_env1.json` and `envelope.sha256` refuses its envelope layer with the error `envelope_incomplete`" |
| `envelope-and-sidecar-absent` | `envelope-absent` | [`bundle-objects.md`](bundle-objects.md) "file and sidecar both absent is `REVIEW`" |

## 7. `envelope_env1.json`

The closed field set of [`bundle-objects.md`](bundle-objects.md) §4. A member outside it, or a row
below broken, is `envelope-layer`. The envelope has no other name: `envelope.json` is an ordinary
member.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `s` | yes | `string` | exactly `env1` | `"env2"` `1` `null` `"ENV1"` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "`s` MUST be exactly `env1`." |
| `v` | yes | `integer` | `1` is the only supported version; `1` and `1.0` are the same value | `2` `"1"` `true` `null` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "`v` supports only `1`" |
| `bundle_id` | yes | `string` | equal to the manifest's `bundle_id`, code unit for code unit | `7` `null` `""` `"not-the-manifest-bundle-id"` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "its link holds only when it equals the manifest's `bundle_id` code unit for code unit" |
| `bundle_manifest_sha256` | yes | `string` | the digest `sha256:<64 lowercase hex>`, equal to the manifest digest | `7` `null` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `"SHA256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `"sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"` `"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "`bundle_manifest_sha256` and `p1_sha256` are digests of the form `sha256:<64 lowercase hex>`" |
| `p1_sha256` | yes | `string` | the digest `sha256:<64 lowercase hex>`, equal to the P1 digest | `7` `null` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `"SHA256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `"sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"` `"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "`bundle_manifest_sha256` and `p1_sha256` are digests of the form `sha256:<64 lowercase hex>`" |
| `registry_entry` | no | `object` or `null` | a registry entry that satisfies the contract of §9 | `5` `"x"` `[]` `true` `{}` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "`registry_entry`, when it is not `null`, is a registry entry: an object that satisfies the entry's contract" |
| `ts` | no | `integer` or `null` | - | `"x"` `[]` `{}` `true` `1.5` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "A member outside this set is a rejection, and a member whose value is not of its declared type is a rejection in the same way." |
| `network` | no | `string` or `null` | a code point outside W | `5` `[]` `{}` `true` `" "` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "The six members typed `string or null` are the envelope's free strings: when one is a string, it has a code point outside W, and a value made only of W is a rejection in the same way as a value of another type." |
| `p1_txid` | no | `string` or `null` | a code point outside W | `5` `[]` `{}` `true` `" "` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "The six members typed `string or null` are the envelope's free strings: when one is a string, it has a code point outside W, and a value made only of W is a rejection in the same way as a value of another type." |
| `uri` | no | `string` or `null` | a code point outside W | `5` `[]` `{}` `true` `" "` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "The six members typed `string or null` are the envelope's free strings: when one is a string, it has a code point outside W, and a value made only of W is a rejection in the same way as a value of another type." |
| `asset_id` | no | `string` or `null` | a code point outside W | `5` `[]` `{}` `true` `" "` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "The six members typed `string or null` are the envelope's free strings: when one is a string, it has a code point outside W, and a value made only of W is a rejection in the same way as a value of another type." |
| `asset_type` | no | `string` or `null` | a code point outside W | `5` `[]` `{}` `true` `" "` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "The six members typed `string or null` are the envelope's free strings: when one is a string, it has a code point outside W, and a value made only of W is a rejection in the same way as a value of another type." |
| `receipt_id` | no | `string` or `null` | a code point outside W | `5` `[]` `{}` `true` `" "` | `envelope-layer` | [`bundle-objects.md`](bundle-objects.md) "The six members typed `string or null` are the envelope's free strings: when one is a string, it has a code point outside W, and a value made only of W is a rejection in the same way as a value of another type." |

The rows of `bundle_id`, `bundle_manifest_sha256` and `p1_sha256` are links
([`bundle-objects.md`](bundle-objects.md) §4): a present value of another type, like a string of
another value, fails its link and makes `envelope_links` `false`; it does not break the envelope's
closed contract, so the `structure` check is not withheld for it
([`report-contract.md`](report-contract.md) §3.2).

No check reads the optional members above, and that is why their types are written down rather
than left open. `integer` in the `ts` row is an integer of the canonical numeric model, under
which `1` and `1.0` are the same value; the row states no rule beyond that type, so any integer
is a time this envelope may carry.

| case | outcome | rule |
| --- | --- | --- |
| `envelope-not-an-object` | `envelope-refused` | [`report-contract.md`](report-contract.md) "the envelope is not strict JSON, exceeds the per-member bound, is not an object" |
| `envelope-json-is-an-ordinary-member` | `bundle-extra-files` | [`bundle-objects.md`](bundle-objects.md) "`envelope.json`, in particular, is an ordinary member name." |

## 8. `verification_receipt.json`

The receipt satisfies its contract when it is a JSON object that satisfies
`schemas/verification_receipt.schema.json`, every one of its instants is a calendar instant and
its free strings are not empty ([`registry-link.md`](registry-link.md) §2). A row below broken is
`receipt-refused` whichever checks the run requests, whether or not a registry entry is supplied.
Every member of the schema is listed; a member the schema does not name is refused by
`additionalProperties`.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `anchor_provider` | no | `string` or `null` | at least 1 character; a code point outside W | `7` `""` `" "` | `receipt-refused` | `verification_receipt.schema.json` `/properties/anchor_provider` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `anchor_type` | no | `string` or `null` | at least 1 character; a code point outside W | `7` `""` `" "` | `receipt-refused` | `verification_receipt.schema.json` `/properties/anchor_type` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `asset_id` | no | `string` or `null` | at least 1 character; a code point outside W | `7` `""` `" "` | `receipt-refused` | `verification_receipt.schema.json` `/properties/asset_id` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `asset_type` | yes | `string` | matches `^[a-z0-9][a-z0-9_]{0,63}$` | `7` `"Fund_NAV"` `"fund-nav"` `" "` | `receipt-refused` | `verification_receipt.schema.json` `/properties/asset_type` |
| `bundle_id` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `receipt-refused` | `verification_receipt.schema.json` `/properties/bundle_id` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `manifest_sha256` | yes | `string` | matches `^sha256:[a-f0-9]{64}$` | `7` `"zz"` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `"sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/manifest_sha256` |
| `network` | no | `string` or `null` | at least 1 character; a code point outside W | `7` `""` `" "` | `receipt-refused` | `verification_receipt.schema.json` `/properties/network` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `object_type` | yes | `string` | exactly `"verification_receipt"` | `7` `"not-the-const"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/object_type` |
| `p1_sha256` | no | `string` or `null` | matches `^sha256:[a-f0-9]{64}$` | `7` `"zz"` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `"sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/p1_sha256` |
| `policy_id` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `receipt-refused` | `verification_receipt.schema.json` `/properties/policy_id` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `policy_pack_sha256` | no | `string` or `null` | matches `^sha256:[a-f0-9]{64}$` | `7` `"zz"` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` `"sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/policy_pack_sha256` |
| `policy_version` | yes | `integer` | at least 1 | `"not-a-value"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/policy_version` |
| `primary_anchor` | no | `object` or `null` | - | `"not-a-value"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/primary_anchor` |
| `reason_code_vocabulary_version` | yes | `string` | exactly `"loquitur.reason_codes.v1"` | `7` `"not-the-const"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/reason_code_vocabulary_version` |
| `reason_codes` | yes | `array` | at least 1 item; items distinct; each item a code of the catalog ([`reason-codes.md`](reason-codes.md)) | `"not-a-value"` `[]` `["INTEGRITY_OK","INTEGRITY_OK"]` `["not-in-the-enum"]` | `receipt-refused` | `verification_receipt.schema.json` `/properties/reason_codes` |
| `schema_version` | yes | `string` | one of `"v2"` | `7` `"not-in-the-enum"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/schema_version` |
| `status` | yes | `string` | one of `"pass"`, `"warning"`, `"review"`, `"fail"` | `7` `"not-in-the-enum"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/status` |
| `storage` | no | `array` | each item `object` | `"not-a-value"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/storage` |
| `verification_mode` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `receipt-refused` | `verification_receipt.schema.json` `/properties/verification_mode` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `verified_at` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `receipt-refused` | `verification_receipt.schema.json` `/properties/verified_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |

`policy_pack_sha256` is opaque in this version: the specification defines no policy pack, and
nothing is inferred from the value beyond its form. An `asset_type` that is an identifier and is not
registered in the verifier's vocabulary satisfies the contract, and is a review reason
([`verification-vocabularies.md`](verification-vocabularies.md) §7).

| case | outcome | rule |
| --- | --- | --- |
| `receipt-not-an-object` | `receipt-refused` | [`report-contract.md`](report-contract.md) "is not strict JSON, exceeds the per-member bound, is not an object, or breaks its contract" |
| `receipt-carries-a-member-the-schema-does-not-name` | `receipt-refused` | [`registry-link.md`](registry-link.md) "satisfies `schemas/verification_receipt.schema.json`" |

## 9. The registry entry

The entry satisfies its contract when it is a JSON object that satisfies
`schemas/registry_entry.schema.json`, every one of its instants is a calendar instant, its free
strings are not empty, and its verdict is the verdict its reason codes derive
([`registry-link.md`](registry-link.md) §2). A row below broken is `entry-refused`; a document that
is not a JSON object is `entry-unreadable`.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `anchor` | no | `object` or `null` | closed field set | `"not-a-value"` | `entry-refused` | `registry_entry.schema.json` `/properties/anchor` |
| `anchor.anchor_reference` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `entry-refused` | `registry_entry.schema.json` `/properties/anchor/properties/anchor_reference` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `anchor.method` | yes | `string` | matches `^[a-z0-9][a-z0-9_]{0,63}$` | `7` `"Blockchain"` `"blockchain-transaction"` `" "` | `entry-refused` | `registry_entry.schema.json` `/properties/anchor/properties/method` |
| `anchor.system` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `entry-refused` | `registry_entry.schema.json` `/properties/anchor/properties/system` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `anchored_at` | no | `string` or `null` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `entry-refused` | `registry_entry.schema.json` `/properties/anchored_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `asset_type` | yes | `string` | matches `^[a-z0-9][a-z0-9_]{0,63}$` | `7` `"Fund_NAV"` `"fund-nav"` `" "` | `entry-refused` | `registry_entry.schema.json` `/properties/asset_type` |
| `disclosure_profile` | yes | `string` | one of `"minimal_public"`, `"issuer_controlled_bundle"`, `"partner_authorized_bundle"` | `7` `"not-in-the-enum"` | `entry-refused` | `registry_entry.schema.json` `/properties/disclosure_profile` |
| `effective_at` | no | `string` or `null` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `entry-refused` | `registry_entry.schema.json` `/properties/effective_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `issued_at` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `entry-refused` | `registry_entry.schema.json` `/properties/issued_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `issuer_id` | yes | `string` | matches `^issuer_[A-Za-z0-9_-]{3,128}$` | `7` `"zz"` | `entry-refused` | `registry_entry.schema.json` `/properties/issuer_id` |
| `issuer_key_id` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `entry-refused` | `registry_entry.schema.json` `/properties/issuer_key_id` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `manifest_hash` | yes | `string` | matches `^sha256:[a-f0-9]{64}$` | `7` `"zz"` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` | `entry-refused` | `registry_entry.schema.json` `/properties/manifest_hash` |
| `object_type` | yes | `string` | exactly `"registry_entry"` | `7` `"not-the-const"` | `entry-refused` | `registry_entry.schema.json` `/properties/object_type` |
| `policy_id` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `entry-refused` | `registry_entry.schema.json` `/properties/policy_id` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `policy_version` | yes | `string` | matches `^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9_.-]+)?$` | `7` `"zz"` | `entry-refused` | `registry_entry.schema.json` `/properties/policy_version` |
| `privacy_classification` | yes | `string` | one of `"public_commitment"` | `7` `"not-in-the-enum"` | `entry-refused` | `registry_entry.schema.json` `/properties/privacy_classification` |
| `reason_code_catalog_version` | yes | `string` | exactly `"loquitur.reason_codes.v1"` | `7` `"not-the-const"` | `entry-refused` | `registry_entry.schema.json` `/properties/reason_code_catalog_version` |
| `reason_codes` | yes | `array` | at least 1 item; items distinct; each item a code of the catalog ([`reason-codes.md`](reason-codes.md)) | `"not-a-value"` `[]` `["INTEGRITY_OK","INTEGRITY_OK"]` `["not-in-the-enum"]` | `entry-refused` | `registry_entry.schema.json` `/properties/reason_codes` |
| `receipt_hash` | yes | `string` | matches `^sha256:[a-f0-9]{64}$` | `7` `"zz"` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` | `entry-refused` | `registry_entry.schema.json` `/properties/receipt_hash` |
| `receipt_id` | yes | `string` | matches `^vr_[A-Za-z0-9_-]{8,128}$` | `7` `"zz"` | `entry-refused` | `registry_entry.schema.json` `/properties/receipt_id` |
| `registry_entry_id` | yes | `string` | matches `^reg_[A-Za-z0-9_-]{8,128}$` | `7` `"zz"` | `entry-refused` | `registry_entry.schema.json` `/properties/registry_entry_id` |
| `schema_version` | yes | `string` | one of `"v1"` | `7` `"not-in-the-enum"` | `entry-refused` | `registry_entry.schema.json` `/properties/schema_version` |
| `signature` | no | `object` or `null` | one of the branches of the schema's `oneOf` | `"not-a-value"` `[]` | `entry-refused` | `registry_entry.schema.json` `/properties/signature` |
| `signature.algorithm` | yes | `string` | matches `^[a-z0-9][a-z0-9_]{0,63}$` | `7` `""` `"Ed25519"` `"secp256k1-ecdsa"` | `entry-refused` | `registry_entry.schema.json` `/properties/signature/oneOf/1/properties/algorithm` |
| `signature.key_id` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `entry-refused` | `registry_entry.schema.json` `/properties/signature/oneOf/1/properties/key_id` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `signature.payload_id` | yes | `string` | exactly `"registry_entry_signing_payload_v2"` | `7` `"not-the-const"` | `entry-refused` | `registry_entry.schema.json` `/properties/signature/oneOf/1/properties/payload_id` |
| `signature.payload_version` | yes | `integer` | exactly `2` | `"not-a-value"` `0` | `entry-refused` | `registry_entry.schema.json` `/properties/signature/oneOf/1/properties/payload_version` |
| `signature.signature` | yes | `string` | matches `^[a-f0-9]{128}$` | `7` `"zz"` | `entry-refused` | `registry_entry.schema.json` `/properties/signature/oneOf/1/properties/signature` |
| `subject_ref_hash` | yes | `string` | matches `^sha256:[a-f0-9]{64}$` | `7` `"zz"` `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` | `entry-refused` | `registry_entry.schema.json` `/properties/subject_ref_hash` |
| `verdict` | yes | `string` | one of `"PASS"`, `"WARN"`, `"REVIEW"`, `"FAIL"` | `7` `"not-in-the-enum"` | `entry-refused` | `registry_entry.schema.json` `/properties/verdict` |
| `workflow` | yes | `string` | matches `^[a-z0-9][a-z0-9_]{0,63}$` | `7` `"Fund_NAV_Update"` `"fund-nav-update"` `" "` | `entry-refused` | `registry_entry.schema.json` `/properties/workflow` |

The `signature` rows are the members of the v2 shape, the only one this version defines: a
signature object that lacks `payload_id` and `payload_version` breaks the entry's contract. A
well-formed `algorithm` the verifier does not support satisfies the contract and is answered at
the signature step (`UNSUPPORTED_SIGNATURE_ALGORITHM`,
[`trust-registry-authorization.md`](trust-registry-authorization.md) §6, row 16). An `asset_type` or
a `workflow` that is an identifier and is not registered in the verifier's vocabulary satisfies the
contract, and is a review reason; an `anchor.method` that is an identifier satisfies it whatever the
vocabulary holds ([`verification-vocabularies.md`](verification-vocabularies.md) §7).
`schema_version`, `reason_code_catalog_version` and the pair `signature.payload_id`,
`signature.payload_version` are read first under the version gate (§1): a well-formed later version
is an unsupported version, and the rows below hold every other value.

| case | outcome | rule |
| --- | --- | --- |
| `entry-not-an-object` | `entry-unreadable` | [`report-contract.md`](report-contract.md) "its document is not strict JSON or is not an object" |
| `entry-is-json-null` | `entry-unreadable` | [`registry-link.md`](registry-link.md) "the entry document is not strict JSON or is not an object (JSON `null` included)" |
| `entry-carries-a-member-the-schema-does-not-name` | `entry-refused` | [`registry-link.md`](registry-link.md) "satisfies `schemas/registry_entry.schema.json`" |
| `entry-verdict-is-not-the-verdict-its-reason-codes-derive` | `entry-refused` | [`registry-link.md`](registry-link.md) "its verdict is the verdict its reason codes derive" |

## 10. The trust registry

The trust registry satisfies its contract when it is a JSON object that satisfies
`schemas/trust_registry.schema.json`, every instant it carries is a calendar instant, used or
not, its free strings are not empty, and it does not contradict itself
([`trust-registry-authorization.md`](trust-registry-authorization.md) §3). A row below
broken is `trust-refused`, and so is a document that is not a JSON object.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `effective_at` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `trust-refused` | `trust_registry.schema.json` `/properties/effective_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `entries` | yes | `array` | items distinct; each item `object` | `"not-a-value"` | `trust-refused` | `trust_registry.schema.json` `/properties/entries` |
| `entries[i].allowed_asset_types` | yes | `array` | items distinct; each item matches `^[a-z0-9][a-z0-9_]{0,63}$` | `"not-a-value"` `["property","property"]` `["Fund_NAV"]` `["fund-nav"]` `[7]` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/allowed_asset_types` |
| `entries[i].allowed_workflows` | yes | `array` | items distinct; each item matches `^[a-z0-9][a-z0-9_]{0,63}$` | `"not-a-value"` `["property_review","property_review"]` `["Property_Review"]` `["property-review"]` `[7]` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/allowed_workflows` |
| `entries[i].effective_from` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/effective_from` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `entries[i].expires_at` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/expires_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `entries[i].issuer_display_name` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/issuer_display_name` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `entries[i].issuer_id` | yes | `string` | matches `^issuer_[A-Za-z0-9_-]{3,128}$` | `7` `"zz"` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/issuer_id` |
| `entries[i].issuer_key_id` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/issuer_key_id` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `entries[i].key_type` | yes | `string` | matches `^[a-z0-9][a-z0-9_]{0,63}$` | `7` `""` `"Secp256k1"` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/key_type` |
| `entries[i].notes` | no | `string` or `null` | at least 1 character; a code point outside W | `7` `""` `" "` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/notes` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `entries[i].public_key_hex` | yes | `string` | matches `^([a-f0-9]{2}){1,512}$` | `7` `"zz"` `"abc"` `"04AB"` `""` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/public_key_hex` |
| `entries[i].revocation_reason` | no | `string` or `null` | at least 1 character; a code point outside W | `7` `""` `" "` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/revocation_reason` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `entries[i].revoked_at` | no | `string` or `null` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/revoked_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `entries[i].status` | yes | `string` | one of `"active"`, `"suspended"`, `"revoked"` | `7` `"not-in-the-enum"` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/properties/status` |
| `expires_at` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `trust-refused` | `trust_registry.schema.json` `/properties/expires_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `issued_at` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `7` `"zz"` `"2026-02-30T00:00:00Z"` `"2026-04-29T12:00:60Z"` | `trust-refused` | `trust_registry.schema.json` `/properties/issued_at` and [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) "Instants are calendar instants." |
| `object_type` | yes | `string` | exactly `"trust_registry"` | `7` `"not-the-const"` | `trust-refused` | `trust_registry.schema.json` `/properties/object_type` |
| `registry_operator_id` | yes | `string` | matches `^operator_[A-Za-z0-9_-]{3,128}$` | `7` `"zz"` | `trust-refused` | `trust_registry.schema.json` `/properties/registry_operator_id` |
| `registry_version` | yes | `string` | matches `^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9_.-]+)?$` | `7` `"zz"` | `trust-refused` | `trust_registry.schema.json` `/properties/registry_version` |
| `schema_version` | yes | `string` | one of `"v1"` | `7` `"not-in-the-enum"` | `trust-refused` | `trust_registry.schema.json` `/properties/schema_version` |
| `signature` | yes | `object` | closed field set | `"not-a-value"` | `trust-refused` | `trust_registry.schema.json` `/properties/signature` |
| `signature.algorithm` | yes | `string` | matches `^[a-z0-9][a-z0-9_]{0,63}$` | `7` `""` `"Bad"` | `trust-refused` | `trust_registry.schema.json` `/properties/signature/properties/algorithm` |
| `signature.key_id` | yes | `string` | at least 1 character; a code point outside W | `7` `""` `" "` | `trust-refused` | `trust_registry.schema.json` `/properties/signature/properties/key_id` and [`bundle-objects.md`](bundle-objects.md) "A free string is not empty: a value made only of code points in W breaks the document's contract, whether or not a schema's `minLength` admits it." |
| `signature.signature` | yes | `string` | at least 1 character | `7` `""` | `trust-refused` | `trust_registry.schema.json` `/properties/signature/properties/signature` |
| `trust_registry_id` | yes | `string` | matches `^tr_[A-Za-z0-9_-]{8,128}$` | `7` `"zz"` | `trust-refused` | `trust_registry.schema.json` `/properties/trust_registry_id` |

A trust entry's `key_type` and `public_key_hex`, and the registry's `signature.algorithm`, admit
every well-formed value: whether the verifier supports the key type and algorithm, and whether
the key has the form its key type requires (for `secp256k1`, `^04[a-f0-9]{128}$`, coordinates
below the field prime and a point on the curve), are answered at the signature step
([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, rows 16 and 20;
[`trust-root.md`](trust-root.md) §5, rows 4 and 11), not by this contract.

The trust registry's `signature.signature` is held to `minLength` by the schema and to its form
by root authentication: a value that is not 128 lowercase hexadecimal characters is
`MALFORMED_SIGNATURE` there, not a malformed document ([`trust-root.md`](trust-root.md) §5, row 5
(`MALFORMED_SIGNATURE`)).

Each element of `allowed_asset_types` and `allowed_workflows` is an identifier, and a well-formed
element the verifier's vocabulary does not register is not a finding: scope compares values exactly,
whatever the vocabulary holds ([`verification-vocabularies.md`](verification-vocabularies.md) §7,
[`trust-registry-authorization.md`](trust-registry-authorization.md) §11).

The contradictions that make a well-typed trust registry malformed are in
[`trust-registry-authorization.md`](trust-registry-authorization.md) §3, with their own case table,
and are not repeated here.

| case | outcome | rule |
| --- | --- | --- |
| `trust-registry-not-an-object` | `trust-refused` | [`trust-registry-authorization.md`](trust-registry-authorization.md) "its document is not strict JSON or is not an object" |
| `trust-registry-carries-a-member-the-schema-does-not-name` | `trust-refused` | [`trust-registry-authorization.md`](trust-registry-authorization.md) "satisfies `schemas/trust_registry.schema.json`" |
| `trust-registry-entry-is-not-an-object` | `trust-refused` | `trust_registry.schema.json` `/properties/entries/items/type` |

## 11. The trust-root document

The trust-root document is supplied out of band and is validated as a whole when it is read.
Every row below is stated by [`trust-root.md`](trust-root.md) §3, whose two case tables carry the
cases; a document that breaks any of them is `input-refused`.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| the document | yes | `object` | exactly the members `object_type`, which is exactly `trust_root_document`, `schema_version`, which is exactly `v1` after the version gate (§1), and `roots`; no other member | `[]` `{}` `5` `{"roots":[]}` `{"object_type":"trust_root_document","schema_version":"v1","trust_roots":[]}` | `input-refused` | [`trust-root.md`](trust-root.md) "The document is a JSON object with exactly three members, all required" |
| `roots` | yes | `array` | a non-empty array of root objects | `[]` `5` `null` | `input-refused` | [`trust-root.md`](trust-root.md) "`roots`, a non-empty array" |
| `roots[i].key_id` | yes | `string` | a code point outside W; matched by exact equality of code units | `9` `""` | `input-refused` | [`trust-root.md`](trust-root.md) "`key_id` is not empty in the sense of [`bundle-objects.md`](bundle-objects.md)" |
| `roots[i].key_type` | yes | `string` | matches `^[a-z0-9][a-z0-9_]{0,63}$` | `"Ed25519"` `""` `7` | `input-refused` | [`trust-root.md`](trust-root.md) "`key_type` matches `^[a-z0-9][a-z0-9_]{0,63}$`." |
| `roots[i].public_key_hex` | yes | `string` | matches `^([0-9a-f]{2}){1,512}$`, and `^04[0-9a-f]{128}$` when `key_type` is `secp256k1` | `"04AB"` `7` | `input-refused` | [`trust-root.md`](trust-root.md) "when `key_type` is `secp256k1` it matches `^04[0-9a-f]{128}$`. It is not lower-cased first." |
| `roots[i].not_before` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant | `"2026-02-30T00:00:00Z"` `7` | `input-refused` | [`trust-root.md`](trust-root.md) "No offset forms, no fractional seconds, no February 30 and no second 60." |
| `roots[i].not_after` | yes | `string` | an instant `YYYY-MM-DDTHH:MM:SSZ`, and a calendar instant, strictly later than `not_before` | `"0001-01-01T00:00:00Z"` `7` | `input-refused` | [`trust-root.md`](trust-root.md) "`not_after` is strictly later than `not_before`." |
| `roots[i].status` | no | `string` | `active` (the default) or `revoked` | `"suspended"` `null` `7` | `input-refused` | [`trust-root.md`](trust-root.md) "`status` is one of `active` or `revoked`. Any other value is malformed." |

This version defines no other name for the array: a document whose array is named
`trust_roots` is malformed. A document whose `object_type` is `trust_root_document` and whose
`schema_version` is a well-formed later version, such as `v2`, is not malformed: it is an
unsupported version (§1, "Version gate"; [`report-contract.md`](report-contract.md) §5.5).

## 12. The verifier's own inputs

A run takes a bundle and, optionally, a registry entry, a trust registry, a set of trust roots,
an evaluation time and, for each kind, a registered vocabulary document
([`report-contract.md`](report-contract.md) §1). These are not members of a document, and
they are listed here because the same question is asked of them: what does a verifier do when this
input is absent, of the wrong kind or malformed.

| input | required | form | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- |
| the bundle | yes | a directory carrying `manifest.json`, or, for a verifier that reads archives, a ZIP archive holding one bundle root; archive intake is optional ([`report-contract.md`](report-contract.md) §5.3) | no bundle argument; two of them; an empty path | `input-refused` | [`report-contract.md`](report-contract.md) "A command line **MUST** return it, with no report, when an argument is missing or malformed" |
| the registry entry | no | a path naming a regular file holding the entry (§9) | - | - | [`report-contract.md`](report-contract.md) "a registry entry was supplied, and any of these holds: something that is not a regular file is found at its path" |
| the trust registry | no | a path naming a regular file holding the registry (§10); only beside a registry entry | supplied without a registry entry | `input-refused` | [`report-contract.md`](report-contract.md) "when a trust registry is supplied without a registry entry" |
| the trust roots | no | a trust-root document (§11); only beside a trust registry | supplied without a trust registry; a path that names no regular file; malformed under [`trust-root.md`](trust-root.md) §3 | `input-refused` | [`report-contract.md`](report-contract.md) "when trust roots are supplied without a trust registry, or the trust-root document's path names no regular file or the document is malformed" |
| the evaluation time | no | `--evaluation-time YYYY-MM-DDTHH:MM:SSZ`, a calendar instant; only beside a trust registry | supplied without a trust registry; an empty value; not a calendar instant | `input-refused` | [`report-contract.md`](report-contract.md) "when an evaluation time is supplied without a trust registry, or is given an empty value" |
| the asset-type vocabulary | no | `--asset-type-vocabulary PATH`, a registered vocabulary document of the kind `asset_type` (§15) | a path that names no regular file; a document of another kind; malformed under §15 | `input-refused` | [`report-contract.md`](report-contract.md) "when a registered vocabulary document an option of §4.1 supplies is refused" |
| the workflow vocabulary | no | `--workflow-vocabulary PATH`, a registered vocabulary document of the kind `workflow` (§15) | a path that names no regular file; a document of another kind; malformed under §15 | `input-refused` | [`report-contract.md`](report-contract.md) "when a registered vocabulary document an option of §4.1 supplies is refused" |
| the anchoring-method vocabulary | no | `--anchoring-method-vocabulary PATH`, a registered vocabulary document of the kind `anchoring_method` (§15) | a path that names no regular file; a document of another kind; malformed under §15 | `input-refused` | [`report-contract.md`](report-contract.md) "when a registered vocabulary document an option of §4.1 supplies is refused" |
| any option | - | at most once, by its full name, with a value that is not empty | given twice; given by a prefix; an option this version does not define, such as `--attested-time` or `--tsa-token`; an empty value | `input-refused` | [`report-contract.md`](report-contract.md) "an option is given more than once, in either form, whatever its values" |

The `input-refused` rows are the outcomes of a command line; a library interface takes the same
inputs as §2 states.

A bundle, registry-entry or trust-registry path that does not exist, a bundle path that exists and
is neither a directory nor a regular file, and a registry-entry path that names a directory are not
usage refusals: each gives a report with the error [`report-contract.md`](report-contract.md) §5.3
names. A trust-root or vocabulary path that names no regular file is a usage refusal, as the table
of this section and [`report-contract.md`](report-contract.md) §4 state. A bundle, registry-entry or
trust-registry path at which nothing is found is `input_not_found`, a host outcome (`HOST_FAILURE`,
exit `5`); a bundle path that is neither a directory nor a regular file is `unsupported_input`, and
a registry-entry path that names a directory is `registry_link_verification_failed`, both
`OFFLINE_FAIL`. An empty path is a usage refusal ([`report-contract.md`](report-contract.md) §4.1).
A library interface that takes documents rather than paths is told by its host what a path names
([`report-contract.md`](report-contract.md) §4).

## 13. What is not here

- The rules that read two documents against each other: the comparisons of the `link` check
  ([`registry-link.md`](registry-link.md) §3 and §4), the evaluation order of the `authorization`
  check ([`trust-registry-authorization.md`](trust-registry-authorization.md) §6) and root
  authentication ([`trust-root.md`](trust-root.md) §5).
- Input strictness, which every document is loaded under: duplicate member names, the
  safe-integer range, finite numbers, Unicode scalar values, pattern anchoring, the nesting
  bound, exact UTF-8 and calendar instants
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md)).
- The rules of the container: the bundle root, undeclared members, links and the ZIP intake
  limits ([`bundle-objects.md`](bundle-objects.md) §1 and §5).
- The published objects no verifier loads: the verification summary and the change, lineage and
  coverage summaries ([`introduction.md`](introduction.md) §7). They are validated by their schemas
  where they are produced and consumed, and no check of a verifier reads them.

## 14. What each suite runs

The sections above say how a row is held and how it is run. How much is covered is here, and
only here, because a sentence a reader cannot check is worth nothing: the three suites read
these two tables and compare them with the cases they run, so a number that outruns
the coverage fails a build.

**How every member row's `type` cell is held.** `loquitur-protocol`'s
`tests/test_document_contracts.py` classifies every member row of §3 to §11 and holds this
count.

| held by | what holds it | member rows |
| --- | --- | --- |
| `schema` | the keyword of the schema the row cites | 77 |
| `table` | the `type` column of the document that declares the member | 37 |
| `sentence` | the one JSON type the sentence the row cites names | 3 |
| `bytes` | the `refused` column and the bytes run, the cell naming no JSON type | 3 |

**What each suite runs.** Each suite reads its own row and compares it with what it ran. A `-`
in the last column means the suite compares no report, and in any other column that it runs no
row of that kind.

| suite | member rows | case rows | input rows | report surface compared |
| --- | --- | --- | --- | --- |
| `loquitur-protocol` `tests/test_document_contracts.py` | 120 | 35 | 9 | - |
| `loquitur-verify-py` `tests/test_spec_document_contracts.py` | 120 | 35 | 9 | `status`, `verdict`, `exit_code`, `outcome.reason`, `errors[].code` |
| `loquitur-verify-ts` `test/spec-document-contracts.test.ts` | 120 | 35 | - | `status`, `verdict`, `exit_code`, `outcome.reason`, `errors[].code` |

`loquitur-protocol` runs no verifier and reads no bundle: it holds each row against the rule
the row cites, which is why it compares no report surface. `loquitur-verify-py` runs 102 member
rows through its library, and the 8 rows of §11 and the 10 rows of §15 through its command line,
which is the whole difference between the two means. `loquitur-verify-ts` runs the 120 through
its library, the 8 rows of §11 and the 10 rows of §15 as refusals of the document before any
evidence is read, and none of the input rows: §12 needs a command line it does not have, and its
suite names that omission rather than passing over it. Both verifier suites compare the same five
fields, which are the normative report surface of a run without a trust registry
([`report-contract.md`](report-contract.md) §2).

## 15. The registered vocabulary document

A registered vocabulary document is supplied by the operator, one per kind, out of band, and is
validated as a whole when it is read, before any evidence
([`verification-vocabularies.md`](verification-vocabularies.md) §6 and §8). Every row below is
stated by [`verification-vocabularies.md`](verification-vocabularies.md) §6, and a document that
breaks any of them is `input-refused`. `values.*` stands for every member of `values`; the rows are
run against a document of the kind `workflow`, the one kind whose values carry every member.

| member | required | type | value | refused | outcome | rule |
| --- | --- | --- | --- | --- | --- | --- |
| `object_type` | yes | `string` | exactly `registered_vocabulary` | `7` `"vocabulary"` `null` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`object_type` is exactly `registered_vocabulary`" |
| `schema_version` | yes | `string` | exactly `v1` | `7` `"v2"` `"V1"` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`schema_version` is exactly `v1`" |
| `kind` | yes | `string` | one of `asset_type`, `workflow` and `anchoring_method`, and the kind the option names | `7` `"vessel"` `"Workflow"` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`kind` is one of the three kinds of section 5." |
| `version` | yes | `string` | `MAJOR.MINOR.PATCH`, three decimal integers of at most nine digits with no leading zero, and no suffix | `7` `"1.0"` `"1.0.0-rc1"` `"01.0.0"` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`version` and every `since` are three decimal integers joined by `.`" |
| `values` | yes | `object` | at least one member, each named by an identifier | `{}` `[]` `"x"` `null` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "Every member name of `values` is an identifier (section 7), and `values` has at least one member." |
| `values.*.since` | yes | `string` | a version of the form of `version`, not later than `version` | `7` `"1.1.0"` `"1.0"` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "No value's `since` is later than the document's `version`." |
| `values.*.status` | yes | `string` | `active` or `deprecated` | `7` `"retired"` `null` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`status` is `active` or `deprecated`." |
| `values.*.title` | yes | `string` | a code point outside W | `7` `""` `" "` `null` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`title`, and `profile` when it is a string, are not empty" |
| `values.*.profile` | yes | `string` or `null` | a code point outside W | `7` `""` `" "` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`title`, and `profile` when it is a string, are not empty" |
| `values.*.asset_types` | when `kind` is `workflow` | `array` | a non-empty array of distinct identifiers | `[]` `["fund_nav","fund_nav"]` `["Fund_NAV"]` `"fund_nav"` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`asset_types` is present on a value exactly when `kind` is `workflow`." |

A document whose `schema_version` is a well-formed later version, such as `v2`, is malformed: a
vocabulary is configuration, not evidence, and no version gate applies to it (§1.1 does not list
it). A document that registers a value the verifier's embedded vocabulary does not hold is not
malformed: holding that value is what supplying the document is for.

| case | outcome | rule |
| --- | --- | --- |
| `vocabulary-not-an-object` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "A verifier MUST refuse a supplied vocabulary document that is not strict JSON, is not an object" |
| `vocabulary-registers-another-kind` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "or registers another kind than the kind it was supplied for" |
| `vocabulary-schema-version-is-a-later-version` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "a document whose `schema_version` is a later version is malformed and refused" |
| `vocabulary-carries-a-member-the-format-does-not-name` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "No other member is admitted, at either level." |
| `vocabulary-value-carries-a-member-the-format-does-not-name` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "No other member is admitted, at either level." |
| `vocabulary-names-a-value-twice` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "A value named twice is a duplicate member name, which input strictness refuses." |
| `vocabulary-asset-types-on-a-value-of-another-kind` | `input-refused` | [`verification-vocabularies.md`](verification-vocabularies.md) "`asset_types` is present on a value exactly when `kind` is `workflow`." |
