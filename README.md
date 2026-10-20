# Loquitur Protocol

Loquitur is a protocol for checking the evidence behind a claim about a real-world asset, such as
a fund's net asset value or the valuation of a property, without making that evidence public. The
issuer keeps the evidence in a private bundle and publishes a small registry entry that commits to
it and is signed with a key a trust registry authorizes. Anyone who is given the bundle can then
check it offline, on their own machine and with no service involved: that the bundle is the one the
entry commits to, and that the key that signed the entry was authorized by a trust registry whose
root they chose to trust. The answer is a verdict, `PASS`, `REVIEW` or `FAIL`, with the reasons for
it. Tokenized assets are one application; the check works the same for assets that were never
tokenized.

This repository is the public specification surface of the protocol: the specification, one text
in numbered parts, its machine-readable artifacts, the conformance corpus that implementations are
tested against, and the governance of all three. It is not a server or runtime implementation, a
hosted registry or a package; the implementations live in the repositories the map below lists.

## Status

Specification preview (Alpha), protocol release 0.1. The specification may still change before
1.0.0; how a change is classified and made is in [`GOVERNANCE.md`](GOVERNANCE.md).

No independent cryptographic review of this protocol or its reference verifiers has been done yet.
The project is maintained by one person. What this preview does not provide is listed in
[`docs/preview-limitations.md`](docs/preview-limitations.md), and what release 0.1 does not claim
in section 12 of [`introduction.md`](docs/specification/introduction.md).

## Start here

**If you rely on a verdict or assess the risk of relying on one,** read section 2 of
[`threat-model.md`](docs/specification/threat-model.md), which says what a verdict asserts and what
it leaves out, then its sections 8 and 9 on the assumptions you inherit and the risks you carry, and
[`docs/preview-limitations.md`](docs/preview-limitations.md).

**If you implement a verifier or another part of the protocol,** start with
[`introduction.md`](docs/specification/introduction.md), part 1 of the specification, and follow
the table of contents in [`docs/README.md`](docs/README.md).
[`docs/specification/README.md`](docs/specification/README.md) indexes the JSON Schemas, the
reason-code catalog and the other machine-readable artifacts, and
[`conformance-testing.md`](docs/specification/conformance-testing.md) says how to check and extract
the conformance corpus, how to run it against an implementation, and what counts as conforming.

**If you review the protocol's security,** read
[`threat-model.md`](docs/specification/threat-model.md), which is the security considerations of
the specification,
[`cryptographic-capabilities.md`](docs/specification/cryptographic-capabilities.md), the privacy
considerations in section 6 of
[`public-private-boundary.md`](docs/specification/public-private-boundary.md),
[`conformance-testing.md`](docs/specification/conformance-testing.md), and
[`SECURITY.md`](SECURITY.md) for how to report a vulnerability.

## What this repository holds

| Path | What it is |
| --- | --- |
| [`docs/README.md`](docs/README.md) | the table of contents of the specification |
| [`docs/specification/`](docs/specification/) | the parts of the specification and the machine-readable artifacts they own |
| [`docs/change-proposals.md`](docs/change-proposals.md) | the register of the `LCP-` change proposals |
| [`docs/preview-limitations.md`](docs/preview-limitations.md) | what this preview does not provide |
| [`vocabularies/`](vocabularies/) | the registered asset types, workflows and anchoring methods |
| [`conformance/`](conformance/) | the conformance corpus, as the archive `CONFORMANCE_LOCK.json` pins |
| `*.json` at the root | the release and lock files: the protocol release, the conformance lock and authority, the capability and vocabulary contracts, the release set |
| [`IMPLEMENTATIONS.md`](IMPLEMENTATIONS.md) | the reference implementations of this release, by name, with the repository of each |
| `tests/`, `tools/` | the checks this repository runs on itself; [`docs/maintainers/`](docs/maintainers/) says how to run them |

## Repository map

