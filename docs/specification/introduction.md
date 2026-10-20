# Loquitur Protocol specification

Status: normative.

Protocol release 0.1, identified in `PROTOCOL_RELEASE.json` as `loquitur-protocol-0.1.0`. The
release is a public preview: its public API is not yet stable and may change before 1.0.0, and no
independent cryptographic review of the protocol or of its reference verifiers has been done.

The specification is one text in several documents, called parts. This document is part 1. It
gives the scope, the map of the parts, the conventions every part is read under, the terms they
use, the conformance classes and the references. Read it first.

## 1. Abstract

This section is informative.

Loquitur is a protocol for verifiable records of the evidence behind claims about real-world
assets. An issuer keeps the evidence private, in a bundle, and publishes a registry entry: a small
public record that commits to digests of the bundle and is signed with a key that a trust registry
authorizes. A verifier that holds the bundle, the entry, the trust registry and a trust root it
pinned decides, offline and with no service, whether the bundle has the shape the protocol defines,
whether its bytes are the ones committed to, whether the public entry refers to it, and whether the
party that signed the entry was entitled to. It reports the answer as a status, a verdict and the
reasons for them.

The specification defines those objects, their canonical bytes and digests, the checks and their
order, the vocabularies a verdict is stated in, the report a verifier produces, and the conformance
corpus that tests an implementation against all of it.

## 2. Scope and non-goals

### 2.1 Scope

This specification defines:

- what a public commitment may carry and what stays private (part 2);
- the named checks of verification and the order in which they depend on one another (part 3);
- canonical JSON, digests, hash constructions and the signature scheme (parts 4, 6 and 7);
- the bundle, the closed field contracts of its three objects, and archive intake (part 5);
- the registry entry, how a verifier links it to a bundle, how a trust registry authorizes the key
  that signed it, and how a trust root authenticates that trust registry (parts 8 to 11);
- the closed vocabularies of statuses, verdicts and reason codes, and the rules that tie a verdict
  to the grounds it cites (parts 12 to 14);
- the report of a verification run (part 15);
- what an anchor must commit to, before any anchoring exists (part 16);
- the threat model (part 17), conformance testing (part 18), and every member of every document a
  verifier loads (appendix A).

### 2.2 Non-goals

The protocol does not calculate economically correct asset values, issue tokens, custody evidence,
run a marketplace, provide investment advice, provide regulatory approval, or replace independent
due diligence.

This release does not define:

- the checks `transparency` and `anchoring`, which are named and reserved, and never requested or
  reported ([`verification-checks.md`](verification-checks.md) sections 2.5 and 2.6);
- any live anchoring: part 16 fixes only what an anchor must commit to;
- a time-stamp token or any other attestation of time
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) section 2);
- an HTTP API or a hosted service.

## 3. Document map

The parts, in reading order. Part numbers belong to this table and to the table of contents in
`docs/README.md`. They are not part of file names, section numbers, anchors or citations, so a part
added later moves nothing.

