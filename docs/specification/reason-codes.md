# Reason-code register

Status: normative.

`loquitur.reason_codes.v1` is the closed vocabulary of machine-readable grounds that a
verification outcome cites. This document is the register for it: it enumerates every code
with its category and severity, and states the rules that bind a code to a verdict. The
register is what an implementer reads the codes from; everything below it is the rule set that
the schemas' `enum` cannot express.

> **Non-normative note on citations.** The one citation of the form `<module>.py::<name>` in
> this document names the module docstring of `src/loquitur/verify/narrative.py` in
> `loquitur-verify-py`, the reference implementation, which is a separate repository and not part
> of this one. It resolves in release `0.1.0` of `loquitur-verify-py`, once that repository is
> published, and names no line, and this repository's tests check it against the source of a
> `loquitur-verify-py` checkout placed beside it, and that checkout's version against the release
> named here. The citation is evidence, not part of the protocol.

## 1. What a reason code is for

A verdict alone is insufficient. `PASS` and `FAIL` are conclusions; the reason codes are the
grounds. A protocol-grade verification output carries the codes, the policy identity and the
object-version metadata together, so that a reviewer can see not only what was concluded but
what it was concluded from, and so that two implementations reaching the same conclusion can
be compared on the grounds and not only on the word.

Three public objects carry them, and in each the field is required:

| Object | Field | Vocabulary pin |
| --- | --- | --- |
| `verification_summary` | `reason_codes` | `reason_code_vocabulary_version`, `const` `loquitur.reason_codes.v1` |
| `registry_entry` | `reason_codes` | `reason_code_catalog_version`, `const` `loquitur.reason_codes.v1` |
| `verification_receipt` | `reason_codes` | `reason_code_vocabulary_version`, `const` `loquitur.reason_codes.v1` |

In the three schemas `reason_codes` is an array of strings with `uniqueItems: true`, `minItems: 1`,
and an `enum` on its items that is exactly the register below.

## 2. The register

<!-- BEGIN GENERATED REGISTER -->

Vocabulary `loquitur.reason_codes.v1`, catalog version `2.0.0`: **57 codes across 11 categories**.

| Category | Codes | info | warn | review | fail |
| --- | ---: | ---: | ---: | ---: | ---: |
| `integrity` | 12 | 1 | 1 | 0 | 10 |
| `coverage` | 2 | 1 | 0 | 1 | 0 |
| `freshness` | 6 | 1 | 5 | 0 | 0 |
| `conflict` | 1 | 0 | 0 | 1 | 0 |
| `policy` | 5 | 0 | 1 | 4 | 0 |
| `evidence` | 1 | 1 | 0 | 0 | 0 |
| `offline` | 12 | 0 | 1 | 10 | 1 |
| `materiality` | 1 | 0 | 1 | 0 | 0 |
| `valuation_crosscheck` | 4 | 0 | 3 | 1 | 0 |
| `authorization` | 11 | 1 | 0 | 3 | 7 |
| `vocabulary` | 2 | 0 | 0 | 1 | 1 |
| **Total** | **57** | **5** | **12** | **21** | **19** |

### 2.1 `integrity` — 12 codes

| Code | Severity |
| --- | --- |
| `BUNDLE_EXTRA_FILES` | `warn` |
| `INTEGRITY_CHECK_FAILED` | `fail` |
| `INTEGRITY_OFFLINE_CANONICALIZATION_FAILED` | `fail` |
| `INTEGRITY_OFFLINE_ENVELOPE_LINKS_MISMATCH` | `fail` |
| `INTEGRITY_OFFLINE_ENVELOPE_SHA_MISMATCH` | `fail` |
| `INTEGRITY_OFFLINE_EXTRA_FILES_STRICT` | `fail` |
| `INTEGRITY_OFFLINE_FAIL` | `fail` |
| `INTEGRITY_OFFLINE_INPUT_HASH_MISMATCH` | `fail` |
| `INTEGRITY_OFFLINE_MANIFEST_FILE_MISMATCH` | `fail` |
| `INTEGRITY_OFFLINE_MANIFEST_SHA_MISMATCH` | `fail` |
| `INTEGRITY_OFFLINE_SCHEMA_INVALID` | `fail` |
| `INTEGRITY_OK` | `info` |

