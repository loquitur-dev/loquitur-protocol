# Change proposals

Normative documents in this repository cite change proposals by id, such as `LCP-0008`. An id is
`LCP-` (Loquitur Change Proposal) followed by four digits, the pattern
`docs/specification/change-proposal.schema.json` fixes. This page is the public record of them and
it is authoritative. The deposits it derives from are not published, and they do not travel inside
the conformance archive either: several record material that stays private, and a proposal is never
edited after deposit, so a redacted copy under the same id would put two versions of one identifier
into circulation.

Nothing in the specification defers to a deposit for its content. Every citation of a
proposal in these documents attributes a decision whose substance is published here in
full. Where this page and a deposit differ, this page is what the
protocol says, and the difference is a defect in this page, to be corrected here.

A deposit a reader cannot open does not outrank the page they can: a specification that
defers to an unpublishable artifact is not self-contained, whatever else it contains.

## Register

| id | compatibility class | what it changes |
|---|---|---|
| `LCP-0001` | breaking | Adds an authorization reason-code vocabulary, so a failure of authority is not reported as a failure of integrity. |
| `LCP-0002` | breaking | Sets the protocol's name in the domain-separation prefixes and in every published identifier. |
| `LCP-0003` | source-api-breaking | Gives the code-derived names the protocol's name: the Python namespace, the distributions, the npm scope, the environment variables and the generated filenames. |
| `LCP-0004` | governance-only | Gives the repository directories, the hosting identity and the prose the protocol's name. |
| `LCP-0005` | breaking | Makes trust-registry root authentication and the evaluation time of the authorization check computed and attributed, rather than asserted. |
| `LCP-0006` | governance-only | Aligns every artifact with the signing domain prefix `LCP-0002` sets, and pins the conformance corpus to the archive that exists. |
| `LCP-0007` | governance-only | Keeps material of a repository that is not published out of the conformance corpus. |
| `LCP-0008` | breaking | Binds the verification verdict to the grounds it cites: a substance-free `PASS` is unrepresentable, and every reason code carries the context that makes it actionable. |
| `LCP-0009` | breaking | Moves the asset types, workflows and anchoring methods out of the schemas into registered vocabularies: the schemas fix an identifier grammar, a value the verifier's vocabulary does not hold is a review, the anchor becomes `method`, `system` and `anchor_reference`, the catalog gains the `vocabulary` codes and drops the six chain codes, and a registration is the compatibility class `vocabulary-registration`. |
| `LCP-0010` | breaking | Corrects four rules before the first publication: one public key under two labels makes a trust entry or a pinned root ambiguous, the verification summary's `policy_pack_sha256` carries the `sha256:` label, the verdict-grounds rules read members of any type, and the profile `independent-conformance-oracle-v1` is `semantic-exact`. Affects `trust-authorization-v1`, `schema-validity-v1` and `independent-conformance-oracle-v1`; the change to `trust-authorization-v1`, a `wire-exact-legacy` profile, is an exception stated below. |

## A recorded policy that binds nothing

**The time-stamp seam `LCP-0005` records for the reference implementation binds nothing.**
`LCP-0005` makes the evaluation time of the authorization check attributed rather than asserted,
and that stands: the operator supplies it and the report carries it as `evaluation_time`. It
also records, as a policy of the Python reference implementation and not of the protocol, a
seam for RFC 3161 time-stamp tokens, whose rules (the token's message imprint bound to the
evidence, the authority pinned by certificate fingerprint, duplicate anchors refused) it leaves
to a later version. Version 0.1 defines no time-stamp token as a source of the evaluation
time (`trust-registry-authorization.md` §2), and the reference implementation carries no
time-stamp code. The seam paragraph of `LCP-0005` therefore describes nothing that exists and
binds no verifier; the deposit is not edited, because a proposal is never edited after deposit,
and this note is where that is recorded. A later version that admits a third-party clock
specifies its source, binding and pinning here, as protocol text, and does not inherit them
from a deposit. A command line has no time-stamp option: one given is an unknown option, refused
with exit 64 (`report-contract.md` §4.1), and the refusal is a rule of the protocol.

## A frozen profile changed once, before publication

**`LCP-0010` changes two outcomes of `trust-authorization-v1` without superseding the profile.**
The profile is `wire-exact-legacy`, whose meaning is that current behavior is frozen to make a
known defect explicit and is superseded by a new profile, never edited
(`docs/specification/compatibility-classes.json`). `LCP-0010` closes that defect inside the profile
instead: the conformance runs `authorization_dup_other_issuer_same_key`, from `OFFLINE_REVIEW` with
`AUTHORIZED_ACTIVE_KEY` to `OFFLINE_FAIL` with `TRUST_REGISTRY_AMBIGUOUS_KEY`, and
`authorization_root_other_root_revoked`, from `OFFLINE_OK` with `ROOT_SIGNATURE_VALID` to
`OFFLINE_FAIL` with `AMBIGUOUS_ROOT_KEY`, change their declared outcomes in the 0.1.0 corpus, and no
other declared run of the profile changes. This is an exception, made once and recorded here: no
object, verifier or corpus of release 0.1.0 had been published when it was made, so no consumer
conforms to the earlier outcomes and a second profile would have frozen a defect nobody relies on.
The profile keeps its class and its status. After the first publication the rule of the class holds
without exception, and a change to an outcome of the profile is made by a new profile.

## Two classes this register corrects

**`LCP-0001` and `LCP-0005` are `breaking`, whatever their deposits record.** The register gave
`LCP-0001` the class `source-api-breaking` and `LCP-0005` the class `additive-compatible`, the
classes their deposits name. Both change expected outcomes, which neither class admits
(`docs/specification/compatibility-classes.json`): `source-api-breaking` requires that expected
verification outcomes remain unchanged, and `additive-compatible` that every older consumer remains
conforming. `LCP-0001` reports a failure of authority under the `authorization` codes, where an
integrity code was reported before, and `LCP-0005` judges an issuer's key at the evaluation time the
operator supplies, no longer at an instant the registry entry carries, so a back-dated entry reaches
a different outcome. Both are therefore `breaking`, the class whose meaning is that expected
outcomes change, and the rows above say so. The deposits are not edited, because a proposal is never
edited after deposit, and this note is where the correction is recorded. No object of release 0.1.0
had been published when either took effect, so the correction changes no published outcome.

## Two things this register states rather than smooths over

**The absence of an `unknown` status is a resolution of `LCP-0008`, not its decision.**
The specification cites this resolution for the four-value status vocabulary. `LCP-0008` step
six is a migration step requiring that an `unknown` status be resolved one of two ways: give
it a reason code naming why verification could not run, or remove it from the enum if nothing
legitimately produces it. The vocabulary takes the second: `pass · warning · review · fail`,
enforced by `VERIFICATION_VOCABULARIES.json` and by `tools/check_protocol_release.py`.
Attributing the choice to the proposal would overstate what the proposal says.

**No proposal here carries a recorded approval, and the rule says so.** Every deposit records
`protocol-owner: pending` and no consumer-owner approvals, and every one is in effect. One
person owns the protocol and every consumer repository, so an approval would be a signature
from that person to that person, recording nothing a reader could not read in the commit
history. Read this page as what it is, a record of what was decided and why, and not as
evidence that a governance gate was passed, because there is no second party for it to gate
against. When a consumer repository has an owner who is not the
protocol owner, a change affecting it requires that owner's approval, and the requirement will
mean something.
