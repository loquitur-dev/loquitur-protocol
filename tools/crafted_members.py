"""The crafted members of the conformance archive: the bytes that are not text, built from text.

    python tools/crafted_members.py [--check]

Most members of the pinned corpus archive (``conformance/``) are UTF-8 text, which the
public-boundary checker reads and searches. A few are not text on purpose, because the property
their vector pins is about bytes that are not text. This module is the one place those bytes come
from, so that each of them is cleared by provenance, by building the same bytes from what was
read, and none by a person's review of a digest:

* ``ARCHIVE_INTAKE``: the archive-intake vectors under ``vectors/inputs``, one crafted ZIP per
  reading of ``bundle-objects.md`` section 5 (and the portable member-name rule of section 2).
  Each is the members of ``vectors/bundles/link_valid_bundle`` written into an archive, plus the
  entries or bytes that break exactly one rule; ``archive_intake_clean`` is that archive with
  nothing added. ``intake_vectors`` builds all of them from the bundle's members.
* ``BINARY_ATTACHMENT``: the attachment ``blob.bin`` of ``binary_attachment_bundle``, six bytes
  that are not UTF-8, which a manifest digest covers as raw bytes.
* ``SPLICED``: the five bundle members and the one trust registry that are deliberately not
  UTF-8, each for the refusal its bundle or run exercises. Each is UTF-8 text with one short run
  of bytes that are not text put at one offset; the run and the offset are listed here, and the
  text around them is read and searched as every other member is.

``built`` gives every member of the first two kinds by its archive name, from the archive's other
members; ``spliced`` gives the text of a member of the third kind with its run taken out, or
``None`` when the member is not that text with that run. With ``--check`` this module compares
its output with the pinned archive and exits 1 on any difference.

Every vector here is written by hand rather than by ``zipfile`` because the central directory is
where the rules are read: a size, a compression ratio, a file type and an encryption flag are what
the central directory records, and several vectors record values no ordinary writer produces.
They stay small for the same reason: the member-size and total vectors declare tens of megabytes
and carry a byte. Nothing varies between runs: there is no timestamp and no comment, and a
deflated entry is written by ``zlib`` at level 9 with a raw stream.

The vectors, by name (each ``archive_intake_NAME.zip``):

* ``clean``: the control bundle with nothing added; it verifies.
* one per rule of section 5, in the order the document lists them: ``name``, ``type``,
  ``method``, ``member_size``, ``ratio``, ``duplicate``, ``count`` and ``total``. The probe entry
  breaks that rule alone; the count and total probes are preceded by entries that bring the
  archive to the bound, counting the control's own members.
* ``name_length_at_bound`` and ``name_length_past_bound``: one undeclared entry whose name is 255
  and 256 bytes long.
* ``portable_*`` and ``local_*``: each clause of the portable member-name rule at its boundary,
  admitted, and one past it, refused; a local header naming another file than its central record;
  an extra field the rule lists, and one it does not, in the central record and in the local
  header.
* ``directory_spelled_twice`` and ``implied_directory_spelled_twice``: one directory spelled two
  ways; ``name_not_utf8``: a name flagged UTF-8 that is not; ``data_not_deflate``: a deflated
  entry whose bytes are not a deflate stream; ``unicode_path_field``: an entry carrying an
  Info-ZIP Unicode Path field.
* ``data_longer_than_recorded``: ``manifest.json`` deflated with one byte more than its record
  states; ``unassigned_code_point``: a name with a code point beyond ASCII;
  ``code_page_437_control``: a name holding the byte 0x01 with bit 11 clear;
  ``short_name_shape``: a Windows short name for ``manifest.json`` before the bundle's entries.
* ``bytes_before_archive``, ``end_record_miscounts``, ``end_record_comment``,
  ``end_record_signature_in_comment`` and ``bytes_after_end_record``: the clean archive behind 16
  bytes, with an end record that counts one entry fewer, with a five-byte comment, with a second
  end record inside its comment, and followed by 16 bytes.
* ``zip64_extra_field_twice`` and ``zip64_extra_field_twice_read``: the ZIP64 extended
  information field held twice, without and with a size read from it;
  ``bytes_before_first_entry``, ``bytes_between_entries`` and
  ``bytes_before_central_directory``: bytes no entry accounts for, with every offset counting
  them; ``data_descriptor`` and ``data_descriptor_mismatch``: a data descriptor that repeats its
  entry's CRC-32 and sizes, and one that does not.
* ``marker_directory_beside_wrapper``, ``wrapper_named_like_the_marker`` and
  ``marker_directory_in_a_peer``: a directory entry ``manifest.json/`` at the top level beside the
  bundle in a wrapper, the bundle in a wrapper named ``manifest.json/``, and a peer of the wrapper
  holding a directory entry ``manifest.json/``; only a file entry marks a root, so each verifies.
* ``two_defects_entry_and_root``, ``two_defects_entry_and_stream``,
  ``two_defects_end_record_and_entry`` and ``two_defects_two_entries``: two whole-input refusals
  at once, for the precedence of section 8.4: an entry rule before a missing root, an entry rule
  before a stream that does not inflate, a trailing end record before an entry rule, and the
  first failing entry in central-directory order.
* ``count_at_bound`` and ``ratio_at_bound``: exactly 512 file entries, and one entry whose
  uncompressed size is exactly 100 times its compressed size; ``encrypted``, ``absolute_name``,
  ``name_with_colon`` and ``fifo``: an entry flagged encrypted, a name with a leading ``/``, a
  name holding ``:``, and an entry whose recorded mode says FIFO.
* ``member_size_at_bound`` and ``total_at_bound``: one undeclared member of exactly 20 MiB, and
  undeclared members that bring the archive to exactly 50 MiB, each a stream of zeros deflated to
  a ratio just under 100; ``version_needed_above_63``, ``flag_patched_data``,
  ``flag_strong_encryption`` and ``disk_number_start``: an entry recording each of the values the
  reading rules refuse.
* ``zip64_record`` and ``zip64_record_size_not_44``: the clean archive as a ZIP64 archive, its
  counts and offsets read from the ZIP64 end-of-central-directory record, and the same with that
  record stating a size other than 44 (an archive no ordinary reader refuses, so the release scan
  can still open it).
* ``root_absent``, ``two_roots`` and ``file_outside_root``: no level carrying ``manifest.json``,
  two wrappers each holding the bundle, and the bundle in a wrapper beside a file outside it.

The limits are section 5's own; the release tests of this repository read them from the
document's tables. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import stat
import struct
import sys
import zlib
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "loquitur-conformance/"
CONTROL = PREFIX + "vectors/bundles/link_valid_bundle/"
INPUTS = PREFIX + "vectors/inputs/"

MIB = 1024 * 1024
STORED, DEFLATED, BZIP2 = 0, 8, 12

# bundle-objects.md section 5, "Limits".
BOUNDS = {"count": 512, "member": 20 * MIB, "total": 50 * MIB, "ratio": 100}

# bundle-objects.md section 2, the portable member-name rule: the longest name, in bytes.
MAX_NAME_BYTES = 255

# bundle-objects.md section 5, "Rules", in the order the document lists them.
RULES = ("name", "type", "method", "member_size", "ratio", "duplicate", "count", "total")

BINARY_ATTACHMENT_NAME = PREFIX + "vectors/bundles/binary_attachment_bundle/blob.bin"
BINARY_ATTACHMENT = bytes([0xFF, 0xFE, 0x00, 0x41, 0x80, 0x90])

# Archive name: (offset, run). The member is UTF-8 text with ``run``, which is not text, put at
# ``offset``.
SPLICED = {
    PREFIX + "vectors/bundles/canonical_input_not_utf8_bundle/canonical_input.json": (27, b"\xc3("),
    PREFIX + "vectors/bundles/envelope_not_utf8_bundle/envelope_env1.json": (27, b"\xc3("),
    PREFIX + "vectors/bundles/manifest_not_utf8_bundle/manifest.json": (414, b"\xff"),
    PREFIX + "vectors/bundles/reason_manifest_sidecar_not_utf8_bundle/manifest.sha256": (0, b"\xff" * 64),
    PREFIX + "vectors/bundles/receipt_not_utf8_bundle/verification_receipt.json": (381, b"\xff"),
    PREFIX + "vectors/authorization/trust_registry_not_utf8.json": (1048, b"\xff"),
}


@dataclass(frozen=True)
class Entry:
    """One archive entry. ``file_size``/``compress_size`` override what the data gives."""

    name: str
    data: bytes = b"x"
    method: int = STORED
    flags: int = 0
    mode: int = 0
    file_size: int | None = None
    compress_size: int | None = None
    raw_name: bytes | None = None
    payload: bytes | None = None
    extra: bytes = b""
    local_name: bytes | None = None
    local_extra: bytes = b""
    before: bytes = b""
    after: bytes = b""
    version_needed: int = 20
    disk_start: int = 0
    crc: int | None = None


def _payload(entry: Entry) -> bytes:
    if entry.payload is not None:
        return entry.payload
    if entry.method == DEFLATED:
        packer = zlib.compressobj(9, zlib.DEFLATED, -15)
        return packer.compress(entry.data) + packer.flush()
    return entry.data


def zip_bytes(entries: list[Entry]) -> bytes:
    """A ZIP whose central directory records exactly what each entry says.

    An entry's ``extra`` is written into its central-directory record only, and its
    ``local_extra`` into its local header only. An entry's ``local_name``, when it has one, is the
    name its local header records instead of the central one. An entry's ``before`` is written
    directly before its local header and its ``after`` directly after its data, and every offset
    counts them.
    """
    body = bytearray()
    central = bytearray()
    for entry in entries:
        name = entry.raw_name if entry.raw_name is not None else entry.name.encode("utf-8")
        flags = entry.flags | (0x800 if entry.raw_name is None and not entry.name.isascii() else 0)
        payload = _payload(entry)
        crc = zlib.crc32(entry.data) if entry.crc is None else entry.crc
        size = len(entry.data) if entry.file_size is None else entry.file_size
        packed = len(payload) if entry.compress_size is None else entry.compress_size
        body += entry.before
        offset = len(body)
        local_name = name if entry.local_name is None else entry.local_name
        body += struct.pack(
            "<4s5H3L2H",
            b"PK\x03\x04",
            entry.version_needed,
            flags,
            entry.method,
            0,
            0x21,
            crc,
            packed,
            size,
            len(local_name),
            len(entry.local_extra),
        )
        body += local_name + entry.local_extra + payload + entry.after
        central += struct.pack(
            "<4s6H3L5H2L",
            b"PK\x01\x02",
            (3 << 8) | 20,
            entry.version_needed,
            flags,
            entry.method,
            0,
            0x21,
            crc,
            packed,
            size,
            len(name),
            len(entry.extra),
            0,
            entry.disk_start,
            0,
            entry.mode << 16,
            offset,
        )
        central += name + entry.extra
    end = struct.pack("<4s4H2LH", b"PK\x05\x06", 0, 0, len(entries), len(entries), len(central), len(body), 0)
    return bytes(body + central + end)


def control_entries(control: dict[str, bytes]) -> list[Entry]:
    """The control bundle's members (file name to bytes), in name order, deflated."""
    if not control:
        raise ValueError("the control bundle has no member")
    return [Entry(name, control[name], DEFLATED) for name in sorted(control)]


