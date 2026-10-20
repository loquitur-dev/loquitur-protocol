"""The canonical conformance archive: one byte stream for one set of members.

The archive in ``conformance/`` is a pure function of its members' paths and bytes. This module
is that function, ``build``, and its inverse on canonical input only, ``members_of``. The release
gate (``check_protocol_release.py``) and the public-boundary checker decide on the pinned archive
by provenance: ``members_of`` reads the canonical layout, rebuilds it with ``build`` and requires
the rebuild to equal the input byte for byte, so any byte the builder would not have written
fails, whatever it holds, without being interpreted.

Format, fixed:

* members sorted by the UTF-8 bytes of their names; every name is a portable member name
  (``bundle-objects.md`` section 2) under ``loquitur-conformance/`` and no two names conflict;
* no directory entries, extra fields, comments, data descriptors or ZIP64 records; version 20,
  flags 0, the DOS time 1980-01-01 00:00, external attributes 0o644 regular file;
* each member is compressed with the DEFLATE encoder below (one fixed-Huffman block of literals
  and distance-1 runs) or stored when that is not strictly smaller.

The encoder is this module's own, so that the bytes do not depend on the zlib a host links.
Reading uses ``zlib`` for inflation only; what decides is the comparison with the rebuild.

The corpus id is ``loquitur-conformance-`` followed by the first 16 hexadecimal characters of
the archive's SHA-256, so an id names exactly one byte stream and the archive never contains its
own id. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import zlib
from collections.abc import Iterable, Mapping
from pathlib import Path

PREFIX = "loquitur-conformance/"
MANIFEST = "conformance-manifest.json"
MANIFEST_SCHEMA = "loquitur.conformance_manifest.v2"
ID_PREFIX = "loquitur-conformance-"
ID_PATTERN = re.compile(r"loquitur-conformance-[0-9a-f]{16}")

# The protocol-owned normative files the vectors need, copied byte for byte under protocol/ at
# their path in loquitur-protocol. The seven schemas travel at vectors/schemas/. The schema of a
# registered vocabulary travels, and the registered vocabularies under vocabularies/ do not: the
# corpus carries vocabularies of its own under vectors/vocabularies/, so that registering a value
# changes no member of the archive (verification-vocabularies.md section 9).
PROTOCOL_COPIES = (
    "CRYPTOGRAPHIC_CAPABILITIES.json",
    "VERIFICATION_VOCABULARIES.json",
    "docs/specification/compatibility-classes.json",
    "docs/specification/reason-codes/schema.json",
    "docs/specification/reason-codes/v2.0/catalog.json",
    "docs/specification/registered-vocabularies/schema.json",
)
SCHEMA_COPIES_DIRECTORY = "docs/specification/schemas/"
VECTOR_SCHEMAS_DIRECTORY = "vectors/schemas/"

_MAX_MEMBERS = 0xFFFF
_MAX_SIZE = 0xFFFFFFFF
_VERSION = 20
_MADE_BY = 0x0300 | _VERSION  # made by a Unix host, so the external attributes carry a file mode
_DOS_TIME = 0x0000
_DOS_DATE = 0x0021
_EXTERNAL = 0o100644 << 16
_LOCAL = struct.Struct("<IHHHHHIIIHH")
_CENTRAL = struct.Struct("<IHHHHHHIIIHHHHHII")
_END = struct.Struct("<IHHHHIIH")
_LOCAL_SIGNATURE = 0x04034B50
_CENTRAL_SIGNATURE = 0x02014B50
_END_SIGNATURE = 0x06054B50

_PORTABLE_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")
_DEVICE_NAMES = frozenset(
    ["con", "prn", "aux", "nul"] + [f"com{n}" for n in range(1, 10)] + [f"lpt{n}" for n in range(1, 10)]
)
_FOLD = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


_NOT_THE_BUILD = "the bytes are not the canonical build of the members they hold"


class CanonicalArchiveError(ValueError):
    """The input is not a canonical archive, or the members cannot form one."""


# --- names -------------------------------------------------------------------------------------


def portable_name(name: str) -> bool:
    """True when ``name`` is a portable member name of ``bundle-objects.md`` section 2."""
    if not name or len(name.encode("utf-8")) > 255:
        return False
    for segment in name.split("/"):
        if not _PORTABLE_SEGMENT.fullmatch(segment):
            return False
        if segment in (".", "..") or segment.endswith(".") or segment.startswith("-"):
            return False
        if segment.split(".", 1)[0].translate(_FOLD) in _DEVICE_NAMES:
            return False
    return True


def name_errors(names: Iterable[str]) -> list[str]:
    """Every name that is not portable or not under the prefix, and every conflicting pair."""
    errors: list[str] = []
    seen: dict[str, tuple[str, str]] = {}  # folded -> (spelling, "file" or "directory")
    for name in sorted(names):
        if not name.startswith(PREFIX) or not portable_name(name):
            errors.append(f"not a portable member name under {PREFIX}: {name!r}")
            continue
        parts = name.split("/")
        entries = [("/".join(parts[:i]), "directory") for i in range(1, len(parts))] + [(name, "file")]
        for spelling, kind in entries:
            folded = spelling.translate(_FOLD)
            previous = seen.get(folded)
            if previous is None:
                seen[folded] = (spelling, kind)
            elif previous != (spelling, kind):
                errors.append(f"member names conflict: {previous[0]!r} and {spelling!r}")
    return errors


# --- deflate -----------------------------------------------------------------------------------


def _fixed_literal_bits() -> list[str]:
    table = []
    for value in range(288):
        if value < 144:
            code, width = 0x30 + value, 8
        elif value < 256:
            code, width = 0x190 + value - 144, 9
        elif value < 280:
            code, width = value - 256, 7
        else:
            code, width = 0xC0 + value - 280, 8
        table.append(format(code, f"0{width}b"))  # Huffman codes are sent most significant bit first
    return table


_LITERAL = _fixed_literal_bits()
_LENGTH_BASE = (
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    13,
    15,
    17,
    19,
    23,
    27,
    31,
    35,
    43,
    51,
    59,
    67,
    83,
    99,
    115,
    131,
    163,
    195,
    227,
    258,
)
_LENGTH_EXTRA = (0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0)


def _length_bits(length: int) -> str:
    index = max(i for i in range(29) if _LENGTH_BASE[i] <= length)
    bits = _LITERAL[257 + index]
    if _LENGTH_EXTRA[index]:
        bits += format(length - _LENGTH_BASE[index], f"0{_LENGTH_EXTRA[index]}b")[::-1]  # extra bits: LSB first
    return bits + "00000"  # distance code 0, distance 1


_LENGTHS = {length: _length_bits(length) for length in range(3, 259)}
_RUN_START = re.compile(rb"(.)\1\1\1", re.S)
_STRIDE = 4096


def _runs(data: bytes):
    """(start, end) of every maximal run of four or more equal bytes, left to right."""
    position, size = 0, len(data)
    while (match := _RUN_START.search(data, position)) is not None:
        start = match.start()
        end = start + 4
        stride = data[start : start + 1] * _STRIDE
        while data.startswith(stride, end):
            end += _STRIDE
        while end < size and data[end] == data[start]:
            end += 1
        yield start, end
        position = end


def deflate(data: bytes) -> bytes:
    """One final fixed-Huffman DEFLATE block (RFC 1951): literals, and runs of four or more equal bytes
    as the byte followed by length codes at distance 1. Deterministic by construction."""
    parts = ["110"]  # BFINAL 1, then BTYPE 01 written least significant bit first
    literal = _LITERAL.__getitem__
    position = 0
    for start, end in _runs(data):
        parts.extend(map(literal, data[position : start + 1]))
        rest = end - start - 1
        while rest >= 3:
            length = min(258, rest)
            if length == 258 and rest - length in (1, 2):
                length = 256
            parts.append(_LENGTHS[length])
            rest -= length
        parts.extend(map(literal, data[end - rest : end]))
        position = end
    parts.extend(map(literal, data[position:]))
    parts.append(_LITERAL[256])
    bits = "".join(parts)
    bits += "0" * (-len(bits) % 8)
    # Character i of ``bits`` is bit i of the stream: bit i % 8 of byte i // 8.
    return int(bits[::-1], 2).to_bytes(len(bits) // 8, "little")


# --- build -------------------------------------------------------------------------------------


def build(members: Mapping[str, bytes]) -> bytes:
    """The canonical archive of ``members``, a mapping of full member name to bytes."""
    errors = name_errors(members)
    if errors:
        raise CanonicalArchiveError("; ".join(errors))
    if len(members) > _MAX_MEMBERS:
        raise CanonicalArchiveError(f"{len(members)} members; the canonical archive holds at most {_MAX_MEMBERS}")
    body = bytearray()
    central = bytearray()
    for name in sorted(members, key=lambda n: n.encode("utf-8")):
        data = bytes(members[name])
        raw = name.encode("ascii")
        packed = deflate(data)
        method = 8
        if len(packed) >= len(data):
            packed, method = data, 0
        if len(data) > _MAX_SIZE or len(body) > _MAX_SIZE:
            raise CanonicalArchiveError("the canonical archive does not use ZIP64; a member or offset is too large")
        crc = zlib.crc32(data)
        offset = len(body)
        body += _local_record(raw, method, crc, len(packed), len(data)) + packed
        central += _central_record(raw, method, crc, len(packed), len(data), offset)
    if len(body) + len(central) > _MAX_SIZE:
        raise CanonicalArchiveError("the canonical archive does not use ZIP64; the archive is too large")
    return bytes(body + central + _end_record(len(members), len(central), len(body)))


def _local_record(raw: bytes, method: int, crc: int, packed: int, size: int) -> bytes:
    """The local record ``build`` writes for one member, up to its data."""
    return (
        _LOCAL.pack(_LOCAL_SIGNATURE, _VERSION, 0, method, _DOS_TIME, _DOS_DATE, crc, packed, size, len(raw), 0) + raw
    )


def _central_record(raw: bytes, method: int, crc: int, packed: int, size: int, offset: int) -> bytes:
    """The central directory record ``build`` writes for one member, its name included."""
    return (
        _CENTRAL.pack(
            _CENTRAL_SIGNATURE,
            _MADE_BY,
            _VERSION,
            0,
            method,
            _DOS_TIME,
            _DOS_DATE,
            crc,
            packed,
            size,
            len(raw),
            0,
            0,
            0,
            0,
            _EXTERNAL,
            offset,
        )
        + raw
    )


def _end_record(count: int, central: int, body: int) -> bytes:
    """The end of central directory record ``build`` writes after ``count`` members."""
    return _END.pack(_END_SIGNATURE, 0, 0, count, count, central, body, 0)


def members_of(data: bytes) -> dict[str, bytes]:
    """The members of ``data`` when it is exactly the canonical archive of them; otherwise raises.

    The layout is walked as ``build`` writes it, local records first, and the members found are
    rebuilt; nothing is accepted on the strength of having been parsed. Two differences from the
    rebuild are looked for first, because each is cheap to find and fails the comparison wherever it
    is: a local record other than the one ``build`` writes for the member it holds, judged by the
    CRC-32 of the member's bytes and the header fields, and a central directory and end record other
    than the ones ``build`` writes for the local records read. Neither accepts anything; the
    comparison with the rebuild alone does.
    """
    members: dict[str, bytes] = {}
    central = bytearray()
    position = 0
    try:
        while data[position : position + 4] == _LOCAL_SIGNATURE.to_bytes(4, "little"):
            fields = _LOCAL.unpack_from(data, position)
            method, size, unpacked, name_length, extra_length = fields[3], fields[7], fields[8], fields[9], fields[10]
            start = position + _LOCAL.size + name_length + extra_length
            raw = data[position + _LOCAL.size : position + _LOCAL.size + name_length]
            name = raw.decode("ascii")
            payload = data[start : start + size]
            if len(payload) != size or name in members:
                raise CanonicalArchiveError("a local record is truncated or repeats a name")
            if method == 0:
                content = payload
            elif method == 8:
                inflater = zlib.decompressobj(-15)
                content = inflater.decompress(payload, unpacked + 1)
            else:
                raise CanonicalArchiveError(f"compression method {method} is not canonical")
            if len(content) != unpacked:
                raise CanonicalArchiveError(f"{name!r} does not hold its recorded size")
            if zlib.crc32(content) != fields[6] or data[position:start] != _local_record(raw, method, *fields[6:9]):
                raise CanonicalArchiveError(_NOT_THE_BUILD)
            members[name] = content
            central += _central_record(raw, method, fields[6], size, unpacked, position)
            position = start + size
        if not members:
            raise CanonicalArchiveError("not a canonical archive: no member record at the start")
        if data[position:] != bytes(central) + _end_record(len(members), len(central), position):
            raise CanonicalArchiveError(_NOT_THE_BUILD)
    except (struct.error, UnicodeDecodeError, zlib.error) as exc:
        raise CanonicalArchiveError(f"not a canonical archive ({type(exc).__name__})") from exc
    if build(members) != data:
        raise CanonicalArchiveError(_NOT_THE_BUILD)
    return members


# --- the corpus --------------------------------------------------------------------------------


def corpus_id(data: bytes) -> str:
    """The id of the corpus archive ``data``: derived from its bytes."""
    return ID_PREFIX + hashlib.sha256(data).hexdigest()[:16]


def manifest_bytes(files: Mapping[str, bytes], profiles: list[dict]) -> bytes:
    """The content manifest: every other member's path, size and digest, and the profiles."""
    listing = [
        {"bytes": len(content), "path": path, "sha256": hashlib.sha256(content).hexdigest()}
        for path, content in sorted(files.items(), key=lambda item: item[0].encode("utf-8"))
    ]
    document = {"files": listing, "profiles": profiles, "schema_version": MANIFEST_SCHEMA}
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def corpus_members(
    vectors: Mapping[str, bytes], protocol: Mapping[str, bytes], profiles: list[dict]
) -> dict[str, bytes]:
    """The archive's members: ``vectors`` (paths under vectors/), ``protocol`` (protocol paths of
    PROTOCOL_COPIES, placed under protocol/), and the manifest of both."""
    files: dict[str, bytes] = {}
    for path, content in vectors.items():
        if not path.startswith("vectors/"):
            raise CanonicalArchiveError(f"a vector path lies outside vectors/: {path!r}")
        files[path] = bytes(content)
    if sorted(protocol) != sorted(PROTOCOL_COPIES):
        raise CanonicalArchiveError(f"the protocol copies are exactly {list(PROTOCOL_COPIES)}")
    for path, content in protocol.items():
        files["protocol/" + path] = bytes(content)
    members = {PREFIX + path: content for path, content in files.items()}
    members[PREFIX + MANIFEST] = manifest_bytes(files, profiles)
    return members


