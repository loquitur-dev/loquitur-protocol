# Verification vocabularies

Status: normative.

This part defines two kinds of vocabulary. Sections 1 to 4 concern the **closed** vocabularies, the
verification statuses and the registry verdicts, whose values this specification fixes. Sections 5
to 10 concern the **registered** vocabularies, the asset types, the workflows and the anchoring
methods, whose values are registered data outside the specification and its schemas.

## 1. Normative source

`VERIFICATION_VOCABULARIES.json` is the machine-readable owner artifact for
protocol release 0.1 verification statuses and public registry verdicts.
Documentation, JSON Schemas and generated client types MUST derive from or be
checked against this artifact.

## 2. Verification status

`verification_receipt.status` and `verification_summary.status` are closed to:

```text
pass | warning | review | fail
```

The vocabulary is enum-constrained in protocol release 0.1. It is not a free
string and consumers MUST reject other values.

There is no fifth value such as `unknown` (the resolution of `LCP-0008` that
`docs/change-proposals.md` records). Such a status
would map to no registry verdict, and since a verdict cites its grounds no
conforming summary could imply it: every reason-code severity resolves to one
of the four above. A status meaning "something is wrong and I will not say what"
is the defect that proposal exists to close.

## 3. Registry verdict

`registry_entry.verdict` is closed to:

```text
PASS | WARN | REVIEW | FAIL
```

The status-to-verdict mapping is defined in the owner artifact and is total:
every verification status resolves to exactly one registry verdict, so a consumer
never has to handle an absent mapping. Implementations MUST NOT introduce a status
outside the four above, and MUST NOT coerce an unrecognized value to PASS, WARN,
REVIEW or FAIL: an unrecognized status is a rejection, not a downgrade.

## 4. Change control

Adding, removing or reinterpreting a value is a coordinated protocol change. It
requires updated schemas, generated declarations, SDK runtime parsing, normative
conformance vectors and a release-set compatibility decision.

This section binds the closed vocabularies of sections 1 to 3, and every other closed vocabulary
the specification defines. A registered vocabulary changes under section 9, and only its kinds,
its grammar, its document format and the rules of section 7 change under this section (section 10).

## 5. Registered vocabularies

Three members of the public objects take values that depend on the domain of a record rather than
on the protocol: the asset type, the workflow, and the method an anchor uses. The protocol fixes
their grammar, and a **registered vocabulary** holds their values.

The **kinds** are closed: `asset_type`, `workflow` and `anchoring_method`. The **values** of each
kind are open: they are registered in a versioned document outside every schema (section 6), and a
value registered after a verifier was built is a value that verifier does not know (section 7).

| kind | governed members | who defines a value |
| --- | --- | --- |
| `asset_type` | `asset_type` of the registry entry, the verification receipt and the verification, coverage, change and lineage summaries; each element of a trust entry's `allowed_asset_types` | the profile of the vertical the value belongs to |
| `workflow` | `workflow` of the registry entry; each element of a trust entry's `allowed_workflows` | the profile of the vertical the value belongs to |
| `anchoring_method` | `anchor.method` of the registry entry | protocol governance |

The core of the protocol, this specification and its schemas, holds no value of any kind. It holds
the grammar of a value, the closed set of kinds, the document format of section 6, and the rules of
sections 7 to 9. The registered vocabularies of this release are the files
`vocabularies/asset_type.json`, `vocabularies/workflow.json` and
`vocabularies/anchoring_method.json` of the `loquitur-protocol` repository. A vocabulary is
identified by its kind and its version, never by its path: moving a file changes no identity.

Each value names the profile that defines it. Values of `anchoring_method` are defined by protocol
governance, because an anchoring method is not a property of a vertical. A value whose defining
profile has no published document yet carries `null` in its place.

## 6. The registered vocabulary document

A registered vocabulary document is a JSON object, read under input strictness
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §6), that satisfies
`registered-vocabularies/schema.json` and the two rules below that the schema cannot state. It has
exactly these members, and a registered value exactly the members whose name begins `values.*.`,
where `*` stands for every member of `values`:

