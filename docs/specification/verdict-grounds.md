# Verdict grounds

Status: normative.

A verdict is a function of the grounds it cites.

This document is the normative statement of that rule set. The rules are stated here so
that they can be implemented from this file, the reason-code catalog and the published
schemas, with no access to any implementation.

> **Non-normative note on citations.** §6 cites definitions of
> `src/loquitur/schemas/verdict_grounds.py` in `loquitur-schemas`, a reference implementation,
> which is a separate repository and not part of this one, in the form `<module>.py::<name>`,
> and names the refusals each rule's check emits. The citations resolve in release `0.1.0` of
> `loquitur-schemas`, once that repository is published, and name no line, and this
> repository's tests check them against the source of a `loquitur-schemas` checkout placed beside
> it, and that checkout's version against the release named here. The citations are not part of
> the protocol: every rule is stated in §3 to §5 and can be implemented without opening them.

## Normative status

This document is normative. Where an implementation disagrees with it, the implementation
is wrong and is to be corrected, not this file amended to describe what the code happens
to do. The reference implementations named in §6 are cited so that a reviewer can check
this document against them, and §7 states how the same rules bind a registry entry and the
narrative a verifier renders from one.

## 1. Scope

The rules govern the **verification summary**: the object defined by
`schemas/verification_summary.schema.json`, carrying a `status`, a `reason_codes` array,
and optionally `reason_context` and `key_checks`.

They govern nothing else. In particular they say nothing about whether the underlying
verification was correct, only about whether the document's verdict is supported by the
grounds the document itself prints. A summary that satisfies every rule here is a summary
whose verdict a third party can re-derive from its own contents; it is not thereby a true
statement about an asset.

The rules of §3 do not depend on schema validity: a checker applies them to any JSON value. Where
a member has a type the schema refuses, the rule that reads it says what that member counts as, so
a summary the schema rejects is still judged by the same seven rules.

### 1.1 The four objects, and which rules bind each

Four different objects carry a verdict, and confusing them is the easiest way to
implement these rules wrongly.

| object | authored by | bound by |
|---|---|---|
| `verification_summary` | whoever issues it | the rules in this document |
| `registry_entry` | the issuer, published | VG-1 to VG-4, as [`registry-link.md`](registry-link.md) §2 applies them (§7) |
| `verification_receipt` | the pipeline that verified the bundle, inside the private bundle | not these rules: its `status` is not bound to its own `reason_codes` ([`registry-link.md`](registry-link.md) §2); it is compared with the entry's verdict by the `link` check |
| a verifier's local report | the verifying tool, for its own reader | [`report-contract.md`](report-contract.md), and not these rules |

The row for a verifier's local report is the one that surprises implementers, so it is
stated with evidence rather than asserted. A verifier's report is not a verification
summary: measured against `schemas/verification_summary.schema.json`, the reference
verifier's report carries none of `object_type`, `schema_version`, `bundle_id`,
`reason_codes` or `reason_code_vocabulary_version`: five of the six required fields. It
is a diagnostic addressed to whoever ran the tool, not a commitment published to anyone.

That distinction is load-bearing, not pedantic. A verifier may legitimately reach a
verdict for a reason that is not a catalog code at all. A verifier returns `REVIEW` when no
trust root is pinned, and the run cites **zero** catalog codes: its reasons are the verifier
reasons [`report-contract.md`](report-contract.md) §5 defines, `outcome.reason`
`trust_registry_root_not_pinned` with the root signature status `NO_PINNED_TRUST_ROOT`. Under the
rules in this document such an object would be malformed, because VG-1 requires grounds. It is not
malformed, because these rules do not bind it.

An implementation that publishes a verification summary must satisfy this document. A
verifier's report is bound instead by [`report-contract.md`](report-contract.md), which fixes its
status, verdict, exit code and reason surface, and it must not be judged non-conforming for
reporting a condition the catalog does not name.

## 2. The three vocabularies

Three closed sets are used below. All three are published; none may be extended by an
implementation.

