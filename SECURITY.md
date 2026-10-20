# Security policy

**Status:** public specification preview security policy.

Loquitur Protocol separates public commitment material from private evidence material. Security
reports should focus on confidentiality, integrity, replayability, boundary leakage,
package-supply-chain posture, and documentation claims that could cause unsafe disclosure or unsafe
integration.

## Current status

This repository is a specification preview. It is not a hosted service, not a service runtime, not
a package repository, and not a service-level commitment.

No independent cryptographic review of this protocol or its reference verifiers has been done yet.

The following surfaces live in separate repositories:

- `loquitur-schemas`;
- `loquitur-verify-py`;
- `loquitur-verify-ts`;
- `loquitur-conformance` (not published; the corpus reaches this repository as a digest-pinned
  archive).

Each repository must define its own security and release posture.

## Reportable issues

Report issues such as:

- public documents that would cause private evidence disclosure;
- specification text that confuses public registry commitments with private bundle access;
- schema or verifier behavior that weakens documented replay/integrity posture;
- package or example guidance that encourages unsafe disclosure of credentials or confidential
  material;
- claim wording that materially overstates implemented guarantees.

## Do not disclose sensitive material

Do not include real issuer evidence, private keys, credentials, personal data, or confidential
third-party material in public issues, pull requests, discussions, or unencrypted reports.

## How to report

**Use GitHub's private vulnerability reporting on this repository**: open the *Security*
tab and choose *Report a vulnerability*. The report is visible only to the maintainer, it
carries no address that can be scraped or spoofed, and it produces an advisory record with
a fixed identifier that both sides can cite later. It is the primary channel and needs
nothing set up on your side.

If private reporting is unavailable to you, write to **security@loquitur.dev**. Keep the
details of the vulnerability out of the first message if you prefer: the maintainer replies
and agrees a private channel for them. Do not describe a vulnerability in a public issue.

## What to expect

- Acknowledgement within 5 working days.
- An assessment, including whether the maintainer considers the report in scope, within 10
  working days.
- Coordinated disclosure: the maintainer agrees a publication date with you first, and
  credits you unless you ask not to be credited.
- The maintainer aims to publish a fix and an advisory within 90 days of the day the report is
  received, and may agree a different date with you.

## Advisories and identifiers

A confirmed vulnerability is published as a GitHub security advisory on the repository it
affects, written from the private report. The advisory carries its GitHub identifier
(`GHSA-...`) from the start, and the maintainer requests a CVE identifier for it through
GitHub. The fix and the advisory name each other, and the changelog of the release that
carries the fix lists it under `Security`.

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | fixes on the default branch only |

This is a pre-1.0 preview. Fixes land on the default branch, and the next release carries
them; no earlier release receives a backport.

Releases are built by `.github/workflows/release.yml`, which attaches `SHA256SUMS` and a
CycloneDX SBOM and records a GitHub artifact attestation for each file;
[`docs/maintainers/releasing.md`](docs/maintainers/releasing.md) says how to check them.

## Scope

This policy covers `loquitur-protocol`: the specification, the normative artifacts it owns,
the conformance corpus archive this repository pins, and the tools of this repository. Each
sibling repository has its own `SECURITY.md` for its code; a flaw in the specification that
an implementation follows is reported here, and a flaw in one implementation is reported on
its repository. If you are not sure which repository a report belongs to, report it here.

In scope: the verification, canonicalization, signing and trust-evaluation rules the
specification states, and any case where a document claims a guarantee the protocol or its
implementations do not deliver.

Out of scope: the capabilities a report lists in `not_implemented_capabilities` for that
run; stating that one of them is absent is a correct reading of the documentation, not a
finding. Trust-registry root-signature verification is implemented and in scope.
