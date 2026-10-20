# Testing an implementation against the conformance corpus

Status: normative.

§6 is normative: it states which declarations of the pinned corpus an implementation must
reproduce, and §8 states how agreement between implementations is established. The other
sections describe the archive and how the reference verifiers are run over it.

Section 8 says the corpus observes the Python and TypeScript verifiers through
black-box adapters. This document says how a third implementation runs the same corpus: where the
archive is, how to check and extract it, what each vector file declares, how the two adapters are
called, and what counts as conforming. It needs this repository and Python 3.11 or later for the
commands; the implementation under test can be written in any language.

## 1. Obtain and check the archive

The corpus is the one ZIP archive under `conformance/` in this repository, which
`CONFORMANCE_LOCK.json` pins: `artifact` is its path, `bytes` its size, `sha256` its digest and
`corpus_id` its identity. The identity is derived from the archive's bytes: it is
`loquitur-conformance-` followed by the first 16 hexadecimal characters of the archive's SHA-256,
so the archive never contains its own identity and two archives with different bytes carry
different identities. From the root of a checkout:

```bash
python -c "import hashlib, json; lock = json.load(open('CONFORMANCE_LOCK.json')); data = open(lock['artifact'], 'rb').read(); digest = hashlib.sha256(data).hexdigest(); print(len(data) == lock['bytes'] and digest == lock['sha256'] and lock['corpus_id'] == 'loquitur-conformance-' + digest[:16])"
```

It prints `True`. An archive for which it prints anything else is not the pinned corpus.
`python tools/check_protocol_release.py --root .` checks the same pin, among other things, and
exits 0.

The archive is written by `tools/corpus_archive.py` as a pure function of its members: the same
members always give the same bytes, and the release gate refuses an archive that is not exactly
that build of the members it holds. The archive is not signed: its digest is recorded in this
repository, beside the archive, so it establishes that the bytes received are the bytes this
repository holds, and nothing about who wrote them.

## 2. Extract and validate it

```bash
python -c "import json, zipfile; zipfile.ZipFile(json.load(open('CONFORMANCE_LOCK.json'))['artifact']).extractall('../corpus')"
```

Every member lies under `loquitur-conformance/`, so the corpus root is
`../corpus/loquitur-conformance`. Paths below are relative to that root. Windows limits a path to
260 characters unless long paths are enabled, and some member paths are long: there, if the
extraction fails with `FileNotFoundError`, run it from a checkout whose path is short.

```bash
python tools/validate_corpus.py ../corpus/loquitur-conformance
```

It prints `corpus OK` and exits 0. `tools/validate_corpus.py` needs `jsonschema` and
`cryptography`. It checks what the corpus states about itself: that the content manifest lists every
file with its size and digest and nothing else, that each declared run is well formed, and that the
schema fixtures, canonicalization and signature vectors and bundle seals hold; run from this
repository, it also checks that the corpus's copies of the protocol's normative files equal this
repository's. It runs no implementation.

## 3. Layout

| path | what it is |
| --- | --- |
| `conformance-manifest.json` | the content manifest: every other file with its size and SHA-256, and the profiles, each naming its compatibility class and the files that exercise it |
| `protocol/` | byte-for-byte copies of the protocol's normative files the vectors are read against, at their path in this repository: `CRYPTOGRAPHIC_CAPABILITIES.json`, `VERIFICATION_VOCABULARIES.json`, `docs/specification/compatibility-classes.json`, the reason-code catalog with its schema under `docs/specification/reason-codes/`, and the schema of a registered vocabulary, `docs/specification/registered-vocabularies/schema.json` |
| `vectors/verify.json` | verification runs and their declared outcomes (§4.1) |
| `vectors/bundles/` | one directory per bundle, which a run names by directory name, `manifest.json` declaring the bundle runs (§4.2), and `SENTINEL_OUTSIDE_BUNDLE.txt`, the file outside every bundle root that one bundle's manifest declares |
| `vectors/inputs/` | inputs a run names instead of a bundle directory: archives, one of them clean and each of the rest that archive with the entries or bytes one reading of [`bundle-objects.md`](bundle-objects.md) §5 turns on; directories that contain a bundle; a directory that holds a bundle's members with its manifest stored under another spelling of `manifest.json`; and a regular file that is no archive at all |
| `vectors/link_*_registry_entry.json`, `vectors/authorization_*_registry_entry.json`, `vectors/authorization_*_trust_registry.json` | the registry entries and trust registries the runs name at the corpus root; the directories below hold the rest |
| `vectors/trust-roots/` | the trust-root documents a run names as `trust_root` |
| `vectors/version-gates/`, `vectors/algorithms/` | documents that carry a later version of their object, and signatures and keys of an algorithm or key type outside the verifier's allowlist |
| `vectors/schemas/` | the seven protocol schemas, byte for byte those of `docs/specification/schemas/` |
| `vectors/schema-valid/` | documents each schema accepts, and `expected.json` |
| `vectors/schema-negative/` | documents a schema rejects, and `manifest.json` |
| `vectors/canonicalization.json`, `vectors/canonicalization_unicode.json`, `vectors/jcs-numeric.json` | canonicalization vectors |
| `vectors/signature.json`, `vectors/signature_payload_version.json` | registry-entry signature vectors |
| `vectors/entry-signatures/`, `vectors/signature-step/`, `vectors/key-ids/` | registry entries and registries that ask what the signature step reads: a signature's spelling, the registry it is checked against, and how a key id is compared |
| `vectors/authorization/`, `vectors/verdict-grounds/`, `vectors/instants/` | registry entries and trust registries that ask which authorization status, committed verdict and evaluation time a run reaches |
| `vectors/receipt-contract/`, `vectors/entry-contract/`, `vectors/reason-surface/` | documents that ask what a receipt agrees with, what breaks an entry's contract, and what a run that reaches no conclusion reports |
| `vectors/free-strings/`, `vectors/member-names/`, `vectors/strict-parsing/` | documents that ask how a free string, a member name and a strictness rule of [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) are read |
| `vectors/cryptographic_capabilities.json`, `vectors/report-invariants.json` | declarations about the capability set and per-check results |
| `vectors/anchor-methods.json` | one signed registry entry with no anchor and under an anchor of each anchoring method, with one signing-message digest `H` ([`anchor-commitment.md`](anchor-commitment.md) §6) |
| `vectors/vocabularies/` | the corpus's own registered vocabularies (§4.1): `baseline/`, the version a run that names none is verified with, the other versions runs name, and `refused/`, documents a verifier refuses |
| `vectors/vocabulary/` | the registry entries and trust registries of the runs on registered vocabularies |
| `vectors/subject-ref-hash.json` | the construction of `subject_ref_hash` an issuer applies ([`registry-entry.md`](registry-entry.md), "Subject reference hash"), as one worked case |
| `vectors/additional-negatives/` | further runs, with `expected.json` (§4.2) |
| `vectors/summary-checks/` | verification summaries, and `expected.json`, the summary runs that check them against [`verdict-grounds.md`](verdict-grounds.md) (§4.1) |