| Part | Document | Kind | Subject |
| --- | --- | --- | --- |
| 1 | [`introduction.md`](introduction.md) | normative | scope, document map, conventions, terminology, conformance and references |
| 2 | [`public-private-boundary.md`](public-private-boundary.md) | normative | what a public commitment may carry, what stays private, and the privacy considerations |
| 3 | [`verification-checks.md`](verification-checks.md) | normative | the named checks, their dependency order, where the offline checks stop, and the verification modes |
| 4 | [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) | normative | canonical JSON, digests, hash constructions, the signature scheme and input strictness |
| 5 | [`bundle-objects.md`](bundle-objects.md) | normative | the members of a bundle, the closed field contracts of its three objects, and archive intake |
| 6 | [`signing-envelope-v2.md`](signing-envelope-v2.md) | normative | the exact bytes an issuer signs |
| 7 | [`cryptographic-capabilities.md`](cryptographic-capabilities.md) | normative | what is supported, and what is named and refused |
| 8 | [`registry-entry.md`](registry-entry.md) | normative | the public commitment object, its identifiers and the subject reference hash |
| 9 | [`registry-link.md`](registry-link.md) | normative | the `link` check: how a registry entry is compared with a bundle |
| 10 | [`trust-registry-authorization.md`](trust-registry-authorization.md) | normative | the `authorization` check, and what a trust registry may carry |
| 11 | [`trust-root.md`](trust-root.md) | normative | how a trust registry is authenticated against a trust root |
| 12 | [`verification-vocabularies.md`](verification-vocabularies.md) | normative | the closed status and verdict vocabularies, and the registered vocabularies of asset types, workflows and anchoring methods |
| 13 | [`reason-codes.md`](reason-codes.md) | normative | the reason-code register and the rules that bind a code to a verdict |
| 14 | [`verdict-grounds.md`](verdict-grounds.md) | normative | the rules that tie a verdict to the grounds it cites |
| 15 | [`report-contract.md`](report-contract.md) | normative | what a verifier's report carries, and what a conformance comparison reads |
| 16 | [`anchor-commitment.md`](anchor-commitment.md) | reserved | what an anchor must commit to; no anchoring is live |
| 17 | [`threat-model.md`](threat-model.md) | normative | the security considerations: what is protected, the adversaries, the trust boundaries and the residual risks |
| 18 | [`conformance-testing.md`](conformance-testing.md) | normative | how to run the conformance corpus against an implementation, and what counts as conforming |
| Appendix A | [`document-contracts.md`](document-contracts.md) | normative appendix, adds no rule | every member of every document a verifier loads, with what a run reports when it is broken |
| Index | [`README.md`](README.md) | normative | the machine-readable artifacts: schemas, reason-code catalog, compatibility classes, and what normative means for them |

Three files outside this folder belong to the specification as well: `GOVERNANCE.md`, which says
how the specification changes; `docs/change-proposals.md`, the register of the `LCP-` change
proposals the parts cite; and `PROTOCOL_RELEASE.json`, which declares the release. The
machine-readable artifacts the parts define are indexed in [`README.md`](README.md) in this folder.

## 4. Conventions

### 4.1 Requirements language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT",
"RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in the parts of this specification are to
be interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when, they appear in
all capitals, as shown here.

A key word set in bold or in a code span means the same as one set in plain text.

### 4.2 Normative and informative text

A normative part states requirements. Its requirements are not only the sentences that carry a key
word: a statement in the indicative, such as "a verifier refuses the archive" or "the run is
`OFFLINE_FAIL`", is a requirement as binding as one written with "MUST".

These are informative wherever they appear, and add no requirement:

- a section, paragraph or note that says it is informative or non-normative;
- a section whose title begins with "Why", which gives the reason for a rule; a sentence in it
  that carries a key word is still a requirement;
- an example. Where an example and a rule disagree, the rule is the protocol.

Some parts cite code in a reference implementation in the form `<module>.py::<name>`. Each such
part says so in a note above its first section; the citations are evidence for a reviewer and not
part of the protocol.

### 4.3 Status lines

Every document in this folder opens with one status line, in one of these forms:

- "Status: normative." The document is normative, as section 4.2 states.
- "Status: informative." The document states no requirement.
- "Status: reserved." The document fixes requirements for a capability that no component of this
  release provides and no check evaluates. Its requirements bind an implementation of that
  capability; nothing in the document is live.
- "Status: normative appendix, adds no rule." The document restates, member by member, rules that
  other parts and the schemas state, and cites the source of each.

A status line names no part number.

### 4.4 Sections and citations

Every section of a part is numbered, except a preamble before its section 1 and a subsection named
by an identifier of its own, such as VG-1 of [`verdict-grounds.md`](verdict-grounds.md). Numbers are
only added: a section keeps its number, and a section added to a part takes the next free number.