### 2.2 `coverage` — 2 codes

| Code | Severity |
| --- | --- |
| `REQUIRED_CLAIMS_PRESENT` | `info` |
| `UNSUPPORTED_KEY_CLAIM` | `review` |

### 2.3 `freshness` — 6 codes

| Code | Severity |
| --- | --- |
| `FRESHNESS_OK` | `info` |
| `FRESHNESS_P1_TIMESTAMP_OOW` | `warn` |
| `FRESHNESS_WARNING` | `warn` |
| `MARK_ASOF_UNPARSEABLE` | `warn` |
| `MARK_STALE` | `warn` |
| `P1_TIMESTAMP_OUT_OF_WINDOW` | `warn` |

### 2.4 `conflict` — 1 code

| Code | Severity |
| --- | --- |
| `CONFLICTING_EVIDENCE_DETECTED` | `review` |

### 2.5 `policy` — 5 codes

| Code | Severity |
| --- | --- |
| `METHOD_BINDING_MISSING` | `review` |
| `MISSING_MARK_FIELDS` | `review` |
| `MISSING_REQUIRED_INPUTS` | `review` |
| `NEEDS_REVIEW` | `review` |
| `POLICY_BUNDLE_EXTRA_FILES` | `warn` |

### 2.6 `evidence` — 1 code

| Code | Severity |
| --- | --- |
| `REQUIRED_EVIDENCE_PRESENT` | `info` |

### 2.7 `offline` — 12 codes

| Code | Severity |
| --- | --- |
| `COMPLETENESS_OFFLINE_CHECKS_SKIPPED` | `review` |
| `COMPLETENESS_OFFLINE_MATERIAL_MISSING` | `review` |
| `COMPLETENESS_OFFLINE_MISSING_CANONICAL_INPUT` | `review` |
| `COMPLETENESS_OFFLINE_MISSING_MANIFEST` | `review` |
| `OFFLINE_CANONICAL_INPUT_MISSING` | `review` |
| `OFFLINE_INPUT_HASH_NOT_VERIFIED` | `review` |
| `OFFLINE_MANIFEST_MISSING` | `review` |
| `OFFLINE_MATERIAL_MISSING` | `review` |
| `OFFLINE_REPLAY_FAILED` | `fail` |
| `OFFLINE_REPLAY_REVIEW` | `review` |
| `OFFLINE_REPLAY_SKIPPED` | `review` |
| `OFFLINE_REPLAY_WARN` | `warn` |

### 2.8 `anchoring` — reserved

The category name is reserved. It holds no code in this version (section 3).

### 2.9 `materiality` — 1 code

| Code | Severity |
| --- | --- |
| `MATERIAL_CHANGE_DETECTED` | `warn` |

### 2.10 `valuation_crosscheck` — 4 codes

| Code | Severity |
| --- | --- |
| `MARK_FAR_OUTSIDE_RANGE` | `review` |
| `MARK_NEAR_BOUNDARY` | `warn` |
| `MARK_OFFSET_FROM_MIDPOINT` | `warn` |
| `MARK_OUTSIDE_RANGE` | `warn` |

### 2.11 `authorization` — 11 codes

