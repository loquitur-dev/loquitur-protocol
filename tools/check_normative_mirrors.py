"""Declare which repository owns the normative artifacts, and prove the copies follow.

The seven JSON Schemas, the reason-code catalog, the compatibility classes and the
change-proposal schema exist in more than one place: here, inside the loquitur-schemas
package data or the loquitur-conformance tree, and inside the digest-pinned conformance
archive. docs/specification/README.md says that this repository is the source and the others
are mirrors, and prose is not a check: two copies could drift for a whole release with every
gate green.

So the direction is recorded machine-readably in docs/specification/NORMATIVE_ARTIFACTS.json
and enforced here. The manifest is generated from the files, never hand-written, because a
hand-maintained digest list drifts from what it describes exactly as silently as the copies
it exists to police.

Three checks, deliberately separate:

  * SELF-CONSISTENCY: the manifest matches this repository's own files. This can always
    run, needs nothing else checked out, and failing it means the manifest is stale.
  * MIRRORS: each declared mirror matches the artifact it mirrors. This needs the sibling
    repositories, so it SKIPS a sibling that is absent and FAILS on it when
    LOQUITUR_REQUIRE_SIBLINGS is set. That inversion is what turns the check from
    documentation into enforcement where every sibling is checked out.
    docs/specification/README.md says where each mirror is compared.
  * PROSE: docs/specification/PROSE_DIGESTS.json binds the bytes of every normative Markdown
    file and of PROTOCOL_RELEASE.json, through tools/refresh_prose_digests.py, which tools/check_protocol_release.py
    calls too. Like self-consistency it needs nothing else checked out and never skips. The
    list is not an artifact of the manifest above: it has no mirror.

Regenerating and then verifying is verifying a file against itself, so --write refuses to
do both: it rewrites the manifest, says so, and tells you to run again without the flag.

Exit codes: 0 verified, 1 verification failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# A plain import of the file beside this one; the directory is put on the path so that loading
# this module by location finds it as running it as a script does.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_prose_digests import LIST as PROSE_LIST  # noqa: E402
from refresh_prose_digests import covered_paths as prose_paths  # noqa: E402
from refresh_prose_digests import verify as verify_prose_digests  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
MANIFEST = ROOT / "docs/specification/NORMATIVE_ARTIFACTS.json"
PROSE_DIGESTS = ROOT / PROSE_LIST
SCHEMA_VERSION = "loquitur.normative_artifacts.v1"
REQUIRE_SIBLINGS_ENV = "LOQUITUR_REQUIRE_SIBLINGS"

# What an absent sibling means to someone who does not have it. loquitur-conformance is not
# published, so a reader of a published copy of this repository never has it beside this one,
# and "is not checked out" alone reads as a prerequisite they failed to meet. Of the artifacts
# it mirrors, those the corpus reads travel inside the digest-pinned archive in conformance/,
# where tools/check_protocol_release.py compares them with this repository; the note names the
# one it mirrors that the archive does not carry, so that it claims no comparison that is not
# made.
ABSENT_SIBLING_NOTES = {
    "loquitur-conformance": (
        "it is not published; the archive in conformance/ carries its copies of the artifacts the "
        "corpus reads, which tools/check_protocol_release.py compares with this repository, and not "
        "its copy of docs/specification/change-proposal.schema.json"
    ),
}


def absent_sibling_message(repository: str) -> str:
    message = repository + " is not checked out beside this repository"
    note = ABSENT_SIBLING_NOTES.get(repository)
    return message + "; " + note if note else message

_SCHEMA_NAMES = (
    "change_summary",
    "coverage_summary",
    "lineage_summary",
    "registry_entry",
    "trust_registry",
    "verification_receipt",
    "verification_summary",
)

# Every normative artifact this repository owns, and where each one is copied. The mirror
# paths are declared rather than discovered: a mirror that quietly stops existing is a
# finding, and discovery would report it as a success.
OWNED: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = tuple(
    (
        "docs/specification/schemas/" + name + ".schema.json",
        (("loquitur-schemas", "src/loquitur/schemas/data/" + name + ".schema.json"),),
    )
    for name in _SCHEMA_NAMES
) + (
    (
        "docs/specification/reason-codes/schema.json",
        (("loquitur-schemas", "src/loquitur/schemas/data/reason_codes_catalog/schema.json"),),
    ),
    (
        "docs/specification/reason-codes/v2.0/catalog.json",
        (("loquitur-schemas", "src/loquitur/schemas/data/reason_codes_catalog/v2.0/catalog.json"),),
    ),
    (
        "docs/specification/compatibility-classes.json",
        (("loquitur-conformance", "compatibility-classes.json"),),
    ),
    # Published here so that the instruction in GOVERNANCE.md to file a conforming change
    # proposal names a schema an outside contributor can read. The direction is the same as
    # for every other artifact: this copy owns the bytes, and the corpus source's copy follows.
    (
        "docs/specification/change-proposal.schema.json",
        (("loquitur-conformance", "governance/change-proposal.schema.json"),),
    ),
    # The meta-schema of a registered vocabulary, and the vocabularies themselves. The corpus
    # archive carries a copy of the meta-schema only, under protocol/: a registration changes no
    # archive member (verification-vocabularies.md section 9). The verifiers embed the
    # vocabularies in generated modules, which loquitur-conformance's copy bindings compare.
    (
        "docs/specification/registered-vocabularies/schema.json",
        (("loquitur-schemas", "src/loquitur/schemas/data/registered_vocabularies/schema.json"),),
    ),
) + tuple(
    (
        "vocabularies/" + kind + ".json",
        (("loquitur-schemas", "src/loquitur/schemas/data/registered_vocabularies/" + kind + ".json"),),
    )
    for kind in ("anchoring_method", "asset_type", "workflow")
)


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict:
    artifacts = []
    for rel, mirrors in OWNED:
        source = ROOT / rel
        if not source.is_file():
            raise SystemExit("declared normative artifact is missing: " + rel)
        raw = source.read_bytes()
        artifacts.append(
            {
                "path": rel,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "mirrors": [{"repository": repo, "path": path} for repo, path in mirrors],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "owner": "loquitur-protocol",
        "note": (
            "This repository owns these bytes. Every other copy, including the "
            "loquitur-schemas package data and the mirrors inside the conformance "
            "archive, is a mirror of them and must match. Generated by "
            "tools/check_normative_mirrors.py --write."
        ),
        "artifacts": artifacts,
    }


def check_self(manifest: dict) -> list[str]:
    """Compare the manifest against this repository's own files."""
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            "manifest schema_version is " + repr(manifest.get("schema_version")) + ", expected " + repr(SCHEMA_VERSION)
        )
    declared = {a["path"]: a for a in manifest.get("artifacts", [])}
    expected = {rel for rel, _ in OWNED}
    for missing in sorted(expected - set(declared)):
        errors.append("artifact owned by this repository is absent from the manifest: " + missing)
    for extra in sorted(set(declared) - expected):
        errors.append("manifest declares an artifact this repository does not own: " + extra)
    # Discovery, in addition to the declaration. OWNED is a hand-written list, so an artifact
    # added to the specification without being added to it would escape the binding with
    # nothing saying so. Mirror paths stay declared rather than discovered (see OWNED), but
    # what this repository owns is whatever machine-readable file it publishes as
    # specification.
    for path in sorted((ROOT / "docs/specification").rglob("*.json")):
        rel = path.relative_to(ROOT).as_posix()
        # PROSE_DIGESTS.json binds prose and is checked on its own below; routed through OWNED
        # it would need a mirror it does not have.
        if path not in (MANIFEST, PROSE_DIGESTS) and rel not in expected:
            errors.append(
                "machine-readable file under docs/specification/ is not declared in OWNED, so nothing binds its copies: "
                + rel
            )
    # Refuse to pass on nothing: an empty manifest satisfies every comparison below.
    if not declared:
        errors.append("manifest declares no artifacts; nothing would be compared")
    for rel in sorted(expected & set(declared)):
        source = ROOT / rel
        if not source.is_file():
            errors.append("declared artifact is missing from disk: " + rel)
            continue
        actual = digest(source)
        if actual != declared[rel].get("sha256"):
            errors.append(
                rel + ": the file is " + actual[:16] + "... but the manifest says " + str(declared[rel].get("sha256"))[:16] + "..."
            )
    if errors:
        return errors
    return _compare_with_generated(manifest)


