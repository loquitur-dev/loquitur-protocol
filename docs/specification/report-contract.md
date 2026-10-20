# Verifier report contract

Status: normative.

This document states what the report of one verification run carries, which of its members a
conformance comparison reads, and the exact values those members may take, so that a third
implementation settles from this text whether a verifier that reaches the right verdict with a
different per-check value conforms.

## 1. Scope

A run verifies one bundle, and optionally a registry entry (the `link` check,
[`registry-link.md`](registry-link.md)), a trust registry (the `authorization` check,
[`trust-registry-authorization.md`](trust-registry-authorization.md)), a trust-root document
([`trust-root.md`](trust-root.md)) and an evaluation time supplied by the operator. Its report is a
JSON object addressed to whoever ran the verifier.

For each kind of registered vocabulary, a run uses one vocabulary document: the one built into the
verifier, or one the operator supplies
([`verification-vocabularies.md`](verification-vocabularies.md) §8). No input of the run supplies
one.

The report is not a verification summary. It cites no code of the reason-code catalog, and the
rules of [`verdict-grounds.md`](verdict-grounds.md) do not apply to it. This document is the rule
set that binds it.

## 2. Normative and informative members

| member | domain | class |
| --- | --- | --- |
| `status` | §3 | normative |
| `verdict` | §3 | normative |
| `exit_code` | §3 and §4 | normative |
| `outcome.reason` | §5.2 | normative |
| `errors` | an array of objects, each with a `code` from §5.3 | normative: the list of codes, in order, and for `unsupported_version` its members `object` and `version` (§5.5) |
| `checks_requested` | §3.2 | normative |
| `checks_established` | §3.2 | normative |
| `review_reasons` | §3.3 | normative |
| `evaluation_time` | the operator's evaluation time as supplied, or `null` | normative |
| `trust_registry.authorization_status` | [`trust-registry-authorization.md`](trust-registry-authorization.md) §8 | normative when the trust registry was evaluated (§5.4) |
| `trust_registry.signature_status` | [`trust-registry-authorization.md`](trust-registry-authorization.md) §8, or `null` | normative when the trust registry was evaluated (§5.4) |
| `trust_registry.trust_registry_root_signature_status` | [`trust-root.md`](trust-root.md) §5, or `ROOT_SIGNATURE_NOT_EVALUATED` | normative when the trust registry was evaluated (§5.4) |

Every other member of the report is informative. That includes `checks_evaluated`, the `checks`
object and each of its per-check results, `notes`, `outcome.category`, the members of an error
other than those named above (such as `type` and `message`), and every nested section that
restates a component's work.

`outcome.not_implemented_capabilities` is one informative member, named here because
[`threat-model.md`](threat-model.md) §9 maps each of its values to a residual risk. A verifier that
carries it gives an array of the capabilities it does not implement, each one of
`trust_registry_root_signature_verification`, `registry_inclusion_or_finality_verification`,
`anchor_timestamp_or_chain_finality_verification`, `revocation_or_supersession_verification`,
`valuation_correctness_verification` and `kyc_aml_or_compliance_verification`, and computes it per
run: `trust_registry_root_signature_verification` is left out exactly when a pinned root verified
the trust registry in that run. A verifier need not carry it.

A verifier **MAY** carry members this document does not name, and each of them is informative.
The member `vocabularies`, which records the registered vocabulary documents a run held
([`verification-vocabularies.md`](verification-vocabularies.md) §8), is one of them.
A nested section that restates one component's work speaks for that component only: a member of
the `link` check's section saying that no signature, trust registry or log inclusion was verified
describes the link check, which verifies none of them ([`registry-link.md`](registry-link.md)), and
does not contradict an `authorization` check the same run establishes. What a run established is
read from `checks_established`, and the authorization statuses from `trust_registry` (§5.4).

Informative means that a conformance comparison does not read the member and **MUST NOT** fail
on it. It does not license a verifier to report it falsely: a per-check result that contradicts
the run is a defect of the verifier, and [`bundle-objects.md`](bundle-objects.md) §6 still defines
what the three per-check values mean.

A conformance comparison of runs over the same inputs compares exactly these: `status`,
`verdict`, `exit_code`, `outcome.reason`, the list of `errors[].code` in order with the members
§5.5 names, `checks_requested`, `checks_established`, `review_reasons`, `evaluation_time`, and,
when the trust registry was evaluated, the three statuses of §5.4. Runs that agree on all of them
agree.

No normative member names the trust material a run rested on. The report need not identify the
trust registry (its digest, `trust_registry_id`, `registry_version`, `issued_at` or
`registry_operator_id`), the root that authenticated it, or the trust-root document; an
implementation may carry some of them as informative members, and none has to. Runs over two
different trust registries that reach the same statuses give reports that agree, so a party that
sees only the report can neither apply the freshness rule of [`threat-model.md`](threat-model.md)
§16 nor tell which pinned root vouched for the registry. An operator that keeps a report, or passes
it on, SHOULD keep with it the SHA-256 of the trust registry and of the trust-root document supplied
to the run, and the registry's `trust_registry_id`, `registry_version`, `issued_at` and
`registry_operator_id`. Adding them to the report is not part of this version: it changes the report
contract.

A report names no verification level. The checks it requested and established are named as
[`verification-checks.md`](verification-checks.md) names them.

## 3. Status, verdict and exit code

### 3.1 The outcome table

The three members move together, one to one. The column `class` says which outcomes are about
the evidence; the others are not, and carry no verdict.

