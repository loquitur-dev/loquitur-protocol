# The conformance archive

This page says what `conformance/` holds, how to check it, and how to propose a vector. The folder
holds nothing but the archive, because the release gate refuses any other entry in it, so this text
lives here and not beside the archive. [`conformance-testing.md`](../specification/conformance-testing.md)
is the specification of the corpus; this page is the short route into it.

## What the archive is

`conformance/loquitur-conformance-<16 hex>.zip` is the conformance corpus: the test vectors, copies
of this repository's normative files and a content manifest. It holds data only, no code. A
verifier is compared with the runs the vectors declare. `CONFORMANCE_LOCK.json` pins the archive by
size, SHA-256 and corpus id, and the corpus id is derived from the archive's bytes.

## Check it against the lock

From the root of a checkout:

```bash
python tools/check_protocol_release.py --root .
```

The command checks the archive against `CONFORMANCE_LOCK.json`, among other things, and exits 0. The
one-line check of the digest that needs no tool of this repository is in
[`conformance-testing.md`](../specification/conformance-testing.md) section 1.

## Extract it and run the comparison

```bash
python -c "import json, zipfile; zipfile.ZipFile(json.load(open('CONFORMANCE_LOCK.json'))['artifact']).extractall('../corpus')"
python tools/validate_corpus.py ../corpus/loquitur-conformance
python tools/compare_verify_vectors.py --summaries --intake archive ../corpus/loquitur-conformance <your command>
```

`<your command>` is the command that runs your verifier on one request and writes one report as
JSON; section 7 of the specification names its arguments and what the comparison prints. The first
two commands need only this repository.

## Older archives

An archive is replaced by a new one when the corpus changes, and the old file leaves the tree. The
archives of earlier releases are in the files of the release tag that pinned them.

## Where the corpus comes from, and how to propose a vector

The sources the archive is built from are in a repository that is not published, and the archive is
the form in which the corpus reaches this one. To propose a vector, open an issue of this
repository that says which rule the vector exercises, the input, and the report you expect, and
cite the sentence of the specification that states the rule. A vector that changes an outcome the
archive declares is a change of the protocol and goes through the change-proposal register
([`change-proposals.md`](../change-proposals.md)).