The archive holds nothing else: no tools, tests, implementation code or copies of an
implementation's files. Two profiles the manifest declares, `public-object-projection-v1` and
`schema-generated-types-v1`, bind implementation artifacts rather than a verifier's
behavior, and name no corpus file.

## 4. What each vector file declares

| file | profile | cases | §6 |
| --- | --- | --- | --- |
| `vectors/verify.json` | `offline-verification-v1`, `registry-link-v1`, `trust-authorization-v1`, `registered-vocabularies-v1` | 1061 | binding |
| `vectors/schema-valid/expected.json` | `schema-validity-v1` | 9 | binding |
| `vectors/schema-negative/manifest.json` | `independent-conformance-oracle-v1` | 54 | binding |
| `vectors/canonicalization.json` | `canonical-json-v1` | 15 | binding |
| `vectors/canonicalization_unicode.json` | `canonical-json-v1` | 9 | binding |
| `vectors/jcs-numeric.json` | `independent-conformance-oracle-v1` | 14 | binding |
| `vectors/signature.json` | `registry-entry-signing-envelope-v2` | 1 | binding |
| `vectors/signature_payload_version.json` | `registry-entry-signing-envelope-v2` | 2 | binding |
| `vectors/anchor-methods.json` | `registry-entry-signing-envelope-v2` | 4 | binding |
| `vectors/additional-negatives/expected.json` | `registry-link-v1`, `trust-authorization-v1` | 13 | binding |
| `vectors/bundles/manifest.json` | none | 19 | binding |
| `vectors/summary-checks/expected.json` | `independent-conformance-oracle-v1` | 28 | binding |
| `vectors/cryptographic_capabilities.json` | `cryptographic-capability-matrix-v0.1` | 6 | not binding |
| `vectors/report-invariants.json` | `independent-conformance-oracle-v1` | 1 | not binding |
| `vectors/subject-ref-hash.json` | `independent-conformance-oracle-v1` | 1 | not binding |

### 4.1 The declared runs

`vectors/verify.json` is an object of runs keyed by name.
`vectors/additional-negatives/expected.json` and `vectors/bundles/manifest.json` hold further runs
as `cases`, each keyed by its `id`; a run is the same thing in all three, and §6 item 1 binds all
three alike.

A run names its input, either `bundle`, a directory under `vectors/bundles/`, or `input`, a path
under `vectors/` whose reading is itself the question: an archive, a directory containing a
bundle, a directory whose manifest is stored under another spelling of its name, or a regular
file that is no archive at all. It optionally names `registry_entry` and `trust_registry`, files
under `vectors/`, and the two inputs an operator supplies out of band: `trust_root`, a document
under `vectors/trust-roots/`, and `evaluation_time`, the operator's evaluation time as one instant
`YYYY-MM-DDTHH:MM:SSZ`. A run whose question is what one of those three paths names lists it under
`not_a_regular_file`: its path names nothing, or a directory, and is handed to the verifier as it is
([`report-contract.md`](report-contract.md) §4 and §5.3). A run whose `input` names nothing lists
`input` there too. A run whose `input`, `registry_entry` or `trust_registry` names nothing is
refused as a whole with `input_not_found` ([`report-contract.md`](report-contract.md) §5.3).