A citation names a document and a section: "[`report-contract.md`](report-contract.md) section 5.3"
or "[`report-contract.md`](report-contract.md) §5.3". A section number with no document, such as
"section 5.3" or "§5.3", cites the document it appears in. A few citations name a section by its
title in quotation marks, such as
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness". A
reference to a document is a link to its file; the section it names is found by its number.

The notation of a digest, `sha256:<64 hex>`, is defined in
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) section 2. In a construction,
`||` joins byte strings in the order written.

## 5. Terminology

The parts use these terms with these meanings. The last column names where each is defined.

| Term | Meaning | Defined in |
| --- | --- | --- |
| bundle | the private evidence package a verifier checks, as a directory or a ZIP archive | [`bundle-objects.md`](bundle-objects.md) section 1 |
| member | a regular file of a bundle, its default data stream | [`bundle-objects.md`](bundle-objects.md) section 1 |
| manifest, P1, envelope | the three objects of a bundle: `manifest.json`, `p1.json` and `envelope_env1.json` | [`bundle-objects.md`](bundle-objects.md) sections 2 to 4 |
| envelope | three things carry the word. The bundle envelope is `envelope_env1.json`, a member of a bundle. The registry-entry signing envelope is the object a registry entry's signature covers. The trust-root signing envelope is the object a trust root's signature covers over a trust registry. A sentence that relies on one names it | [`bundle-objects.md`](bundle-objects.md) section 4; [`signing-envelope-v2.md`](signing-envelope-v2.md); [`trust-root.md`](trust-root.md) section 4 |
| profile | four things carry the word. A conformance profile is a group of rules `PROTOCOL_RELEASE.json` lists, with its compatibility class. A capability profile is the closed set of cryptographic capabilities of a release. A disclosure profile is the `disclosure_profile` of a registry entry. An asset profile is the profile a registered asset type names as its definition. In prose written from now on, an unqualified "profile" means an asset profile | section 8.2 of this document; [`cryptographic-capabilities.md`](cryptographic-capabilities.md); [`public-private-boundary.md`](public-private-boundary.md); [`verification-vocabularies.md`](verification-vocabularies.md) |
| registry | a trust registry (the document that authorizes keys), or a registry entry (the public record of one bundle). A future public log would be neither, and is not called "the registry" | [`registry-entry.md`](registry-entry.md); [`trust-registry-authorization.md`](trust-registry-authorization.md) section 10 |
| mint | to build a new corpus archive from its sources and pin it | [`conformance-testing.md`](conformance-testing.md) |
| check | one of the named questions verification answers: `structure`, `integrity`, `link`, `authorization`, and the reserved `transparency` and `anchoring`. A check is not a level: a report names no level, number or rank | [`verification-checks.md`](verification-checks.md) sections 1 and 2 |
| verifier | an implementation that checks a bundle, and optionally a registry entry, a trust registry and a trust-root document, against this specification, and reports the run | [`report-contract.md`](report-contract.md) section 1 |
| operator | whoever runs a verifier and supplies its inputs, the evaluation time included | [`report-contract.md`](report-contract.md) section 1 |
| evaluation time | the instant, supplied by the operator, at which a key and a trust root are judged | [`trust-registry-authorization.md`](trust-registry-authorization.md) section 2 |
| issuer | the party whose key signs a registry entry | [`registry-entry.md`](registry-entry.md) |
| relying party | a party that acts on a verdict | [`threat-model.md`](threat-model.md) section 8 |
| registry entry | the public record that commits to a bundle's manifest and receipt digests | [`registry-entry.md`](registry-entry.md) |
| trust registry | the document that authorizes issuer keys for asset types and workflows | [`trust-registry-authorization.md`](trust-registry-authorization.md) section 10 |
| trust root | a public key, pinned by the operator out of band, that signs a trust registry; roots reach the verifier in a trust-root document | [`trust-root.md`](trust-root.md) sections 1 and 3 |
| verification receipt, verification summary | two of the public object families, each carrying a verification status and reason codes | section 7 of this document |
| status | of a report: `OFFLINE_OK`, `OFFLINE_FAIL`, `OFFLINE_REVIEW`, `INTERNAL_ERROR`, `UNSUPPORTED_VERSION` or `HOST_FAILURE`. Of a receipt or a summary: `pass`, `warning`, `review` or `fail` | [`report-contract.md`](report-contract.md) section 3.1; [`verification-vocabularies.md`](verification-vocabularies.md) section 2 |
| verdict | of a report: `PASS`, `FAIL` or `REVIEW`, or `null` when no verdict on the evidence was computed. Of a registry entry: `PASS`, `WARN`, `REVIEW` or `FAIL` | [`report-contract.md`](report-contract.md) section 3.1; [`verification-vocabularies.md`](verification-vocabularies.md) section 3 |
| registered vocabulary | a versioned document that registers the values of one kind: `asset_type`, `workflow` or `anchoring_method`. The kinds are closed and the values are registered outside the schemas | [`verification-vocabularies.md`](verification-vocabularies.md) sections 5 and 6 |
| unknown value | an identifier at a member a registered vocabulary governs that the vocabulary a verifier holds does not register; it is a review, not a failure | [`verification-vocabularies.md`](verification-vocabularies.md) section 7 |
| invalid value | a value at a member a registered vocabulary governs that is not an identifier `^[a-z0-9][a-z0-9_]{0,63}$`; it breaks the contract of the document that carries it | [`verification-vocabularies.md`](verification-vocabularies.md) section 7 |
| reason code | a code of the catalog `loquitur.reason_codes.v1`, written in upper snake case, such as `INTEGRITY_OK`. Published objects cite reason codes; a verifier's report cites none | [`reason-codes.md`](reason-codes.md) |
| verifier reason | a value of a report's reason surface: `outcome.reason`, the codes of `errors` and the review reasons, written in lower snake case, such as `trust_registry_root_not_pinned`, and the trust-registry statuses, written in upper snake case. Verifier reasons are not catalog codes | [`report-contract.md`](report-contract.md) section 5.1 |
| refuse, refusal | three senses, which a sentence that relies on one names. A bundle object, a receipt, a registry entry or a trust registry is refused when it breaks its contract, and so is the layer that reads it: the check it serves does not hold and the run is `OFFLINE_FAIL`, exit `1`. An input is refused as a whole by a row of the error table from `input_not_found` to `filesystem_error`: it is the run's only error and nothing else is evaluated, `HOST_FAILURE` or `OFFLINE_FAIL` by the row's class. An invocation is refused before any evidence is read, a malformed trust-root document or registered vocabulary document included: a command line exits `64` and prints no report, and a library raises an error of the host language and returns none | [`report-contract.md`](report-contract.md) sections 3.1, 5.3 and 4 |
| byte-wise | of a comparison of two strings: they are equal when, and only when, their UTF-8 encodings are the same bytes; nothing is trimmed, case-folded or normalized first. Every comparison of strings is byte-wise unless a rule names another | [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) section 7 |
| maintainer | the person who maintains the protocol and its repositories | `GOVERNANCE.md` |
| `loquitur-protocol-governance` | the role that holds normative authority over the protocol; it names no repository | `GOVERNANCE.md` |

