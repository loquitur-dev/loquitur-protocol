# Contributing to Loquitur Protocol

**Status:** public specification preview contributor guide.

Loquitur is a protocol for checking the evidence behind a claim about a real-world asset.
Contributions to this repository should strengthen the public specification, boundary clarity,
governance posture, or documentation precision.

## Repository model

This repository contains public specification and governance material only. It contains no runtime
code, package source, API definitions, or documentation-site, website or user-interface application
code, and neither does the digest-pinned conformance archive: the archive holds the corpus's data
only, the vectors, copies of this repository's normative files and a content manifest, so the corpus
can travel without its repository.

Sibling repositories own implementation-adjacent surfaces:

- `loquitur-schemas` for schema package work;
- `loquitur-verify-py` for verifier package work;
- `loquitur-verify-ts` for TypeScript verifier preview work;
- `loquitur-conformance` for the conformance corpus (not published; the corpus reaches this
  repository as a digest-pinned archive).

## Contribution priorities

Preferred contributions:

- clearer protocol terminology;
- stronger public/private boundary wording;
- canonical object documentation improvements;
- reason-code and verification-mode explanation improvements;
- governance clarifications;
- tests that prevent accidental inclusion of private material, package source, service runtime
  or user-interface code.

Non-goals unless explicitly scoped:

- service runtime changes;
- package implementation changes;
- HTTP API definitions;
- SDK code changes;
- UI application changes;
- new protocol features, such as a new check, a new object or a new reason code, outside a change
  proposal;
- valuation computation;
- token issuance flows;
- investor dashboard features;
- undocumented public contract changes.

Registering a value of a registered vocabulary, such as a new asset type or workflow, is not a
non-goal: it is welcome through a proposal, under
[`verification-vocabularies.md`](docs/specification/verification-vocabularies.md) section 9.

## Contributions during the preview

External contributions start with an issue. A pull request is welcome under the Developer
Certificate of Origin when it is tied to an issue the maintainer has accepted. A normative
change to the protocol goes through the LCP change-proposal register of `loquitur-protocol`,
`docs/change-proposals.md`.

## Pull request expectations

A good pull request is small, reviewable, and tied to one public specification concern.

State in the pull request:

1. which public spec surface changes;
2. whether any public claim changes;
3. what boundary risk was considered;
4. what checks were run;
5. what remains unverified.

The pull request template (`.github/PULL_REQUEST_TEMPLATE.md`) asks for these five statements as a
checklist, and the issue forms (`.github/ISSUE_TEMPLATE/`) cover a specification question or error
and a change proposal.

Run the checks as [`docs/maintainers/testing.md`](docs/maintainers/testing.md) says before you
open the pull request; CI runs the same suite.

Do not add private evidence, third-party material, credentials, package source, service runtime
code, or documentation-site, website or user-interface application code to this repository.

## Documents for contributors

[`docs/maintainers/`](docs/maintainers/) holds the documents written for the maintainer and for
contributors rather than for readers of the specification:

- [`testing.md`](docs/maintainers/testing.md): how to run the checks, on Linux, macOS and Windows,
  and what each covers;
- [`REPOSITORY_LAYOUT.md`](docs/maintainers/REPOSITORY_LAYOUT.md): the map of the tree, file by
  file;
- [`conformance.md`](docs/maintainers/conformance.md): what the conformance archive is, how to
  check it, and how to propose a vector;
- [`releasing.md`](docs/maintainers/releasing.md): how a release is made, what the release
  workflow does, and how anyone checks the files of a release;
- [`DOCS_OWNERSHIP.md`](docs/maintainers/DOCS_OWNERSHIP.md) and
  [`TEST_OWNERSHIP.md`](docs/maintainers/TEST_OWNERSHIP.md): what the documents and the tests of
  this repository own, and what belongs in a sibling repository.

## Developer Certificate of Origin

Contributions are made under the Developer Certificate of Origin 1.1
(https://developercertificate.org/). Every commit, the maintainer's own included, carries a
sign-off line whose name and address match the commit's author, and CI checks every commit of
a push or pull request for it. `git commit -s` adds the line:

```
Signed-off-by: Your Name <your.email@example.com>
```

A squash merge made in the GitHub web interface can drop the `Signed-off-by` trailer of the
commits it combines: whoever merges adds the trailer back to the squashed commit's message.

The sign-off certifies that the contributor wrote the change or otherwise has the right to
submit it under the licenses the next section names. There is no separate contributor agreement.

## License

Unless you explicitly state otherwise, any contribution you intentionally submit for inclusion in
this repository, as defined in the Apache License, Version 2.0, is licensed as the file it changes,
without any additional terms or conditions:

- a change to the specification prose, a Markdown document under `docs/specification/` or
  `docs/README.md`, under the Creative Commons Attribution 4.0 International license
  (`LICENSE-docs`); a code block, example or schema fragment inside the specification is also
  available under MIT OR Apache-2.0;
- any other change is dual licensed under the Apache License, Version 2.0 (`LICENSE-APACHE`) or
  the MIT license (`LICENSE-MIT`), at the recipient's option.

Every commit carries the Developer Certificate of Origin sign-off described above. Copyright and
licensing are as `NOTICE` states them.