A run optionally names `vocabularies`, an object whose members are kinds of registered vocabulary
([`verification-vocabularies.md`](verification-vocabularies.md) §5) and whose values are paths of
registered vocabulary documents under `vectors/vocabularies/`. A run is verified with the document
it names for a kind, and with `vectors/vocabularies/baseline/` followed by the kind's name and
`.json` for a kind it names none of: the corpus's own version of that vocabulary, and never the one
a verifier embeds. A value registered after the corpus was built therefore changes no declared
outcome ([`verification-vocabularies.md`](verification-vocabularies.md) §9). A run whose document
the invocation refuses declares `{"exit_code": 64, "report": null}`
([`verification-vocabularies.md`](verification-vocabularies.md) §8).

`expected` declares the members a conformance comparison reads
([`report-contract.md`](report-contract.md) §2): `status`, `verdict`, `exit_code`, `reason`, which
is `outcome.reason`, `errors`, the error codes in the order
[`report-contract.md`](report-contract.md) §5.3 gives them, `checks_requested`,
`checks_established`, `review_reasons`, `evaluation_time`, `unsupported_version`, the members
`object` and `version` of that error where the run declares it
([`report-contract.md`](report-contract.md) §5.5), and `trust_registry`, the three statuses of that
member, or `null` where the run evaluates no registry. A declared `null` is compared like any other
value. `informative_checks` is not a member of `expected`: a run that records it declares it beside
`expected`, inside the run, and not every run does. It holds the eleven per-check results, which
[`report-contract.md`](report-contract.md) §2 makes informative; they are recorded rather than
compared.

Two declarations have another shape. A run the invocation refuses declares
`{"exit_code": 64, "report": null}`: the refusal happens before any evidence is read, so there is
no report, and no reason surface to declare ([`report-contract.md`](report-contract.md) §4). A run
whose outcome depends on which input a reader accepts declares `expected_by_intake` instead of
`expected`, with one outcome under `archive` and one under `directory_only`. A verifier's intake is
a property of the verifier ([`report-contract.md`](report-contract.md) §5.3): it reproduces the
outcome of the intake it declares, the same intake on every such run, and a report that reproduces
only the other intake's outcome does not conform. `intake` names the readers a declaration is for,
and is `any` for every run that declares one outcome.

A run whose answer depends on the interface rather than on the verifier declares the answer of a
command line beside `expected`, as `expected_command_line`, in either shape above, such as
`{"exit_code": 64, "report": null}` for an invocation [`report-contract.md`](report-contract.md) §4
refuses on a command line and answers with a report from a library interface. A command line
reproduces `expected_command_line` where a run declares it, and every other interface reproduces
`expected`.

`surface` names what a run exercises: `verify`, a verification of the named input, which is what a
run without the member exercises; or `summary`, a check of one verification summary against the
rules of [`verdict-grounds.md`](verdict-grounds.md). A summary run names `summary`, a document under
`vectors/`, and declares `expected` as `{"violated_rules": [...]}`: the rules of
[`verdict-grounds.md`](verdict-grounds.md) §3 the document violates, by their identifiers `VG-1` to
`VG-7`, in rule order, with the evaluation order of [`verdict-grounds.md`](verdict-grounds.md) §5,
so that a violation of `VG-1` or `VG-2` is the only rule it lists. `[]` declares a summary that
satisfies every rule. A summary run names no input, registry entry, trust registry, trust root or
evaluation time, and the members of a verification's declared outcome do not apply to it.

A run's outermost check is the last check its inputs request
([`verification-checks.md`](verification-checks.md)), and the table counts it there, over every run
of the three files: `vectors/verify.json`, `vectors/additional-negatives/expected.json` and
`vectors/bundles/manifest.json`.

| outermost check | runs |
| --- | --- |
| `integrity`: a bundle alone | 431 |
| `link`: a registry entry and no trust registry | 226 |
| `authorization`: a trust registry | 436 |

`authorization_reason_trust_without_entry`, `authorization_reason_trust_malformed_without_entry` and
`authorization_reason_trust_without_entry_after_bundle_error` are the three authorization runs that
supply a trust registry with no registry entry, which is the question they ask. Each declares
`trust_registry_requires_registry_entry`, the answer a library interface gives, after every error
the bundle gives: the first two run a bundle that gives none, and the third a bundle whose manifest
is refused, so it declares `manifest_verification_failed` first
([`report-contract.md`](report-contract.md) §4 and §5.3). [`report-contract.md`](report-contract.md)
§4 makes that same invocation a refusal on a command line, with exit 64 and no report, and each of
the three declares that answer as `expected_command_line`: a command line reproduces it, and a
library interface reproduces `expected`.

Where no trust root is pinned, `OFFLINE_REVIEW` is the most an authorization run reaches
([`trust-root.md`](trust-root.md) §2); one that fails a check before the registry's root is weighed
reaches `OFFLINE_FAIL`. A run that a version gate stops reaches `UNSUPPORTED_VERSION`, which is no
evidence outcome ([`report-contract.md`](report-contract.md) §3), and a run refused as a whole, such
as one whose trust registry path names nothing, reaches `HOST_FAILURE`
([`report-contract.md`](report-contract.md) §5.3). An authorization run reaches `OFFLINE_OK` with
exit 0 only where a trust root is supplied and authenticates the registry's root, and an evaluation
time is supplied ([`trust-registry-authorization.md`](trust-registry-authorization.md) §2).

