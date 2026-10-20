"""Check a release of loquitur-protocol and build the files a release carries.

`.github/workflows/release.yml` runs this tool, and `docs/maintainers/releasing.md` says what each
command does in the release. Four commands:

* ``check [--tag vX.Y.Z]``: the version `PROTOCOL_RELEASE.json` gives has a section with text in
  `CHANGELOG.md`; `CONFORMANCE_LOCK.json` reads as `tools/check_protocol_release.py` reads it, and
  the archive it pins is a regular file with the size, the sha256 and the corpus id the lock
  records; and `tools/compare_verify_vectors.py` is the script of `conformance-testing.md`
  section 7 byte for byte. With ``--tag``, the tag is ``v`` followed by that version. Whether the
  tag is annotated and signed is asked of git or GitHub, not of this tool, and the rest of what
  the release gate checks of the archive is asked of `tools/check_protocol_release.py`.
* ``build OUT``: writes the release files into the empty or absent directory ``OUT``: the pinned
  archive and the comparison script, copied byte for byte; a tar.gz of the specification, the
  other files `PROSE_DIGESTS.json` binds and the license files; and `LICENSE-APACHE`,
  `LICENSE-MIT`, `LICENSE-docs` and `NOTICE` themselves. The tar.gz holds the tracked files only, with their mtime set to the commit
  time of ``HEAD`` and no owner, so that two builds of one commit with one Python give the same
  bytes.
* ``sbom OUT``: writes into ``OUT`` the CycloneDX SBOM of the release files ``build`` wrote there:
  one component per file, with its name, its sha256 and its license as `NOTICE` gives it, and no
  dependency, since the files are documents, data and a script that uses only the standard library.
* ``sums OUT``: writes ``OUT/SHA256SUMS`` over every other file of ``OUT``, in the format
  ``sha256sum -c`` reads.

``version`` prints the version, ``artifact`` the path of the archive `CONFORMANCE_LOCK.json` pins,
``sbom-name`` the name of the SBOM, and ``names`` the names of every file a release carries, the
SBOM and ``SHA256SUMS`` among them, one per line: the job that attests the files checks that it was
handed exactly these, and gives the SBOM attestation the SBOM by that name.

Nothing here reads the network, runs anything the archive carries, or writes outside ``OUT``.

Exit codes: 0 done, 1 a check or a step failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import uuid
from pathlib import Path

# A plain import of the release gate beside this file, so that the lock is read by one reader.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_protocol_release import read_lock, read_pinned_archive  # noqa: E402
from refresh_prose_digests import OUTSIDE_SPECIFICATION  # noqa: E402
from requirements_inventory import sections  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# Names the SBOM serial number: the same version and digests give the same UUID.
SBOM_NAMESPACE = "https://github.com/loquitur-dev/loquitur-protocol/sbom/"
RELEASE_ID = re.compile(r"loquitur-protocol-(?P<version>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))")
SCRIPT = "tools/compare_verify_vectors.py"
DOCUMENT = "docs/specification/conformance-testing.md"
LICENSES = ("LICENSE-APACHE", "LICENSE-MIT", "LICENSE-docs", "NOTICE")
LICENSE_TEXTS = LICENSES[:3]
# What the specification tar.gz holds, beside the license files: the specification, and the other
# files docs/specification/PROSE_DIGESTS.json binds, so that the tar.gz can check its own digest list.
# Every relative link of these files resolves inside the tar.gz. docs/README.md, the table of
# contents of the repository's docs/, links pages the tar.gz does not hold, and is left out: the
# specification's own map is introduction.md section 3.
SPECIFICATION = ("docs/specification", *OUTSIDE_SPECIFICATION)
SUMS = "SHA256SUMS"
FENCE = re.compile(r"^```(?P<lang>[a-z]*)\n(?P<body>.*?)^```$", re.M | re.S)


def version(root: Path = ROOT) -> str:
    """The version `PROTOCOL_RELEASE.json` names in its `protocol_release_id`."""
    release = json.loads((root / "PROTOCOL_RELEASE.json").read_text(encoding="utf-8"))
    match = RELEASE_ID.fullmatch(release.get("protocol_release_id", ""))
    if not match:
        raise ValueError("PROTOCOL_RELEASE.json names no release id of the form loquitur-protocol-X.Y.Z")
    return match["version"]


def _lock(root: Path) -> dict:
    """`CONFORMANCE_LOCK.json`, read by the release gate's reader; a lock it refuses raises."""
    lock, errors = read_lock(root)
    if lock is None:
        raise ValueError("; ".join(errors))
    return lock


def sbom_name(current: str) -> str:
    """The name of the CycloneDX SBOM the workflow writes for ``current``."""
    return f"loquitur-protocol-{current}.cdx.json"


