# Verification checks

Status: normative.

This document defines the named checks the rest of the protocol is phrased
in, and the order in which they depend on one another. The checks are defined here, by the
specification, and not by an implementation whose own conformance is judged against them.

## 1. What a check is, and what it is not

A check names **which question has been answered**, not how well. Checks are cumulative in
evidence and independent in meaning: establishing `authorization` does not make `integrity`
stronger, and a run that did not request `authorization` has not failed it: it has not been asked.

A check is never a quality score, a risk rating, or a statement about the asset. It is a
statement about what a holder of the evidence was able to recompute.

A report names the checks a run requested and the checks it established
([`report-contract.md`](report-contract.md) §3.2). It names no level, number or rank: the names
below are the only identifiers of the checks.

## 2. The checks, in dependency order

| order | check | question | status in this version |
| --- | --- | --- | --- |
| 1 | `structure` | is this the shape of a Loquitur bundle | defined |
| 2 | `integrity` | are these the bytes that were committed to | defined |
| 3 | `link` | does this public entry refer to this private evidence, and to no other | defined |
| 4 | `authorization` | was the party who signed this entitled to, at the operator's time | defined |
| 5 | `transparency` | has the operator shown everyone the same thing | reserved |
| 6 | `anchoring` | can this be un-said | reserved |

**Dependency.** A check is established only when every check before it in this order is
established. A run that establishes `link` over a bundle whose `integrity` is not established has
established nothing about the link.

This prefix rule (`checks_established` is a prefix of `checks_requested`,
[`report-contract.md`](report-contract.md) §3.2) is the rule of this version of the contract; a
later version may replace the prefix by a dependency graph between the checks. The statuses of a
report carry the prefix `OFFLINE_` because they name the evaluation mode of this version, in which
the operator supplies every document and the verifier reads no network. The checks that need an
observation of the world, `transparency` and `anchoring`, will report through a separate member or
mode defined with them and will not reuse those statuses.

### 2.1 `structure`

The bundle is well formed: the files the manifest names are present, each object parses,
and each satisfies the closed field contract for its kind. Answers *is this the shape of a
Loquitur bundle*.

The published schemas cover the seven canonical object families in
[`introduction.md`](introduction.md) §7, and `manifest.json`, `p1.json` and `envelope_env1.json` are
not among them. What a verifier enforces in this check are closed field contracts (a fixed set of
permitted members, required members present, each of a declared type, and no others) applied to
those three bundle files, and to `verification_receipt.json` whenever it is present, against
`schemas/verification_receipt.schema.json` and the rules of
[`document-contracts.md`](document-contracts.md) §8 that the schema does not carry. A member the
contract does not name is a rejection, not an extension point. Where
[`bundle-objects.md`](bundle-objects.md) makes a member's type part of a later check instead, the
type is judged there and not here: a present link of the envelope (`bundle_id`,
`bundle_manifest_sha256`, `p1_sha256`) of another type fails its link in `integrity` and does not
break the contract ([`bundle-objects.md`](bundle-objects.md) §4). The three field sets are
enumerated in [`bundle-objects.md`](bundle-objects.md), because a field set that lives only inside
an implementation makes a second implementation conforming only by copying the first.

Passing `structure` says nothing about whether the contents are true, consistent, or authorized.

### 2.2 `integrity`

Every file digest recomputes to the value the manifest declares, and the manifest digest
recomputes to the value the envelope declares. Answers *are these the bytes that were
committed to*.

Digest self-consistency is not conformance: an object is trivially consistent with a
digest computed over itself, so `integrity` is meaningful only above an established
`structure`.

### 2.3 `link`

The registry entry's `manifest_hash` and `receipt_hash` recompute from the bundle in
hand. Answers *does this public entry refer to this private evidence, and to no other*.

`link` is where a public commitment stops being an assertion and becomes checkable. It says
nothing about who made the entry. Every comparison it makes, its exact operands and the three
values of its result are specified in [`registry-link.md`](registry-link.md).

### 2.4 `authorization`

The entry's signature verifies under a key the trust registry authorizes for that issuer,
for that scope, at the operator's evaluation time, and the key is neither revoked, suspended, nor
outside its validity window; and a trust root the operator pinned authenticates the trust
registry at that time. Answers *was the party who signed this entitled to*. The evaluation time,
the lifecycle states, the windows, the scope, the order of evaluation and the statuses are
specified in [`trust-registry-authorization.md`](trust-registry-authorization.md).