**Severity**: a property of a reason code, carried by each catalog entry at
`reason-codes/v2.0/catalog.json` and constrained by the `severity` enum in
`reason-codes/schema.json`. [`reason-codes.md`](reason-codes.md) beside this file registers every
code with its category and severity. The four values, **in this ascending order**, are:

```text
info  <  warn  <  review  <  fail
```

That ordering is normative and is the only ordering. An implementation MUST NOT sort
severities alphabetically, by insertion order, or by any other means.

**Status**: the value of `verification_summary.status`, closed to
`pass · warning · review · fail` by the schema's enum and by
`VERIFICATION_VOCABULARIES.json`. See
[`verification-vocabularies.md`](verification-vocabularies.md).

**Verdict**: the value of `registry_entry.verdict`, closed to `PASS · WARN · REVIEW ·
FAIL`. The status-to-verdict mapping is total and lives in `VERIFICATION_VOCABULARIES.json`.

The **severity-to-status map** is the bridge between the first two, and is normative:

| Severity | Status  | Corresponding verdict |
| -------- | ------- | --------------------- |
| `info`   | `pass`    | `PASS`   |
| `warn`   | `warning` | `WARN`   |
| `review` | `review`  | `REVIEW` |
| `fail`   | `fail`    | `FAIL`   |

The two spellings differ in one place: severity `warn` maps to status
`warning`, not to `warn`. An implementation that copies the severity string into the status
field produces a value outside the status vocabulary.

**Implied status.** For a non-empty set of reason codes, the *implied status* is the status
mapped from the **maximum** severity over the cited codes, under the ordering above. One
`fail` code among twenty `info` codes yields an implied status of `fail`. For an empty set
the implied status is undefined, and rule VG-1 already forbids the empty set.

## 3. The rules

Each rule states what it requires, what it forbids, and what a conforming implementation
does when the rule is violated. The answer to the last question is the same for all seven
and is stated once in §4: **reject**.

### VG-1 — A verdict MUST cite its grounds

`reason_codes` MUST be present and MUST contain at least one entry. Entries MUST be
unique.

Entries are compared as JSON values, not as the bytes that spell them: `1`, `1.0` and `1e0` are
one entry, so `[1, 1.0]` carries a duplicate, and a string is compared after its escapes are
decoded.

Forbidden: a summary with `reason_codes` absent, `reason_codes: []`, or `reason_codes`
present but not an array. A value that is not an array (a bare string, an object, `null`)
MUST be treated exactly as an absent one: it cites nothing.

The published schema carries this rule on its own: `reason_codes` appears in `required`,
with `"minItems": 1` and `"uniqueItems": true`. Of the other six it carries only VG-2,
through the enum that closes the entries of `reason_codes` to the catalog's codes. It is
nonetheless restated here, and a conforming checker MUST apply it independently of schema
validation, because a caller may reach the grounds check without having validated the
document first, and a rule enforced in only one of two places holds only when someone
remembers to run the other.

### VG-2 — Every cited code MUST be in the catalog

Every entry of `reason_codes` MUST be a code defined by the reason-code catalog.

`reason_code_vocabulary_version` is not read by these rules. The schema closes it to the one
vocabulary this release publishes, `loquitur.reason_codes.v1`, and every code is looked up in that
vocabulary's catalog whatever the member holds.

Forbidden: citing a code the catalog does not define. An implementation MUST NOT skip an
unrecognized code and continue: a skipped code contributes no severity, so the maximum
comes out too low, and an unrecognized failure silently becomes a pass. This is the reason
the rule exists at all, and it is why VG-2 is evaluated before VG-3 and terminates the
check (§5).

A narrative renderer holds the same rule (§7): it does not skip an unrecognized code
either.

### VG-3 — The status MUST equal the status its grounds imply

`status` MUST equal the implied status defined in §2 (the status mapped from the maximum
severity over the cited codes).

Forbidden, in both directions:

- **Understating.** A `pass` citing `AUTHORIZATION_ISSUER_KEY_REVOKED` (severity `fail`).
  This is the defect the rule exists to close: without it, such a document validates,
  and the verdict is an independent assertion the reader has to trust.
