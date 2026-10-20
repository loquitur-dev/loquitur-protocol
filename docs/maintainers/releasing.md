# Releasing

This page says how a release of `loquitur-protocol` is made, what the release workflow does, and
how anyone checks the files of a release. The workflow is
[`.github/workflows/release.yml`](../../.github/workflows/release.yml); the files it builds come
from [`tools/release_files.py`](../../tools/release_files.py).

This repository is not a package and is never uploaded to a package index. A release is a GitHub
release of a tag, with these files attached:

| File | What it is |
| --- | --- |
| `loquitur-conformance-<id>.zip` | the conformance archive `CONFORMANCE_LOCK.json` pins, copied byte for byte from `conformance/` |
| `compare_verify_vectors.py` | the comparison script of [`conformance-testing.md`](../specification/conformance-testing.md) section 7, copied byte for byte from `tools/` |
| `loquitur-protocol-specification-X.Y.Z.tar.gz` | `docs/specification/`, the other files its `PROSE_DIGESTS.json` binds (`GOVERNANCE.md`, `PROTOCOL_RELEASE.json`, `docs/change-proposals.md`), `LICENSE-APACHE`, `LICENSE-MIT`, `LICENSE-docs` and `NOTICE` |
| `LICENSE-APACHE`, `LICENSE-MIT`, `LICENSE-docs`, `NOTICE` | the licenses, for the files outside the tar.gz |
| `loquitur-protocol-X.Y.Z.cdx.json` | a CycloneDX SBOM of the release files above: each file with its sha256 and its license |
| `SHA256SUMS` | the sha256 of every other file, in the format `sha256sum -c` reads |

Every file, `SHA256SUMS` and the SBOM included, has a GitHub artifact attestation of the build
that made it, and the files other than the SBOM and `SHA256SUMS` also have an SBOM attestation,
which carries the SBOM.

## Tag rules

- A release tag is `vX.Y.Z`, the version `PROTOCOL_RELEASE.json` gives in `protocol_release_id`,
  and `CHANGELOG.md` has a section headed exactly `## [X.Y.Z]` or `## [X.Y.Z] - YYYY-MM-DD`, with
  text in it. No other tag starts the release workflow.
- A release tag is annotated and signed with the maintainer's key: `git tag -s`. The workflow
  refuses a lightweight tag, and a tag whose signature GitHub does not report as verified.
- A release tag names a commit on the default branch; the workflow refuses any other.
- A release tag is never moved or deleted. A mistake in a release is corrected by a new patch
  release, listed in the changelog, as [`GOVERNANCE.md`](../../GOVERNANCE.md) says of the text of
  a published release.

## What the workflow does

A push of a tag `vX.Y.Z` starts five jobs. The workflow grants no permission by default, and each
job names the few it needs. The workflows run on a pinned runner image (`ubuntu-24.04`), not on
the moving `ubuntu-latest` label, so that the CI does not change when GitHub moves the label; the
pin is moved deliberately, with a run on the new image.

1. `verify` refuses a manual run started on a tag. It asks GitHub whether the tag is annotated,
   names the commit the run builds, and carries a signature GitHub reports as verified, and checks
   that the commit is on the default branch; then `python tools/release_files.py check --tag vX.Y.Z`
   checks the tag against the version, that the changelog section has text in it,
   `CONFORMANCE_LOCK.json` as `tools/check_protocol_release.py` reads it, the archive it pins
   against the size, the sha256 and the corpus id it records, and the comparison script against
   section 7 of `conformance-testing.md`. Last, `python tools/release_files.py names` lists the files a release
   carries, and `python tools/release_files.py sbom-name` the name of the SBOM, for `attest`. It
   runs only the repository's own code and the Python standard library.
   Read access only.
2. `ci`, after `verify`, runs [`ci.yml`](../../.github/workflows/ci.yml), the checks every push to
   the default branch and every pull request runs, on the tagged commit;
   `tools/check_protocol_release.py` among them checks the whole archive. A tag `verify` refuses
   stops the release before these checks start. The sibling checks read loquitur-verify-py,
   loquitur-schemas and loquitur-verify-ts at the head of their default branches, not at a
   matching tag, so a release run depends on their state at the time it runs. A sibling check that
   fails on a tag is fixed in the sibling and the run is re-run; the tag is not moved. Read access
   only.