| `status` | `verdict` | `exit_code` | class | meaning |
| --- | --- | --- | --- | --- |
| `OFFLINE_OK` | `PASS` | `0` | evidence | every requested check was established |
| `OFFLINE_FAIL` | `FAIL` | `1` | evidence | a check did not hold, or content was refused |
| `OFFLINE_REVIEW` | `REVIEW` | `2` | evidence | nothing failed, and a review reason holds (§3.3) |
| `INTERNAL_ERROR` | `null` | `3` | not evidence | the verifier itself failed (§4) |
| `UNSUPPORTED_VERSION` | `null` | `4` | not evidence | an object of a known type carries a well-formed version identifier the verifier does not support (§5.5) |
| `HOST_FAILURE` | `null` | `5` | not evidence | the host failed an operation on the operator's input or on the verifier's working space; the failure is the host's and can be repeated, and says nothing about the evidence |

No other value is a status, a verdict or a report exit code. `verdict` is `null` exactly when no
verdict on the evidence was computed, and a consumer **MUST** read only `PASS` as verified.
`OFFLINE_REVIEW` means *not established*: it is neither a failure nor a pass
([`threat-model.md`](threat-model.md) §2). The numbering is fixed by the pinned conformance corpus.

The prefix `OFFLINE_` of the three evidence statuses names the evaluation mode of this version, the
0.1 mode: the verifier evaluates documents the operator supplied and reads no network. A check that
needs an observation of the world (`transparency` and `anchoring` of
[`verification-checks.md`](verification-checks.md) §2, and the evidence checks that are planned)
will report through a member or a mode defined together with it, and will not reuse these statuses.

The status of a run is the first of these that applies:

1. `INTERNAL_ERROR`, when the verifier failed (§4);
2. `UNSUPPORTED_VERSION`, when a version gate fired (§5.5); the run stops there;
3. when a row of §5.3 refuses the input as a whole: `HOST_FAILURE` when that row's class is
   *host*, and `OFFLINE_FAIL` when it is *content*;
4. `OFFLINE_FAIL`, when any of the failure conditions below holds;
5. `HOST_FAILURE`, when the report carries an error whose class is *host* (§5.3);
6. `OFFLINE_REVIEW`, when a review reason holds (§3.3);
7. `OFFLINE_OK`.

The failure conditions are:

- the report carries an error whose class is *content* (§5.3);
- the manifest, P1 or envelope layer fails ([`bundle-objects.md`](bundle-objects.md) §2 to §4 and
  §6, [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §3);
- a registry entry was supplied, the bundle carries `verification_receipt.json`, and the link
  does not hold ([`registry-link.md`](registry-link.md) §5);
- the registry entry satisfies its contract and commits the verdict `FAIL`
  ([`registry-link.md`](registry-link.md) §6);
- the trust registry was evaluated and stopped at a row whose effect is a failure
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §6 and §9);
- trust roots were supplied and root authentication stopped at a status whose effect is a failure
  ([`trust-root.md`](trust-root.md) §5 and §6).

A host failure on a bundle member brings a failure condition with it: the row
`manifest_read_failed`, `p1_read_failed` or `envelope_read_failed` refuses the layer that reads
the member ([`bundle-objects.md`](bundle-objects.md) §6), a refused layer fails, and the run is
`OFFLINE_FAIL` with that host error among its errors, because rule 4 comes before rule 5. The rows
for a document beside the bundle, `registry_link_read_failed`, `trust_registry_read_failed` and
`trust_root_read_failed`, refuse no layer: what reads the document is not evaluated, and the run is
`HOST_FAILURE` unless a failure condition holds.

A check that was not requested is not a question left open. A run over a bundle alone reports
`registry_link: null` and `trust_registry: null` among its per-check results and is still
`OFFLINE_OK` when its bundle layers hold. The `null` per-check results that make a run
`OFFLINE_REVIEW` under [`bundle-objects.md`](bundle-objects.md) §6 are those of the bundle layers,
as the review reasons below name them.

### 3.2 The checks requested and established

[`verification-checks.md`](verification-checks.md) names the checks and their order: `structure`,
`integrity`, `link`, `authorization`. A run requests exactly what its caller supplied, and this
version offers no option that changes the request:

- `structure` and `integrity`, always;
- `link`, when a registry entry was supplied;
- `authorization`, when a trust registry was supplied.

`checks_requested` lists the requested checks, and `checks_established` the requested checks that
were established, each in that order. A check is established only when every check before it is
established, so `checks_established` is a prefix of `checks_requested`. That rule is the rule of
this version of the contract; a later version may replace the prefix by a dependency graph between
the checks. A check is established when:

- `structure`: the input was not refused as a whole, the run carries no error of the rows
  `bundle_inventory_failed` to `verification_receipt_contract_violation` of §5.3, the host read
  every document the run reads, and the manifest, P1 and, when the bundle carries one, the
  envelope each satisfy their closed contracts;
- `integrity`: every per-check result of the bundle layers (`manifest_sha256`, `manifest_files`,
  `p1_sha256`, `p1_input_hash`, `envelope_sha256`, `envelope_links`) is `true`, and none of the
  review reasons `bundle_reserved_member` to `offline_review_required` holds;
- `link`: the link holds ([`registry-link.md`](registry-link.md) §5);
- `authorization`: an evaluation time was supplied, the trust registry holds at it
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §9), and the trust roots
  supplied authenticate it at that time (`ROOT_SIGNATURE_VALID`, [`trust-root.md`](trust-root.md)
  §5).

A run is `OFFLINE_OK` exactly when `checks_established` equals `checks_requested`, no review reason
holds (§3.3) and no failure condition holds. Every requested check can be established in an
`OFFLINE_REVIEW` run: an entry that commits the verdict `WARN` or `REVIEW` leaves the `link` check
established and still gives the review reason `registry_entry_verdict_requires_review`. The
informative member `checks_evaluated` lists the requested checks the run reached. A run whose status
is not an evidence outcome reports `checks_established` `[]`.

