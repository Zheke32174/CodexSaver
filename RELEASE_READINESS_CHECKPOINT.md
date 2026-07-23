# Release-readiness checkpoint

## Identity

- Repository: `Zheke32174/CodexSaver`
- Checkpoint branch: `release/public-boundary-v1`
- Reviewed default head: `8c291b5c9760c09daf61877dac61477284e7a850`
- Validated implementation head: `cceb0e01b2b24e2a358523b9f48500f058bb2fec`
- Validation run: `30006137541`
- Current branch head after this ledger-only update: recorded by Git history
- Related architecture draft: PR #1

## Last completed scope

Workspace confidentiality, delegated-context path handling, provider-visible
payload serialization, Agent Card confinement, Python package metadata,
provider-suggested verification containment, and active work-packet
preflight/post-patch command containment.

## Findings resolved on this draft

- Refused absolute, parent-traversing, and outward-symlink context paths.
- Kept provider-visible file and workspace identities relative.
- Confined repository Agent Card discovery to the selected workspace.
- Added explicit Python build/test metadata and package-boundary inspection.
- Removed active shell execution from provider-suggested verification.
- Routed provider and steward work-packet checks through one bounded argv recipe
  executor with no shell.
- Added an idempotent compatibility guard for the public `PatchSandbox` API.
- Limited each check lane to eight recipes.
- Added argv, option, path, timeout, and output bounds.
- Removed inherited credential-bearing environment variables, user-site Python,
  and external pip configuration from check processes.
- Redacted both copied-sandbox and original-workspace topology plus common secret
  shapes from human-readable receipts.
- Preserved hashes and byte counts over the captured stdout/stderr.
- Preserved only one narrow AST-validated legacy smoke form:
  `import module; assert module.function() == literal`.
- Added adversarial coverage for shell chaining, traversal, arbitrary Python,
  unsafe pytest options, sensitive output, excessive recipes, and guard setup.

## Validation receipts

Implementation head `cceb0e01b2b24e2a358523b9f48500f058bb2fec`
passed hosted run `30006137541`:

- immutable read-only checkout;
- Python 3.12 dependency installation;
- source/test compilation;
- all **156 tests**;
- durable pytest receipt upload;
- wheel and source-distribution construction;
- archive-boundary inspection.

The immediately preceding head reached 155 passes and one redaction regression:
a check executed in the copied sandbox printed the original workspace path. The
repair redacts both path identities while preserving the raw-output hashes.

## Changed conclusion

Both active local-check lanes are now contained and validated. The current
source/test/package boundary is green.

Current classification:

**GREEN current source/test/package boundary — HOLD for legacy-body removal,
isolation policy, release governance, licensing, and lifecycle evidence.**

## Open blockers

- Superseded `shell=True` method bodies remain physically present in
  `codexsaver/work_packet.py` and are replaced at package import by the guard.
  Delete them through a direct module refactor before public release so static
  scanners and unusual loader paths cannot encounter misleading code.
- Network egress and stronger process isolation remain policy decisions; the
  cleaned environment is not a network sandbox.
- Orchestration worktrees, patch aggregation, transcripts, and future
  session/recovery records require topology, credential, and retention auditing.
- No source license has been selected.
- PyPI name ownership and trusted-publishing authority are unverified.
- No authenticated immutable release, checksum set, artifact attestation, or
  consumer-verification receipt exists.
- Global install/update/rollback/removal needs a disposable fixture.
- Provider credential storage and configuration-file permissions need
  cross-platform fixture coverage.
- Live hosted-provider behavior requires explicit credentials and authorization.
- Repository security, private vulnerability reporting, branch policy, secret
  scanning, push protection, and immutable-release settings require
  administrative verification.

## External comparison provenance

Current agent execution systems favor repository-scoped filesystems, explicit
runtime identities, restricted networking, credential minimization, and
provenance-bearing evidence. CodexSaver now adapts those principles with copied
workspaces, a minimal child environment, bounded recipes, no shell, redacted
outputs, and content-addressed receipts. It does not claim container or network
isolation.

Current GitHub release practice favors full-SHA Action references, immutable
release tags/assets, and verified artifact attestations. The draft pins Actions
by full commit SHA but does not claim a release.

## Reconsideration triggers

Direct removal of legacy shell bodies, changed CI result, command-policy change,
sandbox/egress implementation, provider/session evidence change, license or
registry decision, lifecycle fixture, security incident, or explicit steward
request.

## Next action

Refactor `codexsaver/work_packet.py` to contain the bounded methods directly,
delete every legacy `shell=True` check path, and remove the temporary
compatibility guard. Then audit transcripts, worktrees, patch aggregation, and
recovery/session persistence.