# Registry-entry signing envelope v2

Status: normative.

## 1. Exact signing message

New registry-entry signatures MUST use payload ID `registry_entry_signing_payload_v2` and payload
version `2`. The exact bytes hashed by SHA-256 are:

```text
ASCII/hex prefix:
LOQUITUR 00 REGISTRY_ENTRY 00 SIGNATURE 00 V2 00

followed immediately by:
RFC 8785 canonical UTF-8 bytes of the signing envelope object.
```

The prefix bytes are:

```text
4c4f5155495455520052454749535452595f454e545259005349474e415455524500563200
```

The closed signing envelope is:

```json
{
  "domain": "org.loquitur.protocol.registry-entry-signature",
  "envelope_schema": "loquitur.signing_envelope.v2",
  "envelope_version": 2,
  "payload": { "...": "registry entry without signature, anchor, anchored_at" },
  "payload_id": "registry_entry_signing_payload_v2",
  "payload_schema": "loquitur.registry_entry.v1",
  "signature_algorithm": "secp256k1_ecdsa_sha256"
}
```

The issuer signs:

```text
SHA-256(prefix || JCS(envelope))
```

SHA-256 is applied exactly once. The 32-byte digest above is the ECDSA hash value `e`; that is
the same as ECDSA with SHA-256 over the signing message bytes `prefix || JCS(envelope)`. A
verifier never hashes the digest again
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4).

**Domain-separation tags.** The prefix and the strings `domain`, `envelope_schema`, `payload_id`
and `payload_schema` are opaque domain-separation tags. They are compared as bytes, they name no
internet domain and claim nothing about who controls one, and their only job is to make the
message of this construction differ from the message of every other. The `$id` of the published
schemas are a separate matter and stay where they are.

The signature object MUST declare:

```json
{
  "algorithm": "secp256k1_ecdsa_sha256",
  "key_id": "<issuer_key_id>",
  "payload_id": "registry_entry_signing_payload_v2",
  "payload_version": 2,
  "signature": "<compact-low-S-r||s-hex>"
}
```

## 2. Domain-separation invariant

A signature created for another protocol object, another envelope version,
another payload schema or another signature algorithm MUST NOT verify as v2.
The fixed prefix and the canonical envelope both bind the context.

## 3. Legacy migration policy

This specification defines no signing payload before v2, and so no legacy payload to migrate
from. A signature object that carries
neither `payload_id` nor `payload_version` breaks the registry entry's contract
([`document-contracts.md`](document-contracts.md) §9), and no verifier offers an option that
verifies it: the reference verifiers offer no such option. A signature object whose `payload_id` and
`payload_version` are a well-formed pair other than `registry_entry_signing_payload_v2` and `2` is
an unsupported version ([`document-contracts.md`](document-contracts.md), "Version gate";
[`report-contract.md`](report-contract.md) §5.5).

The algorithm is an identifier, and the verifier's allowlist decides whether it is supported
([`canonicalization-and-hashing.md`](canonicalization-and-hashing.md) §4). Protocol release 0.1
supports only `secp256k1_ecdsa_sha256`; see
[`cryptographic-capabilities.md`](cryptographic-capabilities.md). Ed25519 is not a 0.1 capability: a
verifier answers a signature that names it with `UNSUPPORTED_SIGNATURE_ALGORITHM` at the signature
step ([`trust-registry-authorization.md`](trust-registry-authorization.md) §6, row 16).