### 4.2 The other binding files

- `vectors/schema-valid/expected.json`: `cases`, each naming a `fixture` under
  `vectors/schema-valid/` and a `schema` under `vectors/schemas/`, with `expected` `valid`.
- `vectors/schema-negative/manifest.json`: `cases`, each naming a `fixture` under
  `vectors/schema-negative/` and a `schema`, with `expected_valid` `false`. `expected_keyword` and
  `expected_path_prefix` record the first error one JSON Schema validator reports.
- `vectors/canonicalization.json`: `canonicalize_ok`, each an `input` with its RFC 8785 bytes as
  `canonical_utf8` and `canonical_hex` and its digest as `sha256`; and `canonicalize_reject`, each
  an `input` canonicalization refuses
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §1).
- `vectors/canonicalization_unicode.json`: an array, each a `value` with its canonical bytes as
  `canonical_utf8_hex`.
- `vectors/jcs-numeric.json`: `cases`, each a number given as `value`, or as `expression` for
  negative zero (`-0`), with its RFC 8785 serialization as `expected`; and `reject`, each a value
  canonicalization refuses, written as the JSON text a reader is handed because the non-finite
  spellings are not JSON values. "Input strictness" of
  [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) refuses them: rule 3 the
  three non-finite spellings, rule 2 an integer-valued number beyond 2^53 - 1.
- `vectors/signature.json`: one signed registry entry, `signed_entry`. It declares the domain
  prefix, the signing envelope built from the entry, the exact signing message as
  `signing_message_hex` and its digest as `signing_payload_sha256`
  ([`signing-envelope-v2.md`](signing-envelope-v2.md)); the signature verifies under
  `public_key_hex`. `tampered_entry` differs from it in one field and carries the same signature,
  which does not verify: `expected.tampered_status` is `SIGNATURE_INVALID`.
- `vectors/signature_payload_version.json`: two signed entries. An entry naming a well-formed later
  signing payload (`unknown_payload_entry`), whose run stops at the version gate of the signing
  payload: `unknown_payload_expected_error` declares the error `unsupported_version` with its
  `object` `signing_payload` and its `version` ([`report-contract.md`](report-contract.md) §5.5).
  And a v2 entry whose `payload_id` and `payload_version` were removed
  (`v2_metadata_stripped_entry`), which breaks the entry's contract:
  `v2_metadata_stripped_expected_error` is `registry_entry_contract_violation`. `automatic_fallback`
  is `false`, and no member declares a legacy payload or outcome.
- `vectors/anchor-methods.json`: `cases`, each one registry entry: the entry of `signature.json`
  with `anchor` `null` and with an anchor of each method the corpus's baseline vocabulary registers.
  Every case's signing message has the digest `signing_payload_sha256`, and its signature verifies
  under `public_key_hex`: the anchor is outside the signing payload, so `H` is one whatever the
  method ([`anchor-commitment.md`](anchor-commitment.md) §1 and §6).
- `vectors/additional-negatives/expected.json` and `vectors/bundles/manifest.json`: runs, in the
  shape §4.1 gives. A case of the second carries `expectation`, a sentence naming what the bundle
  deviates in; it is prose beside the declaration and nothing compares it.

The signature files name the signature statuses of
[`trust-registry-authorization.md`](trust-registry-authorization.md) §8, which is the closed
vocabulary a declaration may use. A status naming what checking an entry's signature found without a
trust registry is one of those; the corpus declares no label of its own.

## 5. How the reference verifiers are run over the corpus

The verifiers are separate repositories, `loquitur-verify-py` and `loquitur-verify-ts`, published
after this one. Until they are, the commands of this section cannot be run from this repository
alone; the pinned corpus and its lock can still be checked with the commands of sections 1 and 2.

The corpus's gates run each reference verifier through an adapter, a small program that turns
one request into one report. The adapters are not part of the protocol, and a third implementation
needs neither of them. They are described here as they are implemented, so that a result can be
reproduced and a third implementation can offer the same interface.

**Python**, `tools/conformance_adapter.py` of loquitur-verify-py, with the `loquitur-verify`
distribution installed in the interpreter first on `PATH`. Arguments:
`--bundle PATH`, and optionally `--registry-entry PATH`, `--trust-registry PATH`,
`--trust-root PATH`, `--evaluation-time TIMESTAMP`, `--asset-type-vocabulary PATH`,
`--workflow-vocabulary PATH` and `--anchoring-method-vocabulary PATH`. It writes the report as one
line of JSON with sorted keys to standard output and exits 0 whenever it wrote a report, whatever
the report's status; the report carries its own `exit_code`. Given `--summary PATH` alone, it checks
the one verification summary at PATH against [`verdict-grounds.md`](verdict-grounds.md) and writes
`{"violated_rules": [...]}` the same way (§4.1). It refuses an invocation that names a trust root or
an evaluation time without a trust registry, or a value [`report-contract.md`](report-contract.md)
§4 refuses, by exiting 64 and writing no report; a trust-root document the host fails to read is
reported, not refused. It runs the verifier's library interface, so a trust registry without a
registry entry gives the report [`report-contract.md`](report-contract.md) §4 states for a library,
not exit 64.