The trust registry is a document the verifier was handed, and authenticating it against a root is
part of this check: without a pinned root the check is not established (the run is at
most `OFFLINE_REVIEW`), and a verifier does not assume it is. The exact bytes a root signs, the shape of
the trust-root document, and the order a verifier evaluates them in are specified in
[`trust-root.md`](trust-root.md).

### 2.5 `transparency`

An entry is provably included in an append-only log whose history can be shown to extend
what it showed before. Answers *has the operator shown everyone the same thing*.

The adversary changes here: `structure` to `authorization` constrain the issuer,
`transparency` constrains the **operator**.

Status: reserved, never requested and never reported. The name is reserved so that the order is
complete; its definition is planned for a later version of the protocol. No log is operated, this
repository specifies no tree head, `log_id`, checkpoint, inclusion proof or consistency proof, and
no reference package computes or verifies any of them.

Two things are already clear, and the definition has to respect both. First, inclusion and
consistency proofs alone do not show that every reader was shown the same history: a log can
give each reader a history that is consistent in itself and different from the one it gives
another reader, and every proof each reader checks will hold. Showing that the histories are
the same takes observation from outside the log, such as independent parties comparing the tree
heads they were shown. Second, the cryptographic part of the check, a proof checked against a tree
head and the signature on that tree head, can be checked from local files; whether the tree head is
current, and whether it is the one other readers see, cannot.

### 2.6 `anchoring`

A commitment is placed where the operator cannot retract it, so that the time and content
of a publication are attested by something outside the protocol. Answers *can this be
un-said*.

Status: reserved, never requested and never reported; no anchoring is live. What an anchor must
commit to is fixed in [`anchor-commitment.md`](anchor-commitment.md), so the meaning is settled
before the mechanism exists.

The anchor names its method, a value of the registered vocabulary `anchoring_method`
([`verification-vocabularies.md`](verification-vocabularies.md) §5), and no method is checked in
this version.

As for `transparency`, the check divides. That an anchoring record commits to the bytes in hand is
cryptographic and can be checked from local files, given a copy of the record. That the record
is final, and when it became so, needs observation of the system that carries it.

## 3. Two properties that constrain every check

**`structure` to `authorization` are offline and complete.** Each is decidable from the bundle,
the entry, the trust registry, the trust-root document and the operator's evaluation time in hand,
with no network, no service and no dependency on the party that issued the evidence. That is the
protocol's central claim, and it is why the offline checks stop at `authorization`:
**`transparency` and `anchoring` cannot be completed offline.** Their cryptographic parts can be
checked from local files, as every check before them is. Freshness and finality, which both
exist to establish, need observation from outside the files in hand, because both ask about
something that happened elsewhere. A verifier that reported either from local files alone
would be reporting a belief, not a check.

**Absence is not failure.** A report whose `checks_established` is
`["structure","integrity","link"]` has not failed `authorization`. The distinction matters in both
directions: a consumer must not read a short list as a negative finding, and a producer must not
present a short list as a complete one. The checks a verifier requested and established are
reported explicitly for this reason, rather than being inferred from a verdict.

## 4. Verification modes

This section is informative. It names the postures a verifier can be in; the checks of §2 and the
documents they cite are what binds.

The protocol names three verification postures, and this version defines two of them: offline
and link verification. Version 0.1 has no online retrieval: a verifier fetches nothing, and every
document it reads, a registry entry included, reaches it as a local file
([`threat-model.md`](threat-model.md) §3).

### 4.1 Online verification

Status: reserved and not defined in this version. The name is kept for a posture in which a
verifier would retrieve the registry entry itself rather than be handed it. This version defines no
service to query, no retrieval procedure and no check for this posture, and the reference verifiers
do not perform it. A registry entry obtained by any means is evaluated from the local file, as in
§4.3, and anchoring stays reserved (§2.6).

### 4.2 Offline verification

A verifier examines a private bundle or disclosed package without depending on any hosted
service. Offline verification requires access to the private material, or to a registry entry
supplied by the operator ([`registry-link.md`](registry-link.md)).

### 4.3 Link verification

A verifier holds both private material and a public registry commitment and checks that the private
material corresponds to the public commitment.

### 4.4 Limits

Verification output is not investment advice, legal advice, regulatory approval, valuation approval,
source-document truth, or a replacement for independent due diligence.

## 5. Change control

The set of checks and their order are closed for protocol release 0.1. Adding, removing,
renaming or reordering a check is a breaking protocol change requiring normative vectors and
support in every consumer, because the names appear in reports that third parties parse.
