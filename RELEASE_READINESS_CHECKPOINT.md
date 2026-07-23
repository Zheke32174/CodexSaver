# Release-readiness checkpoint

## Identity

- Repository: `Zheke32174/CodexSaver`
- Checkpoint branch: `release/public-boundary-v1`
- Reviewed default head: `8c291b5c9760c09daf61877dac61477284e7a850`
- Prior validated head: `a3289fbf8f1ef3c22e94795842b65081991f7c2c`
- Prior validation run: `29978864346`
- Related architecture draft: PR #1

## Last completed scope

Workspace confidentiality, delegated-context path handling, provider-visible
payload serialization, Agent Card discovery, Python package metadata, source
build validation, and provider-suggested verification-command containment.

## Findings resolved on this draft

- Refused absolute, parent-traversing, and outward-symlink context paths.
- Kept provider-visible file and workspace identities relative.
- Confined repository Agent Card discovery to the selected workspace.
- Added explicit Python build and test metadata plus package inspection.
- Removed `shell=True` from the simple delegation verifier.
- Restricted provider-suggested checks to narrowly validated argv recipes.
- Added command-count, argument, option, path, output, and timeout bounds.
- Stripped inherited credential-bearing environment variables from checks.
- Redacted workspace/home topology and common secret shapes from returned output.
- Added content digests and byte counts for verification stdout/stderr.
- Added adversarial tests for shell commands, inline Python, traversal, unsafe
  pytest options, command chaining, and sensitive-output redaction.

## Validation receipts

Prior exact head `a3289fbf8f1ef3c22e94795842b65081991f7c2c`
passed run `29978864346`: immutable read-only checkout, Python 3.12 install,
source/test compilation, all 150 tests, durable pytest receipt, wheel/sdist
construction, and package inspection.

The provider-command containment batch requires a new exact-head hosted receipt.
No green conclusion is carried forward to the new head until that run passes.

## Changed conclusion

The earlier broader audit gate was materially justified: the simple delegation
verifier executed worker-provided shell text with `shell=True`, no timeout or
allowlist, and returned raw stdout/stderr. A compromised or mistaken provider
could execute arbitrary local commands and expose local data through verifier
evidence.

That immediate provider-controlled execution path is repaired in this draft.
The source/package classification is temporarily **HOLD pending exact-head CI**.

## Open blockers

- Work-packet `allowed_commands` still use raw shell strings with `shell=True`.
  They are steward-provided rather than provider-selected, but still require a
  typed recipe model, clean environment, network/process isolation decision,
  redacted digest receipts, and migration tests.
- Orchestration worktrees, patch aggregation records, transcript persistence,
  and future session/recovery records still require the same topology and
  sensitive-output audit.
- The repository has no selected source license.
- No PyPI ownership, trusted publishing identity, or package-name availability
  has been verified.
- No authenticated release, checksum set, provenance attestation, or consumer
  verification receipt exists.
- Global install/update/rollback/removal behavior needs a disposable fixture.
- Provider credential storage and configuration-file permissions need
  cross-platform fixture coverage.
- Live hosted-provider behavior requires explicit credentials and authorization.
- Repository security and immutable-release settings require administrative
  verification.

## External comparison provenance

Current agent-sandbox practice favors repository-scoped filesystems, isolated
execution, explicit network/credential policy, and provenance-bearing evidence.
This batch narrows provider-suggested local checks to approved argv recipes with
cleaned environment and redacted receipts. It does not claim network isolation.

Current Python packaging guidance supports PEP 517/518 metadata, wheel plus sdist
construction, and testing the sdist boundary before publication. The existing
draft preserves that flow without claiming registry publication.

## Reconsideration triggers

New head or CI result, command-policy change, work-packet recipe migration,
sandbox/egress implementation, provider/session evidence change, license or
registry decision, lifecycle fixture, security incident, or explicit steward
request.

## Next action

Obtain an exact-head compile/test/package receipt. Then replace work-packet shell
strings with typed verification recipes and audit returned transcripts,
orchestration worktrees, patch aggregation, and recovery/session state.
