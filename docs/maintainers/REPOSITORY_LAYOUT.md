# Repository layout of `loquitur-protocol`

`loquitur-protocol` is a public specification repository. It is intentionally small.

```text
loquitur-protocol/
├─ .github/
│  ├─ ISSUE_TEMPLATE/                      # the issue forms
│  │  ├─ change-proposal.yml               # a change proposal (LCP)
│  │  └─ specification-question.yml        # a specification question or error
│  ├─ PULL_REQUEST_TEMPLATE.md             # the five statements CONTRIBUTING.md asks for, as a checklist
│  ├─ dependabot.yml                       # weekly check of the pinned action commits
│  └─ workflows/
│     ├─ ci.yml                            # the release checks, the test suite and the sign-off check
│     └─ release.yml                       # builds, attests and drafts a release from a vX.Y.Z tag
├─ docs/
│  ├─ specification/
│  │  ├─ *.md                              # the prose specification, introduction.md first
│  │  ├─ README.md                         # index of the normative artifacts below
│  │  ├─ NORMATIVE_ARTIFACTS.json          # the machine-readable artifacts owned here, and their mirrors
│  │  ├─ PROSE_DIGESTS.json                # size and sha256 of the normative Markdown, PROTOCOL_RELEASE.json and the change-proposal register
│  │  ├─ schemas/                          # the seven public JSON Schemas
│  │  ├─ reason-codes/                     # reason-code catalog, and the schema it satisfies
│  │  ├─ registered-vocabularies/          # the schema a registered vocabulary satisfies
│  │  ├─ compatibility-classes.json        # the change-classification vocabulary
│  │  └─ change-proposal.schema.json       # the schema a change proposal satisfies
│  ├─ traceability/                        # the requirements inventory, the rule tables it reads, and its generated page
│  ├─ maintainers/                         # documents for the maintainer and contributors
│  │  ├─ testing.md                        # how to run the checks
│  │  ├─ conformance.md                    # what the conformance archive is, how to check it and how to propose a vector
│  │  ├─ releasing.md                      # how a release is made, and how its files are checked
│  │  ├─ DOCS_OWNERSHIP.md                 # what the documents of this repository own
│  │  ├─ REPOSITORY_LAYOUT.md              # this map
│  │  └─ TEST_OWNERSHIP.md                 # what the tests of this repository own
│  ├─ README.md                            # table of contents of the specification
│  ├─ change-proposals.md                  # register of the change proposals the specification cites
│  ├─ preview-limitations.md               # what this preview does not provide
│  └─ release-set.md                       # what release-set.json and RELEASE_SET_POINTER.json record
├─ conformance/
│  └─ loquitur-conformance-*.zip           # the conformance archive CONFORMANCE_LOCK.json pins
├─ vocabularies/                           # the registered vocabularies: asset types, workflows, anchoring methods
├─ tests/
├─ tools/
│  ├─ check_corpus_stranger_run.py         # runs conformance-testing.md sections 1 and 2 in an empty directory
│  ├─ check_normative_mirrors.py           # NORMATIVE_ARTIFACTS.json and the copies it declares
│  ├─ check_protocol_release.py            # the release artifacts and the archive they pin
│  ├─ check_public_spec_boundary.py        # no disclosure and no private-perimeter routes or hosts in the tree
│  ├─ public_boundary.json                 # what check_public_spec_boundary.py refuses
│  ├─ corpus_archive.py                    # the canonical archive build, used by the tools above
│  ├─ crafted_members.py                   # the archive members that are not text, built from text
│  ├─ compare_verify_vectors.py            # the comparison script of conformance-testing.md section 7, as a file
│  ├─ link_specification_references.py     # links or checks every reference to a specification document
│  ├─ propose_requirements.py              # proposes inventory records for unclaimed requirements, for review
│  ├─ refresh_prose_digests.py             # writes and checks PROSE_DIGESTS.json
│  ├─ registered_vocabularies.py           # checks the registered vocabularies, and that a change only adds
│  ├─ release_files.py                     # checks a release tag and builds the files a release carries
│  ├─ render_reason_codes.py               # checks or rewrites the reason-code register in reason-codes.md
│  ├─ render_requirements.py               # checks or rewrites docs/traceability/README.md
│  ├─ requirements_inventory.py            # reads the requirements and checks the inventory that names them
│  ├─ validate_corpus.py                   # validates the pinned archive or an extraction of it
│  └─ verify_release_set.py                # checks the release set across the sibling repositories
│
│  # normative governance artifacts (the published contract surface)
├─ PROTOCOL_RELEASE.json
├─ CONFORMANCE_AUTHORITY.json
├─ CONFORMANCE_LOCK.json
├─ CONFORMANCE_ORACLE_POLICY.json
├─ CRYPTOGRAPHIC_CAPABILITIES.json
├─ VERIFICATION_VOCABULARIES.json
├─ RELEASE_SET_POINTER.json
├─ release-set.json
├─ public_spec_manifest.json
│
├─ pyproject.toml                         # pytest and ruff configuration
├─ requirements-dev.txt                   # the packages the checks need
├─ .gitattributes
├─ .gitignore
│
├─ README.md                              # what the protocol is, where to start, the repository map
├─ IMPLEMENTATIONS.md                     # the record of the implementations, and which this copy lists; changes without a release
├─ CHANGELOG.md
├─ SECURITY.md
├─ CONTRIBUTING.md
├─ GOVERNANCE.md
├─ CODE_OF_CONDUCT.md
├─ NOTICE                                 # copyright, and which license covers which files
├─ LICENSE-APACHE                         # Apache License 2.0: with LICENSE-MIT, every file LICENSE-docs does not cover
├─ LICENSE-MIT                            # MIT license: the other license of those files, at the recipient's option
└─ LICENSE-docs                           # CC BY 4.0: the specification and docs/README.md
```

`pyproject.toml` carries pytest and ruff configuration only. This repository is **not** a
Python package and must never become one: `tools/check_public_spec_boundary.py`
fails if packaging build residue (`*.egg-info`, `build/`, `dist/`) appears.

## Included

- The specification of the protocol, one text in numbered parts; `docs/README.md` is its table of
  contents.
- Repository boundary tests.
- The machine-readable normative artifacts themselves, under `docs/specification/`: the
  seven public JSON Schemas, the reason-code catalog and the schema it satisfies, and the
  compatibility classes, so that an implementer reads them here rather than by installing a
  package or unzipping the conformance archive. See `docs/specification/README.md`.
- The registered vocabularies under `vocabularies/`: the values of the asset types, workflows and
  anchoring methods, which are registered data rather than specification text
  (`docs/specification/verification-vocabularies.md` §5).

## Excluded

- Service runtime code.
- Python schema package source. The schema *documents* are included above; what stays out
  is the package that loads and ships them.
- Python verifier package source.
- TypeScript verifier package source.
- OpenAPI JSON/YAML artifacts, inside the digest-pinned conformance archive as much as outside it:
  the archive carries none.
- Documentation-site, website and user-interface application code.
- Private demo fixtures.
- Third-party material, and the internals of an unpublished repository.
