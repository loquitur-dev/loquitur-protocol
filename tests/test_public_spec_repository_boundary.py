from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from conftest import tool
from status_blocks import views

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    "docs/maintainers/REPOSITORY_LAYOUT.md",
    "docs/maintainers/testing.md",
    "LICENSE-APACHE",
    "LICENSE-MIT",
    "LICENSE-docs",
    "NOTICE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "CODE_OF_CONDUCT.md",
    "docs/README.md",
    "docs/specification/introduction.md",
    "docs/specification/public-private-boundary.md",
    "docs/specification/canonicalization-and-hashing.md",
    "docs/specification/registry-entry.md",
    "docs/specification/signing-envelope-v2.md",
    "docs/specification/cryptographic-capabilities.md",
    "docs/specification/trust-root.md",
    "docs/specification/bundle-objects.md",
    "docs/specification/registry-link.md",
    "docs/specification/report-contract.md",
    "docs/specification/trust-registry-authorization.md",
    "docs/specification/verification-checks.md",
    "docs/specification/reason-codes.md",
    "docs/preview-limitations.md",
    "tools/check_public_spec_boundary.py",
    "tools/check_protocol_release.py",
    "PROTOCOL_RELEASE.json",
    "CONFORMANCE_AUTHORITY.json",
    "CONFORMANCE_LOCK.json",
    "CONFORMANCE_ORACLE_POLICY.json",
    "docs/specification/conformance-testing.md",
    "CRYPTOGRAPHIC_CAPABILITIES.json",
    "VERIFICATION_VOCABULARIES.json",
    "docs/specification/verification-vocabularies.md",
    "tools/corpus_archive.py",
    "tools/validate_corpus.py",
]

FORBIDDEN_ROOTS = [
    "scripts",
    "schemas",
    "verify",
    "verify-ts",
    "openapi",
    "docs-site",
    "website",
    "examples",
    "test_support",
]


def test_required_public_spec_paths_exist() -> None:
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).exists()]
    assert not missing


def test_forbidden_roots_absent() -> None:
    present = [p for p in FORBIDDEN_ROOTS if (ROOT / p).exists()]
    assert not present


