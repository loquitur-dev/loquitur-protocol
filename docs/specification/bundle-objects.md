# Bundle objects and their closed field contracts

Status: normative.

[`verification-checks.md`](verification-checks.md) defines the `structure` check as "the files the
manifest names are present, each object parses, and each satisfies the closed field contract for its
kind", and states that "a member the contract does not name is a rejection, not an extension point".
It also notes that `manifest.json`, `p1.json` and `envelope_env1.json` are not among the seven
canonical object families and therefore have no published JSON Schema.

This document is where those three field sets are defined. A verifier that held a field set
more permissive than another verifier's would diverge on exactly the axis `structure` is about, and
divergence in that direction means accepting evidence that should be refused.

The digest constructions for these objects are in
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §3 and are not restated here.

**A rejection.** "A rejection" of a member or of a value, here and in
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md), is a break of the contract of
the layer that reads it, and it never passes. What the run then reports is the row of
[`report-contract.md`](report-contract.md) §5.3 whose condition the break meets, such as
`p1_verification_failed`, or, where no row's condition names it, a `false` result of the layer's
checks (§6).

**The whitespace set W.** Where this specification asks for a string that is not empty, it
means a string with at least one code point outside the set W:

| W |
| --- |
| U+0009 to U+000D |
| U+001C to U+001F |
| U+0020 |
| U+0085 |
| U+00A0 |
| U+1680 |
| U+2000 to U+200A |
| U+2028 |
| U+2029 |
| U+202F |
| U+205F |
| U+3000 |
| U+FEFF |

W decides whether a value is empty, and nothing else: a verifier never removes a code point of
W from a value it compares, and a value that has one is compared with it. U+200B and U+180E are
not in W.

**Free strings.** Every member a document's contract types as a string and holds to no other
form (no pattern, enumeration, constant, digest or signature form) is a free string, except the
envelope's `bundle_id`, which is a link and is judged by its link (§4). A free string is not
empty: a value made only of code points in W breaks the document's contract,
whether or not a schema's `minLength` admits it. Each document below, and each contract of
[`registry-link.md`](registry-link.md) and
[`trust-registry-authorization.md`](trust-registry-authorization.md), names its free strings.

## 1. Bundle members

A bundle is a directory, or a ZIP archive containing one.

**Members, and what is present.** A member of a bundle is a regular file under its root, or a file
entry of an archive (§5); a directory, a device, a pipe or a socket is never a member. A
structural name below is **present** when a regular member with exactly that name exists at the
root. A directory carrying a structural name is not that member, and the name is absent: the
files under such a directory are members under their own paths and are judged by completeness
like any other. A link carrying a structural name refuses the run (`unsafe_bundle_member`, below)
and makes no name present. A member is the content of a regular file, its default data stream: an
alternate data stream, an extended attribute, a resource fork and other metadata a host keeps
beside a file are not members and are not part of the bundle, and a verifier neither verifies nor
reports them.

**The bundle root.** A directory given to a verifier is itself the bundle root: its listing holds an
entry named exactly `manifest.json` at its top level, or it is not a bundle, and a verifier does
not search inside it for one. The entry marks the root whatever it is. When it is a directory, the
bundle's manifest is absent ("Members, and what is present" above) and the run reports
`manifest_verification_failed`; when it is a link, the run reports `unsafe_bundle_member` and
`manifest_verification_failed` ("Names, then links" below). "Exactly" is decided in the directory's
own listing, code unit for code unit: a host that ignores letter case opens `MANIFEST.JSON` under
the name `manifest.json`, and a directory holding it is still not a bundle. A level of a ZIP archive
carries `manifest.json` only through a file entry of that name, a member (§5); a directory entry
named `manifest.json/` never marks a root, whatever it holds. A ZIP archive whose top level carries
`manifest.json` is the bundle root; otherwise the one top-level directory that carries it is, and an
archive with none or with more than one is not a bundle. A file of the archive outside the selected
root was delivered beside the bundle and is committed to by nothing: a verifier **MUST** report it,
and the run yields `OFFLINE_REVIEW`, as for an undeclared member.

These member names are structural and are verified by their own layer rather than by
`manifest.files`:

```text
manifest.json              the declaration
manifest.sha256            its digest sidecar
envelope_env1.json         the envelope
envelope.sha256            the envelope digest sidecar
verification_receipt.json  present when the bundle carries a receipt
```

Every other file present in the bundle **MUST** be declared in `manifest.files` (the canonical
input, `p1.json` and the `p1.sha256` sidecar included). Only the five names above are exempt, and
each is exempt because another layer verifies it: the manifest and its sidecar cannot appear in the
manifest's own map (§2), the envelope is checked against its own digest, and a present receipt is
validated against its closed schema in every run and against the registry entry by the `link` check.
This version defines no other name for any of them: `envelope.json`, in particular, is an ordinary
member name.