3. `build`, after both, checks the pinned archive with `tools/check_protocol_release.py` and
   `tools/validate_corpus.py` in a fresh environment holding the packages `requirements-dev.txt`
   lists, builds the files with `python tools/release_files.py build`, writes the SBOM of those
   files with `python tools/release_files.py sbom`, writes `SHA256SUMS` over the files and the
   SBOM, and keeps them all as the workflow artifact `release-files`. Read access only: this job installs packages from PyPI, so it gets no
   identity token and cannot attest anything.
4. `attest`, after `verify` and `build`, takes `release-files` and checks that it holds exactly the
   files `verify` listed, all regular files, that `SHA256SUMS` lists exactly the others, and that
   `sha256sum --strict -c SHA256SUMS` passes. Then it makes an SBOM attestation and a provenance
   attestation of the files with `actions/attest`. It checks out nothing and installs
   nothing: it runs the pinned download and attestation actions and the runner's shell. This job
   alone may request an identity token and write attestations, and it has no other permission.
5. `release`, only for a tag push, after `attest`, checks the same files against `SHA256SUMS` and
   creates the release as a draft: `gh release create vX.Y.Z --draft --verify-tag`.
   `--verify-tag` refuses to create a tag that does not already exist. This job alone may write to
   the repository's contents.