def names(root: Path = ROOT) -> list[str]:
    """Every file a release of the tree at ``root`` carries, sorted by code point."""
    current = version(root)
    built = [Path(_lock(root)["artifact"]).name, Path(SCRIPT).name, f"loquitur-protocol-specification-{current}.tar.gz"]
    return sorted([*built, *LICENSES, sbom_name(current), SUMS])


def has_changelog_section(changelog: str, current: str) -> bool:
    """Whether ``changelog`` has the release section of ``current``, with text in it.

    Its heading is exactly ``## [X.Y.Z]`` or ``## [X.Y.Z] - YYYY-MM-DD``, with an ASCII hyphen and
    ASCII digits, and some text stands between it and the next ``## `` heading or the end of the
    file.
    """
    heading = re.search(rf"^## \[{re.escape(current)}\](?: - \d{{4}}-\d{{2}}-\d{{2}})?$", changelog, re.M | re.ASCII)
    if heading is None:
        return False
    body = re.split(r"^## ", changelog[heading.end() :], maxsplit=1, flags=re.M)[0]
    return bool(body.strip())


def section(text: str, number: str) -> str:
    """Section ``number`` of a document, such as ``7`` or ``4.1``: from its heading to the next one.

    The sections are the ones `tools/requirements_inventory.py` reads, so a heading-like line
    inside a fenced block neither starts nor ends one.
    """
    for found in sections(DOCUMENT, text):
        if found.id == number:
            return found.text
    raise ValueError(f"{DOCUMENT} has no section {number}")


def blocks(text: str, number: str, language: str) -> list[str]:
    """The fenced ``language`` blocks of section ``number`` of a document, in order."""
    return [m["body"] for m in FENCE.finditer(section(text, number)) if m["lang"] == language]


def documented_script(root: Path = ROOT) -> str:
    """The one ``python`` block of section 7 of conformance-testing.md."""
    found = blocks((root / DOCUMENT).read_text(encoding="utf-8"), "7", "python")
    if len(found) != 1:
        raise ValueError(f"section 7 of {DOCUMENT} has {len(found)} python blocks, not one")
    return found[0]


def _check(root: Path, tag: str | None = None) -> tuple[str | None, dict | None, list[str]]:
    """The version, the lock, and what stops a release of the tree at ``root`` under ``tag``."""
    try:
        current = version(root)
    except ValueError as exc:
        return None, None, [str(exc)]
    found: list[str] = []
    # The version has the form X.Y.Z with no leading zero (RELEASE_ID), so this one comparison
    # also holds the tag to the form vX.Y.Z.
    if tag is not None and tag != f"v{current}":
        found.append(f"tag {tag} does not name the version PROTOCOL_RELEASE.json gives, {current}")
    if not has_changelog_section((root / "CHANGELOG.md").read_text(encoding="utf-8"), current):
        found.append(f"CHANGELOG.md has no section ## [{current}] with text in it")
    lock, errors = read_lock(root)
    found.extend(errors)
    if lock is not None:
        found.extend(read_pinned_archive(root, lock)[1])
    try:
        if (root / SCRIPT).read_bytes() != documented_script(root).encode("utf-8"):
            found.append(f"{SCRIPT} is not the script of section 7 of {DOCUMENT}")
    except (OSError, ValueError) as exc:
        found.append(str(exc))
    return current, lock, found


def problems(root: Path = ROOT, tag: str | None = None) -> list[str]:
    """What stops a release of the tree at ``root`` under ``tag``; empty when nothing does."""
    return _check(root, tag)[2]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, encoding="utf-8", check=True).stdout


def _tracked(root: Path, *paths: str) -> list[str]:
    return sorted(name for name in _git(root, "ls-files", "-z", "--", *paths).split("\0") if name)


def specification_tarball(root: Path, name: str) -> bytes:
    """The tar.gz of the specification: every tracked file under SPECIFICATION and the licenses."""
    members = _tracked(root, *SPECIFICATION) + list(LICENSES)
    mtime = int(_git(root, "log", "-1", "--format=%ct", "HEAD").strip())
    # Every directory gets its own entry, with a fixed mode, so the archive extracts alike everywhere.
    directories = {parent.as_posix() for member in members for parent in Path(member).parents} - {"."}
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for directory in [name] + [f"{name}/{d}" for d in sorted(directories)]:
            info = tarfile.TarInfo(directory)
            info.type, info.mode, info.mtime = tarfile.DIRTYPE, 0o755, mtime
            tar.addfile(info)
        for member in members:
            data = (root / member).read_bytes()
            info = tarfile.TarInfo(f"{name}/{member}")
            info.size, info.mode, info.mtime = len(data), 0o644, mtime
            tar.addfile(info, io.BytesIO(data))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0, compresslevel=9) as stream:
        stream.write(raw.getvalue())
    return compressed.getvalue()


