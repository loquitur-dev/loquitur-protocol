# Public/private boundary

Status: normative.

Loquitur uses a commit-and-reveal style boundary.

## 1. Public commitment material

A public registry entry carries only the members its schema,
[`schemas/registry_entry.schema.json`](schemas/registry_entry.schema.json), defines, and the schema
admits no other:

- its object type and schema version (`object_type`, `schema_version`);
- the registry entry identifier and the receipt identifier (`registry_entry_id`, `receipt_id`);
- the issuer identifier and key identifier (`issuer_id`, `issuer_key_id`);
- the asset type and workflow (`asset_type`, `workflow`);
- the subject reference hash, manifest hash and receipt hash (`subject_ref_hash`,
  `manifest_hash`, `receipt_hash`);
- the policy identifier and version (`policy_id`, `policy_version`);
- the reason-code vocabulary and the reason codes (`reason_code_catalog_version`,
  `reason_codes`);
- the verdict (`verdict`);
- the issuance time and, optionally, the effective time (`issued_at`, `effective_at`);
- the privacy classification and disclosure profile (`privacy_classification`,
  `disclosure_profile`);
- optionally, signature material (`signature`);
- optionally, anchor reference material (`anchor`, `anchored_at`).

## 2. Private material

The public repository and public registry commitment MUST NOT disclose:

- raw evidence documents;
- canonical input payloads;
- full bundle contents;
- private bundle download links;
- asset street addresses or private asset identifiers;
- valuation amounts or NAV values;
- cap rate, NOI, IRR, LTV, vacancy, tenant, rent-roll, or similar business-sensitive metrics;
- document names, document contents, unrestricted storage URLs, or evidence URLs;
- private keys, tokens, cookies, authorization headers, or secrets;
- backend operational internals.

## 3. Hiding, and its assumption

The manifest digest is public through the registry entry's `manifest_hash`, and the receipt
digest through `receipt_hash`, and the receipt carries the manifest digest. A bundle of low
entropy, such as a NAV update with no documents, would otherwise be found from those digests by
anyone who knows its `bundle_id` and tries its few possible contents. The manifest's `nonce`
([`bundle-objects.md`](bundle-objects.md) §2) closes that: 32 random bytes inside the manifest make
the digests reveal nothing about the bundle to a party without it. The property holds only under its
assumption, which a verifier cannot check: the producer fills the nonce from a cryptographically
secure random generator, fresh for every bundle, and never reuses, publishes or derives it. A
verifier checks the nonce's form, not its randomness.

For the same reason `receipt_id` and `registry_entry_id` are random or opaque and are never
derived from `bundle_id` ([`registry-entry.md`](registry-entry.md)), and `subject_ref_hash` is built
with a secret salt and never from a public or guessable identifier alone
([`registry-entry.md`](registry-entry.md), "Subject reference hash").

## 4. Personal data in public identifiers

Public identifiers MUST NOT carry personal data: no identifier of a registry entry names a
natural person. In a trust registry, `issuer_display_name` and `notes` name a legal person, or a
natural person only in a professional capacity that is already public. A public value stays in logs
and dossiers for ever and cannot be withdrawn, so this is decided before the value is written.

## 5. Interpretation rule

A public commitment indicates that a receipt-like object was produced and committed under declared
metadata. It does not prove legal ownership, valuation correctness, regulatory status, chain
finality, or source-document truth.

## 6. Privacy considerations

This section adds no rule. It answers the questions of RFC 6973 section 7 from what sections 1 to
5 state, and from the sections of [`registry-entry.md`](registry-entry.md) they cite.

### 6.1 Data minimization

A public commitment carries the fields section 1 lists, among them identifiers, digests,
policy identity, reason codes, a verdict posture and an issuance timestamp. Section 2 lists what it
must not disclose: evidence documents, canonical input payloads, bundle contents, business-sensitive
values, locators of private material, and secrets. The evidence stays on the private side; the
public side carries digests that commit to it.

### 6.2 Identifiers

The public identifiers are those of section 1. `receipt_id` and `registry_entry_id` are random or
opaque and never derived from `bundle_id`, so that an identifier cannot confirm a guess about the
bundle (section 3, [`registry-entry.md`](registry-entry.md) section 3). `subject_ref_hash`
identifies the subject of an entry without naming it: it is built with a secret salt and never from
a public or guessable identifier alone (section 3,
[`registry-entry.md`](registry-entry.md) section 4).

### 6.3 Correlation

`subject_ref_hash` is stable for one subject and one salt, so every entry about that subject under
that salt is linkable in public. An issuer that needs the entries of a series not to be linkable
uses a different salt for each series ([`registry-entry.md`](registry-entry.md) section 4).

### 6.4 Inference from public digests

The manifest and receipt digests are public. A bundle of low entropy could otherwise be found from
them by anyone who knows its `bundle_id` and tries its few possible contents. The manifest's
`nonce` closes that, under an assumption a verifier cannot check: the producer fills it from a
cryptographically secure random generator, fresh for every bundle, and never reuses, publishes or
derives it. A verifier checks the nonce's form, not its randomness (section 3).

### 6.5 Personal data, retention and withdrawal

Public identifiers carry no personal data, and no identifier of a registry entry names a natural
person. In a trust registry, `issuer_display_name` and `notes` name a legal person, or a natural
person only in a professional capacity that is already public. A public value stays in logs and
dossiers for ever and cannot be withdrawn, so what it may carry is decided before it is written
(section 4).

### 6.6 Security of the private material

The private material is the issuer's to keep: section 2 keeps it off the public side, and
[`threat-model.md`](threat-model.md) section 1 states that the confidentiality of a bundle once its
holder has disclosed it is not protected.

### 6.7 The subject reference hash

`subject_ref_hash` is a salted SHA-256 digest of the subject's identifier under a domain prefix
([`registry-entry.md`](registry-entry.md) section 4). Its privacy rests on the salt alone.

- **Why 256 bits of salt.** The identifier under it, an ISIN, a cadastral reference or a fund name,
  is often public or guessable, so the salt is the only secret between a public value and the
  subject it names. A salt of 32 bytes from a cryptographically secure random generator cannot be
  found by trying values, and it matches the length of the digest. A verifier cannot check how the
  salt was made.
- **Linkable within a series, by design.** One salt serves one series: every entry about one subject
  under one salt carries the same value, so anyone can link those entries in public. An issuer that
  needs the entries of a series not to be linkable uses a different salt for each series.
- **Not linkable across series.** Two values made under two salts are unrelated to anyone who holds
  neither salt, even for the same subject.
- **The opening discloses the series.** An issuer that gives a relying party the opening, in the
  bundle member `subject_ref_opening.json`, gives every recipient of that bundle the identifier and
  the salt: each of them can recompute the value and link every public entry that carries it, the
  whole series.
- **A guessable identifier is safe only while the salt stays private.** Anyone who learns a salt can
  test candidate identifiers against every public value made with it. One salt reused for several
  subjects links nothing by itself, since different identifiers give different values, but a salt
  that leaks then exposes every subject made under it.

No check of this version reads the opening or recomputes the value; a verifier treats
`subject_ref_hash` as a digest of the form
[`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) section 2 fixes.
