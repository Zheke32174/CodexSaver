# Release-readiness checkpoint

## Identity

- Repository: `Zheke32174/CodexSaver`
- Checkpoint branch: `release/public-boundary-v1`
- Reviewed default head: `8c291b5c9760c09daf61877dac61477284e7a850`
- Validated implementation head: `2903373334060ad4d09efbdbc4ee8a08619c2329`
- Validation run: `29978810100`
- Related architecture draft: PR #1

## Last completed scope

Workspace confidentiality, delegated-context path handling, provider-visible payload serialization, project Agent Card discovery, Python package metadata, security reporting, source-build validation, public release claims, licensing presence, and install/distribution boundary.

## Findings resolved on this draft

- Refused absolute context paths.
- Refused parent traversal.
- Refused symlinks resolving outside the declared workspace.
- Kept provider-visible file identities workspace-relative.
- Redacted absolute host workspace topology from serialized worker tasks and dry-run/work-packet payloads.
- Replaced unsafe absolute or parent-traversing provider path-policy entries with explicit refusal markers.
- Confined repository-configured Agent Card directories to the selected workspace.
- Preserved explicitly trusted user/global Agent Card registries without exposing their absolute host paths in card provenance.
- Added adversarial tests proving refused paths are not read, local topology is not serialized, and project Agent Card discovery cannot escape the workspace.
- Added an explicit Python build backend and test dependency metadata.
- Added a read-only exact-head workflow for compilation, tests, durable pytest receipts, wheel/sdist construction, and archive inspection.
- Added public security and confidentiality guidance.

## Validation receipts

GitHub Actions run `29978810100` passed at exact implementation head `2903373334060ad4d09efbdbc4ee8a08619c2329`:

- immutable read-only checkout;
- Python 3.12 dependency installation;
- complete source and test compilation;
- all 150 tests;
- durable pytest receipt upload;
- wheel and source-distribution construction;
- package-boundary inspection for runtime modules, metadata, security policy, checkpoint ledger, and boundary tests.

The preceding red run exposed two stale fixtures: one deleted its temporary workspace before using it, and one expected the retired absolute provider-visible file identity. Both were corrected without weakening the confidentiality boundary.

## Changed conclusion

The earlier `bounded context` claim was not true at the filesystem or serialization boundary. Absolute paths, traversal, outward symlinks, host workspace names, and repository-configured Agent Card directories could expose more local topology or files than the public claim implied.

The current source, test, and package boundary is now green. Release readiness remains on HOLD for external governance, credential/lifecycle fixtures, and a broader audit of command output, verifier evidence, worktree persistence, and future session/recovery state.

## Open blockers

- The repository has no selected source license; none was invented.
- No PyPI ownership, trusted publishing identity, or package-name availability has been verified.
- No authenticated release, checksum set, provenance attestation, or consumer verification receipt exists.
- Global install/update/rollback/removal behavior needs a disposable-environment lifecycle fixture.
- Provider credential storage and configuration-file permissions need cross-platform fixture coverage.
- Allowed-command stdout/stderr, verifier evidence, orchestration worktrees, patch aggregation records, and future session snapshots/recovery records require the same local-topology and sensitive-output audit.
- Live hosted-provider behavior has not been exercised on this branch and requires explicit credentials and authorization.
- Branch rules, secret scanning, push protection, private vulnerability reporting, immutable releases, and Action-pin enforcement require administrative verification.

## Deferred items

- Package publication authority.
- Signed or attested release artifacts.
- Registry publication.
- Cross-platform lifecycle testing.
- Live hosted-provider calls.
- Stronger sandbox isolation and network egress controls beyond the current temporary-copy patch sandbox.

## External comparison provenance

Current serious agent-sandbox implementations emphasize repository-scoped mounts, isolated execution, separate persistent volumes, and explicit network/credential policy. CodexSaver now enforces the repository-scoped information boundary in serialized delegation, while stronger process/network isolation remains a future architecture gate rather than an overstated current capability.

Current Python packaging guidance supports PEP 517/518 build metadata, wheel plus sdist construction, and testing the source-distribution boundary before publication. The draft follows that source/package validation flow without claiming registry publication.

## Reconsideration triggers

New commit, changed CI result, dependency or advisory change, changed provider/context flow, new public release claim, license decision, registry identity decision, completed lifecycle fixture, credential-storage fixture, sandbox/egress implementation, security incident, or explicit steward request.

## Next action

Audit allowed-command output, verifier evidence, orchestration worktree persistence, patch aggregation records, and future session/recovery surfaces for local topology or sensitive-data leakage; then design a disposable install/update/rollback/removal fixture before any publication decision.