def test_the_boundary_checker_refuses_every_forbidden_root(tmp_path: Path) -> None:
    """Each root this test lists is planted in a scratch tree, and the checker names it."""
    _scratch(tmp_path)
    for root in FORBIDDEN_ROOTS:
        (tmp_path / root).mkdir()
        (tmp_path / root / "README.md").write_text("# planted\n", encoding="utf-8")
    result = _run_checker(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    missed = [root for root in FORBIDDEN_ROOTS if f"forbidden root path present: {root}\n" not in result.stdout]
    assert not missed, f"the checker does not refuse {missed}:\n{result.stdout}"


def test_boundary_checker_passes() -> None:
    result = subprocess.run(
        [sys.executable, "tools/check_public_spec_boundary.py"],
        cwd=ROOT,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _checker():
    return tool("check_public_spec_boundary")


def _scratch(root: Path, corpus: dict[str, bytes] | None = None) -> Path:
    """A scratch tree beside a copy of the checker and this repository's configuration, its reviews
    emptied; with ``corpus``, a canonical archive of those members pinned by a lock there."""
    (root / "tools").mkdir(parents=True, exist_ok=True)
    for name in ("check_public_spec_boundary.py", "corpus_archive.py"):
        (root / "tools" / name).write_bytes((ROOT / "tools" / name).read_bytes())
    config = json.loads((ROOT / "tools/public_boundary.json").read_text(encoding="utf-8"))
    config["reviewed"] = []
    config["corpus_lock"] = None
    if corpus is not None:
        builder = _checker()._corpus_builder(root)
        data = builder.build(corpus)
        artifact = f"conformance/{builder.corpus_id(data)}.zip"
        (root / "conformance").mkdir()
        (root / artifact).write_bytes(data)
        lock = {"artifact": artifact, "sha256": hashlib.sha256(data).hexdigest()}
        (root / "CONFORMANCE_LOCK.json").write_text(json.dumps(lock), encoding="utf-8")
        config["corpus_lock"] = "CONFORMANCE_LOCK.json"
    (root / "tools/public_boundary.json").write_text(json.dumps(config), encoding="utf-8")
    return root


def _run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/check_public_spec_boundary.py"],
        cwd=root,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def test_every_needle_the_checker_carries_is_named(tmp_path: Path) -> None:
    """Each needle of each list, on the surface that list is applied to: this repository's own
    files, and the text members of the pinned corpus archive. Needles are read from the checker
    rather than restated, which is why this file spells none of them."""
    checker = _checker()
    config = json.loads((ROOT / "tools/public_boundary.json").read_text(encoding="utf-8"))
    own_files = [n for name in config["needle_lists"] for n in checker.NEEDLE_LISTS[name]]
    members = [n for name in config["archive_member_lists"] for n in checker.NEEDLE_LISTS[name]]
    assert own_files and members, "the configuration applies no needles; this test would measure nothing"
    corpus = {
        f"loquitur-conformance/vectors/member-{index}.md": f"A sentence with {needle} in it.".encode()
        for index, needle in enumerate(members)
    }
    _scratch(tmp_path, corpus=corpus)
    for index, needle in enumerate(own_files):
        (tmp_path / f"planted-{index}.md").write_text(f"A sentence with {needle} in it.", encoding="utf-8")
    result = _run_checker(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    missed = [
        f"own files: {needle!r}"
        for index, needle in enumerate(own_files)
        if f"forbidden substring {needle!r} in planted-{index}.md" not in result.stdout
    ] + [
        f"archive members: {needle!r}"
        for index, needle in enumerate(members)
        if f"forbidden substring {needle!r} in loquitur-conformance/vectors/member-{index}.md" not in result.stdout
    ]
    assert not missed, f"the checker does not refuse {missed}: {result.stdout}"


def test_the_pinned_archive_is_cleared_by_provenance_and_nothing_else(tmp_path: Path) -> None:
    """A canonical archive the lock pins is read member by member; the same bytes unpinned, or any
    byte changed, are not text and are not cleared, whatever they hold."""
    corpus = {"loquitur-conformance/vectors/a.json": b"{}\n", "loquitur-conformance/vectors/b.bin": b"\x00\x01"}
    _scratch(tmp_path, corpus=corpus)
    (tmp_path / "GOVERNANCE.md").write_text("Maintained by one person, not a team.\n", encoding="utf-8")
    [failure] = _run_checker(tmp_path).stdout.splitlines()
    assert failure.startswith("not text and no reviewed digest, so not cleared: loquitur-conformance/vectors/b.bin")
    lock = json.loads((tmp_path / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
    artifact = tmp_path / lock["artifact"]
    data = bytearray(artifact.read_bytes())
    data[len(data) // 2] ^= 1
    artifact.write_bytes(bytes(data))
    lock["sha256"] = hashlib.sha256(bytes(data)).hexdigest()
    (tmp_path / "CONFORMANCE_LOCK.json").write_text(json.dumps(lock), encoding="utf-8")
    [failure] = _run_checker(tmp_path).stdout.splitlines()
    assert failure.startswith(f"not text and no reviewed digest, so not cleared: {lock['artifact']}")


def _crafted():
    return tool("crafted_members")


def _pinned_members() -> dict[str, bytes]:
    lock = json.loads((ROOT / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
    return _checker()._corpus_builder(ROOT).members_of((ROOT / lock["artifact"]).read_bytes())


def test_the_crafted_members_are_every_member_of_the_pinned_archive_that_is_not_text() -> None:
    """Every member of the pinned archive that is not text, and holds more than NUL bytes, is one
    tools/crafted_members.py builds or lists, and the tool gives each of them as the archive holds it."""
    crafted = _crafted()
    members = _pinned_members()
    checker = _checker()
    not_text = sorted(name for name, data in members.items() if checker.text_of(data) is None and data.strip(b"\0"))
    assert crafted.differences(members) == []
    assert not_text == sorted(set(crafted.built(members)) | set(crafted.SPLICED))
    assert len(not_text) == 80


def test_the_crafted_members_are_cleared_by_provenance_and_nothing_else(tmp_path: Path) -> None:
    """With the tool, the crafted members are cleared; without it, none is. A crafted ZIP with one
    byte changed, a spliced member whose run moved, and a needle in a spliced member's text are each
    named."""
    crafted = _crafted()
    members = _pinned_members()
    built = crafted.built(members)
    corpus = {
        name: data
        for name, data in members.items()
        if name.startswith(crafted.CONTROL) or name in built or name in crafted.SPLICED
    }
    roots = iter(range(100))

    def run(sources: dict[str, bytes], *, tool: bool = True) -> list[str]:
        root = _scratch(tmp_path / f"r{next(roots)}", corpus=sources)
        (root / "GOVERNANCE.md").write_text("Maintained by one person, not a team.\n", encoding="utf-8")
        if tool:
            (root / "tools/crafted_members.py").write_bytes((ROOT / "tools/crafted_members.py").read_bytes())
        return _run_checker(root).stdout.splitlines()

    assert run(corpus) == ["public_boundary_ok"]
    uncleared = [line for line in run(corpus, tool=False) if line.startswith("not text and no reviewed digest")]
    assert len(uncleared) == 80, uncleared

    zip_name = crafted.INPUTS + "archive_intake_clean.zip"
    changed = {**corpus, zip_name: corpus[zip_name][:-1] + bytes([corpus[zip_name][-1] ^ 1])}
    [failure] = run(changed)
    assert failure.startswith(f"not text and no reviewed digest, so not cleared: {zip_name}")

    name = crafted.PREFIX + "vectors/bundles/canonical_input_not_utf8_bundle/canonical_input.json"
    offset, spliced_run = crafted.SPLICED[name]
    text = crafted.spliced(name, corpus[name])
    moved = {**corpus, name: text[: offset + 1] + spliced_run + text[offset + 1 :]}
    [failure] = run(moved)
    assert failure.startswith(f"not text and no reviewed digest, so not cleared: {name}")

    needle = _checker().NEEDLE_LISTS["private_perimeter"][0]
    planted = {**corpus, name: corpus[name][: offset + len(spliced_run)] + needle.encode() + text[offset:]}
    assert run(planted) == [f"forbidden substring {needle!r} in {name}"]


def test_readme_declares_preview_not_runtime() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "public specification surface" in text
    assert "a server or runtime implementation" in text
    assert "specification preview" in text
    assert "loquitur-schemas" in text
    assert "loquitur-verify-py" in text
    assert "loquitur-verify-ts" in text
    # The README names no repository outside the release set, in a list or in running text: the
    # repository map is the first thing an implementer reads. The lists are held by
    # test_every_repository_list_names_the_release_set_and_nothing_else; this holds the running
    # text against every repository checked out beside this one, whose names are read from the
    # checkout, so this file names none of them.
    members = set(json.loads((ROOT / "release-set.json").read_text(encoding="utf-8"))["members"])
    workspace = ROOT.parent
    others = sorted(
        p.name for p in workspace.iterdir() if p.name.startswith("loquitur-") and p.is_dir() and p.name not in members
    )
    named = [name for name in others if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text)]
    assert not named, f"README names {named}, which the release set does not hold"


def _repository_map(text: str | None = None) -> tuple[list[str], list[list[str]]]:
    """The README repository map: the private view in a working repository, else the copy's."""
    if text is None:
        found = views((ROOT / "README.md").read_text(encoding="utf-8"))
        text = found.get("private", found["published"])
    section = text.split("## Repository map", 1)[1].split("\n## ", 1)[0]
    lines = [line for line in section.splitlines() if line.startswith("|")]
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines[2:]]
    assert rows, "the repository map has no rows"
    return header, rows


def test_the_repositories_planned_for_publication_are_the_release_sets_published_members() -> None:
    # Which repositories are published lives in this map and in PUBLISHED_MEMBERS of the
    # release-set verifier, which decides which absent members it may name. Both are in this
    # repository and are held together here; the map row is how the decision reads.
    header, rows = _repository_map()
    if "Planned for publication" in header:
        column = header.index("Planned for publication")
        planned = {row[0].strip("`") for row in rows if row[column].startswith("yes")}
    else:
        # A published copy's map gives the publication order; "not ..." marks the others.
        column = header.index("Publication")
        planned = {row[0].strip("`") for row in rows if not row[column].startswith("not")}
    assert "loquitur-verify-ts" in planned, "the TypeScript verifier is published with the Python verifier"
    # The release set keys its members by directory, and every repository is checked out
    # beside the others under its own name, so the two sets are the same names.
    assert planned == set(tool("verify_release_set").PUBLISHED_MEMBERS)


# The documents that present the sibling repositories as a list a reader could follow: the two
# contribution and reporting files, and the preview limitations. They are named rather than
# discovered, because the rule below is about a list of places to go and not about every mention
# of a name: the specification documents cite a corpus member path that happens to carry one.
SIBLING_LISTS = (
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/preview-limitations.md",
)
NOT_PUBLISHED = ("not published", "unpublished")


def test_a_repository_a_reader_cannot_open_is_named_as_one() -> None:
    """Every line naming a sibling outside the published set says that it is not published.

    A reader of the published specification is told which sibling repository owns which surface
    and can follow the list; a name on it can be a repository that does not exist for them. A
    list in which one entry carries the qualifier and the entries beside it do not is misleading
    rather than incomplete: the annotated entry reads as the exception.

    The rule is per LINE rather than per document on purpose: a document-wide check passes as
    soon as one entry is annotated.
    """
    published = set(tool("verify_release_set").PUBLISHED_MEMBERS)
    assert published, "the published set is empty; the check would pass vacuously"
    pattern = re.compile(r"`(loquitur-[a-z0-9-]+)`")
    checked = 0
    for name in SIBLING_LISTS:
        for number, line in enumerate((ROOT / name).read_text(encoding="utf-8").splitlines(), start=1):
            outside = {found for found in pattern.findall(line) if found not in published}
            # A name that is a corpus identifier rather than a repository, such as the pinned
            # corpus id, is not a place a reader can go and is not one of these.
            outside = {found for found in outside if not found.startswith("loquitur-conformance-")}
            if not outside:
                continue
            checked += 1
            lowered = line.lower()
            assert any(q in lowered for q in NOT_PUBLISHED), f"{name}:{number} names {sorted(outside)}: {line}"
    assert checked >= 3, f"only {checked} lines name a sibling outside the published set; the check is thin"


def test_readme_claims_no_publication_that_has_not_happened() -> None:
    # The repository map is the first table an implementer reads, and it must not claim a
    # publication that has not happened. The private status block of a working repository
    # says that every repository is private and no package is on an index; the text a
    # published copy carries instead states no publication order and still puts no package
    # on an index. Both views are checked here, and a published copy (which has only the
    # second) is checked by the same test.
    found = views((ROOT / "README.md").read_text(encoding="utf-8"))
    if "private" in found:
        header, rows = _repository_map(found["private"])
        assert "Public" in header, f"the private repository map has no 'Public' column: {header}"
        column = header.index("Public")
        marked = [row[0] for row in rows if row[column] != "no"]
        assert not marked, f"the private status block marks {marked} as public"
    header, rows = _repository_map(found["published"])
    assert "Public" not in header, "a published copy's map has no column saying what is public"
    assert "states its own publication status" in " ".join(found["published"].split())
    for view in found.values():
        assert "repositories are published" not in view.lower()


# A published copy's text must be true at every stage of the other repositories' publication, so it
# states no other repository's publication.
PUBLICATION_CLAIM = re.compile(r"(?<!not )\bpublished\b", re.IGNORECASE)


def _publication_claims(text: str) -> list[str]:
    return [
        line
        for line in text.split("\n")
        if INVENTORY_NAME.search(line)
        and "`loquitur-protocol`" not in line
        and line.lstrip().startswith("|")
        and PUBLICATION_CLAIM.search(line)
    ]


def test_a_published_copy_says_no_other_repository_is_published() -> None:
    for name in COMPLETE_INVENTORIES:
        published = views((ROOT / name).read_text(encoding="utf-8"))["published"]
        assert not _publication_claims(published), f"{name} (published view) states a publication"
    stated = "| `loquitur-schemas` | Standalone schema package. Published after the protocol. |"
    assert _publication_claims(stated) == [stated]
    assert _publication_claims("| `loquitur-conformance` | Corpus. Not published; inside the archive. |") == []


# The documents that list the sibling repositories hold one list: the members of the release
# set, which release-set.json names. Each of them names no other repository, and the two that
# present the whole set, the README map and the GOVERNANCE table, name every member. Both
# status views are read, so a published copy is held to the same list.
COMPLETE_INVENTORIES = ("README.md", "GOVERNANCE.md")
INVENTORY_NAME = re.compile(r"`(loquitur-[a-z0-9-]+)`")


def _inventory_names(text: str) -> set[str]:
    # The pinned corpus id, the normative-authority role GOVERNANCE.md defines and the distribution
    # name of the Python verifier are not repositories.
    return {
        name
        for name in INVENTORY_NAME.findall(text)
        if not name.startswith("loquitur-conformance-") and name not in ("loquitur-protocol-governance", "loquitur-verify")
    }


def _inventory_failures(root: Path) -> list[str]:
    members = set(json.loads((root / "release-set.json").read_text(encoding="utf-8"))["members"])
    failures = []
    for name in dict.fromkeys(COMPLETE_INVENTORIES + SIBLING_LISTS):
        for view, text in views((root / name).read_text(encoding="utf-8")).items():
            found = _inventory_names(text)
            if found - members:
                failures.append(
                    f"{name} ({view} view) names {sorted(found - members)}, which the release set does not hold"
                )
            if name in COMPLETE_INVENTORIES and members - found:
                failures.append(f"{name} ({view} view) does not name {sorted(members - found)}")
    return failures


def test_every_repository_list_names_the_release_set_and_nothing_else() -> None:
    members = json.loads((ROOT / "release-set.json").read_text(encoding="utf-8"))["members"]
    assert len(members) >= 5, f"the release set holds {sorted(members)}; the check would be thin"
    assert not _inventory_failures(ROOT)


def test_the_repository_list_check_refuses_a_stranger_and_a_missing_member(tmp_path: Path) -> None:
    for name in ("release-set.json", *dict.fromkeys(COMPLETE_INVENTORIES + SIBLING_LISTS)):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())
    assert _inventory_failures(tmp_path) == []
    contributing = tmp_path / "CONTRIBUTING.md"
    contributing.write_text(
        contributing.read_text(encoding="utf-8") + "\n- `loquitur-elsewhere` for something else.\n", encoding="utf-8"
    )
    governance = tmp_path / "GOVERNANCE.md"
    governance.write_text(
        "\n".join(
            line for line in governance.read_text(encoding="utf-8").split("\n") if "`loquitur-schemas`" not in line
        ),
        encoding="utf-8",
    )
    # Each failure is reported once for each view of the document it is in: a published copy has
    # no status block left, so no private view to report.
    expected = [
        f"CONTRIBUTING.md ({view} view) names ['loquitur-elsewhere'], which the release set does not hold"
        for view in views(contributing.read_text(encoding="utf-8"))
    ] + [
        f"GOVERNANCE.md ({view} view) does not name ['loquitur-schemas']"
        for view in views(governance.read_text(encoding="utf-8"))
    ]
    assert sorted(_inventory_failures(tmp_path)) == sorted(expected)