| field | type | required | meaning |
| --- | --- | --- | --- |
| `object_type` | string | yes | exactly `registered_vocabulary` |
| `schema_version` | string | yes | exactly `v1` |
| `kind` | string | yes | one of `asset_type`, `workflow` and `anchoring_method` |
| `version` | string | yes | the version of the vocabulary, `MAJOR.MINOR.PATCH` |
| `values` | object | yes | the registered values, at least one, by value |
| `values.*.since` | string | yes | the version that registered the value |
| `values.*.status` | string | yes | `active` or `deprecated` |
| `values.*.title` | string | yes | a short name for a reader, not empty |
| `values.*.profile` | string or null | yes | the profile that defines the value, not empty, or `null` |
| `values.*.asset_types` | array of strings | when `kind` is `workflow` | the asset types the workflow applies to |

The rules for each member:

- `object_type` is exactly `registered_vocabulary`, and `schema_version` is exactly `v1`.
- `kind` is one of the three kinds of section 5.
- `version` and every `since` are three decimal integers joined by `.`, each with at most nine
  digits and no leading zero, with no pre-release label or other suffix.
- Every member name of `values` is an identifier (section 7), and `values` has at least one member.
  A value named twice is a duplicate member name, which input strictness refuses.
- `status` is `active` or `deprecated`.
- `title`, and `profile` when it is a string, are not empty: each has a code point outside the
  whitespace set W of [`bundle-objects.md`](bundle-objects.md).
- `asset_types`, when present, is a non-empty array of distinct identifiers.
- No other member is admitted, at either level.

**No value's `since` is later than the document's `version`.** Two versions are compared component
by component, as integers, from `MAJOR` to `PATCH`.

**`asset_types` is present on a value exactly when `kind` is `workflow`.** It is informative in this
version: no verifier checks that a workflow and an asset type belong together, because a trust
entry's scope already constrains both values independently.

A document that breaks a rule of this section is malformed. This example is informative:

```json
{
  "object_type": "registered_vocabulary",
  "schema_version": "v1",
  "kind": "workflow",
  "version": "1.0.0",
  "values": {
    "fund_nav_update": {"since": "1.0.0", "status": "active", "title": "Fund NAV update", "profile": null, "asset_types": ["fund_nav"]}
  }
}
```

## 7. Known, unknown and invalid values

**The grammar.** A value of a registered vocabulary, and every governed member of section 5, is an
**identifier**: a string that matches `^[a-z0-9][a-z0-9_]{0,63}$`, which is 1 to 64 characters of
lower-case ASCII letters, digits and `_`, beginning with a letter or a digit. It is the grammar of
`signature.algorithm` and of `key_type`. There is no namespace and no private-use prefix in this
version: each kind is one flat vocabulary.

A governed member's value is, with respect to the vocabulary the verifier holds for its kind
(section 8):