```bash
python ../loquitur-verify-py/tools/conformance_adapter.py --bundle ../corpus/loquitur-conformance/vectors/bundles/link_valid_bundle --registry-entry ../corpus/loquitur-conformance/vectors/authorization_valid_registry_entry.json --trust-registry ../corpus/loquitur-conformance/vectors/authorization_valid_trust_registry.json --evaluation-time 2026-05-20T00:00:00Z
```

It prints a report whose `status` is `OFFLINE_REVIEW`, `verdict` `REVIEW`, `exit_code` `2` and
`outcome.reason` `trust_registry_root_not_pinned`, as `verify.json` declares for
`authorization_evaluated_inside_the_registry_window`.

**TypeScript**, `scripts/conformance-adapter.mjs` of loquitur-verify-ts, run with Node.js. It
imports four compiled modules of loquitur-verify-ts, `verify.js`, `verify-core.js`,
`protocol-input.js` and `verdict-grounds.js`, from the directory named by the environment variable
`LOQUITUR_CONFORMANCE_BUILD`, or from `.conformance-build/` in the package root. The modules sit at
the top of that directory, so the sources of `src/` are compiled with `src` as their root. From the
package root, after `npm ci`, this command builds them into `.conformance-build/`:

```text
npx tsc $(find src -name '*.ts' ! -name '*.d.ts') --target ES2022 --module NodeNext --moduleResolution NodeNext --rootDir src --outDir .conformance-build --skipLibCheck --noCheck
```

`--noCheck` only emits; the package's `npm run typecheck` is its type check. The package's own
`npm run build` writes to `dist/` under another root and does not produce this layout. The adapter reads one JSON request from standard input and writes one JSON response to
standard output:

| request | response |
| --- | --- |
| `{"operation": "verify_bundle", "bundle": PATH, "registryEntry": DOCUMENT, "trustRegistry": DOCUMENT, "trustRoots": DOCUMENT, "evaluationTime": TIMESTAMP, "vocabularies": {KIND: DOCUMENT}}`, all but `bundle` optional; `registryEntryUnread`, `trustRegistryUnread` or `trustRootsUnread`, each `"nothing_found"`, `"no_regular_file"` or `"read_failed"`, in place of the document it names | the whole report the verifier returns |
| `{"operation": "check_summary", "summary": DOCUMENT}` | `{"operation": "check_summary", "violated_rules": [...]}` (§4.1) |
| `{"operation": "parse_registry", "cases": [{"id": ID, "input": DOCUMENT}]}`, or `"parse_trust"` | `{"operation": ..., "results": [{"id": ID, "accepted": BOOLEAN, "errors": [...]}]}` |

`bundle` is the path of a bundle directory; `registryEntry`, `trustRegistry` and `trustRoots` are
the documents themselves, not paths. Where the host found no document at a path, it names what it
found instead, as [`report-contract.md`](report-contract.md) §4 requires of a library interface:
`nothing_found` for a path at which nothing is found, `no_regular_file` for a directory or anything
else that is not a regular file, and `read_failed` for a regular file it failed to read. The adapter
passes the verifier's own three values for them, and a request naming both a document and such a
fact for the same input ends the process with an error. A request whose options are refused ends the
process with exit 64 and no response. Those refusals are the ones
[`report-contract.md`](report-contract.md) §4 gives a library interface: trust roots whose path
names no regular file or that break [`trust-root.md`](trust-root.md) §3, an evaluation time that is
empty or is not a calendar instant of the form `YYYY-MM-DDTHH:MM:SSZ`, and a registered vocabulary
document refused under [`verification-vocabularies.md`](verification-vocabularies.md) §8. Both
adapters pass a run's `vocabularies`, and the baseline documents of §4.1 for a kind the run names
none of. The Python adapter refuses those as well and, as the command line does, refuses a trust
root or an evaluation time supplied without a trust registry besides; every run this corpus declares
refused is of the first kind, so both adapters refuse the same 63. When verification throws, the
response is `{"status": "ADAPTER_THREW", "verdict": "ADAPTER_THREW", "exit_code": null, "checks":
{}, "error": MESSAGE}`, so that a crash is recorded rather than read as a verdict. Any other
operation ends the process with an error and no response.

## 6. What counts as conforming

An implementation conforms to the corpus `CONFORMANCE_LOCK.json` pins when it reproduces every
binding declaration below.

1. **The declared runs**, in `vectors/verify.json`,
   `vectors/additional-negatives/expected.json` and `vectors/bundles/manifest.json`. For every
   run, verifying the named input with the named registry entry, trust registry, trust root and
   evaluation time produces the declared `status`, `verdict`, `exit_code`, `reason`, error codes,
   checks requested and established, review reasons and evaluation time, and the three
   trust-registry statuses. A run that declares `trust_registry` as `null` is reproduced only by a
   report whose `trust_registry` is `null`: the declared `null` is part of the compared surface. The
   declared per-check results are informative and are not compared
   ([`report-contract.md`](report-contract.md) §2 and §6). A run declaring a refusal is reproduced
   by writing no report and exiting with the declared code. A verifier declares one intake,
   `archive` or `directory_only`, as a property of the verifier
   ([`report-contract.md`](report-contract.md) §5.3), and reproduces every run that declares one
   outcome per intake with the outcome of that intake, the same intake for every run. A verifier
   that runs as a process also exits with the declared `exit_code`, `4` and `5` included.
