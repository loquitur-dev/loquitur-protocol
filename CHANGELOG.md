# Changelog

All notable changes to `loquitur-protocol` are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project targets [semantic versioning](https://semver.org/spec/v2.0.0.html) once the public API stabilizes.

## [0.1.0] - 2026-10-20

First release of the Loquitur protocol specification. The public API is **not yet stable**
and may change before 1.0.0.

### Added
- The specification under `docs/specification/`: the bundle objects and their canonical
  forms, canonicalization and hashing, the Signing Envelope v2, the verification checks and
  modes, the report contract, the registry entry, the trust registry and its trust root, and
  conformance testing.
- The normative artifacts the specification owns, among them the reason-code catalog, the
  verification vocabularies and the schemas, listed in
  `docs/specification/NORMATIVE_ARTIFACTS.json`.
- Trust decisions that reach the key, not only its label: a trust entry or a pinned root whose
  public key another trust entry or pinned root also carries, in any SEC1 encoding, is ambiguous
  (`TRUST_REGISTRY_AMBIGUOUS_KEY`, `AMBIGUOUS_ROOT_KEY`), so revoking one label of a key withdraws
  its authority under every label. Every digest inside a JSON document carries the `sha256:` label,
  the verification summary's `policy_pack_sha256` included.
- The conformance corpus, carried under `conformance/` and pinned by digest in
  `CONFORMANCE_LOCK.json`, with `tools/validate_corpus.py` to validate it and
  `tools/check_protocol_release.py` to check the pin.
- The registered vocabularies of asset types, workflows and anchoring methods under
  `vocabularies/`, with `tools/registered_vocabularies.py` to check them.
- The requirements inventory under `docs/traceability/`, which names each requirement of the
  specification and the corpus runs that test it.
- `GOVERNANCE.md` and the change-proposal process of `docs/change-proposals.md`.
- A release workflow that builds, attests and drafts a release from a signed tag, described in
  `docs/maintainers/releasing.md`.
- Licensing by kind of file: the specification prose, the Markdown documents under
  `docs/specification/` and `docs/README.md`, under CC BY 4.0 (`LICENSE-docs`), with its code
  blocks, examples and schema fragments also available under MIT OR Apache-2.0; every other
  file, the other Markdown documents, the JSON artifacts, the conformance archive, the tools and
  the tests among them, under MIT OR Apache-2.0 at the recipient's option (`LICENSE-MIT`,
  `LICENSE-APACHE`). `NOTICE` states which license covers which files.

### Notes
- This release is a specification preview (Alpha). No independent cryptographic review of the
  protocol has been done yet. `docs/preview-limitations.md` lists what the preview does not
  provide, and `SECURITY.md` says how to report a vulnerability and which versions receive fixes.