### 3.3 Review reasons

`review_reasons` lists every review reason below that holds, in the order of the table, and is
`[]` unless the status is `OFFLINE_REVIEW`. The vocabulary is closed.

| # | review reason | holds when |
| --- | --- | --- |
| 1 | `registry_entry_verdict_requires_review` | the registry entry satisfies its contract and commits the verdict `WARN` or `REVIEW` ([`registry-link.md`](registry-link.md) §6) |
| 2 | `verification_receipt_not_provided` | a registry entry was supplied and the bundle carries no `verification_receipt.json` ([`registry-link.md`](registry-link.md) §5) |
| 3 | `evaluation_time_not_provided` | the trust registry was evaluated without an evaluation time and did not fail ([`trust-registry-authorization.md`](trust-registry-authorization.md) §2) |
| 4 | `trust_registry_not_current` | the evaluation stopped at `TRUST_REGISTRY_NOT_YET_EFFECTIVE` or `TRUST_REGISTRY_EXPIRED` |
| 5 | `issuer_key_outside_validity_window` | the evaluation stopped at `ISSUER_KEY_NOT_YET_EFFECTIVE` or `ISSUER_KEY_EXPIRED` |
| 6 | `trust_root_outside_validity_window` | root authentication stopped at `ROOT_KEY_NOT_YET_VALID` or `ROOT_KEY_EXPIRED` |
| 7 | `trust_registry_root_not_pinned` | the trust registry holds and no trust root was supplied ([`trust-root.md`](trust-root.md) §2) |
| 8 | `bundle_reserved_member` | the bundle carries a member at a reserved name ([`bundle-objects.md`](bundle-objects.md) §1) |
| 9 | `container_extra_files` | a ZIP archive carries a file outside the bundle root selected in it ([`bundle-objects.md`](bundle-objects.md) §1) |
| 10 | `bundle_extra_files` | the bundle carries an undeclared member that is not at a reserved name ([`bundle-objects.md`](bundle-objects.md) §1) |
| 11 | `canonical_input_not_provided` | the canonical input is absent and the manifest does not declare it ([`bundle-objects.md`](bundle-objects.md) §6) |
| 12 | `envelope_not_provided` | the bundle carries neither the envelope nor its sidecar ([`bundle-objects.md`](bundle-objects.md) §6) |
| 13 | `offline_review_required` | the verifier reads the bundle through an interface that cannot list its members, so its completeness cannot be established |
| 14 | `vocabulary_value_unknown` | the bundle's `verification_receipt.json`, or a registry entry whose contract the run judges (§5.3, `registry_entry_contract_violation`), satisfies its contract and carries at `asset_type`, or for the entry at `workflow`, an identifier the vocabulary the verifier holds for that kind does not register ([`verification-vocabularies.md`](verification-vocabularies.md) §7) |

Row 14 is not among the rows `bundle_reserved_member` to `offline_review_required`, so it withholds
no check (§3.2): a run whose only review reason is `vocabulary_value_unknown` can establish every
check it requested. The value is judged against the vocabulary the verifier holds for the run, and
the same input reaches `OFFLINE_OK` under a vocabulary that registers the value.

## 4. Exit codes

A verifier that runs as a process exits with the report's `exit_code`, with one addition and one
operator option:

| process exit | meaning | report |
| --- | --- | --- |
| `0`, `1`, `2` | the report's `exit_code` | yes |
| `3` | the verifier failed: a fault of the tool, not a property of the evidence | yes: `status` `INTERNAL_ERROR`, `verdict` `null`, `exit_code` `3`, and the single error `internal_error` |
| `4` | an unsupported version (§5.5) | yes: `status` `UNSUPPORTED_VERSION`, `verdict` `null`, `exit_code` `4`, and the single error `unsupported_version` |
| `5` | a host failure (§5.3) | yes: `status` `HOST_FAILURE`, `verdict` `null`, `exit_code` `5` |
| `64` | usage error: the invocation cannot be honored, and no verdict was computed | none |

**Exit 3 is reserved for the verifier's own faults.** No content of a bundle, a registry entry,
a trust registry or a trust-root document may produce it: content a verifier cannot read is a
refusal, `OFFLINE_FAIL`, with the error §5.3 names for it, and a time a verifier cannot spend on
content is a fault of the verifier. A library interface does not return an `INTERNAL_ERROR`
report; a fault there is an exception of the host language.

**Exit 4 and exit 5 are not verdicts.** No option changes them, and neither is converted into
another exit code.

**Exit 64 is a refusal of the invocation.** A command line **MUST** return it, with no report,
when an argument is missing or malformed under the grammar of §4.1; when a trust registry is
supplied without a registry entry; when an evaluation time is supplied without a trust registry,
or is given an empty value; when a supplied evaluation time is not a calendar instant of the form
`YYYY-MM-DDTHH:MM:SSZ`; and when trust roots are supplied without a trust registry, or the
trust-root document's path names no regular file or the document is malformed under
[`trust-root.md`](trust-root.md) §3, in any of its roots, whether or not the trust registry names
that root. A trust-root document of a well-formed version this verifier does not support is not
malformed: the run is `UNSUPPORTED_VERSION` (§5.5). A trust-root document the host fails to read is
not refused either: the run reports the host failure `trust_root_read_failed` (§5.3). A command line
judges the dependencies of §4.1 before it reads any document, so trust roots supplied without a
trust registry are refused with exit `64` whatever the document holds, a later version included.

