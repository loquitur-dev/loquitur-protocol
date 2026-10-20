# Documentation ownership

This repository owns public protocol specification and governance documentation.

It may document:

- protocol identity and scope;
- canonical object families at specification level;
- registry semantics;
- public/private boundary;
- verification checks and modes;
- reason-code vocabulary semantics;
- governance and status limitations.

It also carries the machine-readable normative artifacts those documents describe (the
public JSON Schemas, the reason-code catalog and the schema it satisfies, and the
compatibility classes) under `docs/specification/`. Those files are artifacts rather
than documentation, and they are owned here because a specification a reader cannot
implement from is not published. See `docs/specification/README.md`.

It must not contain service runtime docs, package source docs, documentation-site, website or
user-interface application material, third-party material, the internals of an unpublished
repository, raw runtime API material or implementation history.

The requirements inventory under `docs/traceability/` is owned here too: it names the
requirements of the specification and what tests each, outside the specification's text, and
`docs/traceability/README.md` is generated from it.

The checks that hold these documents are described in [`testing.md`](testing.md). This folder,
`docs/maintainers/`, holds the documents written for the maintainer and for contributors rather
than for readers of the specification.
