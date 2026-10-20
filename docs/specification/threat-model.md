# Threat model

Status: normative.

This document states what Loquitur verification defends against, what
it does not, and which of the remaining risks a relying party carries itself. The other
documents here describe mechanisms; this one says which adversary each check answers, which a
verifier written from the specification needs to know to be correct. The rules below are
phrased as requirements on any conforming verifier, not as a description of one
implementation.

This document serves as the security considerations of the specification
([`introduction.md`](introduction.md) §9).

> **Non-normative note on citations.** A citation of the form `<module>.py::<name>` names a
> function, class or constant defined in `src/loquitur/verify/<module>.py` of
> `loquitur-verify-py`, the reference implementation, which is a separate repository and not
> part of this one. The citations resolve in release `0.1.0` of `loquitur-verify-py`. They name no line, so that they stay true of a later version for as
> long as the named definition does what they cite it for, and this repository's tests check each
> of them against the source of a `loquitur-verify-py` checkout placed beside it, and that
> checkout's version against the release named here. The citations are provenance and are not
> part of the protocol.

## How to read the citations

Requirements are stated in prose and are complete on their own. Where a claim is about
observed behavior rather than about the rule, it carries a citation of the form
`<module>.py::<name>`, naming a definition in `loquitur-verify-py/src/loquitur/verify/<module>.py`.
Those citations are evidence that the rule is implemented and provenance for anyone
maintaining it. They name definitions in `loquitur-verify-py`, a separate repository, and
nothing in this document depends on opening them: if a citation and the prose ever disagree,
the prose is what the protocol says.

Where another normative document of this repository specifies a rule, this document refers
to that section instead of citing code. The citations concern members of the report that
[`report-contract.md`](report-contract.md) §2 makes informative, or the mechanics of the reference
implementation, which no conforming verifier has to reproduce beyond what the prose states.

Section 11 records how every behavioral claim in this document was observed, and what the
observation produced. Nothing here is asserted from reading code alone unless it is
labeled as a rule rather than an observation.

---

## 1. What is being protected

Three things, in decreasing order of how much the protocol can do about them.

**The correspondence between a public commitment and private evidence.** A registry entry
commits to digests of a bundle. The property under attack is that exactly one bundle
satisfies a given entry, and that the holder cannot substitute another. This is the
property the protocol protects best, because it is decidable from the two documents alone.

**The attribution of that commitment to an authorized issuer.** A registry entry carries a
signature and names an issuer and a key. The property under attack is that only a party
holding an authorized key could have produced it. This is protected conditionally: the condition is
the subject of section 5, and it is the single most important limit in this document.

**The verifier process itself.** A bundle is attacker-supplied input processed on a
counterparty's machine. The property under attack is that a verdict is always produced,
and that no path derived from attacker-controlled bytes resolves outside the extraction
directory. (The registry entry, the trust registry and the trust root are paths the *caller* names,
and are read wherever the caller says; that is the caller's choice, not the bundle's.) This is
protected by input gates, described in section 7.

Two things are deliberately *not* protected, and no configuration changes that: the truth
of the underlying evidence about the real world, and the confidentiality of a bundle once
its holder has disclosed it.

## 2. What a verdict asserts

A verdict is one of `PASS`, `REVIEW` or `FAIL`, reported alongside a status
(`OFFLINE_OK` / `OFFLINE_REVIEW` / `OFFLINE_FAIL`) and a process exit code:

| exit | meaning |
| --- | --- |
| `0` | `OFFLINE_OK` / `PASS` |
| `1` | `OFFLINE_FAIL` / `FAIL` |
| `2` | `OFFLINE_REVIEW` / `REVIEW` |
| `3` | internal error: the verifier failed, not the evidence |
| `4` | unsupported version: an object of a later version; upgrade the verifier, no verdict was computed |
| `5` | host failure: the host failed on the operator's path or working space; no verdict was computed |
| `64` | usage error: the invocation was wrong; no verdict was computed |

The taxonomy, the status a run reaches and the reasons it reports are normative in
[`report-contract.md`](report-contract.md) §3 to §5; this table restates them.

A `PASS` asserts exactly this, and only for the checks the report lists in
`checks_established` ([`report-contract.md`](report-contract.md) §3.2):

> Every digest recomputed from the material supplied recomputes to the value some other
> supplied document declares, every supplied document satisfies its closed field
> contract, and, where `authorization` was requested, the entry's signature verifies under
> a key that the trust registry supplied to the verifier authorizes for that issuer, that
> scope, and the operator's evaluation time, and a root the operator pinned authenticates that
> registry.

A `PASS` does **not** assert that the trust registry is authentic beyond the root the operator
pinned (section 5), that the key was inside its window when the entry was signed (section 6), that
the evidence describes the world correctly, that the entry appears in any registry anyone else can
see, that a value is right, or that any party is who it says it is outside the trust material handed
over.

`REVIEW` means *not established*, not *bad*. It is the verdict for questions the verifier
could not answer: canonical input absent so the input-hash link cannot be rebuilt
([`bundle-objects.md`](bundle-objects.md) §6), bundle members present that the manifest never
declared ([`bundle-objects.md`](bundle-objects.md) §1), a registry entry whose committed verdict is
`WARN` or `REVIEW` ([`registry-link.md`](registry-link.md) §6), no evaluation time, or no pinned
trust root ([`trust-root.md`](trust-root.md) §2). The report lists each such question in
`review_reasons` ([`report-contract.md`](report-contract.md) §3.3). A consumer that treats `REVIEW`
as success has taken on the risk the verifier explicitly refused to absorb. The CLI's
`--accept-review` option does that for the reasons the operator names, and only for them; section 10
says what follows from using it.

**Absence of a check is not a negative finding.** A report whose `checks_established` is
`["structure","integrity"]` has not failed `authorization`; it was not asked. The report states
the checks the caller requested and the checks that were established
([`report-contract.md`](report-contract.md) §3.2), and a consumer must read them rather than infer a
scope from a verdict.

## 3. Trust boundaries

```text
   issuer's control                    │  counterparty's control
                                       │
   bundle (manifest, p1, canonical     │   verifier process
   input, envelope, receipt) ──────────┼──►  extraction dir (temporary)
                                       │
   registry entry (signed) ────────────┼──►  entry parsing + link checks
                                       │
   trust registry ─────────────────────┼──►  issuer authorization
                                       │
                      ┌────────────────┤
   trust root document│  OUT OF BAND   │──►  registry authentication
   evaluation time    │  (operator)    │──►  evaluation clock
                      └────────────────┤
```

Everything crossing the boundary from the left is untrusted input, including the trust
registry. The only inputs that carry authority are the ones an operator supplies from
outside the evidence: the trust-root document and the evaluation time. Version 0.1 defines
no time-stamp authority as a source of the instant
([`trust-registry-authorization.md`](trust-registry-authorization.md) §2). The verifier fetches
nothing: every input arrives as a local path, and there is no network path in the verdict
computation at all.

---

## 4. Adversaries

Five, named by what they control.

### A1 — An issuer who tampers with evidence after issuance

**Capability.** Holds the bundle and the entry it already published. Can rewrite any
bundle file, add or remove files, and recompute every digest inside the bundle, because
**nothing in the bundle is signed**. Cannot re-sign the registry entry to match without
its issuing key, and cannot alter an entry another party already holds.

**What the protocol does.** The registry entry commits to `manifest_hash` and
`receipt_hash`, and a conforming verifier MUST recompute both from the bundle in hand and
compare ([`registry-link.md`](registry-link.md) §3). Both are hard checks: an unevaluated hard check
is a failure, not a pass ([`registry-link.md`](registry-link.md) §3 and §5). Within the bundle, the
envelope binds `bundle_id`, `bundle_manifest_sha256` and `p1_sha256`, all three of which are
required members of a conformant envelope, so an envelope that binds nothing is a shape failure
rather than a clean report ([`bundle-objects.md`](bundle-objects.md) §4). Each of the three links
must have been *evaluated and held*; a link that could not be evaluated leaves the envelope
unverifiable, which is `REVIEW` ([`bundle-objects.md`](bundle-objects.md) §4 and §6). A link claim
that is present but malformed fails the link it claims to make, rather than being skipped
([`bundle-objects.md`](bundle-objects.md) §4). The expected `bundle_id` is never derived from the
filesystem, because for a ZIP the extracted root name is a string the counterparty wrote
([`bundle-objects.md`](bundle-objects.md) §2 and §4).

