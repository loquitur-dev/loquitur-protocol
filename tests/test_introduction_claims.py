"""What introduction.md sections 11 and 12, and IMPLEMENTATIONS.md, may say.

Section 11 ("Implementation status") and section 12 ("Non-claims") are part of the release text,
and the release text never changes once it is published. A sentence in them that is true only
for a while, that quotes a count or a digest a later corpus moves, or that claims more than the
release has, would stay wrong for good. So each rule below is held against the text:

- both sections exist under those titles and say they are informative;
- every statement is anchored to the release, and none says "currently", "yet" or "soon";
- neither quotes a number of more than three digits, a digest or a corpus id: counts and digests
  are read from CONFORMANCE_LOCK.json, by reference;
- "independent" and "audit" appear only in the sentences that deny them;
- section 12 says that the verdict path contains no AI, and never that the project as a whole does;
- neither section, nor the published view of IMPLEMENTATIONS.md, names a repository, and none of
  them carries a phrase the public-boundary checker refuses.

IMPLEMENTATIONS.md is the living list section 11 points to. It keeps the text that holds while
its repositories are private inside a status block, with the text a published copy carries
instead, and the published view names no repository that a reader of the copy could not open.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import tool
from status_blocks import STATUS_MARKER, views

ROOT = Path(__file__).resolve().parents[1]
INTRODUCTION = ROOT / "docs" / "specification" / "introduction.md"
IMPLEMENTATIONS = ROOT / "IMPLEMENTATIONS.md"
STATUS = "11. Implementation status"
NON_CLAIMS = "12. Non-claims"
INFORMATIVE = "This section is informative."

# The only sentences of the two sections in which these words may appear: each denies the claim.
ALLOWED = {
    "independent": (
        "it is not\nindependent evidence that the text is right",
        "no independent security or cryptographic review of the specification or of either\n"
        "  implementation has been done",
    ),
    "audit": (
        "and no audit of any kind; the maintainer's own testing, carried out\n"
        "  with the help of AI tools, the conformance corpus included, is internal verification and not an\n"
        "  audit",
    ),
}


def _sections(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if title is not None:
                found[title] = "\n".join(body)
            title, body = line[3:].strip(), []
        else:
            body.append(line)
    if title is not None:
        found[title] = "\n".join(body)
    return found


def _claim_needles() -> list[str]:
    module = tool("check_public_spec_boundary")
    return list(module.CLAIM_DISCIPLINE_SUBSTRINGS) + list(module.DISCLOSURE_SUBSTRINGS)


def _two_sections() -> dict[str, str]:
    sections = _sections(INTRODUCTION.read_text(encoding="utf-8"))
    return {title: sections[title] for title in (STATUS, NON_CLAIMS)}


def test_both_sections_exist_and_say_they_are_informative() -> None:
    sections = _sections(INTRODUCTION.read_text(encoding="utf-8"))
    for title in (STATUS, NON_CLAIMS):
        assert title in sections, f"introduction.md has no section titled {title!r}"
        first = next(line for line in sections[title].splitlines() if line.strip())
        assert first == INFORMATIVE, f"section {title!r} opens with {first!r}"


def test_every_statement_is_anchored_to_the_release() -> None:
    for title, body in _two_sections().items():
        assert "release 0.1" in body, f"section {title!r} does not name the release it speaks of"
        for word in ("currently", "yet", "soon", "today", "at present"):
            assert not re.search(rf"\b{word}\b", body, re.IGNORECASE), f"section {title!r} says {word!r}"
    assert "For release 0.1:" in _two_sections()[NON_CLAIMS]


def test_no_count_digest_or_corpus_id_is_quoted() -> None:
    for title, body in _two_sections().items():
        long_numbers = re.findall(r"\d{4,}", body.replace("0.1", ""))
        assert not long_numbers, f"section {title!r} quotes {long_numbers}"
        assert "sha256:" not in body
        assert "loquitur-conformance-" not in body
        assert "CONFORMANCE_LOCK.json" in _two_sections()[STATUS]


def test_independent_and_audit_appear_only_in_the_sentences_that_deny_them() -> None:
    for title, body in _two_sections().items():
        for word, allowed in ALLOWED.items():
            rest = body
            for sentence in allowed:
                rest = rest.replace(sentence, "")
            assert not re.search(rf"\b{word}", rest, re.IGNORECASE), (
                f"section {title!r} uses {word!r} outside {allowed}"
            )
    joined = "\n".join(_two_sections().values())
    for word, allowed in ALLOWED.items():
        for sentence in allowed:
            assert sentence in joined, f"the allowed sentence for {word!r} is gone: {sentence!r}"


def test_the_non_claims_say_the_verdict_path_contains_no_ai() -> None:
    body = _two_sections()[NON_CLAIMS]
    flat = " ".join(body.split())
    assert "the verdict path contains no AI: no machine-learning model or other learned component" in flat
    assert not re.search(r"\bLoquitur contains no AI\b", flat, re.IGNORECASE)
    assert not re.search(r"\b(?:protocol|project|specification) contains no AI\b", flat, re.IGNORECASE)


def test_the_implementations_are_described_as_one_maintainers() -> None:
    flat = " ".join(_two_sections()[STATUS].split())
    assert "separately against this specification and by the same maintainer" in flat
    # Each view that lists an implementation says so; the published view, which lists none, says
    # nothing about the implementations it does not carry.
    found = views(IMPLEMENTATIONS.read_text(encoding="utf-8"))
    for label, text in found.items():
        flat = " ".join(text.split())
        if "| Implementation |" in text:
            assert "written separately against the specification, by the same maintainer" in flat, label
        else:
            for phrase in ("implementations below", "either implementation", "tests named here", "lists the implementations"):
                assert phrase not in flat, f"the {label} view lists no implementation, yet says {phrase!r}"
    # What points to the file describes it as the record it is in every view, not as a list a
    # copy that lists no implementation lacks.
    for pointer in ("README.md", "docs/README.md", "docs/preview-limitations.md", "docs/specification/introduction.md"):
        flat = " ".join(views((ROOT / pointer).read_text(encoding="utf-8"))["published"].split())
        for phrase in ("are listed in `IMPLEMENTATIONS.md`", "are listed in [`IMPLEMENTATIONS.md`]", "| the implementations known"):
            assert phrase not in flat, f"{pointer} says {phrase!r} of a file whose published copy may list none"


def test_no_section_names_a_repository_or_a_refused_phrase() -> None:
    needles = _claim_needles()
    published = views(IMPLEMENTATIONS.read_text(encoding="utf-8"))["published"]
    texts = {**_two_sections(), "IMPLEMENTATIONS.md (published view)": published}
    for title, body in texts.items():
        # IMPLEMENTATIONS.md names the reference implementations and their repositories; the two
        # introduction sections name no repository.
        named = [] if title.startswith("IMPLEMENTATIONS.md") else re.findall(r"loquitur-[a-z0-9]+(?:-[a-z0-9]+)*", body)
        assert not named, f"{title} names {named}"
        folded = body.lower()
        found = [needle for needle in needles if needle.lower() in folded]
        assert not found, f"{title} carries {found}"
        for unpublished in ("C#", "clean-room", "clean room"):
            assert unpublished.lower() not in folded, f"{title} names {unpublished!r}"


def test_implementations_keeps_its_private_text_in_a_status_block() -> None:
    text = IMPLEMENTATIONS.read_text(encoding="utf-8")
    found = views(text)
    assert STATUS_MARKER not in found["published"]
    assert "introduction.md" in text and "section 11" in text
    if "private" not in found:
        # A published copy: the release workspace has already swapped the block for its public
        # text, so the private wording must be gone with it.
        assert "not published" not in text, "a published IMPLEMENTATIONS.md keeps the private wording"
        return
    assert "not published" in found["private"]