**Reserved names.** These names are reserved for a later version of the bundle: every member
under the directory `attestations/`, the member `document_index.json` and the member
`claims_openings.json`. This version defines no evidence under them. A bundle that carries a
member at a reserved name, declared in `manifest.files` or not, is not refused for it and does
not pass silently: a verifier **MUST** report it, and the run yields `OFFLINE_REVIEW` with the
review reason `bundle_reserved_member` ([`report-contract.md`](report-contract.md) §3). A declared
member at a reserved name is still compared with its digest by the manifest's file check, and an
undeclared one is not also reported as an undeclared member.

An undeclared member is not a silent pass: a verifier **MUST** report it, and the run yields
`OFFLINE_REVIEW` rather than `OFFLINE_OK`. A bundle whose members were all byte-identical
except for one added file would otherwise satisfy every recorded digest while carrying
material nothing committed to.

Completeness needs an inventory. A verifier that reads the bundle through an interface that
cannot list its members cannot show that none is undeclared, and the run yields at least
`OFFLINE_REVIEW`. An empty directory is not a member.

**Names, then links.** A directory bundle is enumerated, without following anything, before any
member is read. Each directory's listing is judged by its names alone before any entry in it is
inspected: an entry whose path from the root is not a portable member name (§2), or two entries of
one listing whose names conflict (§2), refuse the run (`OFFLINE_FAIL`,
`bundle_member_name_invalid`). Such an entry is never opened, inspected or resolved, and it is not
reported as an undeclared member: no manifest can declare it, and whether it is a file, a directory
or a link is what a verifier could learn only by handing its name to the host. A symbolic link, a
junction or any other reparse point anywhere under the root refuses the run (`OFFLINE_FAIL`,
`unsafe_bundle_member`).

An inventory that fails takes the place of a link, and of nothing else. A host that fails to list
the directory given as the input, which a verifier lists first to find its `manifest.json` ("The
bundle root" above), fails an operation on the input itself: the run reports `filesystem_error` and
the input is refused as a whole ([`report-contract.md`](report-contract.md) §5.3). When the host
fails a listing of the inventory below the root, or the inspection of an entry of a listing, the
run reports `bundle_inventory_failed`, a host failure; when any listing is refused by its names, it
reports `bundle_member_name_invalid`; in neither case does it report `unsafe_bundle_member`, even
for a link the verifier met before the failed or refused listing: which entries a verifier meets
before it reaches that listing depends on the order in which it lists directories, which this
specification does not fix, and a report **MUST NOT** depend on that order. A link is judged only
over an inventory that is complete. Every other row of [`report-contract.md`](report-contract.md)
§5.3 is judged on its own, as that section requires, so a bundle holding the entry `a b.json` and a
`manifest.json` that is not JSON reports `bundle_member_name_invalid` and
`manifest_verification_failed`, with or without a link.

The root is the path the verifier is given, not a member name: the portable member-name rule does
not apply to it, and it may be reached through a link. A verifier reads the root and its members
through that path, as given, and never hands the host a path the host resolved; a resolved path
serves only to compare one path with another. Every read re-checks each component of its path below
the root and refuses a link it meets.

A sidecar file holds exactly the 64 lowercase hexadecimal characters of the digest and no
other byte, not even a newline.

## 2. `manifest.json`

**Permitted members, the complete set:**

| member | type | required |
| --- | --- | --- |
| `bundle_id` | string with a code point outside W | yes |
| `files` | object | yes |
| `nonce` | string of exactly 64 lowercase hexadecimal characters | yes |
| `schema_version` | string, exactly `loquitur.bundle.v1` | yes |

A member outside this set is a rejection.

**The bundle version.** `schema_version` is the version identifier of the bundle, and this
version of the protocol defines exactly `loquitur.bundle.v1`. It fixes the manifest, P1, the
envelope and the sidecar form described in this document. A verifier reads it before the
manifest's contract under the version gate of [`document-contracts.md`](document-contracts.md): a
well-formed identifier of another version, such as `loquitur.bundle.v2`, is an unsupported version
(exit `4`), and any other value, such as `bundle-v1`, is a rejection of the manifest.

**The nonce.** `nonce` is exactly 64 lowercase hexadecimal characters, matching
`^[0-9a-f]{64}$`, and any other value is a rejection of the manifest. A producer **MUST** fill it
with 32 bytes from a cryptographically secure random generator, fresh for every bundle, and
**MUST NOT** reuse or publish it. Its purpose is hiding, stated in
[`public-private-boundary.md`](public-private-boundary.md): the manifest digest, and through the
receipt the receipt digest, are public, and without a secret random member a bundle of low entropy
whose `bundle_id` is known could be found by trying its possible contents. A verifier checks its
form only; it cannot check that it is random.

A `bundle_id` that is not a string, or that is made only of code points in W, is a rejection in
its own right; it is the manifest's free string. `bundle_id` is called
out because it is not caught by a presence check: a manifest that does not name its bundle
lets the envelope's `bundle_id` comparison fall back to whatever the extraction directory
happened to be called, which is a name the evidence does not control.

**The `files` map.** Keys are bundle-relative member names; values are digests of the
member's raw bytes in the self-describing form `sha256:<64 lowercase hex>`
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §2).

- A `files` map with no member makes the manifest's file check `false`: a manifest that
  declares nothing commits to nothing, and the run fails its manifest layer. This is a rule of
  its own, and not a consequence of §1: it holds whatever the bundle carries, including a
  bundle that carries only the six structural names. Such a manifest is not malformed (its shape is
  a valid one), and it does not hold vacuously either.