## 6. Protocol overview

This section is informative. The requirements behind each idea are in the parts the document map
names.

Loquitur Protocol defines an evidence-to-commitment model:

```text
private evidence material → verification receipt → public registry commitment → lineage/replay posture
```

The core principle is separation between private evidence material and public commitment material.

### 6.1 Private side

Private evidence material can include documents, canonical inputs, claim support maps, policy
outputs, evidence inventory, change details, and bundle manifests. That material remains
issuer-controlled unless deliberately disclosed to an authorized reviewer.

### 6.2 Public side

Public registry commitments are minimal. They are designed to expose only enough information to
verify that a receipt with a defined policy identity, reason-coded outcome, and manifest/receipt
commitment was produced and committed.

### 6.3 Protocol goals

The protocol is designed to support:

- deterministic object handling (the byte-level rules are specified in
  [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md));
- policy and reason-code traceability;
- private evidence custody;
- minimal public commitments;
- independent verification posture;
- lineage and supersession references;
- replay posture for offline or link verification scenarios.

## 7. Canonical object families

The protocol uses a small set of canonical object families. Their schemas are in
`schemas/` beside this file and are owned here; see [`README.md`](README.md) in this directory for
what that ownership means. `loquitur-schemas` ships validators over mirrors of those
bytes, and where a mirror disagrees with the file here, the file here is what the
protocol says.