The identity token is kept out of `build` because any code that runs in a job holding it can sign
an attestation for any file. `build` runs code this repository does not pin by hash: the packages
`requirements-dev.txt` names by version range, and their dependencies, resolved when the job
runs. `attest` attests only what it has checked against the list `verify` wrote and
against `SHA256SUMS`, so a file the list does not name, or one that does not match `SHA256SUMS`,
stops the release before anything is attested. Code in `build` that changes a file and
`SHA256SUMS` together is not caught by these checks: the attestation then says truthfully that
the run built that file, not that the file is right. The archive, the script and the license
files can still be compared with the repository at the tag, as
[Checking a release](#checking-a-release) shows.

The draft is not public. The maintainer reads it, and publishes it by hand or deletes it; the
workflow never publishes it. Every action the workflow runs is pinned by a full commit SHA, with
the release that commit belongs to in a comment, and `tests/test_release_workflow.py` holds the
triggers, the pins, the permissions of each job, what `attest` runs, and the draft flag.

A manual run, *Actions*, *release*, *Run workflow*, is a dry run: it runs `ci`, `verify` without
the tag checks, `build` and `attest` on the branch it is started on, and the files are kept as a
workflow artifact named `release-files` for seven days. It creates no release. A manual run
started on a tag is refused at the first step of `verify`: it would skip the tag checks and still
attest files under the tag's ref. In a private repository `attest` checks the files but skips the
two attestation steps, and says so in a notice, since GitHub offers artifact attestations there
only on some plans; a tag push never skips them and fails if it cannot attest.

## Settings outside the repository

The workflow relies on settings of the maintainer's GitHub account and of the repository. They
are not files, so this repository cannot show them, and this page does not state that they are in
place.

- Two-factor authentication on the maintainer's account with a security key or passkey (FIDO2),
  not SMS.
- No long-lived token: no personal access token and no repository secret is used to release. The
  workflow uses only the short-lived token GitHub gives each run, and the identity token of the
  run for the attestations.
- Immutable releases turned on for the repository, so that once the maintainer publishes a draft,
  its files and its tag can no longer be changed.
- A tag ruleset on `v*` that blocks updating and deleting a release tag, and lets only the
  maintainer create one.

## Making a release

1. The default branch carries the version to release in `PROTOCOL_RELEASE.json`, and its section
   in `CHANGELOG.md`.
2. On that commit: `python tools/release_files.py check --tag vX.Y.Z`.
3. Tag and check the tag locally:

   ```bash
   git tag -s vX.Y.Z -m "loquitur-protocol X.Y.Z"
   git cat-file -t vX.Y.Z   # prints: tag
   git tag -v vX.Y.Z        # the signature is good, made with the maintainer's key
   ```

4. Push the tag alone: `git push origin vX.Y.Z`. The workflow runs.
5. Read the draft release, then publish it by hand.

## Checking a release

`OWNER/loquitur-protocol` below is the repository the release is on, and `vX.Y.Z` its tag. With
the [GitHub CLI](https://cli.github.com/):

```bash
gh release download vX.Y.Z --repo OWNER/loquitur-protocol --dir release
cd release
sha256sum -c SHA256SUMS
for file in *; do
  gh attestation verify "$file" --repo OWNER/loquitur-protocol \
    --signer-workflow OWNER/loquitur-protocol/.github/workflows/release.yml \
    --source-ref refs/tags/vX.Y.Z --deny-self-hosted-runners
done
```

`sha256sum -c` shows that the files are the ones the workflow summed. `gh attestation verify`
shows, for each file, that a run of `release.yml` in that repository, on the tag, on a
GitHub-hosted runner, built a file with that sha256. On macOS, `shasum -a 256 -c SHA256SUMS` stands
in for `sha256sum -c`.

The SBOM attestation covers the files the SBOM describes: every file except the SBOM itself and
`SHA256SUMS`. It is checked over those files alone:

```bash
for file in *; do
  case "$file" in SHA256SUMS | loquitur-protocol-*.cdx.json) continue ;; esac
  gh attestation verify "$file" --repo OWNER/loquitur-protocol \
    --signer-workflow OWNER/loquitur-protocol/.github/workflows/release.yml \
    --source-ref refs/tags/vX.Y.Z --deny-self-hosted-runners \
    --predicate-type https://cyclonedx.org/bom
done
```

The tag signature is checked in a clone with `git tag -v vX.Y.Z`, given the maintainer's public
key; GitHub shows it as *Verified* when the key is registered to the tagger's account.

### The conformance archive

The archive is a release file, so an implementer can take it without cloning the repository, and
check it against the lock of the same tag and against its attestation:

```bash
gh release download vX.Y.Z --repo OWNER/loquitur-protocol \
  --pattern 'loquitur-conformance-*.zip' --pattern compare_verify_vectors.py
gh api "repos/OWNER/loquitur-protocol/contents/CONFORMANCE_LOCK.json?ref=vX.Y.Z" \
  -H "Accept: application/vnd.github.raw" > CONFORMANCE_LOCK.json
python3 -c 'import hashlib, json; lock = json.load(open("CONFORMANCE_LOCK.json")); data = open(lock["artifact"].rsplit("/", 1)[-1], "rb").read(); print(len(data) == lock["bytes"] and hashlib.sha256(data).hexdigest() == lock["sha256"])'
gh attestation verify loquitur-conformance-*.zip --repo OWNER/loquitur-protocol \
  --signer-workflow OWNER/loquitur-protocol/.github/workflows/release.yml --source-ref refs/tags/vX.Y.Z \
  --deny-self-hosted-runners
```

The `python3` line prints `True` when the archive has the size and the sha256 the lock records. The
lock pins the archive's bytes; the attestation adds where it was built from. The comparison script
is then run as section 7 of [`conformance-testing.md`](../specification/conformance-testing.md)
says, and sections 1 and 2 say how to extract and validate the archive.

## What is not claimed

- No reproducible build. The archive, the comparison script and the license files are copies, so
  their sha256 can be compared with the files of the repository at the tag. The tar.gz is written
  with fixed timestamps and no owner, and two builds of one commit with one Python give the same
  bytes (`tests/test_release_workflow.py`); that two runners give the same bytes has not been
  shown, nor for the SBOM.
- An attestation shows where and from what a file was built: the repository, the workflow, the
  commit and the runner. It does not show that the file is correct, or that the specification or
  the corpus is.
- A tag signature GitHub reports as verified shows that a key registered to the tagger's account
  made it, not who holds that key.
- The SBOM lists the release files themselves, each with its sha256 and the license `NOTICE`
  gives it, and no dependency: the release files are data, documents and one script that uses
  only the Python standard library. It does not list the packages the build checked the archive
  with, which no release file contains or runs.

## Package publication

This repository publishes no package, so it has no publish job. The repositories that do build
packages, `loquitur-schemas` and `loquitur-verify-py` for PyPI and `loquitur-verify-ts` for npm,
leave publication to the maintainer as well. Trusted publishing is how it would be automated: a PyPI
trusted publisher names the repository, the workflow and a GitHub environment, and a job with
`id-token: write` in that environment uploads without a stored token; on npm,
`npm publish --provenance` from a job with `id-token: write` records where the package was built.
Neither is enabled, so that every upload to an index stays a deliberate act of the maintainer.