def breaking(rule: str, bounds: dict[str, int]) -> tuple[list[Entry], Entry]:
    """Entries to put before the probe, and the probe entry, which breaks ``rule`` alone."""
    ratio, member, total, count = bounds["ratio"], bounds["member"], bounds["total"], bounds["count"]
    if rule == "name":
        # A backslash is not a separator in the member-name grammar, so this is one name carrying
        # a character the grammar refuses.
        return [], replace(Entry("sub/x.bin"), raw_name=b"sub\\x.bin")
    if rule == "type":
        # A file entry whose recorded POSIX mode says symbolic link.
        return [], Entry("x.bin", mode=stat.S_IFLNK | 0o777)
    if rule == "method":
        return [], Entry("x.bin", b"x" * 64, method=BZIP2)
    if rule == "member_size":
        return [], Entry("x.bin", file_size=member + 1, compress_size=member + 1)
    if rule == "ratio":
        return [], Entry("x.bin", file_size=ratio * 10 + 1, compress_size=10)
    if rule == "duplicate":
        return [Entry("dup.bin")], Entry("DUP.BIN")
    if rule == "count":
        return [Entry(f"f{i}.txt") for i in range(count)], Entry("x.bin")
    if rule == "total":
        # Up to 5 bytes below the total bound, in entries within the per-member bound, so the
        # probe is what carries the sum past it.
        fill, sizes = total - 5, []
        while fill:
            sizes.append(min(fill, member))
            fill -= sizes[-1]
        before = [Entry(f"big{i}.bin", file_size=s, compress_size=s) for i, s in enumerate(sizes)]
        return before, Entry("x.bin", file_size=6, compress_size=6)
    raise ValueError(f"no probe for the rule {rule!r}")


