"""The views of a document that carries status blocks.

A status block keeps the text that holds while the repositories are private, with the text a
published copy carries instead in a comment beside it. The release copy swaps each block for its
public text, so a published copy has no block left.

Not a test module: pytest collects test_*.py, and this is imported by them.
"""

from __future__ import annotations

# The marker of a status block, spelled in two parts: a published copy must not carry it, and the
# publication scanner refuses it there.
STATUS_MARKER = "<!-- lq-status" + "-block: "


def views(text: str) -> dict[str, str]:
    """The views of ``text`` that exist, by label: ``private`` while it has a block, and ``published``.

    A published copy has no blocks left: its text is the published view, and there is no private one.
    """
    if STATUS_MARKER not in text:
        return {"published": text}
    private: list[str] = []
    public: list[str] = []
    state = "outside"
    for line in text.split("\n"):
        if line == STATUS_MARKER + "private -->":
            state = "private"
        elif line == STATUS_MARKER + "public":
            state = "public"
        elif line == "-->" and state == "public":
            state = "closed"
        elif line == STATUS_MARKER + "end -->":
            state = "outside"
        elif state in ("outside", "private"):
            private.append(line)
            if state == "outside":
                public.append(line)
        elif state == "public":
            public.append(line)
    assert state == "outside", "a status block is not closed"
    return {"private": "\n".join(private), "published": "\n".join(public)}
