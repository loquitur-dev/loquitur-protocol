# The release set

Status: informative. This page says what `release-set.json` and each repository's
`RELEASE_SET_POINTER.json` record, and what a reader can check with them. The checks are run by
`tools/verify_release_set.py` and `tools/check_protocol_release.py`.

## What a release set is

A release set names the repositories released together under one identifier, `release_set_id`
(`loquitur-release-set-0.1.0` for this release), and records, for each of them, the SHA-256 of the
pointer file that repository carries. Its parent, `parent_release_set_id`, is the release set it
extends; `loquitur-release-set-initial` is the empty release set before the first release.

The members are the repositories the manifest lists: `loquitur-protocol`, `loquitur-schemas`,
`loquitur-verify-py`, `loquitur-verify-ts` and `loquitur-conformance`. `loquitur-conformance` is
not published: the manifest names it, and the corpus it holds reaches this repository as the
archive `CONFORMANCE_LOCK.json` pins, but a reader cannot check its pointer.

## The manifest, `release-set.json`

The manifest is kept in this repository and is generated, never hand-written, by
`python tools/verify_release_set.py --write-manifest` with the members checked out side by side.

| member | what it records |
| --- | --- |
| `release_set_id`, `parent_release_set_id`, `branch_id` | the release set, its parent and the release line (`0.1.0`), as every pointer states them |
| `members` | for each member: `pointer_sha256`, the SHA-256 of the bytes of its `RELEASE_SET_POINTER.json`; `repository_role`, the role its pointer states; and the branch input it declares, if any (`branch_input_artifact`, `branch_input_status`) |
| `branch_inputs_declared`, `branch_inputs_present`, `unverifiable_branch_inputs` | how many members declare a branch input, whether every declared input was checked and held, and which could not be checked; no member declares one in this release |
| `owner` | who maintains the manifest: this repository's governance (`GOVERNANCE.md`) |
| `verification_profile_id` | the rules `tools/verify_release_set.py` applies, `loquitur.release_set_verifier.v1` |
| `non_claims` | what the manifest does not establish (below) |

## A pointer, `RELEASE_SET_POINTER.json`

Each member carries one, at its root.

| member | what it records |
| --- | --- |
| `repository`, `repository_role` | the repository the pointer belongs to, and what it holds in the release set |
| `release_set_id`, `parent_release_set_id`, `branch_id` | as in the manifest; every pointer states the same three |
| `inherited_guarantees` | the lineage the release set belongs to (`lineage_start` to `lineage_end`) and its policy, `superset-no-regression`: a release set keeps every guarantee of the release sets before it in its lineage |
| `release_manifest` | where the manifest is, who maintains it, and the verifier profile it is checked under |
| `status` | the conformance posture the protocol release states, one of two values: no known disagreement between the reference verifiers and the corpus, or known disagreements that block the release; `tools/check_protocol_release.py` holds it to the disagreement baseline of the corpus |
| `governance_change`, `semantic_change`, `wire_semantic_change` | whether, against its parent, the release set changes governance documents, the meaning of a rule, or the bytes a verifier reads |
| `non_claims` | what the pointer does not establish (below) |

## What a reader can check

With the published members checked out side by side,
`python tools/verify_release_set.py --workspace ..` checks that each pointer present has the digest
the manifest records and that every pointer states the same release set, parent and release line.
A member that is absent is never reported as checked: a published one is named in a warning, and
one that is not published is counted.

## Non-claims

Each entry of a `non_claims` list names one thing the record does not establish. A release set
records which repositories were released together and which bytes their pointers held; it is not
an approval of a release, a deployment or a publication, not a statement about any party's
readiness, and not a certification of an earlier release set. It records only the repositories
present when it was checked.
