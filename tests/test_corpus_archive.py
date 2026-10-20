"""tools/corpus_archive.py: the canonical archive is a pure function of its members, and nothing else
reads back as one."""

from __future__ import annotations

import hashlib
import io
import json
import random
import zipfile
import zlib
from pathlib import Path

import pytest
from conftest import tool

ROOT = Path(__file__).resolve().parents[1]


ca = tool("corpus_archive")
P = ca.PREFIX

SMALL = {
    P + "vectors/a.json": b'{\n  "a": 1\n}\n',
    P + "vectors/b/zeros.bin": bytes(1000),
    P + "vectors/b/short.txt": b"xy",
    P + "conformance-manifest.json": b"{}\n",
}
# The format is fixed: this digest moves only when the builder's output format changes, and a change
# of format changes every corpus id.
SMALL_SHA256 = "b97fd9f291efa26b06ec913e10d47eb464347bd0cdd8446155bb27048980a081"


def _samples():
    generator = random.Random(7)
    for size in (0, 1, 3, 4, 5, 257, 258, 259, 260, 261, 262, 4099, 70000):
        yield bytes(size)
        yield bytes(generator.randrange(256) for _ in range(size))
        yield bytes(generator.choice(b"aab  \n") for _ in range(size))
        yield b"x" * size + b"y" + b"z" * (size // 2)


@pytest.mark.parametrize("data", list(_samples()), ids=lambda data: f"{len(data)}-{zlib.crc32(data):08x}")
def test_deflate_inflates_back_to_its_input(data: bytes) -> None:
    assert zlib.decompress(ca.deflate(data), -15) == data


def test_build_is_deterministic_and_readable_by_zipfile() -> None:
    first = ca.build(SMALL)
    assert ca.build(dict(reversed(list(SMALL.items())))) == first
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.testzip() is None
        assert {info.filename: archive.read(info) for info in archive.infolist()} == SMALL
        assert [info.filename for info in archive.infolist()] == sorted(SMALL, key=str.encode)
        assert all(info.extra == b"" and info.comment == b"" and info.flag_bits == 0 for info in archive.infolist())


def test_known_answer_pins_the_format() -> None:
    assert hashlib.sha256(ca.build(SMALL)).hexdigest() == SMALL_SHA256


def test_members_of_returns_exactly_the_members() -> None:
    assert ca.members_of(ca.build(SMALL)) == SMALL


def test_every_one_byte_change_is_refused() -> None:
    data = ca.build(SMALL)
    accepted = []
    for offset in range(len(data)):
        changed = bytearray(data)
        changed[offset] ^= 0x01
        try:
            ca.members_of(bytes(changed))
        except ca.CanonicalArchiveError:
            continue
        accepted.append(offset)
    assert accepted == []


@pytest.mark.parametrize(
    "alter",
    [
        lambda data: data + b"\x00",
        lambda data: b"\x00" + data,
        lambda data: data[:-1],
        lambda data: data[:-2] + b"\x01\x00",  # a comment length with no comment
        lambda data: b"",
    ],
    ids=["trailing-byte", "leading-byte", "truncated", "comment-length", "empty"],
)
def test_bytes_the_builder_would_not_write_are_refused(alter) -> None:
    with pytest.raises(ca.CanonicalArchiveError):
        ca.members_of(alter(ca.build(SMALL)))


def _with_member_payload(name: str, packed: bytes) -> bytes:
    """``SMALL``'s archive with ``name`` stored as ``packed``, every record written as the builder writes it."""
    body, central = b"", b""
    for member in sorted(SMALL, key=str.encode):
        data = SMALL[member]
        payload = packed if member == name else ca.deflate(data)
        method = 8
        if member != name and len(payload) >= len(data):
            payload, method = data, 0
        raw = member.encode("ascii")
        central += ca._central_record(raw, method, zlib.crc32(data), len(payload), len(data), len(body))
        body += ca._local_record(raw, method, zlib.crc32(data), len(payload), len(data)) + payload
    return body + central + ca._end_record(len(SMALL), len(central), len(body))


def test_a_member_compressed_otherwise_is_refused_by_the_rebuild_alone() -> None:
    """Records the builder writes around a DEFLATE stream it does not write: only the rebuild sees it."""
    name = P + "vectors/b/zeros.bin"
    other = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = other.compress(SMALL[name]) + other.flush()
    assert packed != ca.deflate(SMALL[name])
    archive = _with_member_payload(name, packed)
    with zipfile.ZipFile(io.BytesIO(archive)) as readable:
        assert readable.testzip() is None
    with pytest.raises(ca.CanonicalArchiveError, match="not the canonical build"):
        ca.members_of(archive)


@pytest.mark.parametrize(
    "place",
    ["stored-bytes", "local-version", "central-offset", "end-count"],
)
def test_a_record_the_builder_would_not_write_is_refused_before_the_rebuild(place: str, monkeypatch) -> None:
    """A member's bytes that do not have its CRC-32, a changed local header field, central directory
    record or end record is found from the records themselves, without rebuilding the archive."""
    data = bytearray(ca.build(SMALL))
    central = data.rindex(b"PK\x01\x02")
    end = data.rindex(b"PK\x05\x06")
    stored = data.index(b"short.txtxy") + len(b"short.txt")
    offset = {"stored-bytes": stored, "local-version": 4, "central-offset": central + 42, "end-count": end + 8}[place]
    data[offset] ^= 0x01

    def no_rebuild(members):
        raise AssertionError("the archive was rebuilt")

    monkeypatch.setattr(ca, "build", no_rebuild)
    with pytest.raises(ca.CanonicalArchiveError, match="not the canonical build"):
        ca.members_of(bytes(data))


def test_an_archive_zipfile_writes_is_not_canonical() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in SMALL.items():
            archive.writestr(zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)), data)
    with pytest.raises(ca.CanonicalArchiveError):
        ca.members_of(buffer.getvalue())