Adding a file is caught separately: the manifest is the inventory the entry commits to, so
the whole bundle tree is enumerated and any member the manifest does not declare is
reported and downgrades the manifest layer to `REVIEW` ([`bundle-objects.md`](bundle-objects.md)
§1). Observed: adding `smuggled.txt` to an otherwise valid bundle gives `OFFLINE_REVIEW` / exit 2
with note `bundle_extra_files`.

**What it explicitly does not do.** Local integrity alone cannot detect this adversary at
all. Observed, and this is the sharpest single result in this document: a bundle whose
`canonical_input.json` was altered and whose `p1.ih`, `p1.sha256`, `manifest.files`,
`manifest.sha256`, envelope links and `envelope.sha256` were all recomputed verifies as
`OFFLINE_OK` / `PASS` / exit 0 with only `structure` and `integrity` requested and every check
`true`. Supplying the public registry entry, with nothing else changed, turns the same
bundle into `OFFLINE_FAIL` / exit 1 with `link.manifest_hash: ok=false`.

> **Requirement.** A verifier MUST NOT present a `PASS` that established only `structure` and
> `integrity` as evidence that a bundle was not modified after issuance. Those two checks
> establish internal consistency. Only a commitment made outside the bundle (the registry entry,
> through the `link` check) establishes that these are the bytes that were committed to.

A second, narrower limit: `p1.ih` commits only to the keys named in `p1.ik`. Observed on
the `link_valid_bundle` fixture, whose projection omits `asset_id`, altering `asset_id`
leaves `p1_input_hash: true`; it is the whole-file digest in `manifest.files` that catches
it (`manifest_files: false`). A projection is a statement about the projected keys and
about nothing else. `ik: []` is refused rather than assigned a meaning, because a
projection over no keys commits to nothing ([`bundle-objects.md`](bundle-objects.md) §3).

### A2 — An issuer who mints the entire trust chain

**Capability.** Generates its own signing key, writes a trust registry authorizing that
key for whatever issuer identity, asset type and workflow it likes, signs a registry entry
with it, and hands the counterparty the bundle, the entry and the registry together. Every
document is internally perfect. This is the adversary the whole of section 5 is about, and
it is the one a naive reading of "the authorization check verified the signature" gets wrong.

**What the protocol does in the `authorization` check.** Against a *dishonest registry operator*, an
adversary who supplies a registry that is not the one it claims to be or a stale one, these checks
are real, and a conforming verifier MUST perform all of them. Their exact conditions, order and
statuses are specified in [`trust-registry-authorization.md`](trust-registry-authorization.md), and
each check below names its section:

- The trust registry is validated against the closed generated contract before anything is
  read from it, because every downstream check inherits its authority
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §3 and §6, rows 1 and 3).
- The registry entry is validated against the closed generated contract, so a smuggled
  extra field cannot ride inside a signed entry ([`registry-link.md`](registry-link.md) §2, and
  [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness", rule 8).
  All three instant fields are checked as *calendar* instants, not merely against a pattern, so
  `2026-02-30` in an unused field cannot pass.
- The signature is verified over domain-separated bytes: a fixed prefix plus the JCS
  canonicalization of a closed envelope that binds the algorithm into the signed message
  ([`signing-envelope-v2.md`](signing-envelope-v2.md)). Algorithm substitution therefore changes the
  message and fails.
- The signature's `key_id` **and** the entry's `issuer_key_id` must both equal the key the
  registry authorized ([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, rows
  18 and 19): matching one and not the other is a key mismatch, not a pass.
- A duplicated `(issuer_id, issuer_key_id)` pair has no well-defined authority and MUST be
  refused rather than resolved by array order
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §5). This is a revocation
  bypass if handled the other way: a registry carrying the same key twice, once `revoked` and once
  `active`, would authorize a revoked key whenever the active duplicate happened to come first.
  The same holds for one public key under two labels: a trust entry found that shares its point
  with another trust entry of the registry, under any issuer and in any status, MUST be refused as
  well ([`trust-registry-authorization.md`](trust-registry-authorization.md) §5 and §6, row 6).
- Revocation is reported before suspension, and both before the window
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, rows 7 and 8); the
  registry window and the key window are then applied (rows 9 to 12), with the registry's own
  staleness deferred so that a revoked key behind a stale copy is still reported as revoked
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §4).
- Scope is enforced: the entry's `asset_type` and `workflow` must both be in the key's
  allow-lists ([`trust-registry-authorization.md`](trust-registry-authorization.md) §5).
- No signing payload before v2 is defined ([`signing-envelope-v2.md`](signing-envelope-v2.md),
  "Legacy migration policy"): a signature object stripped of `payload_id` and `payload_version`
  breaks the entry's contract, and no verifier offers an option to verify it.

**What it explicitly does not do.** Every one of those checks is satisfied trivially by a
party that wrote the registry, because each one asks whether the registry authorizes the key, and
the registry is the adversary's own document. The property that separates this adversary from an
honest issuer is *authentication of the trust registry itself* against a root pinned out of band,
and it is stated in full in section 5. Separately, nothing in the protocol establishes that an
issuer identifier corresponds to a real-world legal entity; the report says so in its own notes,
`issuer_real_world_identity_not_verified_beyond_supplied_trust_registry`
(`trust_registry.py::verify_registry_entry_trust`).

### A3 — A party who alters a bundle in transit

**Capability.** Full read/write over the bundle and the entry as they move between issuer
and counterparty. Cannot forge an issuer signature. Can, however, rewrite any unsigned
field.

**What the protocol does.** The entry's signature covers the entry, so an interceptor who
alters `manifest_hash` to match a substituted bundle invalidates the signature, provided the
counterparty requests the `authorization` check. Under the `link` check alone the signature is never
evaluated: the report carries `checks.registry_signature: "UNSUPPORTED"` and
`registry_link.signature_verified: false` ([`registry-link.md`](registry-link.md) §8,
[`report-contract.md`](report-contract.md) §6; `runner.py::_registry_link_dict` for
`signature_verified`), so an interceptor who alters bundle **and** entry consistently produces a
report that passes. Observed on the link fixture pair: `REGISTRY_ENTRY_LINK_VERIFIED`, exit 0, with
`registry_signature: UNSUPPORTED` and `checks_established` `["structure","integrity","link"]`. The
`link` check answers *does this entry refer to this bundle*, not *is this the entry the issuer
published*.

Three unsigned fields are worth naming explicitly, because the exclusion looks like an
oversight and is not. `signature`, `anchor` and `anchored_at` are excluded from the
signing payload ([`signing-envelope-v2.md`](signing-envelope-v2.md)), for the reason
[`anchor-commitment.md`](anchor-commitment.md) gives: the anchor cannot exist until the entry is
signed, so the issuer cannot sign it. The consequence is that **an anchor claim on a registry entry
is unattributable**. Observed: a fabricated `anchor` (`method: blockchain_transaction`, `system:
eip155:1`, an invented `anchor_reference`) and an `anchored_at` injected into a validly signed
entry, with no key, still yields `signature_status: VALID_SIGNATURE`. The report says
`anchor_finality_verified: false`, which is the honest reading; a consumer that displays the anchor
as though it meant something has manufactured a claim the protocol does not make.

The envelope is the same case inside the bundle. `envelope_env1.json` is checked only against its
own unkeyed sidecar and through its three links, and nothing the issuer signed commits to it
([`bundle-objects.md`](bundle-objects.md) §4). A party with no key can rewrite its subject
identifiers (`asset_id`, `asset_type`, `receipt_id`), its anchor and provenance metadata (`ts`,
`network`, `p1_txid`, `uri`) and its embedded `registry_entry`, recompute `envelope.sha256`, and the
run still reaches `PASS` with every check established. The verdict is not wrong about the signed
objects, but those members are not issuer-authorized, and a consumer that shows them as part of a
verified bundle shows claims nobody signed.

**What it explicitly does not do.** There is no transport integrity, no channel binding,
and no replay window. A bundle and entry that verified once verify the same way forever at the
same evaluation time, with the same trust registry and trust-root document, by design (offline
replayability is the point), which means an interceptor's copy is as good as the original.
Confidentiality of disclosed evidence is entirely outside the protocol.

### A4 — A malicious bundle author attacking the verifier

