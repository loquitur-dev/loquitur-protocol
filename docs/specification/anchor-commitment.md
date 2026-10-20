# Anchor commitment

Status: reserved.

No anchoring is live, no component retrieves an anchor,
and no check evaluates one. This document fixes what an anchor must commit
to, so that the question is settled before anything is built rather than after.

## 1. The rule

The value referenced by `registry_entry.anchor.anchor_reference` MUST commit to `H`,
where `H` is the SHA-256 digest of the registry entry's v2 signing message as defined in
[`signing-envelope-v2.md`](signing-envelope-v2.md).

The commitment MAY be direct, or MAY be to a structure over digests from which the
inclusion of `H` is provable. Nothing else may be committed.

`H` is recomputable by any holder of the entry, from the entry alone. That is the point:
an anchor carries no payload that must be transmitted alongside the entry, and a party
checking an anchor never has to be told what to expect — it derives the expectation and
compares. An anchor either commits to *this* entry or it does not, and there is no third
answer.

Permitting a structure over digests is deliberate. Committing one digest per entry does
not scale, and a Merkle root per period is the compression that makes anchoring
affordable at all; foreclosing it here in order to keep the rule shorter would have to be
undone by a breaking change later.

## 2. Why the anchor is outside the signature, and must stay there

An anchor commits to `H`, the digest of the signing message (§1), so that message is fixed before
any anchor can be made: an anchor inside the bytes `H` covers would change `H`, and would commit to a
message that no longer exists. The issuer signs that message before any anchor exists, and so cannot
sign the anchor. The signing payload of [`signing-envelope-v2.md`](signing-envelope-v2.md), the
registry entry without the members `signature`, `anchor` and `anchored_at`, MUST therefore keep
excluding all three. Certificate Transparency resolves the same circularity the same way: the CA
never signs the SCT.

> **Non-normative note.** The reference implementations name that set of excluded members
> `SIGNING_PAYLOAD_EXCLUDED_FIELDS`. The rule is the set, not the constant.

The consequence must be stated plainly rather than inferred, because it is easy to read
the exclusion as an oversight:

> Because no party signs the anchor, an anchor claim on a registry entry is
> **unattributable**. Any holder of a validly signed entry can add, alter, or remove
> `anchor` and `anchored_at`, with no key, and the signature still verifies.

This is not a defect in the exclusion. It is the absence of a second signer. The two ways
to close it are to have a second party attest the anchor, or to refuse the value; moving
the anchor inside the signed bytes is not among them, and would recreate the circularity.

## 3. What may be committed, and what may never be

Only `H`, or a structure over digests from which the inclusion of `H` is provable.

Entry content MUST NOT be committed. Nor MAY `subject_ref_hash`, `asset_id`, `bundle_id`,
any other identifier, or any locator or retrieval URI.

The reason is not tidiness. An anchoring record is permanent and irrevocable by
construction, so anything committed is placed beyond the reach of erasure, correction, or
any retention policy, including obligations the operator does not get to decline. A
digest of signed bytes is a commitment to a document; an identifier is a publication about
a subject. The first is the mechanism; the second is a disclosure that cannot be walked
back.

Existing publication paths that place identifiers or locators in an anchoring record do not
produce a conforming anchor under this rule, and must be retired before anchoring is enabled. The
rule names no implementation: which implementations it affects is an operator's matter.

## 4. Absence and presence

An absent or null `anchor` MUST NOT be treated as a negative finding. Anchoring is not
part of the checks `structure` to `authorization`, so an entry without one has not failed anything.

A present `anchor` that has not been checked MUST NOT be reported, rendered, or relied on
as corroboration. Until a component retrieves the referenced commitment and compares it to
`H` recomputed from the entry in hand, the field is a declaration by whoever last held the
entry and nothing more.

## 5. What this document does not establish

It does not make anchoring live, does not oblige any component to retrieve an anchor, and
does not confer finality on anything. It fixes the meaning of a field so that the meaning
does not have to be negotiated once implementations exist and disagree.

[`verification-checks.md`](verification-checks.md), under `anchoring`, states the distinction the
commitment `H` sits on: that an anchoring record commits to the bytes in hand is cryptographic and
can be checked from local files, given a copy of the record, while that the record is final, and
when it became so, needs observation of the system that carries it.

Activation follows the pattern used for `ed25519` in `CRYPTOGRAPHIC_CAPABILITIES.json`: a
future protocol release, with normative vectors and support in every consumer, changed
together rather than one at a time.

## 6. Anchoring methods

`registry_entry.anchor` carries `method`, `system` and `anchor_reference`. `method` is a value of
the registered vocabulary `anchoring_method`
([`verification-vocabularies.md`](verification-vocabularies.md) §5), and `system` names the system
that carries the anchoring record. Whatever the method, section 1 binds: the record commits to `H`,
directly or through a structure over digests from which the inclusion of `H` is provable, and to
nothing else. The method decides only how the commitment is carried, and how it would later be
checked.

The methods the vocabulary registers at version 1.0.0, read against section 1. This table is
informative:

| method | what commits to `H` | `system` |
| --- | --- | --- |
| `blockchain_transaction` | a transaction whose payload is `H`, or the root of a Merkle tree over a set of digests that contains `H` | a CAIP-2 chain id, such as `eip155:1`, which names the chain and its network in one value |
| `rfc3161_timestamp` | an RFC 3161 time-stamp token whose `messageImprint` is the algorithm SHA-256 with the hashed message `H`; `H` is already the SHA-256 of the signing message, so the imprint commits to exactly those bytes | the identifier of the time-stamping authority |
| `transparency_log_checkpoint` | a checkpoint of a transparency log whose tree includes a leaf that commits to `H` | the origin of the log |

Whether a time-stamping authority is qualified, for example under Regulation (EU) No 910/2014 as
amended by Regulation (EU) 2024/1183, is a property of the authority and not of the method. The form
of `system` is guidance in this version and is not checked: it tightens when the `anchoring` check
is defined, as the form of `anchor_reference` does ([`registry-entry.md`](registry-entry.md) §6). No
method is checked in this version: no component retrieves an anchoring record (section 5), and an
unknown method has no effect on a run
([`verification-vocabularies.md`](verification-vocabularies.md) §7).
