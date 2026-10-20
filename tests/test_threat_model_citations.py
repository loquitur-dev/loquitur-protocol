"""The code citations in threat-model.md name definitions loquitur-verify-py still has.

threat-model.md cites definitions of the reference implementation by name,
`<module>.py::<name>`: a line is only true of one commit, which the published copies of these
repositories do not carry. Where another normative document of this repository specifies a
rule, the document refers to that section instead of citing code.

This test pins the citations the document keeps, so that one added or dropped is noticed, and
requires, in the loquitur-verify-py checkout beside this repository, that each names a top-level
definition of `src/loquitur/verify/<module>.py` whose source still carries what the document
cites it for. The note above the first section names the release those citations resolve in,
which must be the version of that checkout, and not the name of a commit.
It skips without that sibling, and fails instead under LOQUITUR_REQUIRE_SIBLINGS.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from code_citations import checked_out_version, citations, definitions, releases

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/specification/threat-model.md"
SOURCE = ROOT.parent / "loquitur-verify-py" / "src" / "loquitur" / "verify"
COMMIT = re.compile(r"\b[0-9a-f]{40}\b")

# Each citation the document keeps, how often, and what the named definition's source must hold
# for the sentence citing it to be true.
CITED: dict[tuple[str, str], tuple[int, tuple[str, ...]]] = {
    ("runner.py", "_registry_dict"): (1, ("TRUST_REGISTRY_ROOT_NOT_AUTHENTICATED", "TRUST_REGISTRY_FAILED")),
    ("runner.py", "_registry_link_dict"): (2, ('"signature_verified": False', '"anchor_finality_verified": False')),
    ("runner.py", "_trust_registry_dict"): (1, ('"anchor_finality_verified": False',)),
    ("trust_registry.py", "verify_registry_entry_trust"): (
        1,
        ("issuer_real_world_identity_not_verified_beyond_supplied_trust_registry",),
    ),
    ("secp256k1.py", "verify_digest"): (
        1,
        ("s > SECP256K1_N // 2", "ec.SECP256K1()", "Prehashed(hashes.SHA256())"),
    ),
    ("trust_root.py", "PINNED_TRUST_ROOTS"): (1, ("= ()",)),
    ("archive.py", "safe_extract_zip"): (1, ('open("xb")',)),
}


def test_the_note_names_the_release_a_published_reader_can_resolve() -> None:
    """The note names the release of loquitur-verify-py the citations resolve in, and no commit.

    A published copy of that repository carries one squashed commit, so a commit of its
    development history cannot be resolved there; its release can, and it is the version of the
    checkout the citations are checked against.
    """
    head = DOCUMENT.read_text(encoding="utf-8").split("\n## ", 1)[0]
    flat = " ".join(line.lstrip("> ") for line in head.splitlines())
    assert "Non-normative note on citations." in flat
    assert "`<module>.py::<name>`" in flat and "not part of the protocol" in flat
    assert not COMMIT.search(flat), "the note names a commit a published copy does not carry"
    assert releases(flat) == [("loquitur-verify-py", checked_out_version("loquitur-verify-py"))]


def test_the_document_keeps_exactly_the_pinned_citations_and_no_line_citation() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")
    assert Counter(citations(text)) == {cited: count for cited, (count, _) in CITED.items()}
    assert not re.findall(r"[A-Za-z0-9_./-]+\.py:\d", text), "threat-model.md cites a line"


def test_every_citation_names_a_definition_that_still_does_what_it_is_cited_for() -> None:
    problems: list[str] = []
    for (module, name), (_, anchors) in CITED.items():
        found = definitions(SOURCE / module)
        if name not in found:
            problems.append(f"{module}::{name} is not a top-level definition of loquitur-verify-py")
            continue
        problems += [f"{module}::{name} does not hold {anchor!r}" for anchor in anchors if anchor not in found[name]]
    assert not problems, "\n".join(problems)