def build_corpus(vectors: Mapping[str, bytes], protocol: Mapping[str, bytes], profiles: list[dict]) -> bytes:
    """The canonical corpus archive of these sources."""
    return build(corpus_members(vectors, protocol, profiles))


PROFILES_SOURCE = "corpus-profiles.json"


def protocol_copies(protocol_root: Path) -> dict[str, bytes]:
    """The bytes of PROTOCOL_COPIES in the loquitur-protocol checkout at ``protocol_root``."""
    return {path: (protocol_root / path).read_bytes() for path in PROTOCOL_COPIES}


def build_from_sources(source_root: Path, protocol_root: Path) -> bytes:
    """The canonical corpus archive of a corpus source checkout.

    The sources are every file under ``vectors/`` in ``source_root``, the profile list in its
    ``corpus-profiles.json``, and the protocol copies of ``protocol_root``. Nothing else in the
    checkout is read. A symbolic link or other non-regular file under ``vectors/`` is refused.
    """
    vectors: dict[str, bytes] = {}
    base = source_root / "vectors"
    for current, directories, names in os.walk(base):
        directories.sort()
        for name in directories + names:
            path = Path(current) / name
            if path.is_symlink() or not (path.is_dir() or path.is_file()):
                raise CanonicalArchiveError(f"not a regular file or directory: {path.relative_to(source_root)}")
        for name in names:
            path = Path(current) / name
            vectors[path.relative_to(source_root).as_posix()] = path.read_bytes()
    if not vectors:
        raise CanonicalArchiveError(f"no file under {base}")
    profiles = json.loads((source_root / PROFILES_SOURCE).read_text(encoding="utf-8"))["profiles"]
    return build_corpus(vectors, protocol_copies(protocol_root), profiles)