def _descriptor(entry: Entry, *, crc_delta: int = 0) -> bytes:
    """The data descriptor of ``entry``, with its signature: its CRC-32 (moved by ``crc_delta``) and
    its two sizes as 4-byte values, as the central-directory record states them."""
    packed = len(_payload(entry))
    return b"PK\x07\x08" + struct.pack("<3L", zlib.crc32(entry.data) ^ crc_delta, packed, len(entry.data))


def _ratio_at_bound(ratio: int) -> Entry:
    """An entry of zeros whose uncompressed size is exactly ``ratio`` times its compressed size: a
    deflate stream lengthened by empty stored blocks, five bytes each, to the size that holds it."""
    for packed in range(64, 4096):
        data = bytes(packed * ratio)
        packer = zlib.compressobj(9, zlib.DEFLATED, -15)
        head = packer.compress(data) + packer.flush(zlib.Z_SYNC_FLUSH)
        end = b"\x03\x00"  # an empty final block with fixed codes
        pad = packed - len(head) - len(end)
        if pad >= 0 and pad % 5 == 0:
            payload = head + b"\x00\x00\x00\xff\xff" * (pad // 5) + end
            if len(payload) == packed and zlib.decompress(payload, -15) == data:
                return Entry("z.bin", data, DEFLATED, payload=payload)
    raise ValueError("no stream holds the ratio")


def _zeros_at_ratio(name: str, size: int, ratio: int) -> Entry:
    """An entry of ``size`` zeros whose compressed size is the least that keeps its ratio at most
    ``ratio``: a deflate stream lengthened by empty stored blocks, five bytes each."""
    packer = zlib.compressobj(9, zlib.DEFLATED, -15)
    head = packer.compress(bytes(size)) + packer.flush(zlib.Z_SYNC_FLUSH)
    end = b"\x03\x00"  # an empty final block with fixed codes
    packed = -(-size // ratio)
    while (packed - len(head) - len(end)) % 5:
        packed += 1
    payload = head + b"\x00\x00\x00\xff\xff" * ((packed - len(head) - len(end)) // 5) + end
    if len(payload) != packed or size > ratio * packed:
        raise ValueError("no stream holds the ratio")
    return Entry(name, b"", DEFLATED, file_size=size, payload=payload, crc=zlib.crc32(bytes(size)))


def zip64(archive: bytes, *, record_size: int = 44) -> bytes:
    """``archive`` rewritten as a ZIP64 archive: a ZIP64 end-of-central-directory record and its
    locator before the end record, whose counts and central-directory size and offset then hold
    their ZIP64 markers. ``record_size`` is the size the ZIP64 record states for itself."""
    end = archive.rindex(b"PK\x05\x06")
    _, _, _, count, total, size, offset, _ = struct.unpack("<4s4H2LH", archive[end : end + 22])
    record = struct.pack("<4sQ2H2L4Q", b"PK\x06\x06", record_size, (3 << 8) | 45, 45, 0, 0, count, total, size, offset)
    locator = struct.pack("<4sLQL", b"PK\x06\x07", 0, end, 1)
    marked = struct.pack("<4s4H2LH", b"PK\x05\x06", 0, 0, 0xFFFF, 0xFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0)
    return archive[:end] + record + locator + marked


def late_vectors(base: list[Entry]) -> dict[str, list[Entry]]:
    """The entries of the ZIP64-field and unaccounted-bytes vectors, by file name."""
    twice = struct.pack("<HHQ", 0x0001, 8, 1) + struct.pack("<HHQ", 0x0001, 8, 2)
    first, second, last = base[0], base[1], base[-1]
    return {
        "archive_intake_zip64_extra_field_twice.zip": base + [Entry("z.bin", extra=twice)],
        "archive_intake_zip64_extra_field_twice_read.zip": base + [Entry("z.bin", file_size=0xFFFFFFFF, extra=twice)],
        "archive_intake_bytes_before_first_entry.zip": [replace(first, before=b"MZ" + bytes(62)), *base[1:]],
        "archive_intake_bytes_between_entries.zip": [first, replace(second, before=bytes(16)), *base[2:]],
        "archive_intake_bytes_before_central_directory.zip": [*base[:-1], replace(last, after=bytes(16))],
        "archive_intake_data_descriptor.zip": [replace(first, after=_descriptor(first)), *base[1:]],
        "archive_intake_data_descriptor_mismatch.zip": [
            replace(first, after=_descriptor(first, crc_delta=1)),
            *base[1:],
        ],
    }


def intake_vectors(control: dict[str, bytes]) -> dict[str, bytes]:
    """Every archive-intake vector, by file name, from the control bundle's members."""
    base = control_entries(control)
    # The control's own members count towards the file-entry and total bounds: leave room for
    # them, or the count and total vectors would be refused on an entry that is not the probe.
    used = sum(len(entry.data) for entry in base)
    bounds = {**BOUNDS, "count": BOUNDS["count"] - len(base), "total": BOUNDS["total"] - used}
    out: dict[str, bytes] = {}

    def put(label: str, entries: list[Entry]) -> None:
        out[f"archive_intake_{label}.zip"] = zip_bytes(entries)

    put("clean", base)
    for rule in RULES:
        before, probe = breaking(rule, bounds)
        put(rule, base + before + [probe])
    put("name_length_at_bound", base + [Entry("s" * (MAX_NAME_BYTES - len(".json")) + ".json")])
    put("name_length_past_bound", base + [Entry("s" * (MAX_NAME_BYTES + 1 - len(".json")) + ".json")])
    stream = Entry("y.bin", b"abc" * 100, DEFLATED)
    readings = {
        "directory_spelled_twice": [Entry("DATA/", b""), Entry("data/y.json")],
        "implied_directory_spelled_twice": [Entry("Sub/a.json"), Entry("sub/b.json")],
        "name_not_utf8": [Entry("x.bin", raw_name=b"\xed\xa0\x80x.bin", flags=0x800)],
        "data_not_deflate": [replace(stream, payload=b"\xff" * len(_payload(stream)))],
        "unicode_path_field": [Entry("u.bin", extra=struct.pack("<HH", 0x7075, 2) + b"\x01\x00")],
    }
    for label, added in readings.items():
        put(label, base + added)
    (manifest,) = [entry for entry in base if entry.name == "manifest.json"]
    longer = replace(
        manifest, method=DEFLATED, payload=_payload(replace(manifest, data=manifest.data + b" ", method=DEFLATED))
    )
    put("data_longer_than_recorded", [longer if entry is manifest else entry for entry in base])
    put("unassigned_code_point", base + [Entry("x\U0001e4d0.json")])
    clean = out["archive_intake_clean.zip"]
    out["archive_intake_bytes_before_archive.zip"] = bytes(16) + clean
    end = clean.rindex(b"PK\x05\x06")
    fields = list(struct.unpack("<4s4H2LH", clean[end : end + 22]))
    fields[3] -= 1
    fields[4] -= 1
    out["archive_intake_end_record_miscounts.zip"] = clean[:end] + struct.pack("<4s4H2LH", *fields) + clean[end + 22 :]
    record = clean[end : end + 20]
    commented = {
        "end_record_comment": b"notes",
        "end_record_signature_in_comment": record + struct.pack("<H", 7),
    }
    for label, comment in commented.items():
        out[f"archive_intake_{label}.zip"] = clean[: end + 20] + struct.pack("<H", len(comment)) + comment
    out["archive_intake_bytes_after_end_record.zip"] = clean + bytes(16)
    put("code_page_437_control", base + [Entry("x.json", raw_name=b"x\x01.json")])
    put("short_name_shape", [Entry("MANIFE~1.JSO", b"{}")] + base)
    # The portable member-name rule of section 2, one clause at a time: at its boundary, admitted,
    # and one past it, refused. An extended-timestamp field holds a flag byte and one time.
    timestamp = struct.pack("<HHBL", 0x5455, 5, 1, 0)
    unicode_path = struct.pack("<HHBL", 0x7075, 5 + len(b"v.json"), 1, zlib.crc32(b"u.json")) + b"v.json"
    portable = {
        "portable_every_character": [Entry("AZaz09._-.json")],
        "portable_character_past_set": [Entry("a+.json")],
        "portable_dots_inside": [Entry("sub/..x.json")],
        "portable_dot_segment": [Entry("sub/./x.json")],
        "portable_hyphen_inside": [Entry("x-y.json")],
        "portable_leading_hyphen": [Entry("-x.json")],
        "portable_leading_dot": [Entry(".x.json")],
        "portable_trailing_dot": [Entry("x.json.")],
        "portable_device_name_near": [Entry("COM0.json")],
        "portable_device_name": [Entry("com1.json")],
        "portable_names_distinct": [Entry("d.json"), Entry("D/y.json")],
        "portable_file_named_like_a_directory": [Entry("d"), Entry("D/y.json")],
        "portable_extra_field_listed": [Entry("t.bin", extra=timestamp)],
        "portable_extra_field_unlisted": [Entry("t.bin", extra=struct.pack("<HH", 0x6375, 1) + b"\x01")],
        "local_name_differs": [Entry("y.json", local_name=b"z.json")],
        "local_extra_field_listed": [Entry("t.bin", local_extra=timestamp)],
        "local_extra_field_unlisted": [Entry("u.json", local_extra=unicode_path)],
    }
    for label, added in portable.items():
        put(label, base + added)
    # Section 1: a level carries manifest.json only through a file entry of that name.
    wrapped = [replace(entry, name="w/" + entry.name) for entry in base]
    put("marker_directory_beside_wrapper", [Entry("manifest.json/", b""), *wrapped])
    put("wrapper_named_like_the_marker", [replace(entry, name="manifest.json/" + entry.name) for entry in base])
    put("marker_directory_in_a_peer", [*wrapped, Entry("x/manifest.json/", b"")])
    # Section 8.4: the precedence of whole-input refusals, two defects at a time.
    _, link = breaking("type", bounds)
    _, method = breaking("method", bounds)
    _, name = breaking("name", bounds)
    put("two_defects_entry_and_root", [entry for entry in base if entry.name != "manifest.json"] + [link])
    put("two_defects_entry_and_stream", [replace(stream, payload=b"\xff" * len(_payload(stream))), *base, name])
    put("two_defects_two_entries", [*base, method, name])
    out["archive_intake_two_defects_end_record_and_entry.zip"] = zip_bytes(base + [link]) + bytes(16)
    # Section 5 at its bounds, and the entry kinds the rules name.
    put("count_at_bound", base + [Entry(f"f{i}.txt") for i in range(BOUNDS["count"] - len(base))])
    put("ratio_at_bound", base + [_ratio_at_bound(BOUNDS["ratio"])])
    put("encrypted", base + [Entry("x.bin", flags=0x1)])
    put("absolute_name", base + [Entry("/x.json")])
    put("name_with_colon", base + [Entry("x:y.json")])
    put("fifo", base + [Entry("x.bin", mode=stat.S_IFIFO | 0o644)])
    put("member_size_at_bound", base + [_zeros_at_ratio("z.bin", BOUNDS["member"], BOUNDS["ratio"])])
    fill, sizes = BOUNDS["total"] - used, []
    while fill:
        sizes.append(min(fill, BOUNDS["member"]))
        fill -= sizes[-1]
    put("total_at_bound", base + [_zeros_at_ratio(f"z{i}.bin", s, BOUNDS["ratio"]) for i, s in enumerate(sizes)])
    put("version_needed_above_63", base + [Entry("x.bin", version_needed=64)])
    put("flag_patched_data", base + [Entry("x.bin", flags=0x20)])
    put("flag_strong_encryption", base + [Entry("x.bin", flags=0x40)])
    put("disk_number_start", base + [Entry("x.bin", disk_start=1)])
    out["archive_intake_zip64_record.zip"] = zip64(clean)
    out["archive_intake_zip64_record_size_not_44.zip"] = zip64(clean, record_size=45)
    # Section 1: exactly one level carries manifest.json.
    put("root_absent", [entry for entry in base if entry.name != "manifest.json"])
    put(
        "two_roots",
        [replace(entry, name="a/" + entry.name) for entry in base]
        + [replace(entry, name="b/" + entry.name) for entry in base],
    )
    put("file_outside_root", [*wrapped, Entry("outside.txt", b"outside the bundle\n")])
    for name, entries in late_vectors(base).items():
        out[name] = zip_bytes(entries)
    return out


def built(members: dict[str, bytes]) -> dict[str, bytes]:
    """The crafted members built from ``members`` (archive name to bytes), by archive name.

    The archive-intake vectors are built from the members directly under the control bundle;
    without them there are none."""
    control = {
        name[len(CONTROL) :]: data
        for name, data in members.items()
        if name.startswith(CONTROL) and "/" not in name[len(CONTROL) :]
    }
    out = {INPUTS + name: data for name, data in intake_vectors(control).items()} if control else {}
    out[BINARY_ATTACHMENT_NAME] = BINARY_ATTACHMENT
    return out


def spliced(name: str, data: bytes) -> bytes | None:
    """``data`` with the run ``SPLICED`` lists for ``name`` taken out, when ``data`` holds that run at
    that offset; otherwise ``None``. What is returned is to be read as any member is."""
    if name not in SPLICED:
        return None
    offset, run = SPLICED[name]
    if data[offset : offset + len(run)] != run:
        return None
    return data[:offset] + data[offset + len(run) :]


def _pinned_members(root: Path) -> dict[str, bytes]:
    lock = json.loads((root / "CONFORMANCE_LOCK.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("corpus_archive", root / "tools/corpus_archive.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.members_of((root / lock["artifact"]).read_bytes())


def differences(members: dict[str, bytes]) -> list[str]:
    """How the crafted members of ``members`` differ from what this module gives."""
    found = []
    for name, data in sorted(built(members).items()):
        if name not in members:
            found.append(f"absent: {name}")
        elif members[name] != data:
            found.append(f"differs: {name} (sha256 {hashlib.sha256(members[name]).hexdigest()})")
    for name in sorted(SPLICED):
        if name not in members:
            found.append(f"absent: {name}")
        elif spliced(name, members[name]) is None:
            found.append(f"does not hold its run: {name}")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="compare with the pinned archive")
    args = parser.parse_args(argv)
    members = _pinned_members(args.root.resolve())
    found = differences(members)
    for line in found:
        print(line)
    if found:
        return 1
    print(f"crafted members OK: {len(built(members))} built, {len(SPLICED)} spliced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