def _compare_with_generated(manifest: dict) -> list[str]:
    """The committed manifest must be exactly what --write would produce.

    The checks above compare the set of paths and each sha256. This comparison covers every
    other field, the `mirrors` and `bytes` fields included, so that "generated, never
    hand-written" is a property enforced rather than a fact about how the file was made: a
    hand edit pointing one artifact's mirror at this repository's own copy of it would
    otherwise let a diverged mirror pass. OWNED is the declaration; the manifest is its
    generated image, and any field that differs from the image is a hand edit.
    """
    expected = build_manifest()
    if manifest == expected:
        return []
    errors: list[str] = []
    for key in sorted((set(manifest) | set(expected)) - {"artifacts"}):
        if manifest.get(key) != expected.get(key):
            errors.append(
                "manifest field " + repr(key) + " is " + repr(manifest.get(key)) + " but --write generates "
                + repr(expected.get(key))
            )
    committed = {a["path"]: a for a in manifest.get("artifacts", [])}
    for artifact in expected["artifacts"]:
        ours = committed.get(artifact["path"], {})
        for field in sorted((set(ours) | set(artifact)) - {"path"}):
            if ours.get(field) != artifact.get(field):
                errors.append(
                    artifact["path"] + ": manifest field " + repr(field) + " is " + repr(ours.get(field))
                    + " but OWNED generates " + repr(artifact.get(field))
                )
    if not errors:
        errors.append("the manifest lists the right artifacts in a different form than --write generates")
    errors.append("the manifest is generated, never hand-written: run tools/check_normative_mirrors.py --write")
    return errors


