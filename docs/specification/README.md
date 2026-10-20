# Normative specification artifacts

Status: normative.

The prose documents are normative, each as its status line states
([`introduction.md`](introduction.md) §4.3), and the machine-readable files below are normative;
`PROSE_DIGESTS.json` binds the prose bytes and `NORMATIVE_ARTIFACTS.json` the
machine-readable files. The machine-readable files are the artifacts an implementer needs
to write a conforming verifier, and they are carried here as ordinary browsable
files so that reading them requires nothing but this repository: the specification is
implemented from the specification, without installing a package or unzipping the conformance
archive.

## 1. What is here

### 1.1 `schemas/`: the seven public protocol schemas

JSON Schema (draft 2020-12) definitions of the public objects. Each file's `$id` is its
filename under `https://schemas.loquitur.dev/v1/`, for example
`https://schemas.loquitur.dev/v1/verification_summary.schema.json`. Those URIs are stable
schema identities; they do not promise that anything is hosted at them today (section 3.1). Each schema
carries a root keyword `example`, one example instance. It is not a keyword of JSON Schema draft
2020-12: it is a non-validating annotation, an extension of the vocabulary that a validator
ignores, and it decides nothing about any instance.

| File | Object |
| --- | --- |
| `schemas/verification_summary.schema.json` | Verification summary |
| `schemas/verification_receipt.schema.json` | Verification receipt |
| `schemas/change_summary.schema.json` | Change summary |
| `schemas/lineage_summary.schema.json` | Lineage summary |
| `schemas/coverage_summary.schema.json` | Coverage summary |
| `schemas/registry_entry.schema.json` | Registry entry; see [`registry-entry.md`](registry-entry.md) |
| `schemas/trust_registry.schema.json` | Trust registry; see [`trust-registry-authorization.md`](trust-registry-authorization.md) section 10 |

These are public protocol contracts. They are not internal schemas, and they carry no
confidential business data.

### 1.2 `reason-codes/`: the reason-code catalog and the schema it must satisfy

- `reason-codes/v2.0/catalog.json`: catalog version 2.0.0 for the vocabulary
  `loquitur.reason_codes.v1`: 57 entries, each carrying deterministic narrative content
  for the `technical`, `compliance` and `executive` audiences, plus the composition
  templates that assemble an explanation from them.
- `reason-codes/schema.json`: the schema the catalog is validated against, with `$id`
  `https://schemas.loquitur.dev/v1/reason_codes_catalog.schema.json`.

[`reason-codes.md`](reason-codes.md) beside this file describes the vocabulary and its categories in
prose. The catalog is the vocabulary's actual content.

### 1.3 `compatibility-classes.json`: the change-classification vocabulary

The nine compatibility classes (`schema_version` `loquitur.compatibility_classes.v1`),
each with its rank and whether it requires consumer coordination or a new protocol
version, and the rule that an unclassified change defaults to `breaking`. A class's rank is the
integer, from 0 to 8, that fixes the order in which the classes are listed, in that file and in
`change-proposal.schema.json`; it orders them and does not measure how far a change reaches.
The class `vocabulary-registration` is the one a registration of a value takes
([`verification-vocabularies.md`](verification-vocabularies.md) §9): it needs no new protocol
version. The governance documents and `PROTOCOL_RELEASE.json` classify changes using these
identifiers; this file is where the identifiers are defined.

### 1.4 `change-proposal.schema.json`: the shape of a change proposal

The JSON Schema a machine-readable change proposal must satisfy. `GOVERNANCE.md` requires
every public semantic change to be filed as one, and this is the schema it means.
`tests/test_change_proposal_schema.py` checks that its list of compatibility classes is the
set `compatibility-classes.json` declares, in rank order. The conformance archive does not
carry it.

### 1.5 The two constructions that are not schemas

Two normative surfaces are prose rather than JSON Schema, because neither is a public
object that crosses an organizational boundary:

- [`trust-root.md`](trust-root.md): the exact bytes a trust root signs over a trust registry, the
  closed shape of the out-of-band trust-root document, the evaluation order and the status
  vocabulary. This is the only path from `REVIEW` to `PASS` in the `authorization` check.
- [`bundle-objects.md`](bundle-objects.md): the closed field contracts for `manifest.json`,
  `p1.json` and `envelope_env1.json`, plus the rules and limits of ZIP intake.

