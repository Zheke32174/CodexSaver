# Security policy

CodexSaver delegates selected repository context to configured local or hosted workers. Treat the context boundary as a confidentiality boundary, even for read-only tasks.

## Supported security boundary

- Context paths are relative to the explicitly selected workspace.
- Absolute paths, parent traversal, and symlinks resolving outside that workspace are refused.
- Provider credentials must not be committed to this repository.
- A successful worker response is a proposal, not authorization to apply or publish a change.
- Security, authentication, payment, permission, deployment, and destructive operations remain outside the delegated execution lane.

## Reporting

Report sensitive vulnerabilities through GitHub private vulnerability reporting when available, or through an established private channel with the repository owner. Do not include active credentials, private source, personal data, or working exploit payloads in public issues.

## Distribution status

This repository currently provides source code only. It does not claim a published PyPI package, signed executable, authenticated release artifact, or selected source license.