- **Overstating.** A `fail` citing only `INTEGRITY_OK` (severity `info`). Overstating a
  failure is as much a contradiction as understating one: the document asserts a
  conclusion its own printed grounds do not support, and a reader cannot re-derive it.

Equality, not a floor. An implementation MUST NOT accept a status merely because it is at
least as severe as the grounds require.

A `status` outside the closed status vocabulary also violates this rule, because no such
value can equal an implied status. An implementation SHOULD additionally reject it as an
out-of-vocabulary value, with a diagnostic that says so, rather than reporting only that it
contradicts the grounds: the two defects call for different fixes.

### VG-4 — A `pass` MUST cite an affirmative ground

If `status` is `pass`, at least one cited code MUST have severity `info`.

Forbidden: a `pass` whose cited codes are all non-affirmative. The catalog defines exactly
five `info` codes (`AUTHORIZATION_VERIFIED`, `FRESHNESS_OK`, `INTEGRITY_OK`,
`REQUIRED_CLAIMS_PRESENT`, `REQUIRED_EVIDENCE_PRESENT`), so a producer that has verified nothing has
nothing to cite and cannot emit a conforming `pass`.

VG-4 follows from VG-1 to VG-3 together: with at least one cited code, every code in the
catalog and the status equal to the implied one, a `pass` cites only `info` codes. It is stated
on its own so that a `pass` without an affirmative ground gets its own diagnostic
(`pass_without_affirmative_ground`, §6), and so that it holds for an implementation that checks
VG-3 in isolation: under VG-3 alone a `pass` could be reached by citing codes that carry no
severity at all, or by resolving an empty maximum to `pass`.

### VG-5 — A `pass` MUST report the checks it ran

If `status` is `pass`, `key_checks` MUST be present and non-empty.

`key_checks` is typed as array-or-object-or-null, so an empty `key_checks` takes four forms
(absent, `null`, `[]` and `{}`), and each of them violates this rule. A pass says what it checked,
not only that checking succeeded.

A `key_checks` value that is not an array, an object or `null` (a string, a number or a boolean,
whatever its value) MUST be treated exactly as an absent one, and so violates this rule for a
`pass`.

This rule is expressible in JSON Schema generally, through `if`/`then`, and is deliberately
not expressed in this project's schemas. The protocol's own validator accepts a closed set
of nineteen keywords and fails closed on anything else, so that a third party can write an
independent validator: `$schema`, `$id`, `title`, `type`, `required`, `properties`,
`additionalProperties`, `items`, `const`, `enum`, `minLength`, `minItems`, `minimum`, `pattern`,
`uniqueItems`, `example`, `description`, `deprecated` and `oneOf`. `if`, `then`, `$ref` and
`minProperties` are all outside that set. The set binds the object schemas under `schemas/`, which
the verifiers validate with; the meta-schema of the reason-code catalog is not one of them.
Widening the dialect to express one conditional would put that cost on every future
implementation. The conditional is therefore a prose rule, and an implementer MUST enforce
it outside schema validation.

### VG-6 — Actionable codes MUST carry context

Every cited code whose severity is `fail` or `review` MUST have at least one matching entry
in `reason_context`: an entry whose `code` equals that cited code.

`fail` and `review` are the actionable severities: the reader has to go and do something.
A bare code does not say what. "The issuing key had already expired" names neither the key
nor the instant. `info` and `warn` are exempt because there is nothing to remedy.

Forbidden: a `fail` or `review` summary that cites an actionable code with no matching
context entry. `reason_context` entries for codes that are *not* cited are permitted and
MUST NOT be treated as violations of this rule; only the actionable cited codes create an
obligation.

The context entry's non-`code` fields (`subject`, `observed`, `expected`, `window`) are each
optional, on purpose: a producer able to name only the code must still be able to report at all. A
conforming producer SHOULD populate whichever of them the finding has.

### VG-7 — Every context entry MUST name a code in the catalog