Both are here for the same reason the schemas are: an implementer reads them in this
repository, and never has to open a reference implementation this repository does not carry.

### 1.6 The rules a verifier applies across objects

The documents above define objects. These define what a verifier concludes from several of
them together, in the order it concludes it:

- [`registry-link.md`](registry-link.md): the `link` check: every comparison between a registry
  entry and a bundle's receipt, its exact operands, the three values of the link result, the
  committed verdict, and the rule that an entry's verdict is the verdict its reason codes derive.
- [`report-contract.md`](report-contract.md): what the report of a run carries: status, verdict and
  exit code, the exit-code taxonomy, the reason surface a conformance comparison reads, and which
  members are informative.
- [`trust-registry-authorization.md`](trust-registry-authorization.md): the `authorization` check:
  the evaluation time, lifecycle states and windows, the trust registry's coherence, finding and
  scoping the key, the evaluation order, the signature step and the status vocabularies.

### 1.7 The completeness surface of all of them

- [`document-contracts.md`](document-contracts.md): every member of every document a verifier loads,
  at every depth: required or optional, JSON type, allowed values, and what a run reports when the
  member is missing, of the wrong type or out of range. It adds no rule: every row cites the
  sentence or the schema keyword that states it. The rules above are complete only when read
  together with the schemas, and this page says, per member, what a run reports. Read it to check an
  implementation member by member; read the documents above to understand why the rules are what
  they are.

### 1.8 Testing an implementation

- [`conformance-testing.md`](conformance-testing.md): how to check and extract the pinned
  conformance archive, what each of its vector files declares, how the reference verifiers are run
  over it, and which of its declarations an implementation must reproduce to conform.

### 1.9 `registered-vocabularies/` and `vocabularies/`: the registered vocabularies

- `registered-vocabularies/schema.json`: the schema a registered vocabulary document satisfies, with
  `$id` `https://schemas.loquitur.dev/v1/registered_vocabulary.schema.json`. It closes the kinds,
  `asset_type`, `workflow` and `anchoring_method`, and fixes the document format; it holds no value.
  The conformance archive carries a copy of it under `protocol/`.
- `vocabularies/asset_type.json`, `vocabularies/workflow.json` and
  `vocabularies/anchoring_method.json`, at the root of this repository rather than in this folder,
  because they are registered data and not specification text: the values of each kind, each with
  the version that registered it, its status, a title and the profile that defines it. A
  registration changes them and nothing in this folder
  ([`verification-vocabularies.md`](verification-vocabularies.md) §9), and the conformance archive
  carries no copy of them. `loquitur-schemas` mirrors them, and the reference verifiers embed them.

## 2. Normative status, and what that does and does not mean

These files are the source of truth for the artifacts they define. Copies that appear
elsewhere are mirrors of these bytes and not independent originals:

- the copies bundled as package data inside `loquitur-schemas`;
- the copies carried inside the digest-pinned conformance archive that `CONFORMANCE_LOCK.json`
  names;
- any copy vendored by a consumer.

Where a mirror disagrees with the file here, the file here is what the protocol says and
the mirror is wrong.

That ownership is recorded machine-readably and enforced. `NORMATIVE_ARTIFACTS.json` lists every
artifact this repository owns, its digest, and the repository and path of each declared mirror. A
JSON file placed under this folder without being declared there fails the check, except
`NORMATIVE_ARTIFACTS.json` itself and `PROSE_DIGESTS.json` (§2.1), which are checked on their own,
so the list cannot fall behind the folder it describes. `tools/check_normative_mirrors.py` compares
them. In this repository alone it checks the manifest against this repository's own files; with
`loquitur-schemas` checked out beside this repository, it also compares that package's copies with
the files here. `tools/check_protocol_release.py` compares the copies inside the conformance archive
with the files here. The other mirrors are in `loquitur-conformance`, which is not published: the
same tool compares them when that repository is checked out beside this one, which a reader of a
published copy never has.

The two halves are deliberately separate. Self-consistency needs nothing else checked
out, so it can never skip: if it fails, the manifest is stale. The mirror comparison
needs the sibling repositories, so it skips a sibling that is absent, and fails on it when
`LOQUITUR_REQUIRE_SIBLINGS` is set. The skip is reported rather than swallowed: a check that
passes because the thing it compares is not there has checked nothing.