A library interface has no exit 64. Given a trust registry without a registry entry, it returns a
report: `OFFLINE_FAIL`, with the errors §5.3 gives the run, and `registry_link` and
`trust_registry` both `null` among its per-check results; it does not read the trust registry.
Those errors are every error the bundle gives, in the order of §5.3, followed by
`trust_registry_requires_registry_entry`, which is the only error when the bundle gives none; a
refusal of the input as a whole (§5.3, `input_not_found` to `filesystem_error`) stays the only
error of its run, with the status §3.1 gives it. Given trust roots that break
[`trust-root.md`](trust-root.md) §3, any one of them, it returns no report: it refuses them with an
error of the host language before it reads any evidence ([`trust-root.md`](trust-root.md) §3). Given
an evaluation time that is empty or that is not a calendar instant of the form
`YYYY-MM-DDTHH:MM:SSZ`, it returns no report either: it refuses the time with an error of the host
language before it reads any evidence
([`trust-registry-authorization.md`](trust-registry-authorization.md) §2). Given trust roots or an
evaluation time without a trust registry, it refuses them as above when they break those rules, and
otherwise does not use them: it returns the report of the same run without them. The trust-root
document's version gate (§5.5) is the exception: it fires whether or not a trust registry is
supplied, so a library given a trust-root document of a well-formed later version returns the
`UNSUPPORTED_VERSION` report with or without a trust registry, where a command line given it without
a trust registry exits `64`.

**Registered vocabularies.** A command line **MUST** also return exit `64`, with no report, when a
registered vocabulary document an option of §4.1 supplies is refused under
[`verification-vocabularies.md`](verification-vocabularies.md) §8: its path names no regular file,
the host fails to read it, or the document is not strict JSON, is not an object, breaks
[`verification-vocabularies.md`](verification-vocabularies.md) §6 or registers another kind than its
option names. A library interface given such a document returns no report: it refuses it with an
error of the host language before it reads any evidence.