Every `reason_context[].code` MUST be a code the catalog defines.

`reason_context[].code` is typed in the schema as a plain string rather than as a second
copy of the catalog's enumeration, because a second hand-maintained copy of a vocabulary
drifts from the first. The schema therefore
admits `{"code": "NOT_A_REAL_CODE"}`, and VG-7 is the rule that refuses it.

An entry of `reason_context` that is not an object, has no `code`, or whose `code` is not a string
names no catalog code and violates VG-7. Such an entry matches no cited code either, so it meets
no obligation of VG-6.

A `reason_context` that is not an array MUST be treated exactly as an absent one: it carries no
entry, so it violates no part of VG-7 and meets no obligation of VG-6.

## 4. What an implementation does on violation

**Reject.** A summary violating any rule in §3 is not conforming, and a consumer MUST NOT
act on its verdict.

Specifically:

- An implementation MUST NOT repair a violating document. It MUST NOT rewrite the status to
  the one the grounds imply, MUST NOT drop the codes that contradict the status, and MUST
  NOT synthesize a missing context entry.
- An implementation MUST NOT downgrade or coerce an out-of-vocabulary value to the nearest
  recognized one. This is the same rule
  [`verification-vocabularies.md`](verification-vocabularies.md) states for statuses and verdicts:
  an unrecognized value is a rejection, not a downgrade. Fail-closed routing is the right
  *direction*, but a document that says `PASS` and is narrated as `FAIL` has been described falsely,
  and quietly rewriting a counterparty's verdict leaves the output disagreeing with the document it
  purports to describe. That disagreement is the finding, and it is to be reported, not smoothed
  over.
- Rejection is a statement about the *document*, not about the asset. A rejected summary
  means the verdict cannot be checked, which is distinct from a verdict of `fail`.

A checker SHOULD report every violation it finds rather than stopping at the first, subject
to the ordering in §5. The pinned conformance corpus declares, for each of its summary runs, the
rules the summary violates ([`conformance-testing.md`](conformance-testing.md) §4.1 and §6). A
verifier that stops at the first violation makes its own diagnostics worse than the documents it is
judging.

## 5. Evaluation order

Two rules are preconditions for the rest and terminate the check when violated, because
every later rule reads something they establish:

1. **VG-1.** If `reason_codes` is absent, empty or carries a duplicate, report the VG-1
   violation and stop.
2. **VG-2.** If any cited code is outside the catalog, the maximum severity cannot be
   computed correctly. Report the unrecognized codes and stop. An implementation MUST NOT
   compute a maximum over the recognized remainder.

The remaining five (VG-3 through VG-7) are independent and are evaluated together, so that
one document can report several violations at once. The check that the status, or a registry
entry's verdict, is inside its closed vocabulary is part of VG-3, and is made after VG-1 and VG-2
like the rest of VG-3. A `pass` citing only a `warn` code and
carrying no `key_checks` violates VG-3, VG-4 and VG-5 simultaneously, and a conforming
checker reports all three.

## 6. Where each rule is implemented

The definitions are named so that a reviewer can check this document against the code. They
are a citation, not a definition: if the code and this document disagree, the code is
wrong. Each refusal is named by the identifier its message starts with.

| Rule | Reference implementation | Refusals |
| ---- | ------------------------ | -------- |
| Severity ordering | `verdict_grounds.py::SEVERITY_ORDER` | — |
| Severity-to-status map | `verdict_grounds.py::SEVERITY_TO_STATUS` | — |
| Actionable severities | `verdict_grounds.py::STATUSES_REQUIRING_CONTEXT` | — |
| Implied status | `verdict_grounds.py::max_severity`, `verdict_grounds.py::status_for_codes` | — |
| VG-1 | `verdict_grounds.py::verdict_grounds_errors` | `reason_codes_absent`, `reason_codes_duplicated` |
| VG-2 | `verdict_grounds.py::verdict_grounds_errors` | `reason_code_not_in_catalog` |
| VG-3 | `verdict_grounds.py::verdict_grounds_errors` | `verdict_outside_vocabulary`, `status_contradicts_grounds` |
| VG-4 | `verdict_grounds.py::verdict_grounds_errors` | `pass_without_affirmative_ground` |
| VG-5 | `verdict_grounds.py::verdict_grounds_errors` | `pass_without_key_checks` |
| VG-6 | `verdict_grounds.py::verdict_grounds_errors` | `reason_context_missing` |
| VG-7 | `verdict_grounds.py::verdict_grounds_errors` | `reason_context_code_not_in_catalog` |
| VG-1 (schema half) | `schemas/verification_summary.schema.json`: `required`, `minItems`, `uniqueItems` | — |

