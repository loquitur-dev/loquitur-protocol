# Loquitur Protocol specification: table of contents

The specification of protocol release 0.1, in its parts. Part 1, the introduction, gives the
scope, the conventions, the terminology, the conformance classes and the references; read it
first. The kind of each part is the status line it opens with.

| Part | Document | Kind | Subject |
| --- | --- | --- | --- |
| 1 | [`specification/introduction.md`](specification/introduction.md) | normative | scope, document map, conventions, terminology, conformance and references |
| 2 | [`specification/public-private-boundary.md`](specification/public-private-boundary.md) | normative | what a public commitment may carry, what stays private, and the privacy considerations |
| 3 | [`specification/verification-checks.md`](specification/verification-checks.md) | normative | the named checks, their dependency order, where the offline checks stop, and the verification modes |
| 4 | [`specification/canonicalization-and-hashing.md`](specification/canonicalization-and-hashing.md) | normative | canonical JSON, digests, hash constructions, the signature scheme and input strictness |
| 5 | [`specification/bundle-objects.md`](specification/bundle-objects.md) | normative | the members of a bundle, the closed field contracts of its three objects, and archive intake |
| 6 | [`specification/signing-envelope-v2.md`](specification/signing-envelope-v2.md) | normative | the exact bytes an issuer signs |
| 7 | [`specification/cryptographic-capabilities.md`](specification/cryptographic-capabilities.md) | normative | what is supported, and what is named and refused |
| 8 | [`specification/registry-entry.md`](specification/registry-entry.md) | normative | the public commitment object, its identifiers and the subject reference hash |
| 9 | [`specification/registry-link.md`](specification/registry-link.md) | normative | the `link` check: how a registry entry is compared with a bundle |
| 10 | [`specification/trust-registry-authorization.md`](specification/trust-registry-authorization.md) | normative | the `authorization` check, and what a trust registry may carry |
| 11 | [`specification/trust-root.md`](specification/trust-root.md) | normative | how a trust registry is authenticated against a trust root |
| 12 | [`specification/verification-vocabularies.md`](specification/verification-vocabularies.md) | normative | the closed status and verdict vocabularies, and the registered vocabularies of asset types, workflows and anchoring methods |
| 13 | [`specification/reason-codes.md`](specification/reason-codes.md) | normative | the reason-code register and the rules that bind a code to a verdict |
| 14 | [`specification/verdict-grounds.md`](specification/verdict-grounds.md) | normative | the rules that tie a verdict to the grounds it cites |
| 15 | [`specification/report-contract.md`](specification/report-contract.md) | normative | what a verifier's report carries, and what a conformance comparison reads |
| 16 | [`specification/anchor-commitment.md`](specification/anchor-commitment.md) | reserved | what an anchor must commit to; no anchoring is live |
| 17 | [`specification/threat-model.md`](specification/threat-model.md) | normative | the security considerations: what is protected, the adversaries, the trust boundaries and the residual risks |
| 18 | [`specification/conformance-testing.md`](specification/conformance-testing.md) | normative | how to run the conformance corpus against an implementation, and what counts as conforming |
| Appendix A | [`specification/document-contracts.md`](specification/document-contracts.md) | normative appendix, adds no rule | every member of every document a verifier loads, with what a run reports when it is broken |
| Index | [`specification/README.md`](specification/README.md) | normative | the machine-readable artifacts: schemas, reason-code catalog, compatibility classes, and what normative means for them |

Beside the specification:

- [`change-proposals.md`](change-proposals.md): the public register of the `LCP-` proposals the
  parts cite, and what each one decided.
- [`release-set.md`](release-set.md): what `release-set.json` and `RELEASE_SET_POINTER.json`
  record.
- [`preview-limitations.md`](preview-limitations.md): what this preview does not provide.
- [`traceability/README.md`](traceability/README.md): the requirements inventory, generated from
  [`traceability/requirements.json`](traceability/requirements.json): every requirement with its
  identifier and what tests it, and the requirements no vector exercises
  ([`specification/introduction.md`](specification/introduction.md) section 8.4).
- [`../IMPLEMENTATIONS.md`](../IMPLEMENTATIONS.md): the record of the implementations known to the
  maintainer, saying which of them this copy lists;
  [`specification/introduction.md`](specification/introduction.md) section 11 points to it, and it
  changes without a protocol release.

For the maintainer and for contributors: [`maintainers/`](maintainers/) holds how to run this
repository's checks ([`maintainers/testing.md`](maintainers/testing.md)), the map of its tree
([`maintainers/REPOSITORY_LAYOUT.md`](maintainers/REPOSITORY_LAYOUT.md)) and what its documents and
tests own ([`maintainers/DOCS_OWNERSHIP.md`](maintainers/DOCS_OWNERSHIP.md),
[`maintainers/TEST_OWNERSHIP.md`](maintainers/TEST_OWNERSHIP.md)).