@pytest.mark.parametrize(
    "names",
    [
        [P + "vectors/a b.json"],
        [P + "vectors/CON.json"],
        [P + "vectors/-a.json"],
        [P + "vectors/a."],
        [P + "vectors/../a.json"],
        [P + "vectors/é.json"],
        ["outside/a.json"],
        [P + "vectors/A.json", P + "vectors/a.json"],
        [P + "vectors/a", P + "vectors/A/b"],
        [P + "vectors/D/a", P + "vectors/d/b"],
    ],
)
def test_non_portable_or_conflicting_names_are_refused(names: list[str]) -> None:
    assert ca.name_errors(names)
    with pytest.raises(ca.CanonicalArchiveError):
        ca.build(dict.fromkeys(names, b"x"))


def test_portable_distinct_names_pass() -> None:
    assert ca.name_errors([P + "vectors/a/b.json", P + "vectors/a/c.json", P + "vectors/A.b"]) == []


def _protocol_copies() -> dict[str, bytes]:
    return {path: (ROOT / path).read_bytes() for path in ca.PROTOCOL_COPIES}


def test_corpus_members_and_manifest_carry_no_self_reference() -> None:
    vectors = {"vectors/x.json": b"{}\n", "vectors/y/z.bin": bytes(10)}
    profiles = [{"compatibility_class": "wire-exact", "files": ["vectors/x.json"], "id": "p"}]
    members = ca.corpus_members(vectors, _protocol_copies(), profiles)
    manifest = json.loads(members[P + ca.MANIFEST])
    assert manifest["schema_version"] == ca.MANIFEST_SCHEMA
    assert manifest["profiles"] == profiles
    assert [entry["path"] for entry in manifest["files"]] == sorted(
        [*vectors, *("protocol/" + path for path in ca.PROTOCOL_COPIES)], key=str.encode
    )
    for entry in manifest["files"]:
        content = members[P + entry["path"]]
        assert entry == {"bytes": len(content), "path": entry["path"], "sha256": hashlib.sha256(content).hexdigest()}
    data = ca.build_corpus(vectors, _protocol_copies(), profiles)
    identity = ca.corpus_id(data)
    assert ca.ID_PATTERN.fullmatch(identity)
    assert identity == "loquitur-conformance-" + hashlib.sha256(data).hexdigest()[:16]
    assert all(identity.encode() not in content for content in members.values())
    assert ca.build_corpus(vectors, _protocol_copies(), profiles) == data


def test_corpus_sources_outside_the_layout_are_refused() -> None:
    with pytest.raises(ca.CanonicalArchiveError):
        ca.corpus_members({"tools/x.py": b""}, _protocol_copies(), [])
    copies = _protocol_copies()
    copies.pop(ca.PROTOCOL_COPIES[0])
    with pytest.raises(ca.CanonicalArchiveError):
        ca.corpus_members({}, copies, [])
