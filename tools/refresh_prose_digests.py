"""Bind the bytes of the normative prose, and check that the binding is current.

NORMATIVE_ARTIFACTS.json binds the machine-readable files under docs/specification/ by
digest, and not the Markdown beside them, although each of those documents says it is
normative. Without this list, rewriting the type of a member in bundle-objects.md would leave
PROTOCOL_RELEASE.json, release-set.json, public_spec_manifest.json, NORMATIVE_ARTIFACTS.json and
CONFORMANCE_LOCK.json unchanged, and every protocol, conformance and cross-repository gate
green.

docs/specification/PROSE_DIGESTS.json lists every Markdown file under docs/specification/ (a
`.md` suffix in any case, so the bound set is the same on every host), GOVERNANCE.md,
PROTOCOL_RELEASE.json and docs/change-proposals.md, with its size and SHA-256. tools/check_protocol_release.py and
tools/check_normative_mirrors.py both call verify() below, so a byte of normative prose
cannot change without this list changing in the same commit, which is where the change is
classified.

The list is deliberately NOT an entry of NORMATIVE_ARTIFACTS.json, which declares the
artifacts that have mirrors: the list has none, and it is checked here on its own. Nor is it
an archive member, and public_spec_manifest.json carries no file list, so adding it changes
nothing the pinned corpus holds.

The list is generated from the files, never hand-written: verify() requires the committed
document to be exactly what this tool writes.

    python tools/refresh_prose_digests.py          rewrite the list from the files
    python tools/refresh_prose_digests.py --check  verify it and write nothing

Exit codes: 0 written or verified, 1 verification failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

LIST = "docs/specification/PROSE_DIGESTS.json"
SCHEMA_VERSION = "loquitur.prose_digests.v1"
SPECIFICATION = "docs/specification"
# Normative files outside docs/specification/. GOVERNANCE.md defines how the protocol
# changes, including the classification a prose change needs. PROTOCOL_RELEASE.json declares
# the release itself; check_protocol_release.py reads some of its fields and none of its bytes,
# so a changed non-claim, owner or indentation would pass both gates. docs/change-proposals.md
# is the authoritative register of the change proposals the specification cites. Listed here,
# any byte of them changes this list in the same commit.
OUTSIDE_SPECIFICATION = ("GOVERNANCE.md", "PROTOCOL_RELEASE.json", "docs/change-proposals.md")


def covered_paths(root: Path) -> list[str]:
    """The files the list must bind, as repository-relative POSIX paths, sorted.

    The suffix is compared in lower case here rather than by the glob, whose case rule is the
    host filesystem's: a `*.MD` file would otherwise be bound on Windows and not on Linux.
    """
    found = {
        path.relative_to(root).as_posix()
        for path in (root / SPECIFICATION).rglob("*")
        if path.suffix.lower() == ".md" and path.is_file()
    }
    return sorted(found | set(OUTSIDE_SPECIFICATION))


def build(root: Path) -> dict:
    files = []
    for rel in covered_paths(root):
        data = (root / rel).read_bytes()
        files.append({"bytes": len(data), "path": rel, "sha256": hashlib.sha256(data).hexdigest()})
    return {"files": files, "schema_version": SCHEMA_VERSION}


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def verify(root: Path) -> list[str]:
    """Every error that makes the committed list differ from the prose it binds."""
    path = root / LIST
    if not path.is_file():
        return [LIST + " is missing, so nothing binds the bytes of the normative prose"]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return [LIST + " cannot be read as JSON (" + type(exc).__name__ + ")"]
    errors: list[str] = []
    if not isinstance(document, dict):
        return [LIST + " is not a JSON object"]
    if document.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            LIST + " schema_version is " + repr(document.get("schema_version")) + ", expected " + repr(SCHEMA_VERSION)
        )
    entries = document.get("files")
    # Refuse to pass on nothing: an empty list agrees with every file it does not name.
    if not isinstance(entries, list) or not entries:
        return errors + [LIST + " lists no files; nothing would be compared"]

    listed: dict[str, dict] = {}
    for index, entry in enumerate(entries):
        rel = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(rel, str) or not rel:
            errors.append(LIST + " entry #" + str(index) + " has no path")
            continue
        if rel in listed:
            errors.append(LIST + " lists " + rel + " more than once")
            continue
        listed[rel] = entry

    covered = covered_paths(root)
    for rel in covered:
        if rel not in listed:
            errors.append("normative prose is not listed in " + LIST + ", so nothing binds its bytes: " + rel)
    for rel in sorted(set(listed) - set(covered)):
        errors.append(LIST + " lists a file that is not normative prose or does not exist: " + rel)
    for rel in covered:
        entry = listed.get(rel)
        if entry is None:
            continue
        if not (root / rel).is_file():
            errors.append(LIST + " lists " + rel + ", which does not exist")
            continue
        data = (root / rel).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if entry.get("bytes") != len(data) or entry.get("sha256") != actual:
            errors.append(
                rel + " is " + str(len(data)) + " bytes, sha256 " + actual[:16] + "..., but " + LIST
                + " records " + repr(entry.get("bytes")) + " bytes, sha256 " + str(entry.get("sha256"))[:16] + "..."
            )
    # Bytes, not text: reading as text would fold a CRLF copy of the list into the LF one.
    if not errors and path.read_bytes() != render(build(root)).encode("utf-8"):
        errors.append(LIST + " binds the right bytes in a different form than the tool writes")
    if errors:
        errors.append(
            "the prose list is generated, never hand-written: classify the prose change, then run "
            "python tools/refresh_prose_digests.py and commit the list with it"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify the list and write nothing")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.check:
        errors = verify(root)
        for error in errors:
            print(error)
        if errors:
            return 1
        print("normative prose OK: " + str(len(covered_paths(root))) + " file(s) bound in " + LIST)
        return 0
    for rel in OUTSIDE_SPECIFICATION:
        if not (root / rel).is_file():
            print("cannot write " + LIST + ": " + rel + " is missing")
            return 1
    (root / LIST).write_text(render(build(root)), encoding="utf-8", newline="\n")
    print("wrote " + LIST + " (" + str(len(covered_paths(root))) + " files)")
    print("not verified: this run wrote the list from the files; run again with --check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