| Code | Severity |
| --- | --- |
| `AUTHORIZATION_ISSUER_KEY_EXPIRED` | `review` |
| `AUTHORIZATION_ISSUER_KEY_NOT_YET_EFFECTIVE` | `review` |
| `AUTHORIZATION_ISSUER_KEY_REVOKED` | `fail` |
| `AUTHORIZATION_ISSUER_KEY_SUSPENDED` | `fail` |
| `AUTHORIZATION_ISSUER_NOT_RECOGNISED` | `fail` |
| `AUTHORIZATION_SCOPE_MISMATCH` | `fail` |
| `AUTHORIZATION_SIGNATURE_NOT_VERIFIED` | `fail` |
| `AUTHORIZATION_SIGNING_METHOD_UNSUPPORTED` | `fail` |
| `AUTHORIZATION_TRUST_MATERIAL_OUTSIDE_VALIDITY_WINDOW` | `review` |
| `AUTHORIZATION_TRUST_REGISTRY_AMBIGUOUS_KEY` | `fail` |
| `AUTHORIZATION_VERIFIED` | `info` |

### 2.12 `vocabulary` — 2 codes

| Code | Severity |
| --- | --- |
| `VOCABULARY_VALUE_INVALID` | `fail` |
| `VOCABULARY_VALUE_UNKNOWN` | `review` |

<!-- END GENERATED REGISTER -->

## 3. The vocabulary is closed

The codes above are the whole of `loquitur.reason_codes.v1`. There is no extension point, no
vendor prefix and no reserved range.

One category name is reserved: `anchoring`, for codes about an anchoring record, written for any
anchoring method ([`anchor-commitment.md`](anchor-commitment.md) §6). It holds no code in this
version, because no anchoring is live and no component of this version can truthfully report on an
anchor. The catalog's meta-schema does not admit it as a category, and the register keeps its place
in the canonical order (§2.8) so that the order of the other categories does not change when it is
defined.

- A producer MUST NOT emit a code outside the register.
- A consumer MUST reject an object carrying one. An unrecognized code is a rejection, not a
  downgrade: it must not be silently dropped, mapped onto a neighboring code, or absorbed
  into a generic warning. This is the same rule
  [`verification-vocabularies.md`](verification-vocabularies.md) states for an unrecognized
  verification status or registry verdict, and it exists for the same reason: the failure mode being
  closed off is an outcome that means "something is wrong and I will not say what".
- Adding, removing or reinterpreting a code is a coordinated protocol change: a new catalog
  version, both schema enums updated together, and new conformance vectors. Adding or removing a
  code also mints a new vocabulary identifier (`loquitur.reason_codes.v2`, say), because the
  identifier names the set of codes and not a number of revisions. A verifier that does not hold
  that identifier answers `UNSUPPORTED_VERSION`, exit code `4`
  ([`report-contract.md`](report-contract.md) §5.5), and not `FAIL`. The vocabulary
  pin on each object is what lets a consumer detect that it is reading an object produced
  against a vocabulary it does not hold.

Three version notions meet here, and none stands for another:

| Notion | This version | What it names |
| --- | --- | --- |
| vocabulary identifier | `loquitur.reason_codes.v1` | the closed set of codes; the value of `reason_code_vocabulary_version` (and `reason_code_catalog_version` in a registry entry), which holds an identifier, a string, and not a number |
| catalog version | `2.0.0` | the revision of the catalog file that enumerates the codes and their attributes |
| catalog directory | `reason-codes/v2.0/` | the path of that file, versioned by the major and minor parts of the catalog version |

A closed code and a registered value are different mechanisms. A code of this register changes
only through the protocol, under the rule above. An asset type, a workflow or an anchoring method is
a value of a registered vocabulary, and a value is added by registration, with no change to this
register, as long as the existing codes suffice to cite a finding about it
([`verification-vocabularies.md`](verification-vocabularies.md) §9). A value whose finding no
existing code can cite needs a new code, and so a protocol change. The two codes of the
category `vocabulary` are how a published object cites a finding about such a value (§11).