**A library interface that takes documents.** The registry entry, the trust registry and the trust
roots are given as paths ([`document-contracts.md`](document-contracts.md) §12), and §5.3 decides
errors on what a path names. A library interface whose host reads those files and hands it documents
instead **MUST** accept, in a document's place, three values no document can be: one by which the
host says nothing is found at the path, one by which it says what is found is not a regular file,
and one by which it says it failed to read the regular file the path names. It **MUST** report each
as this contract reports the path itself: for a registry entry or a trust registry, nothing found
with the error `input_not_found`, which refuses the run as a whole (§5.3); for a registry entry,
something that is not a regular file and a read failure with the errors §5.3 gives those conditions;
for a trust registry, something that is not a regular file as a registry that cannot be read
([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, row 1), and a regular file
the host failed to read with the error `trust_registry_read_failed`; for trust roots, the first two
values alike, refused as above, and a regular file the host failed to read with the error
`trust_root_read_failed` (§5.3). A document that is not strict JSON or is not an object is a third
fact, and neither value stands for it. The path is read as it is written (§5.3, "A path is read as
it is written"), and, links followed, names no regular file when nothing is found at it (§5.3,
"Nothing found, and a host failure") or what is found is not a regular file; any other failure to
inspect, open or read it is a failure to read it.

**Accepting review reasons.** A command line **MAY** offer the option `--accept-review`, whose
value is a comma-separated list of review reasons of §3.3. Under it the process exits `0` for an
`OFFLINE_REVIEW` run when **every** reason in the report's `review_reasons` is in the list, and
with the report's `exit_code` otherwise. The report is unchanged by it: its `status` stays
`OFFLINE_REVIEW` and its `exit_code` stays `2`. Accepting one reason never accepts another:
accepting `registry_entry_verdict_requires_review` leaves a run that also holds
`trust_registry_root_not_pinned` at exit `2`. The option never changes exit `1`, `3`, `4`, `5` or
`64`. [`threat-model.md`](threat-model.md) §10 states what an operator takes on by using it. No
other option changes a process exit, and without this one the process exit equals the report's
`exit_code`.

### 4.1 Command-line grammar

A command line that implements this contract takes the elements below. It **MAY** add options of
its own, such as a choice of output format, under the same rules.

| element | form | occurrences |
| --- | --- | --- |
| the bundle | one path, given as a positional argument | exactly one |
| `--registry-entry` | `--registry-entry PATH` or `--registry-entry=PATH` | at most one |
| `--trust-registry` | `--trust-registry PATH` | at most one, and only with `--registry-entry` |
| `--trust-root` | `--trust-root PATH`, one trust-root document | at most one, and only with `--trust-registry` |
| `--evaluation-time` | `--evaluation-time YYYY-MM-DDTHH:MM:SSZ` | at most one, and only with `--trust-registry` |
| `--accept-review` | `--accept-review REASON[,REASON...]` | at most one |
| `--asset-type-vocabulary` | `--asset-type-vocabulary PATH`, one registered vocabulary document of the kind `asset_type` | at most one |
| `--workflow-vocabulary` | `--workflow-vocabulary PATH`, one registered vocabulary document of the kind `workflow` | at most one |
| `--anchoring-method-vocabulary` | `--anchoring-method-vocabulary PATH`, one registered vocabulary document of the kind `anchoring_method` | at most one |

Every option takes its value in either form, `--option VALUE` or `--option=VALUE`. The order of the
elements is free. The invocation is malformed, exit `64` with no report, when:

- an option is given more than once, in either form, whatever its values;
- an option is given by a prefix of its name, such as `--reg`, or is not an option the command line
  defines (`--attested-time`, `--tsa-token` and `--review-zero` are not options of this version);
- an option has no value, or its value is empty, the bundle path included: an empty path is a
  malformed argument, not a path that names nothing;
- the bundle is missing, or more than one is given;
- `--accept-review` names a value that is not a review reason, or holds an empty element or the
  same reason twice;
- a dependency of the table does not hold, or a condition of §4 above holds.

## 5. The reason surface

### 5.1 What the reason codes of a run are

The reason surface of a run is these things, and nothing else:

1. `outcome.reason`: exactly one value, derived by §5.2;
2. the list of `errors[].code`, in order: zero or more values, emitted by §5.3;
3. `review_reasons` (§3.3);
4. when the trust registry was evaluated, its authorization, signature and root signature
   statuses (§5.4).

These are verifier reasons, not catalog codes. The catalog vocabulary `loquitur.reason_codes.v1`
is what a published object cites ([`reason-codes.md`](reason-codes.md)); a report cites none of it,
and a run can reach its verdict for a reason the catalog does not name. The run with an evaluation
time and no trust root supplied is the standing example. Its verdict is `REVIEW`, it cites no
catalog code and carries no error, and its reason surface is exactly: `outcome.reason`
`trust_registry_root_not_pinned`, `errors` `[]`, `review_reasons`
`["trust_registry_root_not_pinned"]`, authorization status `AUTHORIZED_ACTIVE_KEY`, signature status
`VALID_SIGNATURE`, root signature status `NO_PINNED_TRUST_ROOT`.

`notes` carry detail for a reader, often with a suffix naming a member or a field. They are
informative, and they are not part of the reason surface.

### 5.2 `outcome.reason`

`outcome.reason` is the value of the first rule below that applies to the run.

| # | the run | `outcome.reason` |
| --- | --- | --- |
| 1 | carries at least one error | the `code` of its first error |
| 2 | is `OFFLINE_OK`, and the trust registry was evaluated | `local_integrity_registry_link_and_trust_checks_passed` |
| 3 | is `OFFLINE_OK`, and a registry entry was supplied | `local_integrity_and_registry_link_checks_passed` |
| 4 | is `OFFLINE_OK` | `local_integrity_checks_passed` |
| 5 | evaluated the trust registry, which failed | `trust_registry_verification_failed` |
| 6 | was given a registry entry whose link does not hold | `registry_link_verification_failed` |
| 7 | is `OFFLINE_REVIEW` | the first entry of `review_reasons` |
| 8 | failed its manifest layer: the sidecar, a declared file or the closed contract did not hold | `manifest_integrity_failed` |
| 9 | failed its P1 layer | `p1_integrity_failed` |
| 10 | failed its envelope layer | `envelope_integrity_or_link_failed` |
| 11 | otherwise | `offline_verification_failed` |

The vocabulary of `outcome.reason` is closed: the codes of §5.3, the review reasons of §3.3 and
the values of rows 2 to 6 and 8 to 11.

Rules 8 to 10 read each layer's own outcome, in that order, and apply to an `OFFLINE_FAIL` run
that carries no error. Each names a layer whose outcome is `OFFLINE_FAIL`, and never a layer that
is only `OFFLINE_REVIEW`: a failed run whose P1 layer is `OFFLINE_REVIEW` because the canonical
input is absent, and whose envelope layer failed, is named by rule 10, and a failed run that
carries no error and in which no layer failed is named by rule 11. A run whose registry entry
commits `FAIL` over a link that holds is not such a run: it carries the error
`registry_entry_verdict_fail` (§5.3), so rule 1 names it.

### 5.3 `errors`

An error records that an input was refused, could not be evaluated as what it claims to be, or
could not be read. A check that was evaluated and did not hold is not an error: it fails the run
through its layer, and `outcome.reason` names it (§5.2).

A run appends the error of each row below whose condition holds, in the order of the table, and
no code appears twice. The rows from `input_not_found` to `filesystem_error` refuse the input as
a whole: when one holds, it is the only error of the run, and nothing else is evaluated. When more
than one holds, which can happen only when nothing is found at the path of a registry entry or a
trust registry beside an input another of these rows refuses, the run reports the first of them in
the order of the table.

Every other condition is a predicate over the run's inputs, and each is judged on its own. A
condition that holds is not masked by another that also holds, earlier in the table or not, and a
row that lists several inputs holds when any one of them does, whatever the others are. A
verifier that stops at the first refusal it finds while reading the link, and leaves out an error
whose condition also holds, reports a different list of codes.

Each row has a class, by responsibility. A *content* row is about what the operator's inputs
hold, and its error makes the run `OFFLINE_FAIL`. A *host* row records that the host failed an
operation on the operator's path or on the verifier's working space, or found nothing at the
path, and its error makes the run `HOST_FAILURE` unless a failure condition also holds (§3.1). An
archive that is not a readable ZIP archive is content; failing to open the operator's path or to
write the space an extraction needs is the host's.

Archive intake is optional: a verifier **MAY** read directory bundles only, and
[`bundle-objects.md`](bundle-objects.md) §5 binds the one that reads archives. The kinds a verifier
reads are a property of the verifier, not of the run, and the `invalid_zip` and `unsupported_input`
rows follow from it and never hold together. A verifier with archive intake refuses a regular file
that is not a readable ZIP archive as `invalid_zip`; a verifier without it reads no regular file as
the bundle input, so every regular file given to it as one is an input of a kind it does not read,
and the row is `unsupported_input`. Among the rows that refuse an archive,
[`bundle-objects.md`](bundle-objects.md) §5 ("Which refusal an archive reports") fixes which one a
run reports.

**A path is read as it is written.** A verifier hands each path it is given, the input and every
supplied document, to the file system as it is written: no layer of the host rewrites a name in it
first. On POSIX none does. On Windows the Win32 path layer does: it drops a trailing dot or space
from a name, takes a name such as `NUL` or `CONIN$` in any directory for a device, and refuses a
path longer than `MAX_PATH`. A verifier there reads a path that is not empty in the file
namespace instead:

1. It reads `/` as `\` and finds the path's root. A path that begins with a drive letter, `:` and
   a separator has that drive as its root (`C:\`); one that begins `\\server\share` has that
   share (`\\server\share\`); one that begins `\\?\` or `\\.\` followed by a name has that prefix.
   Any other path that begins with a separator has the root of the working directory's drive. A
   path that begins with a drive letter and `:` and no separator is taken against the working
   directory the host keeps for that drive, else against the working directory when it is on that
   drive, else against that drive's root; any other path is taken against the working directory.
   The server and the share of a root are names of the root, as written: a server or share named
   `.` or `..` is not folded into anything, and a path whose root has one names nothing.
2. Below the root it drops empty names and `.`, and each `..` drops the name before it, never
   the root. The path is its root followed by its names joined by `\`, with no separator after
   the last name.
3. It reads the result with `\\?\` before a drive root, with `\\?\UNC\` in place of the `\\` of
   a share, whatever its server's name begins with, and with `\\?\` in place of a `\\.\` root; a
   path whose root is `\\?\` is read as it now is. A `\\.\` root is replaced because the Win32
   layer still reads a path under it: it drops a trailing dot from each name and a trailing space
   from the last. The verifier hands the host this form and no form the host would normalize
   again.

So, on Windows, `bundle.` names an entry whose name ends in a dot, `C:\data\NUL` an entry named
`NUL`, `\\.\C:\data\bundle ` an entry whose name ends in a space, and the null device is
`\\.\nul`, which is read as `\\?\nul`. A member's path is the root as given followed by the
member's name; the root is never normalized to build it.

**Nothing found, and a host failure.** An operation on a path finds nothing there when no entry
has that name (on Windows `ERROR_FILE_NOT_FOUND` and `ERROR_PATH_NOT_FOUND`), when the path is one
no entry can have (it holds a NUL, or it is longer than the host lets a path or a name be), when
the path holds a noncharacter (U+FDD0 to U+FDEF, and each code point whose last four hexadecimal
digits are FFFE or FFFF), which a verifier does not hand to the host because a host may stop the
process on such a path, when the path is not a sequence of Unicode scalar values (it holds a
surrogate code point, U+D800 to U+DFFF, as a character of its own; in UTF-16, a code unit that is
not half of a pair), which a verifier does not hand to the host because a host may read such a
path as another name, U+FFFD written in its place, when a component of the path is not a
directory, or when a link on the path resolves to nothing or to itself. An empty path is refused
before any of this: by a command line as a usage error (§4.1), and by a library interface with an
error of the host language.

What is found is a directory or a regular file only when it is an entry of a file system: a
device, a named pipe or a socket is neither, whatever the host's first answer about it says, and
so is something that refuses the inspection as an operation or a parameter it does not support
(on Windows, `ERROR_INVALID_FUNCTION` or `ERROR_INVALID_PARAMETER`). On Windows every path whose
root is `\\.\pipe\` or `\\?\pipe\`, in any letter case, names a named pipe: a verifier takes it as
neither a directory nor a regular file from its name, without inspecting or opening it, so a pipe
that is busy (`ERROR_PIPE_BUSY`) or that refuses to open is classified as every other pipe is.

Any other failure of an operation is the host failing it, and a verifier **MUST NOT** report it as
the absence of what it looked for, nor as a finding about bytes it did not read. That includes a
UNC server or share that cannot be reached or does not exist (`ERROR_BAD_NETPATH`,
`ERROR_BAD_NET_NAME`), reparse data the host cannot read (`ERROR_INVALID_REPARSE_DATA`), a denied
access and a sharing violation. A verifier classifies these by the host's error number, never by
the exception class a runtime maps it to:

- a host that fails to resolve or inspect the input's path, to list a directory input, or to read
  a regular file the verifier reads as an archive fails an operation on the input itself:
  `filesystem_error`, which refuses the input as a whole;
- a host that fails to list a directory of the bundle below the root, or to inspect an entry of a
  listing, fails the inventory: `bundle_inventory_failed`. The directory given as the input is
  listed first, to find its `manifest.json`, and a failure of that listing is `filesystem_error`;
- a host that fails to inspect an entry on a member's path, or to open or read the member, leaves
  the member unread. That is what "the host fails to read" means in the rows below: the run
  reports the `*_read_failed` row of the layer that reads the member, and not the member's absence
  ([`bundle-objects.md`](bundle-objects.md) §6 names the members each layer reads). A verifier opens
  a member for reading without denying other readers, writers or deleters, so a member another
  process holds open is read;
- a document supplied by path names no regular file when nothing is found at the path or what is
  found is not a regular file, and any other failure to inspect, open or read it is a failure to
  read it. Nothing found at the path of a supplied registry entry or trust registry refuses the run
  as a whole, as nothing found at the input path does (`input_not_found`), whatever else is
  supplied; something found there that is not a regular file is judged by the rows below. The
  trust-root document is not such an input: nothing found at its path is the refusal of §4.

| code | class | condition |
| --- | --- | --- |
| `input_not_found` | host | nothing is found at the input path, or at the path of a supplied registry entry or trust registry |
| `invalid_zip` | content | the verifier reads ZIP archives and the input is a regular file that is not a readable ZIP archive |
| `archive_unsafe_member` | content | a ZIP entry breaks the rule name, type or duplicate of [`bundle-objects.md`](bundle-objects.md) §5 |
| `archive_safety_limit` | content | a ZIP entry breaks the rule method, member size, ratio, count or total of [`bundle-objects.md`](bundle-objects.md) §5 |
| `bundle_root_invalid` | content | a directory input's listing holds no entry named exactly `manifest.json`, compared code unit for code unit whatever names the host takes as equal ([`bundle-objects.md`](bundle-objects.md) §1); a ZIP archive holds no bundle root, or more than one |
| `archive_load_failed` | host | the host fails to create, write or read the extraction of a ZIP archive |
| `unsupported_input` | content | the input exists and is neither a directory nor a regular file, or is of a kind the verifier does not read (a verifier without archive intake given a regular file) |
| `filesystem_error` | host | the host fails an operation on the input itself: resolving or inspecting its path, listing a directory input, or reading a regular file the verifier reads as an archive |
| `bundle_inventory_failed` | host | the host fails to list a directory of the bundle below the root, or to inspect an entry of a listing ([`bundle-objects.md`](bundle-objects.md) §1); a failure to list the directory given as the input is `filesystem_error` |
| `bundle_member_name_invalid` | content | a listing of the bundle directory holds an entry whose path from the root is not a portable member name, or two entries whose names conflict ([`bundle-objects.md`](bundle-objects.md) §1 and §2) |
| `unsafe_bundle_member` | content | the bundle directory holds a symbolic link, a junction or any other reparse point, whatever its tag, and neither `bundle_inventory_failed` nor `bundle_member_name_invalid` holds ([`bundle-objects.md`](bundle-objects.md) §1: an inventory that fails is reported in place of this row, and every other row is still judged) |
| `manifest_verification_failed` | content | `manifest.json` is not a regular member, is not strict JSON ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness"), exceeds the per-member bound or is not an object; `manifest.sha256` is not a regular member; or the manifest cannot be canonicalized |
| `manifest_read_failed` | host | the host fails to read a manifest member |
| `p1_verification_failed` | content | `p1.json` is not a regular member, is not strict JSON, exceeds the per-member bound or is not an object; P1 breaks its closed contract ([`bundle-objects.md`](bundle-objects.md) §3), cannot be canonicalized or exceeds 1024 bytes in canonical form; or `canonical_input.json` is present and is not strict JSON, exceeds the per-member bound or is not an object |
| `p1_read_failed` | host | the host fails to read a P1 member |
| `envelope_verification_failed` | content | the envelope and `envelope.sha256` are both present and the envelope is not strict JSON, exceeds the per-member bound, is not an object, or satisfies its closed contract and cannot be canonicalized |
| `envelope_incomplete` | content | exactly one of `envelope_env1.json` and `envelope.sha256` is present ([`bundle-objects.md`](bundle-objects.md) §4) |
| `envelope_read_failed` | host | the host fails to read an envelope member |
| `verification_receipt_contract_violation` | content | `verification_receipt.json` is present and is not strict JSON, exceeds the per-member bound, is not an object, or breaks its contract ([`registry-link.md`](registry-link.md) §2) |
| `registry_link_verification_failed` | content | a registry entry was supplied, and any of these holds: something that is not a regular file is found at its path; its document is not strict JSON or is not an object; or the entry and the receipt are objects and the receipt cannot be canonicalized |
| `registry_entry_contract_violation` | content | the registry entry and the receipt are both objects, and the entry breaks its contract ([`registry-link.md`](registry-link.md) §2) |
| `registry_entry_verdict_fail` | content | the registry entry satisfies its contract and commits the verdict `FAIL`, and the run does not carry the error `registry_link_verification_failed` |
| `registry_link_read_failed` | host | the host fails to read a document the link reads |
| `trust_registry_requires_registry_entry` | content | a trust registry was supplied without a registry entry (§4) |
| `trust_registry_requires_valid_registry_entry` | content | a trust registry and a registry entry were supplied, and any of these holds: something that is not a regular file is found at the entry's path; or the entry and the receipt are both objects and the receipt cannot be canonicalized. A host failure to read a document the link reads is `registry_link_read_failed` alone, and the run is `HOST_FAILURE` |
| `trust_registry_read_failed` | host | a registry entry was supplied, satisfies its contract and its link holds, so that the trust registry is read ([`trust-registry-authorization.md`](trust-registry-authorization.md) §1), and the host fails to read the trust registry; the trust registry is then not evaluated, and the report's `trust_registry` is `null` |
| `trust_root_read_failed` | host | trust roots, a trust registry and a registry entry were supplied, and the host fails to read the trust-root document; root authentication is then not evaluated ([`trust-root.md`](trust-root.md) §3) |
| `trust_registry_root_not_authenticated` | content | trust roots were supplied, the trust registry holds, and root authentication stopped at a status whose effect is a failure ([`trust-root.md`](trust-root.md) §5) |
| `unsupported_version` | not evidence | a version gate fired (§5.5); it is the only error of an `UNSUPPORTED_VERSION` report |
| `internal_error` | not evidence | the verifier failed (§4); it is the only error of an `INTERNAL_ERROR` report |

The conditions "cannot be canonicalized" of the table's rows are not reachable from a document that
passed input strictness, whose rules make every such document canonicalizable. They are kept as a
defense in depth, and a verifier that never reports them conforms.

`registry_link_read_failed` covers `verification_receipt.json` in every run: the receipt is a
document the link reads, and a host failure to read it is reported whether or not a registry
entry is supplied, and never as a finding about the document's contract.

A registry entry supplied beside a bundle that carries no `verification_receipt.json` has nothing
to link: no error records it, the link is not established, and the run is `OFFLINE_REVIEW` with
the review reason `verification_receipt_not_provided` unless something fails. A trust registry
beside a link that does not hold or is `null` reaches no conclusion
([`registry-link.md`](registry-link.md) §7), and is an error only where a row of the table above
names the condition.

### 5.4 The authorization statuses

When the trust registry was evaluated, the report's `trust_registry` member is an object that
carries the three statuses; when it was not, `trust_registry` is `null` and the run has no
authorization status.

- `authorization_status` is a value of
  [`trust-registry-authorization.md`](trust-registry-authorization.md) §8, decided by that
  document's §6.
- `signature_status` is a value of the same section, or `null` when the evaluation stopped before
  the signature step.
- `trust_registry_root_signature_status` is a status of [`trust-root.md`](trust-root.md) §5 when
  root authentication was reached, and `ROOT_SIGNATURE_NOT_EVALUATED` on every path that stopped
  before it and when the host failed to read the trust-root document (§5.3,
  `trust_root_read_failed`).

The trust registry is evaluated only when a registry entry was supplied, satisfies its contract
and its link holds ([`registry-link.md`](registry-link.md) §7), whether or not an evaluation time
was supplied, and only when the host read it (§5.3, `trust_registry_read_failed`).

### 5.5 Unsupported versions

A version gate ([`document-contracts.md`](document-contracts.md), "Version gate") fires when an
object of a known type carries a well-formed version identifier other than the one this version
supports. The run stops at the first gate that fires: its report has `status` `UNSUPPORTED_VERSION`,
`verdict` `null`, `exit_code` `4`, `outcome.reason` `unsupported_version`, the single error
`unsupported_version`, `checks_established` `[]` and `review_reasons` `[]`, and it evaluates nothing
else. The error carries two members besides `code`, both normative:

- `object`: which object's gate fired, one of `trust_root_document`, `manifest`,
  `verification_receipt`, `reason_code_vocabulary`, `registry_entry`, `signing_payload` and
  `trust_registry`;
- `version`: the identifier as the object carries it; for the signing payload, its `payload_id`,
  `/` and its `payload_version` written as a decimal integer, such as
  `registry_entry_signing_payload_v3/3`.

A library interface returns this report as a command line does; for the trust-root document's
gate, a command line given no trust registry exits `64` instead (§4).

## 6. The informative per-check results

A report carries a `checks` object with eleven results: `manifest_sha256`, `manifest_files`,
`p1_sha256`, `canonical_input_present`, `p1_input_hash`, `envelope_present`, `envelope_sha256`,
`envelope_links`, `registry_signature`, `registry_link` and `trust_registry`. Their values are
three-valued as [`bundle-objects.md`](bundle-objects.md) §6 defines, except `registry_signature`,
which carries a signature status of
[`trust-registry-authorization.md`](trust-registry-authorization.md) §8, or `UNSUPPORTED` when no
signature was evaluated. A run that refuses its input as a whole (§5.3), and a run in which the host
fails to read a bundle member, report them as [`bundle-objects.md`](bundle-objects.md) §6 states for
such runs. Every digest the report restates is written in the self-describing form of
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §2.

They are informative (§2). The pinned conformance corpus declares them for a subset of runs, in
the `informative_checks` member of a run of `vectors/verify.json`;
a verifier whose report differs from those declarations only in a per-check result does not fail
to conform under this contract.

## 7. Implementations

This section is not normative.

Both reference verifiers report every member of §2, and their reports are comparable on all of
them. The Python reference verifier also carries informative members the TypeScript one does not:
`envelope`, `input`, `manifest`, `p1`, `registry`, `registry_link`, `tool` and `tool_version`.
Its `registry` member names, as `status`, whether the registry entry and trust registry were
used (`REGISTRY_ENTRY_LINK_NOT_EVALUATED` for an entry the run supplied but did not compare), and
its `registry_link` section restates the link check, so its `signature_verified`,
`trust_registry_verified` and `registry_inclusion_verified` are `false` on every run, which §2
reads as a statement about the link check alone. The TypeScript reference verifier reads directory
bundles and no archive, so the rows of §5.3 whose condition is about a ZIP archive alone never hold
for it. `bundle_root_invalid` is not one of them: its condition also names a directory input with no
`manifest.json`, and that half holds for this verifier as for any other. A regular file given to it
is refused as `unsupported_input`. That is the rule of §5.3 and not a fact about this
implementation: every verifier without archive intake reports that code for a regular file, whatever
the file holds, while the Python reference verifier, which reads archives, reports `invalid_zip` for
one that is not a readable ZIP archive and reads one that is. Being a library, the TypeScript
verifier raises a fault of its own instead of reporting `internal_error`. Its suite names those rows
rather than passing over them. It takes documents rather than paths, and the three values §4
requires are the symbols `DOCUMENT_PATH_NAMES_NOTHING`, `DOCUMENT_PATH_NAMES_NO_REGULAR_FILE` and
`DOCUMENT_READ_FAILED` it exports. The Python reference verifier takes the registry entry and the
trust registry as paths and reads them itself; its library takes trust roots as values, and the
values §4 requires for them are `DOCUMENT_PATH_NAMES_NO_REGULAR_FILE`, for the first two alike, and
`DOCUMENT_READ_FAILED` of `loquitur.verify.trust_root`.

## 8. Change control

Adding, removing or renaming a value of §3, §5.2 or §5.3, an exit code of §4 or an authorization
status of §5.4, or changing a rule that decides one, changes what a conforming verifier reports.
Each is a change of a closed vocabulary, and a protocol change under the change-control terms of
[`verification-vocabularies.md`](verification-vocabularies.md) §4: it needs updated schemas where
one carries the value, updated conformance vectors and a compatibility decision. The values of
§5.4 are defined in [`trust-registry-authorization.md`](trust-registry-authorization.md) §8 and
[`trust-root.md`](trust-root.md) §5, and change there under the same terms.