| Repository | Purpose | Publication |
|---|---|---|
| `loquitur-protocol` | Public protocol specification and governance surface; holds the specification and the corpus archive. | this repository |
| `loquitur-schemas` | Standalone schema package repository. | a separate repository, with its own releases |
| `loquitur-verify-py` | Standalone offline verifier in Python (`loquitur-verify`). | a separate repository, with its own releases |
| `loquitur-verify-ts` | Standalone offline verifier in TypeScript (`@loquitur/verify`). | a separate repository, with its own releases |
| `loquitur-conformance` | Canonical vectors, expected outcomes, cross-implementation gate. | not published; travels inside this repository as a digest-pinned archive |

This repository holds the specification and the corpus archive. The schema package and the two
reference verifiers are separate repositories with their own releases, and each states its own
publication status.

The table names `loquitur-conformance` because pinned artifacts refer to it: a reader who
meets the name can tell that the repository exists and is not public.

## Public/private boundary

The public registry commitment is intentionally minimal. It may expose stable identifiers,
issuer and key references, policy identity, reason codes, verdict posture, manifest and receipt
commitments, timestamps, signatures, and anchor references when those are supported by the
relevant contract.

It must not expose private evidence, canonical input payloads, asset addresses, valuation amounts,
NAV values, financial metrics, document names, document contents, unrestricted evidence URLs,
private bundle contents, secrets, tokens, or the operational internals of a service.
[`public-private-boundary.md`](docs/specification/public-private-boundary.md) states the rules.

## The conformance corpus

Protocol governance owns semantic decisions and compatibility classes. The canonical vector corpus
and expected outcomes are produced in the separate `loquitur-conformance` repository, which is not
published. They reach you inside this one: the archive under `conformance/` that
`CONFORMANCE_LOCK.json` pins carries the corpus's data, the vectors with their expected outcomes,
the protocol's normative files they are read against and a content manifest, and nothing else.
Verify the digest before trusting the contents; that pin is the reason the corpus can travel
without its repository. The implementations `PROTOCOL_RELEASE.json` names as required consumers,
`loquitur-schemas`, `loquitur-verify-py` and `loquitur-verify-ts`, consume that corpus read-only;
their local fixtures are not normative.

The corpus id is `corpus_id` in `CONFORMANCE_LOCK.json`, derived from the archive's SHA-256, so an
archive whose bytes differ carries a different id. The corpus fixes the behavior of the profiles it
carries. It does not silently repair known gaps: trust-root authentication stays as the corpus
states it, and changing it requires the protocol change process and a new corpus id.

### What the corpus pin establishes

The archive is **not signed**. Its digest is recorded in this repository, alongside the artifact it
pins, so it establishes that the bytes you received are the bytes this repository published, and
nothing more. Against anyone who can write to this repository it establishes nothing at all,
because the same commit can change both. Treat it as an integrity check on transport, not as
evidence of origin. A detached signature over the archive, with the public key published outside
this repository, is the control that would make it evidence of origin; it is not in place, and this
section will say so until it is.

## Contributing and security

Contributions start with an issue; [`CONTRIBUTING.md`](CONTRIBUTING.md) says how, under the
Developer Certificate of Origin, and how a normative change goes through the change-proposal
register. Report a vulnerability privately as [`SECURITY.md`](SECURITY.md) says, never in a public
issue. Conduct in the project's spaces follows [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

The specification, the Markdown documents under `docs/specification/` and its table of contents
`docs/README.md`, is licensed under the Creative Commons Attribution 4.0 International license
(CC BY 4.0); see [`LICENSE-docs`](LICENSE-docs). The code blocks, examples and schema fragments
inside the specification are also available under MIT OR Apache-2.0, at your option.

Every other file, the other Markdown documents, the JSON artifacts, the conformance archive, the
tools and the tests among them, is licensed under either of

- the Apache License, Version 2.0 ([`LICENSE-APACHE`](LICENSE-APACHE)), or
- the MIT license ([`LICENSE-MIT`](LICENSE-MIT)),

at your option. [`NOTICE`](NOTICE) states which license covers which files.

Unless you explicitly state otherwise, any contribution you intentionally submit for inclusion in
this repository, as defined in the Apache License, Version 2.0, is licensed as the file it changes:
the specification prose under CC BY 4.0, and everything else dual licensed as above, without any
additional terms or conditions. Every commit carries the Developer Certificate of Origin sign-off
that [`CONTRIBUTING.md`](CONTRIBUTING.md) describes.