The rule holds downstream of the schema boundary too. A narrative renderer that holds a
different catalog version than the producer did does not skip a code its own catalog does not
carry: a skipped code contributes no severity, so the verdict it narrates could not be derived
from the codes it prints, and it refuses the entry instead
([`verdict-grounds.md`](verdict-grounds.md) §7). Catalog drift between two parties is a real
condition, and it is resolved by agreeing on the vocabulary each object pins
(`loquitur.reason_codes.v1`, the value of its pinning member in the table of §1) and the catalog
version that defines it (`2.0.0`, §2), not by narrating around the codes one party cannot read.

## 4. Severity, and the verdict a code compels

Every entry in the register carries exactly one severity from a closed set of four, declared
in the catalog's meta-schema (`reason-codes/schema.json`, `CatalogEntry.severity`):

```text
info | warn | review | fail
```

A severity decides a verdict. **The verdict of an object that publishes one is the verdict
its highest-severity code maps to**, and a `PASS` cites at least one code of severity `info`.
The registry verdict vocabulary in increasing severity is:

| Rank | Verdict |
| ---: | --- |
| 0 | `PASS` |
| 1 | `WARN` |
| 2 | `REVIEW` |
| 3 | `FAIL` |

and each code severity maps to exactly one verdict:

| Highest code severity | Verdict | Corresponding verification status |
| --- | --- | --- |
| `info` | `PASS` | `pass` |
| `warn` | `WARN` | `warning` |
| `review` | `REVIEW` | `review` |
| `fail` | `FAIL` | `fail` |

The status column is the same relation expressed in the `verification_summary.status`
vocabulary; the status-to-verdict mapping is total and is owned by
`VERIFICATION_VOCABULARIES.json`.

This rule binds the objects that publish a verdict: a `verification_summary`, under VG-3 and
VG-4 of [`verdict-grounds.md`](verdict-grounds.md), and a `registry_entry`, under the same two rules
as [`registry-link.md`](registry-link.md) §2 applies them. It does not bind a verifying tool's own
local report, which is a different object and may reach a verdict through a condition the vocabulary
does not name; [`verdict-grounds.md`](verdict-grounds.md) §1.1 sets out the distinction.

The rule is an equality and not a floor. A verdict less severe than its codes is malformed: an
object carrying `INTEGRITY_OFFLINE_MANIFEST_SHA_MISMATCH` (severity `fail`) under verdict `PASS`
is malformed, even though both values are individually inside their own enums. A verdict more
severe than its codes is malformed as well: `REVIEW` citing only `warn` codes asserts a
conclusion its own printed grounds do not support, and a reader cannot re-derive it. A policy
that escalates cites the code of the ground it escalates on.

No JSON Schema keyword expresses that constraint, so schema validation will not catch it. It is
a rule an implementation must enforce itself. Both reference verifiers hold it for a registry
entry in the `link` and `authorization` checks as part of the entry's contract, and the reference
narrative renderer refuses to narrate an entry that breaks it rather than composing anything.

Refusal rather than rewriting, deliberately. Rewriting a counterparty's verdict to the one its
codes derive would leave the explanation disagreeing with the record it describes, and that
disagreement is itself the finding. The rule as stated here is complete, and a conforming
verifier is written from it.

## 5. A verdict must carry its grounds

`minItems: 1` on `reason_codes` in the three schemas is the first half of this rule: an object
whose `reason_codes` is `[]` does not validate. The second half is that every cited code
must be one the consumer recognizes ([`verdict-grounds.md`](verdict-grounds.md) VG-2). A
verdict whose every code is unknown has nothing printable underneath it, and the conclusion
alone is an assertion that cannot be supported.

Together these make a substance-free `PASS` unrepresentable. The property holds only when
every component holds both halves: a renderer that printed a `PASS` the schema rejects would
disagree with the schema about the guarantee. The reference renderer refuses an empty code list,
any code outside its catalog and a verdict outside the closed four, on the entry point that
takes a verdict together with a reason-code list.

A `PASS` therefore has to say what passed.

<!-- BEGIN GENERATED AFFIRMATIVE -->