The manifest is generated from the files, never hand-written, and the tool refuses to
regenerate and verify in the same run: comparing a file against itself proves nothing. No
digest table is reproduced in this prose for the same reason a hand-maintained list is not
trusted anywhere else here: it goes stale silently and then misleads. Read the manifest,
or compute the digests from the files.

### 2.1 `PROSE_DIGESTS.json`: the bytes of the normative prose

The manifest above binds JSON only, and the Markdown documents in this folder are normative
too. `PROSE_DIGESTS.json` lists every Markdown file under this folder, whatever the case of its
`.md` suffix, `GOVERNANCE.md`, `PROTOCOL_RELEASE.json` and `docs/change-proposals.md`, with its
size and SHA-256. `tools/refresh_prose_digests.py` generates it, and
`tools/check_protocol_release.py` and `tools/check_normative_mirrors.py` both fail when a
listed file's bytes differ from the list, when a Markdown file here is not listed, or when
the list is not exactly what the tool writes. A change to a normative sentence therefore
changes this list in the same commit, which is where the change is classified.

The list is not an entry of `NORMATIVE_ARTIFACTS.json`, which declares the artifacts that
have mirrors: it has none. It is not a member of the conformance archive either.

## 3. Identifiers, versions and citations

### 3.1 The `$id` policy

The path segment `/v1/` of a schema `$id` versions the schema family. A change that breaks an
instance valid under a `v1` schema is published under a new segment, `/v2/`, and never under the
same `$id`. An `$id` is an identifier, not a location: nothing promises that a document is hosted
at it, and a validator is given the files of this repository and fetches nothing.

For the seven files of `schemas/` the tail of the `$id` is the file name. Three schema files do
not follow that rule, and these are all of them:

| File | `$id` |
| --- | --- |
| `reason-codes/schema.json` | `https://schemas.loquitur.dev/v1/reason_codes_catalog.schema.json` |
| `registered-vocabularies/schema.json` | `https://schemas.loquitur.dev/v1/registered_vocabulary.schema.json` |
| `change-proposal.schema.json` | `https://governance.loquitur.dev/schemas/protocol-change-proposal-v1.json` |

### 3.2 How each family is versioned

- The reason-code catalog is versioned by its path: `reason-codes/v2.0/catalog.json` is catalog
  version 2.0.0 of the vocabulary `loquitur.reason_codes.v1`
  ([`reason-codes.md`](reason-codes.md) §3). A new catalog version is a new directory.
- A registered vocabulary is versioned in its file: its `version` member, and the `since` member of
  each value ([`verification-vocabularies.md`](verification-vocabularies.md) §6).
- A schema is versioned by its URL, the `/v1/` segment of its `$id` (section 3.1).

### 3.3 Root JSON files that are normative

`CRYPTOGRAPHIC_CAPABILITIES.json` and `VERIFICATION_VOCABULARIES.json`, at the root of this
repository, are normative contract data: the first is the closed set of cryptographic capabilities
([`cryptographic-capabilities.md`](cryptographic-capabilities.md)), the second the closed status
and verdict vocabularies ([`verification-vocabularies.md`](verification-vocabularies.md)). They are
not in `NORMATIVE_ARTIFACTS.json` because that list declares the files under this folder, and
these two live outside it; the release gate (`tools/check_protocol_release.py`) requires them and
checks them against `PROTOCOL_RELEASE.json`, and the conformance archive carries byte-for-byte
copies under `protocol/`. The naming convention of the root is that a name in UPPER_SNAKE case is
contract or governance data, and a name in lower case is release tooling (`public_spec_manifest.json`, for example).

### 3.4 Citing a part

The file name of a part is its stable citation key. The part numbers of the document map
([`introduction.md`](introduction.md) §3) belong to that table and are not citation keys; a
citation uses the file name and a section number. A citation of `docs/specification/x.md` means
the text of that file at the release tag that is pinned, and not the text on a branch.

### 3.5 `signing-envelope-v2.md`

The page is named for the version of the envelope it defines, `envelope_version` 2. A version 3
envelope would be a new page, `signing-envelope-v3.md`, and would not rewrite this one.