**Capability.** Authors the archive bytes with no constraint whatsoever. Wants the
verifier process to read or write outside its extraction directory, to consume unbounded
resources, to crash with a traceback instead of returning a verdict, or to be tricked into
verifying different bytes than the ones it reports on.

This is the adversary with the most concrete mitigations, and section 7 gives the whole
list with observed outcomes for each. Archive member names are validated
before any extraction, including forms that are distinct as strings but name one file on a
real filesystem; symlink members, encrypted members, unsupported compression methods,
oversized members, oversized totals, excessive member counts and suspicious compression
ratios are refused;
extraction is exclusive-create so that any collision the name gate did not anticipate is a
hard failure rather than a silent last-member-wins substitution; and JSON parsing rejects
duplicate member names, non-finite numbers, invalid UTF-8 and nesting deeper than 64
levels.

**What it explicitly does not do.** The limits are fixed constants
([`bundle-objects.md`](bundle-objects.md) §5): 512 file entries, 20 MiB per member, 50 MiB total, a
compression ratio of 100:1 for every member whatever its size, stored and deflated entries only, and
no encrypted entry. They are not configurable, so a deployment with a legitimately larger bundle
cannot raise them and a deployment wanting tighter limits cannot lower them. There is no wall-clock
or memory ceiling on the verification itself beyond those input bounds. The entry limit counts file
entries only: an archive's directory entries are not bounded, and intake time grows with their
number, so a host that needs a time bound bounds the archive's size or its entry count before it
calls the verifier ([`bundle-objects.md`](bundle-objects.md) §5). The gates are input-safety gates:
a member that passes them is safe to write into a temporary directory, and is not thereby trusted
evidence ([`bundle-objects.md`](bundle-objects.md) §5).

### A5 — A party who relies on a verdict for more than it says

**Capability.** No technical capability at all. Reads `PASS`, or exit code 0, and treats it
as a statement the protocol never made: that an asset is worth what a document says, that
an issuer is licensed, that a commitment is on a chain, that a receipt is current.

This is the adversary the protocol is least able to constrain and most likely to meet.
Everything the code does about it is a reporting discipline:

- `outcome.not_implemented_capabilities`, which the Python reference verifier carries in
  **every** report, pass or fail, names what the run did not verify
  ([`report-contract.md`](report-contract.md) §2).
- `checks_requested` and `checks_established` name what was asked and what was established,
  computed per run rather than constant ([`report-contract.md`](report-contract.md) §3.2), and
  `review_reasons` names every question left open ([`report-contract.md`](report-contract.md) §3.3).
- `registry.status`, an informative member of the Python reference verifier's report
  ([`report-contract.md`](report-contract.md) §7), distinguishes `TRUST_REGISTRY_VERIFIED` from
  `TRUST_REGISTRY_ROOT_NOT_AUTHENTICATED` from `TRUST_REGISTRY_AUTHORIZATION_NOT_ESTABLISHED`
  (no evaluation time, or a window that does not hold it) from `TRUST_REGISTRY_FAILED`, because
  "verified" for a registry whose root was never authenticated is the sentence a
  counterparty quotes back (`runner.py::_registry_dict`).
- `trust_registry.evaluation_time_source` names whose clock was used
  ([`trust-registry-authorization.md`](trust-registry-authorization.md) §2).
- The registry entry's committed verdict is enforced at report level, so an entry
  publicly committing `FAIL` cannot produce exit 0 ([`registry-link.md`](registry-link.md) §6).

**What it explicitly does not do.** Nothing prevents a consumer from reading only the exit
code. Section 10 is written for the operator who must close that gap organizationally.

---

## 5. The trust-root property, stated exactly

This is the property most likely to be misread, so it is stated mechanically.

**The rule.** A verifier that has no pinned trust root MUST NOT return `PASS` for a
registry entry verified against a trust registry. Absent a cause of `FAIL`, it MUST return
`REVIEW`. Refusing is not accusing: the evidence may be perfect and the verifier cannot say who vouches for
the registry.

**The mechanism, in three parts.**

1. `PINNED_TRUST_ROOTS` is an **empty tuple** in the shipped package
   (`trust_root.py::PINNED_TRUST_ROOTS`). Populating it is a governance act that follows the
   generation of a root key and never precedes it. No root key exists, so none is shipped.

2. Root verification is *computed*, not asserted. With no roots,
   `verify_trust_registry_root_signature` returns immediately with
   `ok=False, status="NO_PINNED_TRUST_ROOT"` ([`trust-root.md`](trust-root.md) §5, row 1). The
   ordering matters: this return happens **before** the registry's signature object is examined at
   all. A registry carrying a placeholder string where a signature should be reaches the same
   `NO_PINNED_TRUST_ROOT` outcome as one carrying a real signature, which is correct, because
   without a root there is nothing to check either against, but it means the status must be read as
   *not evaluated for authenticity*, never as *signature checked and found acceptable*.

3. The runner branches on three cases ([`trust-root.md`](trust-root.md) §6):

   | caller supplied roots | root verified | outcome |
   | --- | --- | --- |
   | no | — | review reason `trust_registry_root_not_pinned` → `REVIEW`, exit 2 |
   | yes | no | error `trust_registry_root_not_authenticated` → `FAIL`, exit 1 |
   | yes | yes | no downgrade; `PASS` if everything else holds, exit 0 |

   A review reason makes the run `OFFLINE_REVIEW` unless a failure holds, and `authorization`
   is then absent from `checks_established` ([`report-contract.md`](report-contract.md) §3). The
   distinction between the row with no roots and the row whose roots did not verify is deliberate:
   the second is an operator who asked "is this registry authentic" and got *no*; the first is an
   operator who never asked.

**Observed.** A trust chain minted end to end (a fresh secp256k1 issuer key, a trust
registry naming issuer `issuer_definitely_not_a_real_bank` and authorizing that key for
exactly the entry's asset type and workflow, a registry entry signed with it, and a
separate root key signing the registry) against the honest fixture bundle, with
`--evaluation-time 2026-05-10T00:00:00Z`:

```text
A. no --trust-root (PINNED_TRUST_ROOTS empty)
   OFFLINE_REVIEW / REVIEW / exit 2
   outcome           : warning_or_review_state | trust_registry_root_not_pinned
   review_reasons    : trust_registry_root_not_pinned
   checks_established: structure, integrity, link
   registry status   : TRUST_REGISTRY_ROOT_NOT_AUTHENTICATED
   authorization     : AUTHORIZED_ACTIVE_KEY  signature_status=VALID_SIGNATURE  signature_verified=True
   root_signature    : verified=False status=NO_PINNED_TRUST_ROOT

B. operator pins a root the rogue registry was not signed by
   OFFLINE_FAIL / FAIL / exit 1
   outcome           : trust_root_authentication_failure | trust_registry_root_not_authenticated
   checks_established: structure, integrity, link
   root_signature    : verified=False status=UNKNOWN_ROOT_KEY
```

Read case A carefully. Every other `authorization` check passed (`AUTHORIZED_ACTIVE_KEY`,
`signature_verified=True`) on a chain the adversary minted in its entirety. The *only* thing
standing between that chain and exit 0 is the root gate. That is the whole security value of
`--trust-root`, and it is why the empty default must be understood as a refusal and not as a gap.

**What pinning a root does not do.** It authenticates the registry document. It does not
establish that the root key belongs to any particular organization; that binding is
whatever process the operator used to obtain the root document, and the protocol has no
opinion about it. It does not verify a certificate chain: a root here is a bare secp256k1
public key with a validity window and a status, on a closed field set
([`trust-root.md`](trust-root.md) §3). Reading roots from the registry they authenticate would be
circular and is refused by construction: the document must be a separate file
([`trust-root.md`](trust-root.md) §3).

**Pinned roots have no scope.** A root in this version carries no issuer, operator or registry
scope, and every pinned root is authoritative for every `issuer_id`
([`trust-root.md`](trust-root.md) §1). Pinning the roots of two registry operators together merges
their authority: either one can sign a trust registry that authorizes its own key under an issuer
the other governs, and an entry signed with that key reaches `PASS` with `authorization`
established. No key needs to be stolen: the holder of either root can do it, which section 15
otherwise describes only as the compromise of a root. An operator that pins more than one root trusts each of them for every issuer, and
[`trust-root.md`](trust-root.md) §1 says how to keep authorities apart.