The register carries **5 codes of severity `info`**. These are the
affirmative ones: they record that a check succeeded rather than that something went wrong,
and they are what a `PASS` cites. The description column is each entry's
`technical.headline` from the catalog, without its final full stop.

| Code | Category | What it records |
| --- | --- | --- |
| `INTEGRITY_OK` | `integrity` | Bundle integrity verification completed without errors |
| `REQUIRED_CLAIMS_PRESENT` | `coverage` | All required claims for the active policy are present |
| `FRESHNESS_OK` | `freshness` | All evidence is within the policy freshness window |
| `REQUIRED_EVIDENCE_PRESENT` | `evidence` | All evidence required by the active policy is present |
| `AUTHORIZATION_VERIFIED` | `authorization` | The issuing key was authorized by the trust registry at the evaluation time |

<!-- END GENERATED AFFIRMATIVE -->

## 6. The narratives, and what composes them

Each register entry carries, besides its category and severity, three audience narratives.
The field contract is in the catalog's meta-schema, `reason-codes/schema.json`:

| Audience | Required fields | Voice |
| --- | --- | --- |
| `technical` | `headline`, `detail` | Neutral, for engineers; canonicalization, hashes, schema names allowed |
| `compliance` | `headline`, `consequence`, `required_action` | Assertive operational consequence and a specific required action |
| `executive` | `summary` | Non-technical, assertive, no jargon and no hash references |

The audience sequence `["technical", "compliance", "executive"]` is contract, not
presentation: the meta-schema pins it with `const`, and the reference loader compares it
positionally.

Alongside the entries the catalog carries `composition_templates`: for each audience, a
verdict lead for each of `PASS`, `WARN`, `REVIEW` and `FAIL` in each of two contexts
(`offline_verification`, when the reader ran the verification; `registry_entry`, when the
reader is consuming a commitment somebody else issued), and a closing set that additionally
distinguishes a single finding from several and calls out the authorization and signature
cases.

**The narratives are composed by templating and are never generated.** A renderer selects a
lead by verdict and context, emits one paragraph per cited code in canonical category order,
and appends a closing. Nothing is predicted, inferred or sampled; the text is a function of
the catalog and the codes and of nothing else, so the same input yields byte-identical output
across runs and machines (`narrative.py::__doc__`, "Determinism mandate"). This is the same property
the verdict path has: there is no model anywhere in it.

Which fields of a catalog entry form a code's paragraph, the separators between the lead, the
paragraphs and the closing, and the rule that selects one closing of the set are not specified in
this version: they are implementation-defined, and two renderers that take every string from the
catalog can assemble different narratives. A closing may be empty, as the executive audience's
`PASS` closing is; a renderer then appends no closing. The byte-identity above holds for one
implementation, across runs and machines, and narrative renderers are outside conformance in this
version ([`conformance-testing.md`](conformance-testing.md) §6).

Two consequences for an implementer. The narratives are content, not control flow: nothing in
the verdict path reads them, so an implementation that renders no narrative at all still
reaches the same verdict and cites the same codes. And an implementation that does render
them MUST take the wording from the catalog rather than compose its own; that is what makes
the wording of two implementations' explanations of the same grounds the same, although their
assembly may differ, and it is why the wording lives in a published artifact instead of inside
verifier source.

The paragraph order is the canonical category order used to group the register above:
`integrity`, `coverage`, `freshness`, `conflict`, `policy`, `evidence`, `offline`, `materiality`,
`valuation_crosscheck`, `authorization`, `vocabulary`; codes within a category sort by their
identifier. The reserved name `anchoring` holds its place between `offline` and `materiality`
(§3).

## 7. How the register above is generated, and how to check it

The register is generated, not transcribed. It and the affirmative-code table are rendered by
`tools/render_reason_codes.py` from four files in this repository:

- `docs/specification/reason-codes/v2.0/catalog.json`: the entries, each with its code,
  category, severity and narratives;
- `docs/specification/schemas/verification_summary.schema.json`: the enum closing
  `reason_codes` on a verification summary;
