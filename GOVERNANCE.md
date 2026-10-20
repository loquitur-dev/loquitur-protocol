# Governance

**Status:** public specification preview governance note.

This repository is maintained by one person, the copyright holder `NOTICE` names; "the maintainer"
in its documents is that person, not a team. Governance must preserve the protocol boundary: public
specification, public schema/verifier/package surfaces, and unpublished implementation surfaces are
separate.

## Repository roles

| Repository | Role |
|---|---|
| `loquitur-protocol` | Public protocol specification and governance notes; holds the specification and the corpus archive. |
| `loquitur-schemas` | Standalone schema package, a separate repository with its own releases. |
| `loquitur-verify-py` | Standalone verifier package (`loquitur-verify`), a separate repository with its own releases. |
| `loquitur-verify-ts` | TypeScript offline verifier preview (`@loquitur/verify`), a separate repository with its own releases. |
| `loquitur-conformance` | Protocol-governed canonical vectors, expected outcomes and compatibility classes. Not published; the corpus reaches readers as a digest-pinned archive inside `loquitur-protocol`. |

Each of these repositories states its own publication status.

## Change discipline

Changes to public protocol semantics require:

1. explicit scope;
2. compatibility assessment;
3. tests or fixtures in the owning repository;
4. documentation update;
5. migration notes when behavior changes.

## Published text and errata

The text of a published release never changes. A correction ships in a patch release, and the
changelog lists it as an erratum of the release it corrects.

## Boundary discipline

The public specification must not absorb service runtime code, private evidence fixtures,
third-party material, user-interface application code, documentation-site code, package source code,
or private operational notes.

The maintainer rejects changes that blur the boundary between public commitment metadata and private
evidence material.

## Protocol change classes and conformance ownership

`loquitur-protocol-governance` owns normative semantics. `loquitur-conformance` owns the corpus,
whose archive `CONFORMANCE_LOCK.json` pins. Implementations own execution code only.

**`loquitur-protocol-governance` is a role, not a repository.** It is the name the ownership fields
across these artifacts use for whoever holds normative authority. Today that is the maintainer of
this repository, and the artifacts are written so that the role can pass to a body without renaming
anything. Every other `loquitur-` name in these artifacts names a repository, a release set (a
`release_set_id` or `parent_release_set_id`), the protocol release (`protocol_release_id`, and
`protocol_release` in the requirements inventory) or the conformance corpus (`corpus_id`), and the
repository table of this file lists each of those repositories, so the exception is stated here
rather than left to be inferred: there is no repository at that name and looking for one will fail.

Every public semantic change must use a machine-readable change proposal conforming to
`docs/specification/change-proposal.schema.json`, identified as `LCP-` (Loquitur Change Proposal)
and four digits, and listed in the register `docs/change-proposals.md`. That schema is in this
repository, so a contributor can follow this rule. An unclassified change is treated as breaking. A
breaking change requires a new protocol profile/version, old/new vectors, and migration and
downgrade behavior. Expected outcomes may not be edited inside an implementation repository to make
its local tests pass.

The deposits are a **register of what was decided and why**, not a gate that was passed, and
`docs/change-proposals.md` says so to a public reader. Today the protocol and every consumer
repository have the same maintainer, so an approval round would be a signature from that person to
that person: a ceremony that records nothing a reader could not already see from the commit history.
Every deposited proposal therefore records `protocol-owner: pending` and no consumer-owner
approvals. When a consumer repository has an owner who is not the protocol owner, a change affecting
it requires that owner's approval, and the requirement will mean something.

## Registering a value

The asset types, workflows and anchoring methods are registered vocabularies under `vocabularies/`
(`docs/specification/verification-vocabularies.md` §5). A value is registered by a pull request that
adds it to its vocabulary file with the version, `since` and `profile` that section 9 there
requires, and that `tools/registered_vocabularies.py --base` accepts against the branch it targets.
Protocol governance approves it, and the change is classified `vocabulary-registration`: it needs no
change proposal of its own, no schema change, no new protocol version and no new conformance
archive. A value of `asset_type` or `workflow` names the profile of the vertical that defines it; a
value of `anchoring_method` is defined by protocol governance. A value is never removed or
reinterpreted; a value that is to be retired is deprecated, which is a registration too.

Adding a kind, or changing the grammar, the document format or what an unknown value does, is a
protocol change and follows the change discipline above.