**Sharp edges a conforming verifier must reproduce.** Two pinned roots sharing a `key_id`, or a
matched root sharing its point with another pinned root, have no well-defined authority and MUST be
refused rather than resolved by list order or by status (`AMBIGUOUS_ROOT_KEY`,
[`trust-root.md`](trust-root.md) §5, row 7). Revocation MUST be reported
before the validity window, because a root revoked inside a lapsed window must read as revoked: the
remedies differ ([`trust-root.md`](trust-root.md) §5, rows 8 to 10). An entry that failed earlier
and never reached root authentication MUST report `ROOT_SIGNATURE_NOT_EVALUATED`, which is a
different fact from `NO_PINNED_TRUST_ROOT` ([`trust-root.md`](trust-root.md) §5,
[`trust-registry-authorization.md`](trust-registry-authorization.md) §7).

---

## 6. The evaluation clock

The `authorization` check asks whether a key was valid *at some instant*. The choice of instant
decides the verdict, so the choice of *who supplies it* is a trust decision.

**Issuer dates never decide.** The entry's `effective_at`, `issued_at` and `anchored_at` are
written by the issuer, and no verifier reads them as a time at which to judge a key, a registry
or a root ([`trust-registry-authorization.md`](trust-registry-authorization.md) §2). The evaluation
time is the operator's `--evaluation-time`. Without it, authorization is not established: the run is
`REVIEW` with the review reason `evaluation_time_not_provided`, while a revoked key, a broken
contract or a bad signature still fail it.

**Why that matters.** The key-window checks run before the signature check
([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, rows 11 and 12 before rows
14 to 20), so whoever chose the instant would decide whether the key is inside its validity window.
A protocol that read the issuer's dates would let the issuer decide: one second of back-dating would
move an entry into the window of an expired key, and an issuer holding the key can re-sign the
back-dated entry. Observed with `--evaluation-time 2026-05-10T00:00:00Z`, against a trust registry
whose key expires at `2026-05-09T23:59:59Z`:

```text
entry as issued   (effective_at 2026-05-10T00:00:00Z) → OFFLINE_REVIEW / 2, ISSUER_KEY_EXPIRED
entry back-dated  (effective_at 2026-05-09T23:59:59Z) → OFFLINE_REVIEW / 2, ISSUER_KEY_EXPIRED
```

Both runs report the review reason `issuer_key_outside_validity_window`: the entry's dates do not
move the instant the key is judged at, so back-dating gains the issuer nothing.

**The remedy, and its limits.** This version has one source of the evaluation time, the
operator ([`trust-registry-authorization.md`](trust-registry-authorization.md) §2). The operator's
clock answers whether the key is in its window *now*, not whether it was when the entry was signed:
no time attested to the signature exists in this version. A key, a registry or a root whose window
does not hold the operator's time therefore leaves authorization not established (`REVIEW`, with
`issuer_key_outside_validity_window`, `trust_registry_not_current` or
`trust_root_outside_validity_window`), not failed. A revocation is not a window, and fails the run
at every time.

**A third party's clock is not a source in this version.** An instant attested by a time-stamp
authority, an anchor or a timeliness record would take the clock from both parties, and this
version defines no such source; `--tsa-token` is not an option, and a command line refuses it as
an unknown option ([`report-contract.md`](report-contract.md) §4.1).

The reference implementation carries no time-stamp code: no token parser, no pinned
authority, no verification backend and no seam for one. The policy that
`LCP-0005` recorded for a time-stamp seam in that implementation binds nothing
(`change-proposals.md`, "A recorded policy that binds nothing"); a later version that admits a
third-party clock defines its source, its binding to the evidence and its authority pinning
in this specification, not in an implementation.

**Determinism.** The accepted instant form is exactly `YYYY-MM-DDTHH:MM:SSZ` and nothing
else ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness", rule
8). This is not pedantry: a laxer parser that accepted a date-only form would produce a *naive*
datetime, read in the host's local time, so the same signed evidence would be evaluated up to ~26
hours apart on two counterparties' machines. Replayability is the product; a verdict that depends on
where it was computed is not one.

---

## 7. The verifier as target — observed outcomes

Every row below was produced by running the Python reference verifier, which reads archives,
against a purpose-built hostile input. All are `OFFLINE_FAIL` / exit 1; none produced a
traceback, and none produced a verdict other than a refusal. Archive intake is optional
([`report-contract.md`](report-contract.md) §5.3), so the rows whose input is an archive bind only a
verifier that has it: every row whose Rule column cites [`bundle-objects.md`](bundle-objects.md) §5,
the `two bundle roots` row, whose ambiguity can arise only inside an archive
([`bundle-objects.md`](bundle-objects.md) §1), and the `not a ZIP` row, whose input a verifier
reading directory bundles only refuses as `unsupported_input` instead. Every other row's input is a
directory bundle, and the rule it cites binds every conforming verifier.

The second column gives the `errors[].code` of [`report-contract.md`](report-contract.md) §5.3 and,
after a colon, the error's informative `message`. A run with no error gives its `outcome.reason`
instead, then the informative note or per-file result that names the cause.