2. **`vectors/schema-negative/manifest.json`.** Every fixture is rejected by its schema.
   `expected_keyword` and `expected_path_prefix` are not compared: another validator may report
   another first error for the same rejection.
3. **`vectors/schema-valid/expected.json`.** Every fixture is accepted by its schema.
4. **Canonicalization.** Every value of `vectors/canonicalization.json`,
   `vectors/canonicalization_unicode.json` and `vectors/jcs-numeric.json` canonicalizes to exactly
   the declared bytes and digest, and every value they declare refused is refused.
5. **Signatures.** For `vectors/signature.json`, the implementation builds exactly the declared
   envelope, message and digest from `signed_entry`; the signature verifies over that message
   under `public_key_hex`; and it does not verify for `tampered_entry`. For
   `vectors/signature_payload_version.json`, the entry stripped of its payload metadata breaks the
   entry's contract, the entry naming a well-formed later payload is an unsupported version, and
   nothing falls back to another payload. The corpus declares no outcome for a legacy opt-in: the
   protocol defines no earlier signing payload, and no verifier offers such an opt-in
   ([`signing-envelope-v2.md`](signing-envelope-v2.md), "Legacy migration policy").

These files are not binding in this corpus:

- `vectors/report-invariants.json`: it constrains a per-check result, which is informative.
- `vectors/cryptographic_capabilities.json`: its cases restate the closed capability set, which
  [`cryptographic-capabilities.md`](cryptographic-capabilities.md) makes binding on every verifier
  directly, and the schema vectors exercise.
- `vectors/subject-ref-hash.json`: it pins a construction an issuer applies, which no check of a
  verifier reads.

Conforming to the corpus is not conforming to the protocol. The vectors exercise part of what the
specification requires, and an implementation that reproduces every binding declaration and breaks
a rule no vector exercises does not conform.

No run declares `bundle_member_name_invalid`. That error answers a directory listing that holds
a name that is not a portable member name, or two names that conflict
([`bundle-objects.md`](bundle-objects.md) §1), and such a listing cannot travel in the archive,
whose member names are portable by construction. The rule binds through the specification alone.

**What the run format cannot express.** A run names files the archive carries. It cannot stage a
state of the host: a symbolic link, a junction or another reparse point, a file the host refuses
to read, a device, a named pipe or a socket, a missing network share, an alternate data stream, or
a fault of the verifier.
The rows of [`report-contract.md`](report-contract.md) §5.3 that answer those states
(`unsafe_bundle_member`, `filesystem_error`, `archive_load_failed`, `bundle_inventory_failed`,
`manifest_read_failed`, `p1_read_failed`, `envelope_read_failed`, `registry_link_read_failed`,
`trust_registry_read_failed`, `trust_root_read_failed` and `internal_error`) bind through the
specification alone in this corpus, and so does every refusal that only a command line makes
([`report-contract.md`](report-contract.md) §4.1), and the process exit that `--accept-review`
changes ([`report-contract.md`](report-contract.md) §4), which leaves the report unchanged. These
are known limitations of the corpus, not of the rules. A run over a path that names nothing
(`input_not_found`) and a run with a refused evaluation time (exit `64`) are expressible, and the
corpus declares them.

**Summary checks.** An implementation that checks verification summaries reproduces, for every
summary run of `vectors/summary-checks/expected.json`, the declared `violated_rules` (§4.1): the
rules VG-1 to VG-7 of [`verdict-grounds.md`](verdict-grounds.md) the summary breaks, in rule order.
The change, coverage and lineage summaries are bound through their schemas (items 2 and 3).

**Outside conformance in this version.** No declaration of this corpus binds a narrative renderer.

## 7. Comparing a verifier with the declared runs

The reference verifiers are separate repositories. The comparison below needs only the script and
the archive, and runs against any verifier you supply; where `loquitur-verify-py` is not available
next to this repository, the command that names it cannot be run from here alone.

The script below runs every declared run of `vectors/verify.json`,
`vectors/additional-negatives/expected.json` and `vectors/bundles/manifest.json` through a command
that follows the argument contract of the Python adapter (§5): it takes `--bundle`,
`--registry-entry`, `--trust-registry`, `--trust-root`, `--evaluation-time` and the three
registered-vocabulary options, and writes one report as JSON to standard output. A run of
`verify.json` is reported by its name, and a case of the other two files by the file and its `id`,
as `bundles/manifest.json#link-valid-baseline`. The script compares the members §6 item 1 compares,
a declared `trust_registry` of `null` included, and counts a run whose command writes no report,
or JSON that is not a report object, as a disagreement.

`--intake` names the verifier's intake, `archive` or `directory_only`, and the script compares
every run that declares one outcome per intake with the outcome of that intake.

With `--summaries` the script also runs every summary run (§4.1) of
`vectors/summary-checks/expected.json` through the same command, as `--summary PATH`, and
compares the `violated_rules` member of the JSON object the command writes with the declared
list. Without it, summary runs are not compared, and a command that checks no summary can be
compared on the verification runs alone.

