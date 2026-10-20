# Testing

This page says how to run this repository's checks and what each covers.
[`TEST_OWNERSHIP.md`](TEST_OWNERSHIP.md) says which tests this repository owns.

## Running the checks

The checks need Python 3.11 or later and the packages `requirements-dev.txt` lists. This
repository is not a Python package and installs nothing itself. The suite runs on Linux and on
Windows; macOS is not tested. From the repository root, on Linux (the same commands apply on
macOS):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python tools/check_public_spec_boundary.py
```

On Windows, in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python tools/check_public_spec_boundary.py
```

In Git Bash on Windows the interpreter is `.venv/Scripts/python`.

Windows limits a path to 260 characters unless long paths are enabled. Some members of the
conformance archive have long paths, and the suite extracts the archive under the temporary
directory. If a test fails with `FileNotFoundError` on a path inside an extracted corpus, run
it with a short temporary directory, such as a folder at the root of a drive:

```powershell
New-Item -ItemType Directory -Force C:\t | Out-Null
$env:TEMP = "C:\t"; $env:TMP = "C:\t"
.venv\Scripts\python -m pytest -q
```

The suite checks the repository's shape, its claims, its public/private boundary and the pinned
conformance archive, and runs the commands
[`conformance-testing.md`](../specification/conformance-testing.md) gives; it takes several
minutes.

A test that reads a sibling repository looks for it beside this checkout. In a clone of this
repository alone those tests are skipped, and each skip reason says what is missing. The
repository must remain runnable on its own: any dependency on a sibling repository is explicit in
the command or the documentation, never implicit through a path outside this one.

## Normative conformance gate

Protocol CI checks the embedded, checksum-pinned conformance archive without executing anything
it carries. `python tools/check_protocol_release.py --root .` verifies that the archive is the one
`CONFORMANCE_LOCK.json` pins, that it is byte for byte the canonical build of the members it holds,
that its content manifest lists exactly those members, and that its copies of this repository's
normative files match this repository; with `--require-siblings` it also requires the archive to
equal the build of the corpus sources checked out beside this repository.
`python tools/validate_corpus.py CORPUS`, where `CORPUS` is the pinned archive or an extraction of
it ([`conformance-testing.md`](../specification/conformance-testing.md) section 2), checks the
corpus's own declarations. Neither runs the vectors against a verifier, and the release gate's
output says so.

[`conformance-testing.md`](../specification/conformance-testing.md) says how to run the vectors
against an implementation and what counts as conforming. `tests/test_conformance_testing.py` runs
the commands that document gives, its comparison script included when `loquitur-verify-py` is
checked out beside this repository. The same script is `tools/compare_verify_vectors.py`, byte for
byte, so that a release can attach it as a file; `python tools/release_files.py check` and
`tests/test_release_workflow.py` hold the two equal.

Implementation repositories may keep local robustness tests, but expected protocol outcomes come
only from the canonical corpus.

## Requirements inventory

`python tools/requirements_inventory.py` checks `docs/traceability/requirements.json`: every
key-word sentence and every row of a listed rule table is claimed once, every locator resolves,
every corpus run it names is a binding run, and every requirement is covered, excluded with a
reason or listed as a known limit. It reads the archive `CONFORMANCE_LOCK.json` pins, or the corpus
root `LOQUITUR_CORPUS_ROOTS` names. `python tools/render_requirements.py --check` checks that
`docs/traceability/README.md` is the rendering of the inventory, and
`python tools/propose_requirements.py` proposes records for a person to review when a part gains a
requirement. `tests/test_requirements_inventory.py` holds each invariant.

## Registered vocabularies

`python tools/registered_vocabularies.py` checks each file under `vocabularies/` against
`docs/specification/registered-vocabularies/schema.json` and the rules that schema cannot state.
With `--base REVISION` it also compares each file with its copy at that git revision and fails
when a value was removed or reinterpreted, or when the version did not grow by the component the
change calls for (`docs/specification/verification-vocabularies.md` §9). CI runs it against the
branch a pull request targets.

## Release workflow

`tests/test_release_workflow.py` reads `.github/workflows/release.yml` and holds its triggers, its
action pins, the permissions of each job, what the attesting job runs, and the draft flag, and runs
`tools/release_files.py` to build the release files into a temporary directory.
[`releasing.md`](releasing.md) says what the workflow does.
