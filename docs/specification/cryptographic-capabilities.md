# Cryptographic capabilities for protocol release 0.1

Status: normative.

## 1. Normative capability profile

Protocol release 0.1 has one closed cryptographic capability profile:
`loquitur.crypto_capabilities.v0.1`.

The only signature algorithm permitted for new issuance and verification is
`secp256k1_ecdsa_sha256`. The corresponding trust-registry key type is
`secp256k1`. Signatures use a SHA-256 digest, compact IEEE P1363 `r || s`
encoding represented as lowercase hexadecimal, an uncompressed SEC1 public key,
and mandatory low-S verification.

## 2. Algorithm agility, and a closed allowlist

Algorithms and key types are named by identifiers matching `^[a-z0-9][a-z0-9_]{0,63}$`, and the
documents admit any identifier of that form
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4). Which pairs a verifier
accepts is the verifier's own closed allowlist, never a value the input chooses: for this release it
is exactly the capability set in `CRYPTOGRAPHIC_CAPABILITIES.json`. A pair not listed there MUST be
refused at the signature step with `UNSUPPORTED_SIGNATURE_ALGORITHM`
([`trust-registry-authorization.md`](trust-registry-authorization.md) §6,
[`trust-root.md`](trust-root.md) §5). Implementations MUST NOT infer an algorithm from key length,
retry with another algorithm, or silently downgrade. Every digest a JSON document carries names its
algorithm as well ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §2).

## 3. Ed25519

Ed25519 is not a protocol 0.1 capability. It is reserved only as a possible
future protocol addition. A protocol 0.1 verifier answers an Ed25519 key type or signature
declaration with `UNSUPPORTED_SIGNATURE_ALGORITHM` at the signature step. No implementation may
advertise Ed25519 issuance or verification support under the 0.1 release identity.

Adding Ed25519 requires a future approved protocol release with domain-separated
message semantics, normative positive and negative vectors, schema
changes, all reference implementations, migration rules and independent security
review.

## 4. Relationship to signing envelope v2

The envelope binds `signature_algorithm: secp256k1_ecdsa_sha256` into the signed
bytes. Algorithm substitution therefore changes the message and MUST fail.

## 5. Why these choices

The rules above fix the algorithms; this section gives the reasons for them, and the weaknesses
they keep.

- **SHA-256** ([FIPS 180-4]) is the one digest. It is implemented in every language a verifier is
  likely to be written in, and it is applied exactly once before ECDSA
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4), so that two
  implementations cannot disagree about whether the message or its digest is what is hashed.
- **secp256k1 ECDSA** is chosen for the keys and libraries that issuers and their tooling already
  have for it, not for a security margin: its strength is comparable to that of other 256-bit
  curves.
- **IEEE P1363 `r || s` in lowercase hexadecimal** has one length and one spelling. A DER encoding
  admits several byte strings for one signature and needs a parser of its own; a fixed-width form
  admits neither.
- **Low S.** For every ECDSA signature `(r, s)`, the pair `(r, n - s)` verifies too. Accepting only
  the low value leaves one encoding of a valid signature for a message and a key, so no party can
  produce a second form of a signature it did not make.
- **Range and point checks before the library call.** `r` and `s` in `[1, n-1]`, coordinates below
  `p` and the point on the curve are checked by the verifier itself, because a library may accept
  what the protocol refuses, such as a high `S`.
- **RFC 8785** is the one canonical form, and a signature covers canonical bytes rather than a
  parsed structure, so that the strict input rules decide what was signed
  ([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §6).
- **No negotiation.** The algorithm is bound into the signed envelope, and the pairs a verifier
  accepts are its own closed allowlist (§2), so an input cannot choose a weaker algorithm.

The weaknesses this release keeps:

- ECDSA reveals the private key when a signer reuses a nonce, or draws nonces with a bias. That is
  a risk of the signer, which no verifier can detect. Deterministic nonces ([RFC 6979]) avoid it;
  this specification does not require them, and a verifier must not assume any nonce scheme.
- Nothing here resists a quantum computer able to run Shor's algorithm on 256-bit curves. Such a
  computer would break secp256k1 and with it every commitment signed under this release at once
  ([`threat-model.md`](threat-model.md) §9).
- The digest `H` an issuer signs and the signing envelope are fixed for this release; a change to
  either needs a new envelope version ([`signing-envelope-v2.md`](signing-envelope-v2.md) §2).