The process exit status is compared where a run declares a refusal, which is a declaration about
the exit status and the silence, and on every run when `--process-exit` is given. The Python
adapter exits 0 whenever it wrote a report, and a command line that follows
[`report-contract.md`](report-contract.md) §4 exits with the report's `exit_code`, so either kind of
command can be compared: an adapter without `--process-exit`, and a command line with it, which
compares its exit status with the declared `exit_code`, `4` and `5` included. With `--process-exit`,
a run that declares `expected_command_line` is compared with that declaration instead of `expected`,
because the command is then a command line. The three runs of §4.1 that supply a trust registry with
no registry entry declare it: [`report-contract.md`](report-contract.md) §4 makes that invocation a
refusal on a command line and an ordinary report from a library interface, so a command line that
refuses them agrees, and one that writes a report for them does not.

The first word of the command is looked up on `PATH`, as a shell looks it up: on Windows a program
name handed straight to the operating system is looked up beside the interpreter running the script
first, which is not always the interpreter the command means. Save the script as
`compare_verify_vectors.py`:

```python
import json
import shutil
import subprocess
import sys
from pathlib import Path

USAGE = "usage: compare_verify_vectors.py [--process-exit] [--summaries] --intake archive|directory_only CORPUS COMMAND..."
arguments = sys.argv[1:]
flags = set()
while arguments[:1] in (["--process-exit"], ["--summaries"]) and arguments[0] not in flags:
    flags.add(arguments.pop(0))
process_exit, summaries = "--process-exit" in flags, "--summaries" in flags
if len(arguments) < 4 or arguments[0] != "--intake" or arguments[1] not in ("archive", "directory_only"):
    sys.exit(USAGE)
intake, corpus, command = arguments[1], Path(arguments[2]), arguments[3:]
program = shutil.which(command[0])
if program is None:
    sys.exit(f"{command[0]} is not on PATH")
command = [program, *command[1:]]
vectors = corpus / "vectors"
COMPARED = ("status", "verdict", "exit_code", "reason", "errors", "checks_requested",
            "checks_established", "review_reasons", "evaluation_time", "unsupported_version")
STATUSES = ("authorization_status", "signature_status", "trust_registry_root_signature_status")


def declared_runs():
    """Every run of the three files section 6 item 1 binds, under the name it is reported by."""
    yield from json.loads((vectors / "verify.json").read_text(encoding="utf-8")).items()
    for rel in ("additional-negatives/expected.json", "bundles/manifest.json"):
        for case in json.loads((vectors / rel).read_text(encoding="utf-8"))["cases"]:
            yield f"{rel}#{case['id']}", case
    if summaries:
        rel = "summary-checks/expected.json"
        for case in json.loads((vectors / rel).read_text(encoding="utf-8"))["cases"]:
            yield f"{rel}#{case['id']}", case


def surface(report):
    """The members of a report that section 6 item 1 compares."""
    outcome = report.get("outcome") or {}
    errors = report.get("errors") or []
    gate = next((error for error in errors if error.get("code") == "unsupported_version"), None)
    registry = report.get("trust_registry")
    return {
        "status": report.get("status"),
        "verdict": report.get("verdict"),
        "exit_code": report.get("exit_code"),
        "reason": outcome.get("reason"),
        "errors": [error.get("code") for error in errors],
        "checks_requested": report.get("checks_requested"),
        "checks_established": report.get("checks_established"),
        "review_reasons": report.get("review_reasons"),
        "evaluation_time": report.get("evaluation_time"),
        "unsupported_version": None if gate is None else {"object": gate.get("object"), "version": gate.get("version")},
        "trust_registry": registry if registry is None else {status: registry.get(status) for status in STATUSES},
    }


def differences(expected, actual):
    """Every member the run declares and the report does not reproduce."""
    out = [
        f"{member} is {actual[member]!r}, declared {expected[member]!r}"
        for member in COMPARED
        if member in expected and actual[member] != expected[member]
    ]
    if "trust_registry" in expected:
        declared, found = expected["trust_registry"], actual["trust_registry"]
        if declared is None or found is None:
            # A declared null is compared too: a report that evaluated a registry does not agree with it.
            if declared != found:
                out.append(f"trust_registry is {found!r}, declared {declared!r}")
        else:
            out += [
                f"trust_registry.{status} is {found.get(status)!r}, declared {value!r}"
                for status, value in declared.items()
                if found.get(status) != value
            ]
    return out


runs = list(declared_runs())
disagreements = 0
for name, run in runs:
    if run.get("surface", "verify") == "summary":
        # A summary run checks one verification summary: the declaration is the rules it violates.
        result = subprocess.run([*command, "--summary", str(vectors / run["summary"])], capture_output=True, encoding="utf-8")
        try:
            found = json.loads(result.stdout).get("violated_rules")
        except (json.JSONDecodeError, AttributeError):
            found = f"no result; the command exited {result.returncode}: {result.stderr.strip()[-300:]}"
        if found != run["expected"]["violated_rules"]:
            disagreements += 1
            print(f"{name}: violated_rules is {found!r}, declared {run['expected']['violated_rules']!r}")
        continue
    # A run names a bundle directory, or an input whose reading is itself the question.
    target = vectors / "bundles" / run["bundle"] if "bundle" in run else vectors / run["input"]
    argv = [*command, "--bundle", str(target)]
    for option, member in (
        ("--registry-entry", "registry_entry"),
        ("--trust-registry", "trust_registry"),
        ("--trust-root", "trust_root"),
    ):
        if member in run:
            argv += [option, str(vectors / run[member])]
    if "evaluation_time" in run:
        argv += ["--evaluation-time", run["evaluation_time"]]
    # The vocabulary a run names for a kind, else the corpus's baseline for it (section 4.1).
    named = run.get("vocabularies", {})
    for kind in ("asset_type", "workflow", "anchoring_method"):
        document = vectors / named[kind] if kind in named else vectors / "vocabularies" / "baseline" / f"{kind}.json"
        if kind in named or document.is_file():
            argv += [f"--{kind.replace('_', '-')}-vocabulary", str(document)]
    result = subprocess.run(argv, capture_output=True, encoding="utf-8")

    # A run whose outcome depends on the reader declares one outcome per intake. The verifier's
    # intake is a property of the verifier, so the same declared intake is compared on every run.
    expected = run["expected"] if "expected" in run else run["expected_by_intake"][intake]
    if process_exit and "expected_command_line" in run:
        # A command line answers some invocations differently from a library (section 4.1).
        expected = run["expected_command_line"]
    if expected.get("report", False) is None:
        # A refused invocation reads no evidence, so there is no report and no reason surface to
        # compare: the declaration is the exit code and the silence. A command that writes a report
        # and then exits with that code has not refused.
        if result.stdout.strip() or result.returncode != expected["exit_code"]:
            disagreements += 1
            print(f"{name}: declared a refusal with exit {expected['exit_code']}; the command exited"
                  f" {result.returncode} and wrote {len(result.stdout)} characters")
        continue
    try:
        found = differences(expected, surface(json.loads(result.stdout)))
    except (json.JSONDecodeError, AttributeError, TypeError):
        # Output that is not JSON, or JSON that is not a report object (null, an array, error
        # codes as plain strings), is no report.
        disagreements += 1
        print(f"{name}: no report; the command exited {result.returncode}: {result.stderr.strip()[-300:]}")
        continue
    if process_exit and result.returncode != expected["exit_code"]:
        found.append(f"the process exited {result.returncode}, declared {expected['exit_code']}")
    for difference in found:
        disagreements += 1
        print(f"{name}: {difference}")
print(f"{len(runs)} runs, {disagreements} disagreements on the reason surface")
sys.exit(1 if disagreements else 0)
```