- `docs/specification/schemas/registry_entry.schema.json`: the enum closing `reason_codes`
  on a public registry entry;
- `docs/specification/schemas/verification_receipt.schema.json`: the enum closing
  `reason_codes` on a verification receipt.

The tool refuses to render unless all four agree: catalog keys equal to each of the three enums
in both directions, every entry's `code` field equal to its map key, and every category and severity
inside the meta-schema enums. Disagreement is a failure and not a merge, because when the
sources differ there is no single answer to "what are the codes" and printing either side
would publish a claim the other file contradicts. The canonical category order is declared in
the tool and checked for set equality against the meta-schema's category enum, so a category
added to the schema cannot be silently rendered last.

```text
python tools/render_reason_codes.py            # verify: exit 0 if the blocks match the catalog
python tools/render_reason_codes.py --write    # regenerate the blocks in place
```

Two blocks on this page are generated and each sits between its own pair of HTML comment
markers: the register above, and the table of affirmative codes under "A verdict must carry
its grounds". Nothing outside those markers is written by the tool. Everything else here is
prose maintained by hand, including the verdict tables above, which state the rule of
[`verdict-grounds.md`](verdict-grounds.md) §2 over the catalog's four severities.

## 8. Undeclared members: producer vocabulary, one verifier behavior

The register carries three codes for files a bundle carries without declaring them:
`BUNDLE_EXTRA_FILES` (`warn`), `POLICY_BUNDLE_EXTRA_FILES` (`warn`) and
`INTEGRITY_OFFLINE_EXTRA_FILES_STRICT` (`fail`). They are vocabulary a producer cites, under its
own policy, in an object it publishes. A verifier has one behavior for an undeclared member,
with no lenient or strict mode: it reports the member and the run yields `OFFLINE_REVIEW`
([`bundle-objects.md`](bundle-objects.md) §1). A verifier's report cites no catalog code
([`report-contract.md`](report-contract.md) §5.1).

## 9. Why `authorization` is a category of its own

Narrated as an integrity failure, a revoked issuer key would tell the reader that the bundle
could not be confirmed internally consistent and should be regenerated. Both statements would be
false: the evidence is intact, and regenerating it changes nothing, because it is the issuer's
authority that has been withdrawn. The category, added by LCP-0001, separates cases by **what the
reader must do**, not by what the verifier saw. The same principle explains splits inside the
category: a revoked key and a suspended key are different codes because one is a security event and
the other a reversible administrative hold, and a key that expired before the record is different
from a record dated before the key took effect because the first is usually paperwork and the second
is a books-and-records concern.

## 10. Interpretation

Reason codes explain verification posture. They do not prove legal ownership, economic
correctness, regulatory status, or the truthfulness of the source documents. A code records
what a deterministic check concluded about the material in front of it, and nothing wider.

## 11. Vocabulary codes

The category `vocabulary` holds the two codes a published object cites about a member a registered
vocabulary governs ([`verification-vocabularies.md`](verification-vocabularies.md) §5 and §7):

- `VOCABULARY_VALUE_UNKNOWN`, severity `review`: the member holds an identifier that the vocabulary
  the producer held does not register. The producer could not confirm what the value means, so the
  object is a review.
- `VOCABULARY_VALUE_INVALID`, severity `fail`: the member holds a value that is not an identifier.
  The object carrying it breaks its contract, so a producer cites this code about an input it
  refused, never about the object it publishes.

Both are actionable codes under VG-6 of [`verdict-grounds.md`](verdict-grounds.md). A context entry
for either names the member as `subject`, the value as `observed`, and the vocabulary held as
`expected`, written as its kind, `@` and its version, such as `asset_type@1.0.0`.

A verifier's report cites neither code: the same findings reach a report as the review reason
`vocabulary_value_unknown` and as the contract violation of the document that carries the value
([`report-contract.md`](report-contract.md) §3.3 and §5.3).