| Hostile input | Reported (code, then informative message) | Rule |
| --- | --- | --- |
| `../escaped.txt` member | `archive_unsafe_member:unsafe_zip_member:traversal` | [`bundle-objects.md`](bundle-objects.md) §5, rule name |
| `/etc/pwned` member | `…:absolute_path` | [`bundle-objects.md`](bundle-objects.md) §5, rule name |
| `sub\x.json` member | `…:backslash` | [`bundle-objects.md`](bundle-objects.md) §5, rule name |
| POSIX symlink member | `…:symlink` | [`bundle-objects.md`](bundle-objects.md) §5, rule type |
| POSIX FIFO member | `…:type` | [`bundle-objects.md`](bundle-objects.md) §5, rule type |
| `p1.json::$DATA` (NTFS ADS alias) | `…:stream_or_drive_alias` | [`bundle-objects.md`](bundle-objects.md) §5, rule name |
| `p1.json.` (NTFS trailing-dot alias) | `…:trailing_dot_or_space` | [`bundle-objects.md`](bundle-objects.md) §5, rule name |
| `P1.JSON` beside `p1.json` | `…:duplicate_path` | [`bundle-objects.md`](bundle-objects.md) §5, rule duplicate |
| a file `a` and a member `a/b` | `…:duplicate_path` | [`bundle-objects.md`](bundle-objects.md) §5, rule duplicate |
| 8 MiB of zeros, deflated | `archive_safety_limit:zip_suspicious_compression_ratio` | [`bundle-objects.md`](bundle-objects.md) §5, rule ratio |
| 500 000 zero bytes, deflated | `…:zip_suspicious_compression_ratio` | [`bundle-objects.md`](bundle-objects.md) §5, rule ratio |
| 4 × 15 MiB members | `…:zip_total_uncompressed_size_too_large` | [`bundle-objects.md`](bundle-objects.md) §5, rule total |
| 600 members | `…:zip_too_many_files` | [`bundle-objects.md`](bundle-objects.md) §5, rule count |
| bzip2 compression | `…:zip_unsupported_compression_method` | [`bundle-objects.md`](bundle-objects.md) §5, rule method |
| an encrypted member | `…:zip_encrypted_member` | [`bundle-objects.md`](bundle-objects.md) §5, rule method |
| two bundle roots | `bundle_root_invalid:ambiguous_bundle_root` | [`bundle-objects.md`](bundle-objects.md) §1 |
| not a ZIP | `invalid_zip` | [`report-contract.md`](report-contract.md) §5.3 |
| duplicate JSON member name in `p1.json` | `p1_verification_failed:duplicate_json_key:p1.json:ih` | [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness", rule 1 |
| 20 000-level nested JSON | `p1_verification_failed:json_nesting_too_deep:canonical_input.json` | [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness", rule 6 |
| `NaN` in canonical input | `p1_verification_failed:non_finite_json_number:NaN:canonical_input.json` | [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness", rule 3 |
| invalid UTF-8 in `p1.json` | `p1_verification_failed:invalid_json_encoding:p1.json` | [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Input strictness", rule 7 |
| extra field in `p1.json` | `p1_verification_failed:p1_unexpected_field:smuggled` | [`bundle-objects.md`](bundle-objects.md) §3 |
| extra field in `manifest.json` | no error, reason `manifest_integrity_failed`; informative `manifest_unexpected_field:smuggled` | [`bundle-objects.md`](bundle-objects.md) §2 |
| extra field in `envelope_env1.json` | no error, reason `envelope_integrity_or_link_failed`; informative `envelope_unexpected_field:smuggled` | [`bundle-objects.md`](bundle-objects.md) §4 |
| envelope with both digest links removed | no error, reason `envelope_integrity_or_link_failed`; informative `envelope_missing_field:bundle_manifest_sha256`, `envelope_missing_field:p1_sha256` | [`bundle-objects.md`](bundle-objects.md) §4 |
| manifest declaring `../../outside.txt` | no error, reason `manifest_integrity_failed`; informative per-file result `unsafe_manifest_path` | [`bundle-objects.md`](bundle-objects.md) §2 |

Three design points behind that table are normative for any implementation.

**Validation precedes extraction.** Every entry is validated before a single byte is
written ([`bundle-objects.md`](bundle-objects.md) §5), and each member's resolved path is re-checked
for containment at write time.

**Names are portable, and compared as a host that folds letter case compares them.** Windows
and macOS both map case variants to one file, and hosts differ beyond that in how they fold and
normalize names. A member name holds only the POSIX portable filename characters, so ASCII
letter case is the only folding left, and duplicate detection compares names with it folded
([`bundle-objects.md`](bundle-objects.md) §2, and §5, rule duplicate). An archive that cannot
extract identically on every host is refused rather than verified differently depending on where it
is run.

**Extraction is exclusive-create.** `target.open("xb")` turns any collision the name gate
did not anticipate into a hard failure instead of a silent last-member-wins substitution
(`archive.py::safe_extract_zip`); the substitution is how one archive could carry tampered bytes
under the real name and honest bytes under an alias.

**Closed contracts are a security control, not tidiness.** A digest is computed over
whatever a document happens to contain, so a malformed document is trivially
self-consistent with its own digest. Digest self-consistency is not conformance. The
closed field sets ([`bundle-objects.md`](bundle-objects.md) §2 to §4,
[`registry-link.md`](registry-link.md) §2 and
[`trust-registry-authorization.md`](trust-registry-authorization.md) §3) are what stop a smuggled
field from riding inside a "verified" object. Observed under the `link` check: an entry with
`verdict: "BANANA"` is `registry_entry_contract_violation`, not a downgrade: an unrecognized value
is a rejection ([`verification-vocabularies.md`](verification-vocabularies.md), and
[`registry-link.md`](registry-link.md) §2 and §4, whose status mapping has no alias, so `"ok"`,
`"success"` and whitespace-padded variants map to nothing).

Bounds worth knowing: canonical P1 is capped at 1024 bytes ([`bundle-objects.md`](bundle-objects.md)
§3), and canonicalization rejects integers outside the JavaScript safe range
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §1, and "Input strictness",
rule 2).

---

## 8. Trust assumptions a relying party inherits

Accepting a Loquitur `PASS` means accepting all of the following. None is verified by the
tool; each is a belief the relying party holds for its own reasons.

1. **The trust registry is authentic.** Unless a root was pinned, this is assumed
   entirely. With no root pinned the verdict is `REVIEW`, so the assumption is at least
   surfaced, but an operator who converts `REVIEW` to success has assumed it silently.
2. **The pinned root, if any, is the right root.** How the operator obtained the root
   document is outside the protocol.
3. **The evaluation clock is honest.** The operator supplies it (section 6), and authorization
   is not established without it; this version defines no source that would move it to a third
   party ([`trust-registry-authorization.md`](trust-registry-authorization.md) §2).
4. **The trust registry copy is current.** The registry's own `effective_at`/`expires_at`
   window and each key's status are read from the file supplied. A key revoked after that
   copy was made is not visible. The window is checked
   ([`trust-registry-authorization.md`](trust-registry-authorization.md) §4), and a revoked key
   behind a stale registry is still reported as revoked, because the deferred-window logic returns
   the key status first ([`trust-registry-authorization.md`](trust-registry-authorization.md) §4,
   and §6, rows 7 to 10). That ordering exists so a revocation signal is never lost to date
   arithmetic.
5. **The registry entry is the one the issuer published.** No inclusion proof exists, and
   one alone would not establish this: `transparency` is reserved
   ([`verification-checks.md`](verification-checks.md)), and inclusion and consistency proofs do not
   by themselves show every reader the same history. A suppressed, superseded or never-published
   entry verifies identically to a published one.
6. **The issuer identifier means something.** Binding `issuer_id` to a legal entity is
   entirely outside the protocol.
7. **The evidence describes the world.** The verdict path contains no model, no valuation
   check and no document analysis.
8. **The disclosed bundle is handled appropriately.** Verification requires the private
   material; the protocol says nothing about what happens to it afterwards.

## 9. Residual risks and out-of-scope items

Each entry in the report's `not_implemented_capabilities` list
([`report-contract.md`](report-contract.md) §2) maps to a residual risk. The Python reference
verifier emits the list on every report.

| Capability | Residual risk carried by the relying party |
| --- | --- |
| `trust_registry_root_signature_verification` | With no root pinned, a fully self-minted chain is indistinguishable from an authorized one *except* that it returns `REVIEW` rather than `PASS`. The entry is omitted in a run where a pinned root verified the trust registry; see the note below. |
| `registry_inclusion_or_finality_verification` | No proof that the entry appears in any log anyone else can see. An issuer can show different entries to different counterparties, and nothing here detects it. The adversary of the reserved `transparency` check is the **operator**, not the issuer, and no log is operated. That check is reserved ([`verification-checks.md`](verification-checks.md)): its proofs can be checked locally, and whether every reader was shown the same history needs outside observation. |
| `anchor_timestamp_or_chain_finality_verification` | `anchor` and `anchored_at` are outside the signature and therefore unattributable (section A3). No chain is read. `anchor_finality_verified` is always `false` (`runner.py::_registry_link_dict`, `runner.py::_trust_registry_dict`). Finality needs observation of the chain, not only local files ([`verification-checks.md`](verification-checks.md), the reserved `anchoring` check). |
| `revocation_or_supersession_verification` | Key status is read from the supplied registry copy and enforced (`ISSUER_KEY_REVOKED` / `ISSUER_KEY_SUSPENDED`, observed). What is *not* implemented is fetching current revocation state, or detecting that a receipt has been superseded by a later one. A stale registry cannot report a revocation that came after it. |
| `valuation_correctness_verification` | Nothing checks that a number is right. [`introduction.md`](introduction.md) §2.2 lists this as a non-goal. |
| `kyc_aml_or_compliance_verification` | No identity, sanctions or regulatory check of any kind. |

Additional residual risks not on that list:

- **The `link` check without the `authorization` check does not authenticate the entry.** An
  interceptor who rewrites bundle and entry consistently passes the `link` check.
- **Transport, storage and disclosure are unaddressed.** No confidentiality, no channel
  binding, no expiry on a disclosed bundle.
- **The archive limits are fixed constants**, neither raisable nor lowerable.
- **Two implementations must agree byte for byte.** Canonicalization is RFC 8785 with a
  named acceptance filter, and divergence between implementations is a consensus split,
  not a bug in one of them. [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) is
  the binding description.
- **Cryptography is one allowlisted pair in this version.** `secp256k1_ecdsa_sha256` over a
  `secp256k1` key, SHA-256, compact P1363 `r||s` hex, uncompressed SEC1 public keys, mandatory
  low-S ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4), with the
  algorithm bound into the signed bytes ([`signing-envelope-v2.md`](signing-envelope-v2.md)) so
  substitution changes the message. Digests and signatures name their algorithm, and the pairs a
  verifier accepts are a closed allowlist the verifier holds, never a value the input chooses
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), "Algorithm agility"): an
  identifier outside it yields `UNSUPPORTED_SIGNATURE_ALGORITHM`. Until a later version adds a pair,
  a break in secp256k1 or SHA-256 breaks every 0.1 commitment at once. Ed25519 is not a 0.1
  capability ([`cryptographic-capabilities.md`](cryptographic-capabilities.md)).