Run it against the Python reference verifier (a separate repository; where it is not available,
run it against your own implementation), with loquitur-verify installed in the interpreter
first on `PATH`, such as an activated virtual environment:

```bash
python compare_verify_vectors.py --summaries --intake archive ../corpus/loquitur-conformance python ../loquitur-verify-py/tools/conformance_adapter.py
```

It prints `1121 runs, 0 disagreements on the reason surface` and exits 0 against the Python
reference verifier. Replace the
command after the corpus path with one that runs your implementation, and give `--process-exit`
when that command exits with the report's `exit_code`.

## 8. Independent conformance oracle

Loquitur conformance is not established by implementation agreement alone.
The canonical corpus uses independent schema, canonical-JSON and report-invariant
oracles, then observes Python and TypeScript consumers through black-box adapters.
A comparison of verification reports reads the members [`report-contract.md`](report-contract.md) §2
makes normative: status, verdict, exit code, `outcome.reason`, the ordered error codes, the checks
requested and established, the review reasons, the evaluation time and, when the trust registry was
evaluated, the authorization, signature and root signature statuses. The per-check results are
informative and are not compared as a condition of conformance. Sections 1 to 7 say how a third
implementation obtains and runs the corpus, and which of its declarations it must reproduce.

The profile `independent-conformance-oracle-v1` is of the compatibility class `semantic-exact`: the
schema-negative, canonical-number and summary runs it names are binding (§4), so they fix expected
outcomes, and a change to one of them is a change to what a conforming implementation does, not a
change to assurance material alone.

Known disagreements are blocking release conditions. A known disagreement may be carried only as
an entry of a remediation baseline: a list kept with the corpus source that names each disagreement
between a consumer and the corpus exactly, until a correction removes it. An unexpected
disagreement or a silently removed disagreement fails closed. Expected outcomes require
protocol-governance review and may not be generated solely by an implementation under test.

Two terms of this section, and of `CONFORMANCE_ORACLE_POLICY.json`, are defined here. An
independent oracle is one written from the specification, without reading or importing the
implementations it judges. Independent review is review by the role `loquitur-protocol-governance`
that `GOVERNANCE.md` defines. One maintainer holds that role today and also maintains every
implementation, so no review is yet independent of that maintainer.

No known consumer disagreement is recorded, and the release says so in the `status` of
`PROTOCOL_RELEASE.json`. That is not a claim of conformance beyond what the vectors exercise. An
unexpected disagreement, and the silent disappearance of a recorded one, both fail closed.