The three objects that live *inside* a bundle (`manifest.json`, `p1.json` and `envelope_env1.json`)
are not among these families and have no JSON Schema. Their closed field contracts are in
[`bundle-objects.md`](bundle-objects.md).

The descriptions in sections 7.1 to 7.7 are informative. What binds each family is its schema and
the parts that cite it.

### 7.1 Verification summary

A summary of status, reason codes, policy identity, key checks, and support posture.

### 7.2 Verification receipt

A compact, hashable proof artifact that records verification outcome metadata, policy identity,
reason codes, and commitments to private material.

### 7.3 Coverage summary

A required-vs-present and supported-vs-declared view of claim/evidence coverage.

### 7.4 Change summary

A structured delta between snapshots, including material changes, evidence shifts, and support
posture changes.

### 7.5 Lineage summary

A supersession and continuity posture across snapshots or receipt updates.

### 7.6 Registry entry

A minimal public commitment record derived from a receipt. It carries no private evidence
material: [`registry-entry.md`](registry-entry.md) §3 states its privacy rule, and
[`public-private-boundary.md`](public-private-boundary.md) says which material is public and which
is private.

### 7.7 Trust registry

A public issuer/key authorization object. It is interpreted only as
[`trust-registry-authorization.md`](trust-registry-authorization.md) specifies.

## 8. Conformance

This section adds no requirement. It says where the requirements on an implementation are stated.

### 8.1 Conformance to the corpus

[`conformance-testing.md`](conformance-testing.md) section 6 states what an implementation must
reproduce to conform to the conformance corpus that `CONFORMANCE_LOCK.json` pins, and says that
conforming to the corpus is not conforming to the protocol: a rule no vector exercises binds through
the specification alone.

### 8.2 Conformance classes

The release groups its rules into the profiles `PROTOCOL_RELEASE.json` lists, each with its
compatibility class (`compatibility-classes.json`). These profiles are the conformance classes of
this release:

| Profile | Compatibility class |
| --- | --- |
| `canonical-json-v1` | `wire-exact` |
| `schema-validity-v1` | `wire-exact` |
| `offline-verification-v1` | `semantic-exact` |
| `registry-link-v1` | `semantic-exact` |
| `trust-authorization-v1` | `wire-exact-legacy` |
| `public-object-projection-v1` | `wire-exact` |
| `registry-entry-signing-envelope-v2` | `breaking` |
| `cryptographic-capability-matrix-v0.1` | `breaking` |
| `schema-generated-types-v1` | `source-api-breaking` |
| `independent-conformance-oracle-v1` | `semantic-exact` |
| `registered-vocabularies-v1` | `semantic-exact` |

[`conformance-testing.md`](conformance-testing.md) section 4 lists the vector files that exercise
each profile. Two of the profiles, `public-object-projection-v1` and `schema-generated-types-v1`,
bind implementation artifacts rather than a verifier's behavior, and no corpus file exercises them
([`conformance-testing.md`](conformance-testing.md) section 3). Each reference implementation names
the profiles it is held to in the `required_profiles` of its `CONFORMANCE_CONSUMER.json`.

### 8.3 Objects and the rules that bind them