- An undeclared member does not make the file check `false`; it yields `OFFLINE_REVIEW` under
  §1, whatever the size of the map. The two rules answer different questions: the file check
  reads the declaration and asks whether every file it names is present with the bytes it
  names, and completeness reads the bundle and asks whether every file it carries is declared.
  A manifest that declares two of three members has a file check that holds and a run that is
  `OFFLINE_REVIEW`.
- A value that is not a digest of the form `sha256:<64 lowercase hex>` makes the **manifest
  malformed**. It is not an absent file and it is not a value to be normalized: in particular a
  bare 64-hex value, an uppercase digest and a value under another label are each a rejection
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §2). A declaration a parser
  cannot read **MUST NOT** be skipped: dropping it means the file it named is never hashed, never
  appears in the per-file results and produces no note, so one readable entry launders any number of
  unchecked ones.
- `manifest.json` and `manifest.sha256` **MUST NOT** appear as keys. The map cannot contain
  its own digest, and the sidecar is not a member of the map. A key is one of those two when,
  with each of the letters `A` to `Z` read as its lower-case letter and otherwise as written, it
  equals one of them ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7):
  `MANIFEST.JSON` is, while `./manifest.json`, and `manifest.json` preceded by a space, are not
  portable member names (below). A key that is one of those two breaks the closed contract and fails
  the manifest layer, and it is not compared as a declared member: the file check compares the other
  keys, so `manifest_files` and `manifest_sha256` report what their own comparisons give, `true`
  when nothing else is wrong. Both are informative ([`report-contract.md`](report-contract.md) §2).
- Every key **MUST** be a portable member name, and no two keys may conflict (both below). A key
  that is not a portable member name, and each of two keys that conflict, fails the manifest's file
  check, and the member it names is not read. Nothing is rewritten first.
- A declared name names the file whose path segments equal its segments exactly, byte for byte,
  entry by entry from the bundle root. A letter-case variant or any other alias a host filesystem
  would resolve is not that member, and the declared member is absent.

**Portable member names.** One rule decides every member name: a key of the `files` map, the path
from the root of an entry of a directory bundle (§1), and the name of an archive entry (§5). A
member name is a sequence of segments separated by `/`, and:

1. every segment is non-empty and holds only characters of the POSIX portable filename character
   set: `A` to `Z`, `a` to `z`, `0` to `9`, `.`, `_` and `-`;
2. no segment is `.` or `..`, ends with `.`, or begins with `-`;
3. no segment is, with ASCII letter case ignored, a Windows reserved device name (`CON`, `PRN`,
   `AUX`, `NUL`, `COM1` to `COM9`, `LPT1` to `LPT9`), alone or followed by `.` and an extension:
   the part of the segment before its first `.` is not one of them;
4. the whole name is at most 255 bytes.

A name implies every directory that is a proper prefix of it ending before a `/`: `a/b/c` implies
`a` and `a/b`. Two member names **conflict** when, with each of the letters `A` to `Z` read as its
lower-case letter and nothing else changed, they are equal; or one names a file and is equal to a
directory the other implies; or a directory one names or implies is equal to a directory the other
names or implies and the two are spelled differently. A directory is named only by a directory entry
of an archive (§5). Conflicting names are refused wherever they meet: two keys of one `files` map,
two entries of one listing of a directory bundle (§1) and two entries of one archive (§5, rule
`duplicate`).