The module's own header docstring names the same seven rules, VG-1 to VG-7, and says that
VG-1 alone also lives in the schema.

The verifiers check VG-3 on a registry entry's `verdict` as part of the entry's contract (§7), and
name its two refusals there `verdict_outside_vocabulary` and `verdict_contradicts_grounds`: the
second reads a verdict, where the summary checker's `status_contradicts_grounds` reads a status.

> **Non-normative note.** Two further behaviors of that module. `max_severity` and
> `status_for_codes` raise when handed a code the catalog does not define, through
> `catalog.get`: they are not tolerant helpers, and VG-2 is evaluated first so that the
> document-level checker never reaches that raise (§5). `verdict_grounds_errors` reads
> `reason_codes` as a list or tuple only, which is how it treats any other JSON type as absent,
> as VG-1 requires.

## 7. The registry entry, and the narrative rendered from one

A registry entry commits to a verdict and cites the reason codes it rests on. VG-1 to VG-4
bind that verdict as they bind a summary's status: [`registry-link.md`](registry-link.md) §2 states
them for the entry, reading `registry_entry.verdict` in place of `verification_summary.status` and
the verdict column of the severity-to-status map in place of the status column. VG-5 to VG-7 do not
apply, because an entry carries neither `key_checks` nor `reason_context`.

**Equality, not a floor, for the entry as for the summary.** An entry whose verdict is less
severe than its grounds and an entry whose verdict is more severe both break the entry's
contract. A verifier holds the rule in the `link` and `authorization` checks as part of that
contract: the link does
not hold, and the run is `OFFLINE_FAIL`. One rule binds a verdict and its codes wherever
either is published, and [`reason-codes.md`](reason-codes.md) states the same equality for the same
field.

**A narrative renderer applies the same four rules.** A renderer that composes an
explanation from an entry's verdict and reason codes **MUST** refuse to narrate an entry that
breaks VG-1 to VG-4, and **MUST NOT** repair it (§4). It does not skip a code its catalog does
not define, does not collapse a code cited twice, and does not narrate a verdict more severe
than the codes it cites. A renderer that tolerated what the verification path refuses would
explain, as if it were settled, an entry the verifier rejects.

### 7.1 What a renderer cannot see

Two differences between a renderer and a checker of documents remain. Both follow from what
a renderer receives, not from a different rule.

**(a) VG-5 to VG-7.** A renderer handed a verdict and a list of codes never sees
`key_checks` or `reason_context`, so it cannot apply the rules that read them. They are not
optional; they are out of that input's reach, and an entry carries neither member anyway.

**(b) One refusal.** A checker of documents reports each violation separately (§4). A renderer
has nothing to render once it has refused, so one refusal is enough for it. As a non-normative
note, the reference renderer names in that refusal every violation of VG-3 and VG-4 it found, and
stops at a violation of VG-1 or VG-2, as §5 orders.

### 7.2 The narrative of a verifier's own report

A renderer may derive codes from a verifier's report rather than read them from an entry. VG-1
applies to that route as much as to the other: a renderer **MUST** refuse to render a narrative
whose verdict it can ground in no catalog code, and a conforming implementation **MUST NOT**
publish a verdict with no grounds by either route. An `OFFLINE_REVIEW` run whose components each
reported cleanly, such as a bundle carrying neither the envelope nor its sidecar, a bundle with
an undeclared member, or an authorization run with no pinned trust root, may give such a
renderer no code; it then refuses rather than narrates. The verifier's report itself is not a
published verdict and is not bound by these rules (§1.1).