A verification summary is bound by [`verdict-grounds.md`](verdict-grounds.md), and a verifier's
report by [`report-contract.md`](report-contract.md) and not by those rules
([`verdict-grounds.md`](verdict-grounds.md) section 1.1). The publication rules for a registry
entry, its identifiers and its signature are in
[`public-private-boundary.md`](public-private-boundary.md), [`registry-entry.md`](registry-entry.md)
and [`signing-envelope-v2.md`](signing-envelope-v2.md).

### 8.4 Traceability

`docs/traceability/requirements.json` in this repository gives each requirement of the parts
an identifier of the form `REQ-<DOC>-<NNN>`, outside the text of the parts, and binds each to its
sentence, or to the row of a rule table, by quotation. It lists every sentence that carries a key
word of section 4.1 that states a requirement, every sentence that carries only one that advises or
permits, and every row of the tables `docs/traceability/rule-tables.json` names. It does not
list a requirement stated in the indicative outside those tables (section 4.2), which binds all the
same. For each requirement it says what tests it: runs of the conformance corpus, tests of an
implementation, or neither, with the reason; `docs/traceability/README.md` renders the list,
including the requirements no vector exercises. A requirement binds whether or not the inventory
lists it, and the inventory and its rendering change without a protocol release.

## 9. Security and privacy considerations

[`threat-model.md`](threat-model.md) (part 17) is the security considerations of this specification.
It states what is protected, what a verdict asserts, the trust boundaries, the adversaries, the
trust assumptions a relying party inherits, the residual risks, and what an operator must do that a
verifier cannot.

[`public-private-boundary.md`](public-private-boundary.md) section 6 is the privacy considerations.
It answers the questions of RFC 6973 section 7 from what that part and
[`registry-entry.md`](registry-entry.md) state.

## 10. References

### 10.1 Normative references

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14,
  RFC 2119, March 1997, https://www.rfc-editor.org/rfc/rfc2119.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14,
  RFC 8174, May 2017, https://www.rfc-editor.org/rfc/rfc8174.
- [RFC 8259] Bray, T., Ed., "The JavaScript Object Notation (JSON) Data Interchange Format",
  STD 90, RFC 8259, December 2017, https://www.rfc-editor.org/rfc/rfc8259.
- [RFC 7493] Bray, T., Ed., "The I-JSON Message Format", RFC 7493, March 2015,
  https://www.rfc-editor.org/rfc/rfc7493.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)",
  RFC 8785, June 2020, https://www.rfc-editor.org/rfc/rfc8785.
- [RFC 3629] Yergeau, F., "UTF-8, a transformation format of ISO 10646", STD 63, RFC 3629,
  November 2003, https://www.rfc-editor.org/rfc/rfc3629.
