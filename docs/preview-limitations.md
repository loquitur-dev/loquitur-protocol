# Preview limitations

Protocol release 0.1 is a specification preview (Alpha). Its public API is not stable and may
change before 1.0.0, and no independent cryptographic review of the protocol or of its reference
verifiers has been done.

This repository does not provide:

- a hosted registry or any other service;
- a service runtime;
- package source code;
- a stable public API or SDK;
- production signing or key-management operations;
- production trust-registry governance;
- the result of an external security audit;
- regulatory approval;
- conclusions about legal ownership;
- correctness of any valuation;
- finality guarantees of any external network;
- service-level commitments.

What release 0.1 does not claim is stated in
[`introduction.md`](specification/introduction.md) section 12, "Non-claims", and
[`IMPLEMENTATIONS.md`](../IMPLEMENTATIONS.md) says which implementations known to the maintainer
this copy lists.
The requirements no conformance vector exercises, each with the reason or its known limit, are
listed under "Rules without a vector" in [`traceability/README.md`](traceability/README.md).

The schema package and the two verifiers live in their own repositories, `loquitur-schemas`,
`loquitur-verify-py` and `loquitur-verify-ts`, and each states its own status and limits there.
The conformance corpus comes from `loquitur-conformance`, which is not published; it reaches
readers as the digest-pinned archive in this repository. This specification defines no HTTP API
and no hosted service, so there is no service status to report.

## Known limitations of the protocol in release 0.1

Each of these is stated where its rule is, with what an operator can do about it.

- **Pinned roots have no scope.** A trust root names no issuer, operator or trust registry, so
  every pinned root can authorize a key for every issuer. Pinning the roots of two registry
  operators in one trust-root document merges their authority. Operators should pin together only
  roots they trust for every issuer, and keep separate trust-root documents otherwise. See
  [`trust-root.md`](specification/trust-root.md) section 1.
- **The envelope is not authenticated.** Nothing the issuer signs commits to
  `envelope_env1.json`, so its subject, anchor and provenance members and any embedded registry
  entry can be rewritten without a key, and the run still passes. A relying party must not treat
  them as authorized by the issuer. See [`bundle-objects.md`](specification/bundle-objects.md) section 4.
- **The subject reference opening is not checked.** A bundle may carry `subject_ref_opening.json`,
  but no check recomputes `subject_ref_hash` from it, so a run passes whether or not it opens the
  entry's commitment. A relying party that relies on the subject it names should recompute the
  value itself. See [`registry-entry.md`](specification/registry-entry.md) section 4.
- **A report does not name its trust material.** No normative report member identifies the trust
  registry, the root that authenticated it or the trust-root document a run used. Operators should
  keep a record of that material with each report. See [`report-contract.md`](specification/report-contract.md) section 2.