- **ECDSA curve arithmetic is a library's** in the reference verifier: the protocol's strictness
  (128 lowercase hex characters, `r` and `s` in `[1, n-1]`, low-S, both public key coordinates below
  `p` and the point on the curve, SHA-256 applied once) is checked before `pyca/cryptography`'s
  `secp256k1` verification is called, because a library verifier admits what the protocol refuses,
  such as a high S (`secp256k1.py::verify_digest`). It is checked against 252 Wycheproof P1363
  known-answer vectors and against cross vectors whose verdicts `@noble/curves` gives, both observed
  passing, with each vector file integrity-pinned so the baseline cannot drift silently. A
  Wycheproof vector passes under the low-S mapping: the 95 vectors Wycheproof marks valid with a low
  S are accepted, and the 72 it marks valid with a high S and the 85 it marks invalid are rejected.
  No independent cryptographic review of either verifier has been done.

### 9.1 `not_implemented_capabilities` is computed per run

`not_implemented_capabilities` is computed per run: `trust_registry_root_signature_verification`
is omitted exactly when a pinned root verified the trust registry in that run.

## 10. What an operator must do that the tool cannot

The verifier answers questions. These are decisions, and no flag makes them:

1. **Obtain a trust root out of band and pin it.** Without `--trust-root`, the trust registry
   proves that *some* key signed the entry and that the registry *the verifier was given* vouches
   for it. Whoever supplied that registry can make both true. Pinning is the difference between
   section 5 case A and case B. Obtaining the root through a channel the issuer does not control
   is the operator's problem entirely.
2. **Supply the evaluation time.** `--evaluation-time` is the only clock that judges a key, a
   registry and a root. Without it, authorization is not established and the run is `REVIEW`.
3. **Refresh trust material.** A registry copy is a snapshot. Decide how old is too old,
   and enforce it; the tool checks the window written in the file, not whether the file is
   current.
4. **Treat `REVIEW` as a stop, or name what you accept.** `--accept-review` converts an
   `OFFLINE_REVIEW` run to exit 0 only when every review reason of the run is in the list the
   operator gives ([`report-contract.md`](report-contract.md) §4). Accepting
   `registry_entry_verdict_requires_review` does not accept `trust_registry_root_not_pinned`: each
   reason accepted is a decision the operator takes on, and a gate that accepts the unpinned root
   has given up section 5.
5. **Read more than the exit code.** At minimum `outcome.reason`, `checks_requested`,
   `checks_established`, `review_reasons`, `evaluation_time` and, when the trust registry was
   evaluated, `trust_registry.authorization_status`, `trust_registry.signature_status` and
   `trust_registry.trust_registry_root_signature_status`. These are normative members
   ([`report-contract.md`](report-contract.md) §2), so every conforming verifier reports them.
6. **Bind issuer identifiers to real entities.** Out of scope for the protocol and
   unavoidable for the relying party.
7. **Decide what a `REVIEW` from an undeclared bundle member means.** The verifier reports
   the names in `manifest.extra_files`; whether the content is material cannot be decided
   by hashing ([`bundle-objects.md`](bundle-objects.md) §1).
8. **Handle disclosed evidence.** Retention, access control and destruction of a bundle
   after verification are entirely the operator's.
9. **Keep the verifier honest about itself.** Verify the package you run, from a source
   you trust; a verifier is a trusted computing base, and this document assumes the one
   executing is the one described.

## 11. How the claims here were verified

This section records the runs behind the behavior described above. The reference verifier
was run from a source checkout as `PYTHONPATH=src python -m loquitur.verify.cli …` against
the fixtures in `loquitur-verify-py/tests/fixtures/` (the fixtures are in the repository of the
reference verifier, a separate repository; where it is not available next to this repository,
these commands cannot be run from here alone),
with hostile inputs and self-minted
trust material generated for the purpose. Each row names one run, the input it was given and
what it produced. Every run that requests `authorization` passes `--evaluation-time
2026-05-10T00:00:00Z` unless its row says it does not.

Where a row counts inputs rather than naming one, the number is the number the suite that
runs them has: a check of this repository compares the hostile-input count with §7's table,
and one of `loquitur-verify-py` compares the Wycheproof count with the corpus that suite
verifies. A count stated here that outruns what is run fails a build rather than standing as
prose.