- [RFC 3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339,
  July 2002, https://www.rfc-editor.org/rfc/rfc3339.
- [RFC 1951] Deutsch, P., "DEFLATE Compressed Data Format Specification version 1.3", RFC 1951,
  May 1996, https://www.rfc-editor.org/rfc/rfc1951.
- [FIPS 180-4] National Institute of Standards and Technology, "Secure Hash Standard (SHS)",
  FIPS PUB 180-4, August 2015, https://doi.org/10.6028/NIST.FIPS.180-4.
- [SEC 1] Certicom Research, "SEC 1: Elliptic Curve Cryptography", Version 2.0, May 2009,
  https://www.secg.org/sec1-v2.pdf.
- [SEC 2] Certicom Research, "SEC 2: Recommended Elliptic Curve Domain Parameters", Version 2.0,
  January 2010, https://www.secg.org/sec2-v2.pdf.
- [IEEE 1363] IEEE, "IEEE Standard Specifications for Public-Key Cryptography", IEEE Std
  1363-2000, the source of the `r || s` signature encoding the parts call IEEE P1363.
- [IEEE 754] IEEE, "IEEE Standard for Floating-Point Arithmetic", IEEE Std 754-2019.
- [JSON Schema] "JSON Schema: A Media Type for Describing JSON Documents" and "JSON Schema
  Validation: A Vocabulary for Structural Validation of JSON", draft 2020-12,
  https://json-schema.org/draft/2020-12.
- [ECMA-262] Ecma International, "ECMAScript Language Specification", ECMA-262, for the regular
  expressions of the schemas' `pattern` keyword, https://tc39.es/ecma262/.
- [Unicode] The Unicode Consortium, "The Unicode Standard", for scalar values and noncharacters,
  https://www.unicode.org/versions/latest/.
- [APPNOTE] PKWARE, ".ZIP File Format Specification" (APPNOTE.TXT),
  https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT.

### 10.2 Informative references

- [RFC 3552] Rescorla, E. and B. Korver, "Guidelines for Writing RFC Text on Security
  Considerations", BCP 72, RFC 3552, July 2003, https://www.rfc-editor.org/rfc/rfc3552.
- [RFC 6973] Cooper, A., Tschofenig, H., Aboba, B., Peterson, J., Morris, J., Hansen, M., and
  R. Smith, "Privacy Considerations for Internet Protocols", RFC 6973, July 2013,
  https://www.rfc-editor.org/rfc/rfc6973.
- [RFC 6979] Pornin, T., "Deterministic Usage of the Digital Signature Algorithm (DSA) and
  Elliptic Curve Digital Signature Algorithm (ECDSA)", RFC 6979, August 2013,
  https://www.rfc-editor.org/rfc/rfc6979.
- [Wycheproof] Project Wycheproof, test vectors for cryptographic libraries,
  https://github.com/C2SP/wycheproof.
- [RFC 3161] Adams, C., Cain, P., Pinkas, D., and R. Zuccherato, "Internet X.509 Public Key
  Infrastructure Time-Stamp Protocol (TSP)", RFC 3161, August 2001,
  https://www.rfc-editor.org/rfc/rfc3161.
- [eIDAS] Regulation (EU) No 910/2014 of the European Parliament and of the Council on electronic
  identification and trust services for electronic transactions in the internal market, as amended
  by Regulation (EU) 2024/1183, https://eur-lex.europa.eu/eli/reg/2014/910/oj.
- [CAIP-2] Chain Agnostic Standards Alliance, "CAIP-2: Blockchain ID Specification",
  https://github.com/ChainAgnostic/CAIPs/blob/main/CAIPs/caip-2.md.

## 11. Implementation status

This section is informative.

Two implementations of the verifier role were written for release 0.1, one in Python and one in
TypeScript, separately against this specification and by the same maintainer. Both reproduce every
binding run of the conformance corpus that `CONFORMANCE_LOCK.json` pins, except where
[`conformance-testing.md`](conformance-testing.md) section 6 lets an implementation declare a
narrower intake. Agreement of two implementations by one author is evidence that the text can be
implemented as written; it is not
independent evidence that the text is right.

`IMPLEMENTATIONS.md` at the root of this repository is the record of the implementations known to
the maintainer: it names the reference implementations of this release, and each repository states
where it is published and what its releases have been tested against. That file changes without a
protocol release; this section does not.

## 12. Non-claims

This section is informative.

For release 0.1:

- no independent security or cryptographic review of the specification or of either
  implementation has been done, and no audit of any kind; the maintainer's own testing, carried out
  with the help of AI tools, the conformance corpus included, is internal verification and not an
  audit;
- conformance to this specification, or to the conformance corpus, is not compliance with any law,
  regulation or standard, and no certification of any kind exists;
- the release is a preview and is not presented as fit for production use or for decisions of real
  value;
- the specification names no adopter, deployment, customer or partner, and claims none;
- no registry, log, anchoring or other service is operated under this specification;
- a verdict says what section 2 of [`threat-model.md`](threat-model.md) says it asserts and nothing
  more: it does not say that the evidence is true, that a value is right, or that an issuer is who
  it claims to be;
- the verdict path contains no AI: no machine-learning model or other learned component takes part
  in any outcome, which follows from the rules of this specification applied to the inputs.