def build(root: Path, out: Path) -> list[str]:
    """Write the release files into ``out`` and return their names; refuses a tree ``check`` fails."""
    current, lock, found = _check(root)
    if found:
        raise ValueError("the tree does not pass the release check: " + "; ".join(found))
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    archive = root / lock["artifact"]
    shutil.copyfile(archive, out / archive.name)
    shutil.copyfile(root / SCRIPT, out / Path(SCRIPT).name)
    tarball = f"loquitur-protocol-specification-{current}"
    (out / f"{tarball}.tar.gz").write_bytes(specification_tarball(root, tarball))
    for name in LICENSES:
        shutil.copyfile(root / name, out / name)
    return sorted(p.name for p in out.iterdir())


def licence(name: str, current: str) -> str | None:
    """The SPDX expression of release file ``name``, as `NOTICE` gives it; None for a license text.

    The specification tar.gz holds the specification, under CC BY 4.0 with its code blocks also
    MIT OR Apache-2.0, beside JSON and governance files under MIT OR Apache-2.0. A license text is
    the text of its license and carries none of its own here.
    """
    if name == f"loquitur-protocol-specification-{current}.tar.gz":
        return "CC-BY-4.0 AND (MIT OR Apache-2.0)"
    if name in LICENSE_TEXTS:
        return None
    return "MIT OR Apache-2.0"


def sbom_document(out: Path, current: str) -> dict:
    """The CycloneDX SBOM of the release files in ``out``: each file, its sha256 and its license.

    The components are the files themselves, every file of ``out`` but the SBOM and SHA256SUMS.
    The release files are documents, data and one script that uses only the Python standard
    library, so the SBOM lists no dependency. The ``serialNumber`` is a name-based UUID of the
    version and the digests, so the same files give the same SBOM; the attestation action
    recognises a CycloneDX document by that member.
    """
    files = sorted(
        (p for p in out.iterdir() if p.is_file() and p.name not in (SUMS, sbom_name(current))), key=lambda p: p.name
    )
    if not files:
        raise ValueError(f"{out} holds no release file to describe")
    components = []
    for path in files:
        component: dict = {
            "type": "file",
            "bom-ref": path.name,
            "name": path.name,
            "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(path.read_bytes()).hexdigest()}],
        }
        expression = licence(path.name, current)
        if expression:
            component["licenses"] = [{"expression": expression}]
        components.append(component)
    identity = chr(10).join([current, *(f"{c['name']} {c['hashes'][0]['content']}" for c in components)])
    serial = uuid.uuid5(uuid.NAMESPACE_URL, SBOM_NAMESPACE + identity)
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "data",
                "bom-ref": f"loquitur-protocol@{current}",
                "name": "loquitur-protocol",
                "version": current,
            }
        },
        "components": components,
    }


def sbom(root: Path, out: Path) -> str:
    """Write the CycloneDX SBOM of the release files in ``out`` into ``out``; return its name."""
    current = version(root)
    name = sbom_name(current)
    if (out / name).exists():
        raise ValueError(f"{out / name} already exists")
    text = json.dumps(sbom_document(out, current), indent=2, ensure_ascii=False) + "\n"
    (out / name).write_bytes(text.encode("utf-8"))
    return name


def sums(out: Path) -> str:
    """Write ``out/SHA256SUMS`` over every other file of ``out`` and return its text."""
    # Sorted by the name's code points, as on every platform, not by a path order that folds case.
    files = sorted((p for p in out.iterdir() if p.is_file() and p.name != SUMS), key=lambda p: p.name)
    if not files:
        raise ValueError(f"{out} holds no file to sum")
    text = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files)
    (out / SUMS).write_bytes(text.encode("utf-8"))
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="the loquitur-protocol checkout")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version", help="print the version PROTOCOL_RELEASE.json gives")
    commands.add_parser("artifact", help="print the path of the archive CONFORMANCE_LOCK.json pins")
    commands.add_parser("names", help="print the name of every file a release carries")
    commands.add_parser("sbom-name", help="print the name of the SBOM a release carries")
    check = commands.add_parser("check", help="check the version, the changelog, the lock and the script")
    check.add_argument("--tag", help="the tag to release, vX.Y.Z")
    for name, text in (
        ("build", "write the release files"),
        ("sbom", "write the CycloneDX SBOM of the release files"),
        ("sums", "write SHA256SUMS"),
    ):
        commands.add_parser(name, help=text).add_argument("out", type=Path)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        if args.command == "version":
            print(version(args.root))
        elif args.command == "artifact":
            print(_lock(args.root)["artifact"])
        elif args.command == "names":
            for name in names(args.root):
                print(name)
        elif args.command == "check":
            found = problems(args.root, args.tag)
            for line in found:
                print(f"release check failed: {line}")
            if found:
                return 1
            print(f"release check ok: {version(args.root)}" + (f" as {args.tag}" if args.tag else ""))
        elif args.command == "sbom-name":
            print(sbom_name(version(args.root)))
        elif args.command == "build":
            for name in build(args.root, args.out):
                print(name)
        elif args.command == "sbom":
            print(sbom(args.root, args.out))
        else:
            sys.stdout.write(sums(args.out))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"release {args.command} failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