def check_mirrors(manifest: dict, require_siblings: bool) -> tuple[list[str], list[str]]:
    """Compare each declared mirror against the artifact it mirrors."""
    errors: list[str] = []
    skipped: list[str] = []
    for artifact in manifest.get("artifacts", []):
        source_digest = artifact.get("sha256")
        for mirror in artifact.get("mirrors", []):
            repo, rel = mirror["repository"], mirror["path"]
            sibling = WORKSPACE / repo
            if not sibling.is_dir():
                message = absent_sibling_message(repo)
                if require_siblings:
                    errors.append(message)
                else:
                    skipped.append(message)
                continue
            target = sibling / rel
            if not target.is_file():
                errors.append(repo + ":" + rel + " is declared as a mirror of " + artifact["path"] + " but does not exist")
                continue
            actual = digest(target)
            if actual != source_digest:
                errors.append(
                    repo + ":" + rel + " is " + actual[:16] + "... but " + artifact["path"] + " is "
                    + str(source_digest)[:16] + "...; the mirror must follow the source, not the other way round"
                )
    return errors, sorted(set(skipped))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="regenerate the manifest from the files")
    parser.add_argument(
        "--require-siblings",
        action="store_true",
        help="treat an absent sibling repository as a failure (also set by " + REQUIRE_SIBLINGS_ENV + ")",
    )
    args = parser.parse_args(argv)

    if args.write:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(
            json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        print("wrote " + MANIFEST.relative_to(ROOT).as_posix())
        print("not verifying: this run regenerated the manifest, so comparing against it proves nothing.")
        print("re-run without --write to verify.")
        return 0

    if not MANIFEST.is_file():
        print("manifest missing: " + MANIFEST.relative_to(ROOT).as_posix() + "; run with --write", file=sys.stderr)
        return 2

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = check_self(manifest)
    errors += verify_prose_digests(ROOT)
    require = args.require_siblings or _truthy(REQUIRE_SIBLINGS_ENV)
    mirror_errors, skipped = check_mirrors(manifest, require)
    errors += mirror_errors

    for note in skipped:
        print("SKIP  " + note)
    for error in errors:
        print("ERROR " + error, file=sys.stderr)
    if errors:
        return 1
    print("normative prose OK: " + str(len(prose_paths(ROOT))) + " file(s) bound in " + PROSE_LIST)
    count = len(manifest.get("artifacts", []))
    mirrors = sum(len(a.get("mirrors", [])) for a in manifest.get("artifacts", []))
    suffix = " (" + str(len(skipped)) + " sibling(s) absent)" if skipped else ""
    print("normative mirrors OK: " + str(count) + " artifact(s), " + str(mirrors) + " declared mirror(s)" + suffix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