| Claim | How it was observed | Result |
| --- | --- | --- |
| Baseline PASS | `valid_bundle` | `OFFLINE_OK` / `PASS` / 0 |
| Tampered manifest | `tampered_manifest_bundle` | `OFFLINE_FAIL` / 1, `manifest_sha256: False` |
| Tampered canonical input | `tampered_canonical_input_bundle` | `OFFLINE_FAIL` / 1, `p1_input_hash: False` |
| Missing canonical input | `missing_canonical_input_bundle` | `OFFLINE_REVIEW` / 2, `canonical_input_not_provided` |
| Undeclared member | `valid_bundle` + `smuggled.txt` | `OFFLINE_REVIEW` / 2, `bundle_extra_files` |
| Link check | `link_valid_bundle` + `link_valid_registry_entry.json` | `OFFLINE_OK` / 0, `REGISTRY_ENTRY_LINK_VERIFIED` |
| Re-sealed altered bundle, structure and integrity | altered `canonical_input.json`, all local digests recomputed | `OFFLINE_OK` / **0**, `checks_established` `["structure","integrity"]` |
| …same bundle, + registry entry | as above with `--registry-entry` | `OFFLINE_FAIL` / 1, `link.manifest_hash: ok=false` |
| Unprojected key altered | `link_valid_bundle`, `asset_id` outside `p1.ik` | `p1_input_hash: True`, `manifest_files: False` |
| Authorization, no pinned root | fixtures + `--trust-registry` | `OFFLINE_REVIEW` / 2, `NO_PINNED_TRUST_ROOT` |
| Authorization, no evaluation time | fixtures + `--trust-registry`, no `--evaluation-time` | `OFFLINE_REVIEW` / 2, `review_reasons` `["evaluation_time_not_provided","trust_registry_root_not_pinned"]` |
| Authorization, root pinned and valid | registry re-signed by a minted root + `--trust-root` | `OFFLINE_OK` / 0, `ROOT_SIGNATURE_VALID` |
| Authorization, root pinned, registry signed by another key | same registry, different signing key | `OFFLINE_FAIL` / 1, `ROOT_SIGNATURE_INVALID`, `trust_root_authentication_failure` |
| Fully self-minted chain, default | minted issuer and root keys, registry root-signed, entry issuer-signed | `OFFLINE_REVIEW` / 2, `trust_registry_root_not_pinned` |
| …with an unrelated root pinned | as above + `--trust-root` | `OFFLINE_FAIL` / 1, `UNKNOWN_ROOT_KEY` |
| …accepting another review reason | default invocation + `--accept-review registry_entry_verdict_requires_review` | exit **2** |
| …accepting the unpinned root | default invocation + `--accept-review trust_registry_root_not_pinned` | exit **0** |
| Revoked key | `authorization_revoked_trust_registry.json` | `OFFLINE_FAIL` / 1, `ISSUER_KEY_REVOKED` |
| …with no evaluation time | as above, no `--evaluation-time` | `OFFLINE_FAIL` / 1, `ISSUER_KEY_REVOKED` |
| Suspended key | `authorization_suspended_trust_registry.json` | `OFFLINE_FAIL` / 1, `ISSUER_KEY_SUSPENDED` |
| Key not yet effective | `authorization_not_yet_effective_trust_registry.json` | `OFFLINE_REVIEW` / 2, `ISSUER_KEY_NOT_YET_EFFECTIVE` |
| Scope mismatch | `authorization_disallowed_asset_type_trust_registry.json` | `OFFLINE_FAIL` / 1, `ISSUER_KEY_SCOPE_MISMATCH` |
| Malformed trust registry | `authorization_malformed_trust_registry.json` | `OFFLINE_FAIL` / 1, `INVALID_TRUST_REGISTRY` |
| Unknown issuer | `authorization_unknown_issuer_registry_entry.json` | `OFFLINE_FAIL` / 1, `ISSUER_NOT_FOUND` |
| Unknown key | `authorization_unknown_key_registry_entry.json` | `OFFLINE_FAIL` / 1, `ISSUER_KEY_NOT_FOUND` |
| Signature mismatch | `authorization_signature_mismatch_registry_entry.json` | `OFFLINE_FAIL` / 1, `AUTHORIZED_ACTIVE_KEY` + `SIGNATURE_INVALID` |
| Duplicate `(issuer_id, key_id)`, active listed first | valid + revoked entry in one registry | `OFFLINE_FAIL` / 1, `TRUST_REGISTRY_AMBIGUOUS_KEY`, **not** the active duplicate |
| One key under two issuers, both entries active | the conformance run `authorization_dup_other_issuer_same_key` | `OFFLINE_FAIL` / 1, `TRUST_REGISTRY_AMBIGUOUS_KEY`, **not** `AUTHORIZED_ACTIVE_KEY` |
| One key under two labels, the entry naming the revoked label | the conformance run `authorization_shared_key_entry_names_the_revoked_label` | `OFFLINE_FAIL` / 1, `TRUST_REGISTRY_AMBIGUOUS_KEY`, **not** `ISSUER_KEY_REVOKED` |
| One root key under two `key_id` values, the other revoked | the conformance run `authorization_root_other_root_revoked` | `OFFLINE_FAIL` / 1, `AMBIGUOUS_ROOT_KEY`, **not** `ROOT_SIGNATURE_VALID` |
| secp256k1 verifier | 252 Wycheproof P1363 vectors | all pass |
| Internal-error path | `internal_error_report` | `INTERNAL_ERROR` / verdict `null` / exit 3 |
| Expired key, entry as issued | `authorization_expired_trust_registry.json` | `OFFLINE_REVIEW` / 2, `ISSUER_KEY_EXPIRED` |
| …entry back-dated by 1 second | same registry, `effective_at` −1s | `OFFLINE_REVIEW` / 2, `ISSUER_KEY_EXPIRED` (the entry's dates are not a time) |
| Committed verdict `FAIL` | entry and receipt agreeing on `FAIL` | `OFFLINE_FAIL` / 1, `registry_verdict_not_pass` |
| Committed verdict `WARN`/`REVIEW` | entry and receipt agreeing | `OFFLINE_REVIEW` / 2, `registry_entry_verdict_requires_review` |
| Committed verdict `BANANA` | out-of-enum value | `registry_entry_contract_violation` |
| Fabricated anchor | `anchor` + `anchored_at` injected into a signed entry | `signature_status: VALID_SIGNATURE`, `anchor_finality_verified: false` |
| Signature naming no payload | `payload_id`/`payload_version` removed | `OFFLINE_FAIL` / 1, `registry_entry_contract_violation` |
| `--tsa-token` | any token bytes | exit 64, no report |
| Empty `--evaluation-time` | `--evaluation-time ""` | exit 64 |
| `--trust-registry` without `--registry-entry` | — | exit 64 |
| Trust-root document of a later version | `schema_version` `v2` + `--trust-root` | `UNSUPPORTED_VERSION` / 4, the error `unsupported_version` with `object` `trust_root_document` and `version` `v2` |
| Nothing at the input path | a bundle path that names nothing | `HOST_FAILURE` / 5, `input_not_found` |
| Hostile archives and JSON | 26 cases, section 7 | all `OFFLINE_FAIL` / 1, no traceback |
| Entry signed over the root construction's message | an entry signed with its issuer key over the trust-root prefix and envelope instead of its own (section 14) | `OFFLINE_FAIL` / 1, `SIGNATURE_INVALID` |
| Rollback of trust material: newer copy, key revoked | a trust registry re-issued and signed by the pinned root, the key `revoked` after the entry was signed; `--trust-root`, `--evaluation-time 2026-05-20T00:00:00Z` (section 16) | `OFFLINE_FAIL` / 1, `ISSUER_KEY_REVOKED` |
| …older copy by the same root, key active | the earlier copy of that registry, signed by the same root, the key `active`, at the same time | `OFFLINE_OK` / 0, `ROOT_SIGNATURE_VALID` |
| Revoked key, entry signed before the revocation | the newer copy above: the entry's `issued_at` precedes the trust entry's `revoked_at` (section 15) | `OFFLINE_FAIL` / 1, `ISSUER_KEY_REVOKED` |
| Full-width digit in `issuer_key_id` | an entry naming its key with the full-width digit U+FF11 where the trust entry has the ASCII digit `1` (section 18) | `OFFLINE_FAIL` / 1, `ISSUER_KEY_NOT_FOUND` |

"All pass" on the secp256k1 row means under the low-S mapping of §9: 95 vectors accepted, and 72
upstream-valid high-S vectors and 85 invalid ones rejected.

Claims **not** observed, and stated as such: no claim is made here about behavior under
concurrent access, under a filesystem the verifier cannot read, or on any platform other
than the one these runs were performed on (Windows, CPython 3.11).

## 12. Change control

This document is normative for protocol release 0.1. Weakening a stated refusal, in particular the
rule in section 5 that a verifier with no pinned root returns `REVIEW` rather than `PASS`, is a
breaking protocol change. Adding a newly implemented capability requires removing it from
`not_implemented_capabilities`, which is a change to a report field that third parties parse and
therefore carries its own compatibility decision.

## 13. Registered vocabularies as operator configuration

The asset types, workflows and anchoring methods a verifier knows come from registered vocabularies
the verifier holds ([`verification-vocabularies.md`](verification-vocabularies.md) §8). They are
configuration chosen by the verifier and its operator, and the threat they raise is a wrong choice,
not a forged input.

- **A permissive vocabulary removes one review reason and nothing else.** An operator who supplies a
  vocabulary that registers a value turns the review reason `vocabulary_value_unknown` into no
  finding. It cannot make a signature verify, put a key in scope, make a link hold or authenticate a
  root: each of those is decided as it is with any other vocabulary.
- **A stale vocabulary yields `REVIEW`, never `PASS`.** A value registered after the vocabulary the
  verifier holds is unknown to it, and the run is `OFFLINE_REVIEW`. The failure mode of an
  out-of-date verifier is a question, not a silent acceptance.
- **The input cannot choose the vocabulary.** No member of a bundle, an entry, a receipt or a trust
  registry selects or supplies one, so an adversary who writes the input cannot bring a vocabulary
  that registers its own values.
- **An injected anchoring method has no effect.** The anchor is outside the signature (section A3),
  so anyone can write `anchor.method`. An unknown method changes no outcome; a malformed one breaks
  the entry's contract, as any malformed member does.
- **Accepting the review reason is a decision.** `--accept-review vocabulary_value_unknown` exits
  `0` on a run whose only open question is a value the verifier does not know
  ([`report-contract.md`](report-contract.md) §4). The operator who passes it accepts records of
  verticals the verifier was not given the vocabulary of, and takes on deciding what such a record
  means.

## 14. Role binding of every signature

Three constructions hash or sign protocol objects, and each begins its message with a domain prefix
of its own. The table binds each to the role that produces it and the key that checks it.

| construction | domain prefix (hex) | `domain` member | produced by | what it binds | checked with | invariant |
| --- | --- | --- | --- | --- | --- | --- |
| registry-entry signature, envelope v2 | `4c4f5155495455520052454749535452595f454e545259005349474e415455524500563200` | `org.loquitur.protocol.registry-entry-signature` | an issuer key | the registry entry without `signature`, `anchor` and `anchored_at`, and the envelope's schema, payload identifier, payload schema and signature algorithm | the `public_key_hex` of the one trust entry that authorizes `issuer_key_id` ([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, row 20) | [`signing-envelope-v2.md`](signing-envelope-v2.md) §2 |
| trust-registry root signature, envelope v1 | `4c4f5155495455520054525553545f524547495354525900524f4f545f5349474e415455524500563100` | `org.loquitur.protocol.trust-registry-root-signature` | a trust-root key | the whole trust registry except its `signature`, and the envelope's schema, payload schema and signature algorithm | the `public_key_hex` of the one pinned root whose `key_id` the registry's `signature.key_id` names ([`trust-root.md`](trust-root.md) §5, row 12) | [`trust-root.md`](trust-root.md) §4.1 |
| subject reference hash | `4c4f515549545552005355424a4543545f52454600563100` | none: it is a salted digest, not a signature | the issuer | `scheme`, `id` and a secret 32-byte salt | no check of this version reads it ([`registry-entry.md`](registry-entry.md) §4) | [`registry-entry.md`](registry-entry.md) §4 |

The three prefixes are distinct byte strings, and none is a prefix of another: they first differ at
the tenth byte. A message of one construction therefore begins differently from every message of the
others, and a signature made for one cannot verify as another, as long as SHA-256 resists collisions
and secp256k1 ECDSA resists forgery. Inside each envelope, `signature_algorithm` binds the algorithm
into the signed bytes, and which pairs of algorithm and key type are accepted is the verifier's own
closed allowlist, never the input's choice
([`cryptographic-capabilities.md`](cryptographic-capabilities.md) §2): there is no negotiation to
downgrade. Observed: an entry signed with its issuer key over the root construction's message, in
place of its own, does not verify (section 11).

**One key in two roles.** No check of this version compares a trust-root key with an issuer key. A
key that serves as both still produces signatures that do not transfer between the two roles,
because the messages differ by their prefixes. An operator SHOULD NOT use one key both as a trust
root and as an issuer key: a compromise of that key is then a compromise of both roles at once
(section 15), and the issuer role cannot be revoked in a trust registry without withdrawing the root
that signs the registry.

## 15. Key compromise, rotation and revocation

**An issuer key is compromised.** Whoever holds an issuer key signs registry entries that verify as
that issuer's, in every scope its trust entry allows, until the trust registry the operator supplies
marks the key `revoked` or `suspended`
([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, rows 7 and 8). The entry's
own dates do not help either side: they are not a time at which a key is judged (section 6). Once
the trust registry the operator supplies marks the key `revoked` in every trust entry that carries
it, every entry signed with it fails, at every evaluation time, the entries signed honestly before the compromise included: `revoked_at`
and `revocation_reason` are compared with nothing
([`trust-registry-authorization.md`](trust-registry-authorization.md) §4), and no time attested to a
signature exists in this version to tell an entry signed before the compromise from one signed after
it (observed, section 11). A suspension fails in the same way while the trust registry records it,
and is reversible.

**A trust-root key is compromised.** Whoever holds a root key signs trust registries that authorize
any key, for any issuer and any scope, and every operator that pinned the root accepts them. The
remedy is the operator's: remove from the trust-root document it supplies every root that carries
the key, or mark each of them `revoked` there, after which every trust registry the key signed fails,
with `UNKNOWN_ROOT_KEY` or `ROOT_KEY_REVOKED` ([`trust-root.md`](trust-root.md) §5, rows 6 and 8),
or, where more than one pinned root still carries the key, with `AMBIGUOUS_ROOT_KEY` (row 7). A
verifier fetches nothing, so no revocation of a root
reaches it except through the document its operator supplies.

**Rotation.** An issuer rotates a key by a trust registry that carries two trust entries for the
issuer, with distinct `issuer_key_id` values and windows that overlap for as long as entries signed
with the old key must keep verifying; each entry names the key that signed it. The same
`(issuer_id, issuer_key_id)` listed twice is ambiguous and refused, whatever the windows
([`trust-registry-authorization.md`](trust-registry-authorization.md) §5). An operator rotates a
root by a trust-root document that lists the old and the new root under distinct `key_id` values,
with overlapping windows; two roots under one `key_id` are refused ([`trust-root.md`](trust-root.md)
§5, row 7).

**One key under two labels.** A status reaches the key material, not only a label: a trust entry
is found by `(issuer_id, issuer_key_id)` and a root by `key_id`, and the key found is then compared,
by its point, with every other trust entry of the registry or every other pinned root
([`trust-registry-authorization.md`](trust-registry-authorization.md) §5,
[`trust-root.md`](trust-root.md) §3). A key listed under two labels, one `revoked` and one `active`,
authorizes through neither: the run stops at `TRUST_REGISTRY_AMBIGUOUS_KEY` or
`AMBIGUOUS_ROOT_KEY`. Without that comparison, anyone who holds a trust registry signed under a
revoked root `key_id` could rename it to an active one carrying the same key, because
`signature.key_id` is not signed. Re-labelling a key is still not a rotation: a rotation moves to a
new key, and two labels of one key make every entry or registry that names either of them
ambiguous.

**What a relying party loses.** A verdict reflects the trust material supplied to the run and
nothing newer. A compromise that the operator's copy of a trust registry or of the trust-root
document does not yet record is invisible to the verifier (section 8, item 4), and fetching current
revocation state is not implemented (section 9, `revocation_or_supersession_verification`).

## 16. Freshness and rollback of trust material

**The property, stated exactly.** A verifier judges a trust registry against its own window, the
evaluation time and the roots the operator pins, and against nothing else. It compares the
registry with no other copy: `registry_version` and `issued_at` are read by no rule of this version.
A trust registry signed by a pinned root, whose window holds the evaluation time, authorizes what it
says whether or not a later registry signed by the same root says otherwise. So a party that keeps
an older copy, correctly signed, in which a key since revoked is still `active`, and whose window
still holds the evaluation time, can present it in place of the newer copy, and a run over an entry
signed with that key reaches `PASS` (observed, section 11).

**What the operator does about it.** Keep the newest copy seen of each trust registry, by
`trust_registry_id`, and refuse a copy whose `issued_at` is earlier than that of a copy already
seen; obtain trust registries through a channel the party presenting the evidence does not control;
and prefer trust registries with short windows, so that a stale copy soon stops holding the
evaluation time. This version defines no input through which an operator tells a verifier the newest
version it has seen. Nor does a report name the trust registry or the root it rested on
([`report-contract.md`](report-contract.md) §2), so this check falls to whoever holds the trust
material, before the run, and a report passed on without a record of that material cannot be
checked later.

**What remains.** Within the window of a correctly signed copy, a verifier alone cannot tell a
rolled-back trust registry from the current one. The trust-root document is the operator's own
input and the evidence cannot replace it, but an operator that replaces it with an older copy of its
own reinstates the roots that copy lists. Showing different trust registries, or different registry
entries, to different relying parties is equivocation, and no check of this version detects it: that
needs the reserved `transparency` check and observation from outside a single verification
([`verification-checks.md`](verification-checks.md); section 9).

## 17. Differentials between implementations

Two conforming verifiers must reach the same outcome on the same inputs; a disagreement between
them is a split in what the evidence means, not a bug in one of them (section 9). The rules that
close the places where implementations of JSON and Unicode most often differ are:

- strict input ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §6): duplicate
  member names after escape decoding, numbers read as binary64 values with no excess precision and
  within the safe-integer range, finite numbers only, Unicode scalar values only, no noncharacters,
  UTF-8 with no byte-order mark, and a nesting depth decided without recursion;
- one canonical form, RFC 8785, with no second profile
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §1);
- byte-wise comparison of strings, with a closed list of the comparisons that read otherwise
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7);
- portable member names, with ASCII letter case the only folding
  ([`bundle-objects.md`](bundle-objects.md) §2);
