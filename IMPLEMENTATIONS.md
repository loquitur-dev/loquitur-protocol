# Implementations

This file is informative and is not part of the specification. It names the reference
implementations of protocol release 0.1. Each is a separate repository with its own releases, and
each repository states its own publication status and what its releases have been tested against.
This file changes without a protocol release;
[`docs/specification/introduction.md`](docs/specification/introduction.md) section 11 points to it.

Both reference implementations were written separately against the specification, by the same
maintainer. Their agreement shows that the text can be implemented as written; it is not
independent evidence that the text is right. Any testing of them by the maintainer is carried out
with the help of AI tools and is internal verification, not an audit.

| Implementation | Role | Language | Repository |
| --- | --- | --- | --- |
| `loquitur-verify` | verifier, directory and archive intake | Python 3.11 or later | `loquitur-verify-py` |
| `@loquitur/verify` | verifier, directory intake | TypeScript, Node.js 22 or later | `loquitur-verify-ts` |

Each repository states its own publication status and what its releases have been tested against.