| value | definition | what follows |
| --- | --- | --- |
| known | an identifier that names a member of `values`, whatever its `status` | nothing |
| unknown | an identifier that names no member of `values` | the review reason `vocabulary_value_unknown`, for the members judged below ([`report-contract.md`](report-contract.md) §3.3); the catalog code `VOCABULARY_VALUE_UNKNOWN` for a published object that cites it |
| invalid | not an identifier: not a string, or a string with an upper-case letter, a hyphen, a space, no character or more than 64 | the document breaks its contract: `registry_entry_contract_violation` or `verification_receipt_contract_violation` ([`report-contract.md`](report-contract.md) §5.3), or `INVALID_TRUST_REGISTRY` ([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, row 3); the catalog code `VOCABULARY_VALUE_INVALID` for a published object that cites it |

A deprecated value is known. Whether a value is invalid is decided by the document's contract, and
needs no vocabulary; whether it is known is decided after the contract holds, and needs one.

**The members a verifier judges.** A verifier judges whether a value is known at exactly three
members: `asset_type` of the verification receipt, and `asset_type` and `workflow` of the registry
entry. It judges each only on a document that satisfies its contract and whose contract the run
judges. An unknown value at one of them makes the review reason `vocabulary_value_unknown` hold. It
masks nothing: a scope mismatch, a link that does not hold or a signature that does not verify fails
the run as it would with a known value.

**The members a verifier does not judge.**

- Each element of a trust entry's `allowed_asset_types` and `allowed_workflows`. A trust registry
  may authorize keys for verticals the verifier does not know, so an unknown value there is not a
  finding. Its grammar is part of the registry's contract.
- `anchor.method` of the registry entry. The anchor is outside the signature and unattributable
  ([`anchor-commitment.md`](anchor-commitment.md) §2), and no check reads it in this version: an
  unknown method has no effect on a run, and a verifier MAY record it among its informative notes.
  A value anyone can add to a signed entry without a key would otherwise turn any run into a review.
  A malformed method breaks the entry's contract.
- `asset_type` of the summaries, which no verifier loads
  ([`document-contracts.md`](document-contracts.md) §13).

## 8. Which vocabulary a verifier holds

**One document per kind.** For each kind, a verifier holds exactly one registered vocabulary
document for a run. By default it is a version built into the verifier. An operator MAY supply
another document for a kind, out of band, and the verifier then holds that document for that kind,
and the built-in one for every other kind. Two documents of one kind are never merged.

**From the operator, never from the input.** No member of a bundle, a registry entry, a verification
receipt or a trust registry selects or supplies a vocabulary, and a verifier MUST NOT take one from
them. The verifier and its operator choose which vocabulary judges the input, as they choose the
trust roots ([`trust-root.md`](trust-root.md)).

**Refusal.** A verifier MUST refuse a supplied vocabulary document that is not strict JSON, is not
an object, breaks section 6, or registers another kind than the kind it was supplied for, and a
command line refuses as well a path that names no regular file and a file the host fails to read.
The refusal comes before any evidence is read: a command line returns exit `64` and no report, and a
library raises an error of the host language ([`report-contract.md`](report-contract.md) §4). A
vocabulary is configuration of the verifier, not evidence, so no version gate applies to it: a
document whose `schema_version` is a later version is malformed and refused, like any other value
outside its rule.

**The report.** A report MAY record the documents the run held. The reference verifiers record them
in the informative member `vocabularies`: for each kind, the document's `version`, the digest of its
bytes as `sha256:<64 lowercase hex>`
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §2), and `source`, `embedded`
for a built-in document and `operator` for a supplied one. The bytes digested are those the
verifier holds: the bytes read, for a verifier that keeps them, and the document's RFC 8785
canonical bytes ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §1) for one
that holds only the parsed document. The two differ for a document that is not already canonical;
the member is informative, so the difference does not make two runs disagree. An
operator who keeps the document can repeat the run.

## 9. Versioning and registration

**Versions.** Adding a value, or moving a value from `active` to `deprecated`, makes a new minor
version: `MINOR` grows by one and `PATCH` is `0`. Correcting a `title`, or naming the `profile` of a
value whose profile was `null`, makes a new patch version. Every added value carries `since` equal
to the version that adds it.

**Values are permanent.** A value is never removed, renamed or reinterpreted, its `since` never
changes, and a deprecated value is never made active again. A major version is not defined: a value
appears in signed public entries that cannot be withdrawn, so reinterpreting it is forbidden rather
than versioned.

**Registration.** A value is registered by a change to its vocabulary file that names the defining
profile, approved by protocol governance and classified `vocabulary-registration`
(`compatibility-classes.json`). A registration changes no schema, no closed vocabulary, no rule and
no protocol version. It changes no member of the conformance archive either, because the corpus
carries vocabularies of its own ([`conformance-testing.md`](conformance-testing.md) §4.1).

**A verifier built before a registration.** It holds an earlier version, reports the value as
unknown, and reaches `OFFLINE_REVIEW` with the review reason `vocabulary_value_unknown` where the
value is judged. It remains conforming. An operator whose verifier must recognize the value supplies
the later version (section 8).

## 10. Change control for registered vocabularies

Adding, removing or renaming a kind, changing the grammar of section 7, changing the document format
of section 6, or changing which members are judged and what an unknown or invalid value does, is a
protocol change under section 4. Registering, deprecating or retitling a value is a registration
under section 9, and is not a protocol change.