- calendar instants of one form, compared as UTC seconds
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §6, rule 8);
- schema patterns read as ECMA-262, with `$` at the absolute end of a string
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §6, rule 5);
- no normative member of a report that depends on the order in which strings are listed
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7).

The maintainer tests these rules with the conformance corpus, with property tests inside each of
the two implementations, and with a seeded comparison of the two over generated inputs: strict
loading, canonical bytes, signing messages, instants and member names. That is the maintainer's own
testing, and its limits are stated here. The two implementations have one author, so a mistake they
share is not found by comparing them; agreement shows that the text can be implemented the same way
twice, not that it is right. A generated input exercises only what its generator can produce. The
references that do not come from the author are the anchors: the examples of RFC 8785, the
Wycheproof vectors of section 9 and the conformance corpus read against the text.

## 18. Identifiers shown to people

A verifier compares identifiers byte-wise
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7). Two identifiers that look
alike to a person, such as a letter and its look-alike in another script, two normalization forms of
one accented letter, a digit and its full-width form, or two letter cases, never match by accident:
a registry entry whose `issuer_key_id` differs from a trust entry's only by a full-width digit names
a key the trust registry does not carry (observed, section 11).

A person reading a report, a registry entry or a trust registry is not protected in the same way.
`issuer_id` is restricted to ASCII letters, digits, `_` and `-`, but `issuer_key_id`,
`signature.key_id`, `policy_id`, `issuer_display_name`, `notes`, `anchor.system` and `bundle_id` are
free strings, and a value that imitates another can be written in any of them. A trust registry's
`issuer_display_name` is a label its operator chose; no check compares it with anything, and it is
not an identity (section 8, item 6). Member names of a bundle are portable member names, so
look-alikes there are limited to ASCII ones, such as `l` and `1`.

An operator that shows identifiers to people SHOULD show a value that is not ASCII in a form that
makes its code points visible, and SHOULD decide on the identifiers the verifier compared, never on
how they are displayed or on a display name.