## 8. Worked examples

The examples are excerpts. Each leaves out the members the summary schema requires and these
rules do not read (`object_type`, `schema_version` and `bundle_id`), and "conforming" says that it
satisfies the seven rules.

Conforming `pass`:

```json
{
  "status": "pass",
  "reason_codes": ["INTEGRITY_OK"],
  "key_checks": [{"check_id": "integrity", "status": "pass"}],
  "reason_code_vocabulary_version": "loquitur.reason_codes.v1"
}
```

Conforming `fail`, with one actionable code and context that says what to act on:

```json
{
  "status": "fail",
  "reason_codes": ["AUTHORIZATION_ISSUER_KEY_REVOKED"],
  "reason_context": [
    {
      "code": "AUTHORIZATION_ISSUER_KEY_REVOKED",
      "subject": "issuer_key_id=key-7",
      "observed": "revoked",
      "expected": "active at the evaluation time"
    }
  ],
  "reason_code_vocabulary_version": "loquitur.reason_codes.v1"
}
```

Non-conforming, and why:

| Document | Violates |
| -------- | -------- |
| `status: "pass"`, `reason_codes: []` | VG-1 |
| `status: "pass"`, `reason_codes: ["INTEGRITY_OK", "NOT_A_REAL_CODE"]` | VG-2 (and evaluation stops there) |
| `status: "pass"`, `reason_codes: ["AUTHORIZATION_ISSUER_KEY_REVOKED"]`, no `key_checks`, no `reason_context` | VG-3 (the implied status is `fail`), VG-4, VG-5 and VG-6 together |
| `status: "fail"`, `reason_codes: ["INTEGRITY_OK"]` | VG-3: the implied status is `pass` |
| `status: "pass"`, `reason_codes: ["FRESHNESS_WARNING"]`, no `key_checks` | VG-3, VG-4 and VG-5 together |
| `status: "pass"`, `reason_codes: ["INTEGRITY_OK"]`, `key_checks: {}` | VG-5 |
| `status: "fail"`, `reason_codes: ["INTEGRITY_OFFLINE_FAIL"]`, no `reason_context` | VG-6 |
| `status: "fail"`, context entry `{"code": "NOT_A_REAL_CODE"}` | VG-7 |
| `status: "fail"`, `reason_codes: ["INTEGRITY_OFFLINE_FAIL"]`, `reason_context: ["INTEGRITY_OFFLINE_FAIL"]` | VG-6 and VG-7: the entry is not an object |
| `status: "fail"`, `reason_codes: ["INTEGRITY_OFFLINE_FAIL"]`, `reason_context: [{"subject": "p1.json"}]` | VG-6 and VG-7: the entry has no `code` |
| `status: "pass"`, `reason_codes: ["INTEGRITY_OK"]`, `key_checks: "integrity"` or `key_checks: true` | VG-5 |
| `status: "pass"`, `reason_codes: [1, 1.0]` | VG-1: the two entries are one value (and evaluation stops there) |

A `warning` summary citing only `warn` codes needs neither `key_checks` nor
`reason_context`: VG-5 binds `pass` only, and VG-4 and VG-6 bind `pass` and the actionable
severities respectively.

## 9. What these rules do not establish

They make a verdict *checkable*, not *true*. A summary that satisfies all seven rules has
stated grounds a reader can re-derive its verdict from. It does not thereby establish that
the underlying evidence is genuine, that the issuer holds any legal status, that a
valuation is correct, or that anything was examined by a person. Those are outside the
protocol, and no rule here should be read as reaching them.

Nor do the rules make the vocabulary complete. Adding, removing or reinterpreting a
severity, a status or a verdict is a coordinated protocol change under the change-control
terms in [`verification-vocabularies.md`](verification-vocabularies.md), and a change to any rule in
§3 is a change to what a conforming verifier accepts.