The rule closes, as one family, every way a host reads, folds, extracts or opens a member name as
another name, and it does so before anything is read, on every host. Outside the set lie letter case
and Unicode normalization beyond ASCII, which hosts and Unicode versions fold differently; the bytes
whose characters depend on the encoding a reader assumes; the separators, stream names and
characters that Windows refuses or reads specially (`\`, `:`, `<`, `>`, `"`, `|`, `?`, `*`); control
characters; the space; `~`, with which Windows writes the short name it generates for a long one,
such as `MANIFE~1.JSO`; and code points some hosts cannot be handed at all. A trailing `.` is
dropped by the Win32 path layer, a device name names a device in every directory on Windows, and a
leading `-` is read as an option by command-line tools. ASCII letter case is the only folding left,
and the conflict rule refuses it. 255 bytes is the most one segment holds on the common file
systems, so a name within the bound fits wherever it is extracted by a host that is not limited to a
whole path of 260 characters (`MAX_PATH`, the Win32 path layer's limit), as a verifier writing in
the file namespace is not ([`report-contract.md`](report-contract.md) §5.3). A bundle whose verdict
depended on the host that verifies it would be verified differently by two readers of the same
bytes.

| member name | a portable member name |
| --- | --- |
| `"data/input.json"` | yes |
| `".hidden"` | yes |
| `"a-b_c.d.json"` | yes |
| `"console.json"` | yes |
| `"Z9/x-"` | yes |
| `" leading-space.json"` | no |
| `"a b.json"` | no |
| `"./p1.json"` | no |
| `"sub\\p1.json"` | no |
| `"p1.json:hidden"` | no |
| `"a<b.json"` | no |
| `"a~1.json"` | no |
| `"caf\u00E9.json"` | no |
| `"x\uFDD0.json"` | no |
| `"x\u0001.json"` | no |
| `"-flag.json"` | no |
| `"p1.json."` | no |
| `"nul.txt"` | no |
| `"Com1"` | no |
| `"CON.tar.gz"` | no |
| `"a//b"` | no |
| `"a/"` | no |
| `"../outside.txt"` | no |
| `"/etc/passwd"` | no |

The member names in that table are written as JSON strings. `Data/x.json` and `data/y.json`
conflict, and so do `a.json` and `A.JSON`, and `a` and `A/b`.

## 3. `p1.json`

`p1` is the name of the file; it carries the four members `s`, `v`, `ih` and `ik`. The documents use
"P1" for the object and for the layer that reads it (§6), and the name expands to nothing else.

**Permitted members, the complete set:**

| member | type | required | value |
| --- | --- | --- | --- |
| `s` | string | yes | exactly `p1` |
| `v` | integer | yes | `1` is the only supported version |
| `ih` | string | yes | the input hash of [`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §3 |
| `ik` | array of strings | no | the input-key projection: distinct member names, each with a code point outside W |

`ih` is a digest of the form `sha256:<64 lowercase hex>`. Any other value breaks the P1
contract, and the P1 layer is refused ([`report-contract.md`](report-contract.md) §5.3,
`p1_verification_failed`), rather than leaving the input-hash check to fail against a value that is
not a digest: an uppercase, bare or otherwise labeled `ih` is a malformed P1, as such a value in the
`files` map of §2 is a malformed manifest. A well-formed `ih` that is not the digest of the
projection is the other case: the check was performed and did not hold.

A member outside this set is a rejection. So is a missing or unsupported `v`: a bundle
whose P1 lacked a version and carried a smuggled member is self-consistent (the digest is computed
over whatever P1 contains) and would otherwise verify. Digest self-consistency is not protocol
conformance.

**`v` under the canonical numeric model.** JSON `1.0` and `1` are the same value under
RFC 8785, which serializes both as `1`, so a verifier **MUST** accept both spellings
identically. A verifier that rejected the float form while another accepted it would make one
bundle `OFFLINE_FAIL` in one verifier and `OFFLINE_OK` in the other with every digest
matching. A JSON boolean is **not** an integer here.

**`ik`, when present, MUST be a non-empty array of distinct strings, each with a code point outside W.**
`ik: []` is refused rather than assigned a meaning. It is vacuously a list of strings, so one
reading computes `JCS({})` and commits to a projection of nothing while another reads it as "no
projection" and hashes the whole canonical input. The two expected `ih` values are mutually
exclusive, so a bundle carrying `ik: []` verifies in exactly one implementation. The keys are the
projection's free strings: a key made only of code points in W names no member of the canonical
input, and is refused in the same way. An array that lists one key twice is refused as well
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §3).

**Size.** The canonical form of `p1.json` is subject to a maximum-size guard. The bound is
1024 bytes of canonical form; a verifier **MUST** fail closed when it is exceeded.

**`p1.json` and `p1.sha256` are both required.** A bundle without `p1.json` refuses the P1 layer
(`p1_verification_failed`). A bundle without `p1.sha256` fails the P1 layer whether or not its
manifest declares it: no digest of P1 is committed, so the P1 digest check does not hold
(`p1_sha256` `false`, [`report-contract.md`](report-contract.md) §5.2 row "failed its P1 layer"); a
manifest that declares the absent sidecar also fails its file check. Neither absence is an open
question.

## 4. `envelope_env1.json`

This envelope is the bundle envelope. It is not the registry-entry signing envelope of
[`signing-envelope-v2.md`](signing-envelope-v2.md) nor the trust-root signing envelope of
[`trust-root.md`](trust-root.md) §4, which are the objects a signature covers
([`introduction.md`](introduction.md) §5).

**Permitted members, the complete set, with the type and the requirement of each:**

| group | member | type | required |
| --- | --- | --- | --- |
| identity and links | `s` | string | yes |
| identity and links | `v` | integer | yes |
| identity and links | `bundle_id` | string | yes |
| identity and links | `bundle_manifest_sha256` | string | yes |
| identity and links | `p1_sha256` | string | yes |
| identity and links | `registry_entry` | object or null | no |
| anchor and provenance metadata | `ts` | integer or null | no |
| anchor and provenance metadata | `network` | string or null | no |
| anchor and provenance metadata | `p1_txid` | string or null | no |
| anchor and provenance metadata | `uri` | string or null | no |
| subject identifiers | `asset_id` | string or null | no |
| subject identifiers | `asset_type` | string or null | no |
| subject identifiers | `receipt_id` | string or null | no |

A member outside this set is a rejection, and a member whose value is not of its declared type is a
rejection in the same way. The three links are the exception to the second rule: a present
`bundle_id`, `bundle_manifest_sha256` or `p1_sha256` of another type, like one of another value,
fails its link (`envelope_links` `false`) and does not break the closed contract, as the links below
state. The table carries the set and the types together, as §2 and §3 do for the manifest and for
P1, so that one reading answers both questions and the two answers cannot drift apart. The six
members typed `string or null` are the envelope's free strings: when one is a string, it has a code
point outside W, and a value made only of W is a rejection in the same way as a value of another
type. `bundle_id`, a link, is not a free string.

The three links are what an envelope *is*. An envelope omitting two of them binds no digest at
all, and a verifier that reads that silence as "no link failed" returns `PASS` over an unbound
envelope.

`s` MUST be exactly `env1`. It says which object this is, and an envelope that does not say so
is not an env1 envelope: reading its absence as "the only envelope there is" accepts a document
this contract never described. `v` supports only `1`, and follows the same canonical numeric
model as `p1.v` in §3.

`ts` is a time in whole seconds, and `registry_entry`, when it is not `null`, is a registry
entry: an object that satisfies the entry's contract ([`registry-link.md`](registry-link.md) §2). No
check reads these members, and that is why their types are written down: a contract that leaves a
member untyped leaves two verifiers to disagree about the same bytes, and an undeclared type is the
same silence as an undeclared member. An absent optional member and a `null` one are the same.

**The envelope is authenticated by nothing.** It is a structural member, outside `manifest.files`
(§1), and nothing the issuer signs commits to it: the registry entry commits to the manifest and
the receipt, the manifest to the members it declares, and the envelope's links point outward, to the
manifest and to P1, never back. Its sidecar `envelope.sha256` is an unkeyed digest inside the
bundle, which whoever rewrites the bundle recomputes. The members other than the three links,
`ts`, `network`, `p1_txid`, `uri`, `asset_id`, `asset_type`, `receipt_id` and `registry_entry`, hold
whatever the last party to write the bundle chose, and a run whose envelope checks hold says nothing
about them. They are not compared with the receipt or with the registry entry, and an embedded
`registry_entry` is neither signature-checked nor compared with a supplied one. A relying party
MUST NOT treat a member of the envelope other than its three links as authorized by the issuer, and
a consumer that shows one SHOULD show it as unauthenticated. Binding the envelope into what the
issuer signs, or removing those members, is not part of this version: either changes the envelope
or the entry contract.

**The links MUST match** the digests the bundle commits to. A link holds only when the
object it names parsed, satisfied its closed contract and matched its sidecar; a link to a
manifest or P1 that failed any of these is `false`.

Each link is compared exactly. `bundle_manifest_sha256` and `p1_sha256` are digests of the form
`sha256:<64 lowercase hex>` ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md)
§2), and any other value fails its link. The envelope's `bundle_id` is a string, and its link holds
only when it equals the manifest's `bundle_id` code unit for code unit: nothing is trimmed or
case-folded, and a value of another type is not converted to a string. When the manifest's own
`bundle_id` breaks its contract (§2), the `bundle_id` link does not hold. Strings are compared as
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §7 states.

The envelope has one name, `envelope_env1.json`; this version defines no earlier one. **The
envelope and its sidecar come together.** A bundle that carries exactly one of
`envelope_env1.json` and `envelope.sha256` refuses its envelope layer with the error
`envelope_incomplete` ([`report-contract.md`](report-contract.md) §5.3): the half that is there
commits to a half that is not. A bundle that carries neither has no envelope layer (§6).

## 5. Archive intake

A verifier reading a ZIP archive **MUST** check every entry of the archive's central directory
against the rules below before it extracts anything, and **MUST** refuse the archive at the
first entry, in central-directory order, that breaks one, rather than proceed on partial data.
Within that entry, the first rule of the table it breaks decides the error. A refused archive
is `OFFLINE_FAIL`, and the rule's code is its one error ([`report-contract.md`](report-contract.md)
§5.3).

**Entries and names.** An entry whose name ends in `/` is a directory entry, and any other entry
is a file entry. Only file entries are members: an empty directory is not a member (§1). An
entry's name is the file name field of its central-directory record, judged as bytes: a byte,
other than a `/` that separates two segments, that is not the ASCII code of a character of the
portable set (§2) breaks the rule `name`, whatever bit
11 of the entry's general-purpose flags says, so no code page and no UTF-8 decoding decides a name.
Nothing in the name is rewritten. The name of a directory entry is read without its final `/`.

**Extra fields.** An entry's extra field is a sequence of fields, each a 2-byte id, a 2-byte size
and that many bytes. A field can carry another spelling of the name, as the Info-ZIP Unicode Path
field (0x7075) does, and a reader that honors it extracts the entry under that spelling. So the
extra field of a central-directory record may hold only these fields, none of which carries a name,
and any other field breaks the rule `name`:

| id | field |
| --- | --- |
| 0x0001 | ZIP64 extended information, read as below |
| 0x000A | NTFS times |
| 0x5455 | extended timestamp |
| 0x7875 | Info-ZIP UNIX owner and group |

None of them is read but 0x0001.

**Reading the archive.** The archive is read from its end-of-central-directory record: the one that
starts at the last occurrence in the file of that record's signature, the four bytes `50 4B 05 06`.
Readers find the record by searching back from the file's end, and some take the last signature
they meet while others take the last record whose comment ends at the file's last byte. Where the
two differ, as they do when a signature stands inside the record's comment, one reader lists one
set of members and another lists another, so such an archive is refused rather than read either
way. When the 20 bytes before that record are a
ZIP64 end-of-central-directory locator, the archive is a ZIP64 archive: its ZIP64
end-of-central-directory record stands directly before the locator, and the entry counts, the
central directory's size and its offset are read from that record, not from the
end-of-central-directory record. A central-directory record's uncompressed size, compressed size or
local-header offset that holds 0xFFFFFFFF is read instead from the entry's ZIP64 extended
information extra field (id `0x0001`), whose 8-byte values stand in that order for the fields that
hold 0xFFFFFFFF. No other extra field is read for a value, and of the general-purpose flags only
bits 0, 5 and 6 are. The archive is not a readable ZIP archive, `invalid_zip`
([`report-contract.md`](report-contract.md) §5.3), and is refused before any entry is checked
against the rules below, when:

- the file holds no end-of-central-directory signature, or the record at its last occurrence does
  not end at the file's last byte, its comment running to that byte exactly;
- in a ZIP64 archive, the locator does not record the offset directly before it as the ZIP64
  record's, or records a disk other than 0 or a number of disks other than 1, or the ZIP64 record
  does not start with its signature or does not record its own size as 44;
- the record the counts are read from records a disk other than 0, a central directory that starts
  on a disk other than 0, or a count of entries on this disk other than its total count of entries;
- the central directory does not end where that record starts, as it does not when bytes stand
  between the central directory and that record, or before an archive whose offsets do not count
  them;
- the central directory is not exactly that count of central-directory records, one after the
  other, each starting with its signature;
- an entry's extra fields, each a 2-byte id, a 2-byte size and that many bytes, do not fill its
  extra field exactly, or a field holding 0xFFFFFFFF has no value in the ZIP64 extended information
  extra field;
- an entry's extra field holds the ZIP64 extended information extra field more than once, whether
  or not a value is read from it: readers that take the first and readers that take the last would
  read two sizes or two offsets for one entry;
- an entry's version needed to extract, in its lower byte, is above 63, or bit 5 (compressed patched
  data) or bit 6 (strong encryption) of its general-purpose flags is set, or it records a disk
  number start other than 0.

**Limits.**

| limit | value |
| --- | --- |
| file entries | 512 |
| uncompressed bytes, per member | 20 MiB |
| uncompressed bytes, total | 50 MiB |
| compression ratio, per member | 100:1 |

A MiB is 1 048 576 bytes. The sizes are the ones the central directory records. The
compression ratio bounds every member, whatever its size: a member breaks it when its
uncompressed size is more than 100 times its compressed size, so a member that records
uncompressed bytes and a compressed size of 0 breaks it too. These values are the bounds: a
verifier **MUST** apply them, and applies the per-member bound to a directory bundle as well.
In a directory bundle the bound is applied to each member the verifier reads: a structural member
or a declared member larger than it fails the layer that reads it (§2 to §4 and §6), and an
undeclared member, which no layer reads, yields `OFFLINE_REVIEW` under §1 whatever its size. The
bound is decided from the member's size before the member is read: a member above it is not read,
so it yields no `*_read_failed` row ([`report-contract.md`](report-contract.md) §5.3).

Directory entries of an archive are not members, and the file-entry limit does not count them. No
limit bounds their number, so the time an archive's intake takes grows with it. A host that needs
a bound on that time bounds the archive's size or its number of entries before it calls the
verifier.

**Rules.**

| rule | an entry is refused when | error |
| --- | --- | --- |
| name | its name is not a portable member name (§2), or its central-directory record's extra field holds a field the table above does not list | `archive_unsafe_member` |
| type | the upper 16 bits of its external file attributes, read as a POSIX mode, record a file type, and that type is not a regular file for a file entry or a directory for a directory entry | `archive_unsafe_member` |
| method | it is encrypted, bit 0 of its general-purpose flags being set, or its compression method is neither 0, stored, nor 8, deflated | `archive_safety_limit` |
| member size | it is a file entry whose uncompressed size exceeds the per-member bound | `archive_safety_limit` |
| ratio | it is a file entry that breaks the compression ratio | `archive_safety_limit` |
| duplicate | its name conflicts (§2) with the name of an earlier entry | `archive_unsafe_member` |
| count | it is a file entry beyond the file-entry bound | `archive_safety_limit` |
| total | the uncompressed sizes of the file entries up to and including it add up to more than the total bound | `archive_safety_limit` |

Two names that conflict are one file on a host that ignores letter case, and a file that another
entry needs as a directory cannot be extracted at all, so an archive holding either would extract,
or fail to, differently depending on where it is verified. One directory spelled two ways, such as
the directory entry `DATA/` and the file entry `data/y.json`, is one directory on a host that folds
and two on a host that does not. A verifier extracts a name within the 255-byte bound under whatever
directory the host gives it, so an archive within the bounds above does not fail to extract for the
length of a name.

An archive whose entries all pass these rules can still fail to extract. Each entry's local header
stands at the offset its central-directory record states, starts with its signature, holds the
same file name field, byte for byte, and holds an extra field that is a sequence of fields filling
it exactly, each of them one the table of extra fields above lists; the entry's data starts after
the local header's file name and extra field, runs for the compressed size the record states and
ends before the central directory; and no two entries' local headers and data overlap. Every byte
before the central directory belongs to an entry: the local header that stands first stands at the
file's first byte, and each entry's data is followed directly by the next local header or, after the
last entry, by the central directory, with nothing between them but at most one data descriptor. A
data descriptor repeats the entry's CRC-32, compressed size and uncompressed size as its record
states them, as three 4-byte values or as a 4-byte value and two 8-byte values, with or without the
signature `50 4B 07 08` before them. Bytes no entry accounts for, such as a self-extracting stub
whose offsets count it, are read by no verifier, so they are refused rather than carried unchecked
with a verified bundle. A file entry's data gives, by its method, exactly the uncompressed size its
record states: stored data is that many bytes, and deflated data is one deflate stream that ends at
the data's last byte and gives that many bytes. Those bytes match the CRC-32 the record states. No
other field of a local header is read, and neither is a directory entry's data. An archive that
breaks one of these is not a readable ZIP archive, `invalid_zip`
([`report-contract.md`](report-contract.md) §5.3); a verifier finds it while it extracts, after
every entry has passed the rules.

**Which refusal an archive reports.** An archive is refused by the first of these that holds, and
that refusal is the run's only error ([`report-contract.md`](report-contract.md) §5.3):

1. `invalid_zip`, for a defect of the end-of-central-directory record or of the central directory
   listed under "Reading the archive", found before any entry is checked;
2. the rules above, at the first entry in central-directory order that breaks one, by the first
   rule of the table it breaks (`archive_unsafe_member` or `archive_safety_limit`);
3. `invalid_zip`, for a defect found while extracting, as the paragraph above states;
4. `archive_load_failed`, when the host fails to create, write or read the extraction;
5. `bundle_root_invalid`, when the extracted archive holds no bundle root or more than one (§1).

So an archive with an entry that breaks the rule `name` and a later entry whose CRC-32 does not
match reports `archive_unsafe_member`, and an archive with no bundle root and a CRC-32 mismatch
reports `invalid_zip`.

These rules keep extraction safe and identical on every host. An entry that passes them is not
thereby evidence: the bundle it extracts to is verified as §1 to §4 describe, and extraction
never replaces a file it has already written.

## 6. Absent input versus failed check

A verifier's per-check result is **three-valued**, and the three values are not
interchangeable:

| value | meaning |
| --- | --- |
| `true` | the check was performed and held |
| `false` | the check was performed and did not hold, or the layer it belongs to was refused |
| `null` | the check could not be performed: its input is absent, or, for `registry_link`, the host failed to read a document the link reads ([`registry-link.md`](registry-link.md) §5) |

Over the checks of the bundle layers, the report status follows from those results, in this
order:

1. any check `false` -> `OFFLINE_FAIL` / `FAIL` / exit `1`
2. otherwise, any check `null` -> `OFFLINE_REVIEW` / `REVIEW` / exit `2`
3. otherwise -> `OFFLINE_OK` / `PASS` / exit `0`

That order is not the whole rule. Some conditions decide the status without a per-check result
of their own, such as an undeclared member, the verdict a registry entry commits to, or a trust
registry no root authenticated, and a check that was not requested leaves its results `null`
without making the run `OFFLINE_REVIEW`. [`report-contract.md`](report-contract.md) §3 states the
complete rule, and §2 there makes the per-check results informative: a conformance comparison reads
the status, the verdict, the exit code and the reasons, and does not fail on a per-check value.

This is stated because it is the rule an independent implementation is most likely to get
wrong, and getting it wrong is not symmetric: collapsing `null` into `false` turns "I could
not check this" into "this is broken", and collapsing it into `true` turns it into a
silent pass.

**Presence flags are facts, not checks.** A field reporting whether an object was found
(`envelope_present`, `canonical_input_present`) records what the verifier saw. It does **not** by
itself decide the status. A bundle with no envelope layer at all reports `envelope_present: false`
and still yields `REVIEW`, because the digest and link checks over that object are `null`: they were
never reached.

**Declared absence is failure; undeclared absence is a question.** The distinction is the
manifest:

- A member `manifest.files` declares that is not present makes the manifest file check
  `false`. The bundle committed to that file, and it is gone: that is tampering or
  truncation, not an open question.
- An object the manifest does not declare, and that is optional for the checks being
  evaluated, is not there. The checks over it are `null` and the run yields
  `REVIEW`.

**A canonical input that is present and unreadable is a refusal.** A `canonical_input.json`
that is not strict JSON ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md),
"Input strictness"), exceeds the per-member bound or is not a JSON object refuses the P1 layer: the
run yields `FAIL`. It is not an absent input, and the input hash is not an open question. The
per-check results are informative ([`report-contract.md`](report-contract.md) §2); both reference
verifiers report `canonical_input_present` `true`, `p1_input_hash` `false` and `p1_sha256` `false`,
because P1 verification did not complete, although `p1.json` matches its sidecar and the envelope's
link to that P1 still holds (`envelope_links` `true`).

**A refused input refuses every layer.** A run that refuses its input as a whole
([`report-contract.md`](report-contract.md) §5.3, the rows `input_not_found` to `filesystem_error`)
reads no bundle, and each layer is refused with the input. Its per-check results are these, whatever
the input is:

- every check of the bundle layers (`manifest_sha256`, `manifest_files`, `p1_sha256`,
  `p1_input_hash`, `envelope_sha256` and `envelope_links`) is `false`;
- the presence flags `canonical_input_present` and `envelope_present` are `false`, because
  nothing was found;
- `registry_signature` is `UNSUPPORTED`, because no signature was evaluated;
- `registry_link` is `false` when a registry entry was supplied, and `null` when none was;
- `trust_registry` is `false` when a registry entry and a trust registry were supplied, and
  `null` otherwise.

An input that does not exist is such a refusal: it is not a member a bundle declares or leaves
out, and a run over it reports no check of the bundle layers as an open question.

**A member the host fails to read refuses the layer that reads it.** A host failure on a member
([`report-contract.md`](report-contract.md) §5.3, the rows `manifest_read_failed`, `p1_read_failed`
and `envelope_read_failed`) is not the member's absence. Each layer reads those of its members the
verifier finds, whatever else refuses the layer:

- the manifest layer reads `manifest.json` and `manifest.sha256`, and, when it has read both and
  does not refuse the manifest, every member `manifest.files` declares that is within the
  per-member bound (§5), to compare it with its digest. Only the conditions of
  `manifest_verification_failed` and a host failure on a manifest member refuse the manifest: a
  sidecar that does not match it, or a manifest that breaks its closed contract, fails the layer
  (`manifest_integrity_failed`) and does not refuse it, so its declared members are still read and
  compared;
- the P1 layer reads `p1.json`, `p1.sha256` and `canonical_input.json`;
- the envelope layer reads the envelope, `envelope_env1.json` (§4), and `envelope.sha256`.

A host failure on a member a layer reads refuses that layer with its `*_read_failed` row. The row is
judged on its own ([`report-contract.md`](report-contract.md) §5.3): the layer's
`*_verification_failed` row is reported beside it when that row's condition holds over the members
the host did read, and neither row masks the other. A bundle whose `manifest.json` is not strict
JSON and whose `manifest.sha256` the host fails to read reports `manifest_verification_failed` and
`manifest_read_failed`; a bundle whose `envelope_env1.json` is not strict JSON and whose
`envelope.sha256` the host fails to read reports `envelope_verification_failed` and
`envelope_read_failed`. The run's per-check results are these:

- every check of a refused layer is `false`: `manifest_sha256` and `manifest_files` for the
  manifest layer, `p1_sha256` and `p1_input_hash` for the P1 layer, and `envelope_sha256` and
  `envelope_links` for the envelope layer. A host failure on a declared member the manifest
  layer reads refuses the manifest layer as well as the layer the member belongs to;
- `envelope_links` is also `false` when the manifest layer is refused and the bundle carries both
  the envelope and its sidecar, because a link to a manifest that was not read does not hold
  (§4). A bundle that lacks either of them evaluates no link, so the manifest layer's refusal
  leaves its `envelope_links` as the envelope layer gives it: `null`, or `false` when the host
  fails to read the half that is present and the envelope layer is refused (the first item);
- every other check of the bundle layers keeps the result its own members give;
- the presence flags record what the verifier found: `canonical_input_present` and
  `envelope_present` are `true` for a member the verifier found and the host then failed to
  read, whichever layer was refused, and `false` for a member the verifier did not find because
  the host failed to list a directory on its path or to inspect its entry. The run reports that
  failure as the layer's read error, not as the member's absence.

The run yields `FAIL`, because a refused layer's checks are `false`.

Worked, because the pair is counter-intuitive: deleting `canonical_input.json` from a
bundle whose manifest declares it yields `FAIL`. A bundle whose manifest never declared a
canonical input yields `REVIEW`: the input hash is unverifiable, which is the outcome
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §3 already requires for that
case. The same reasoning governs the envelope: file and sidecar both absent is `REVIEW`; either one
present without the other is `FAIL`, because the half that is there commits to a half that is not.
An incomplete envelope (`envelope_incomplete`) reports `envelope_sha256` `false` and
`envelope_links` `null`: no link is evaluated over half an envelope, unless the host fails to read
the half that is present, which makes `envelope_links` `false` ("A member the host fails to read"
above).

## 7. Why these are contracts and not schemas

The seven families in [`introduction.md`](introduction.md) §7 are public protocol objects: they
cross organizational boundaries, carry `$id` identities and are validated by published JSON Schema.
The three objects here live inside a private bundle and are read only by a verifier that already
holds the bytes. Giving them schemas would add a second validation surface to keep in step with this
table for no gain in what a relying party can check.

What matters is that the field sets are **closed** and written down. Both halves of that
are load-bearing: closed, because an unexpected member is where an assumption hides; and
written down here, because a contract that lives only in an implementation makes every
other implementation a copy of that one rather than a reading of this specification.
