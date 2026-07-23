# Release-readiness checkpoint

## Identity

- Repository: `Zheke32174/CodexSaver`
- Checkpoint branch: `release/public-boundary-v1`
- Reviewed default head: `8c291b5c9760c09daf61877dac61477284e7a850`
- Current implementation head: `4988b616ec009b2156e5313143a73a9decde9799`
- Prior validated head: `a3289fbf8f1ef3c22e94795842b65081991f7c2c`
- Prior validation run: `29978864346`
- Related architecture draft: PR #1

## Last completed scope

Workspace confidentiality, delegated-context path handling, provider-visible
payload serialization, Agent Card discovery, Python package metadata, source
build validation, provider-suggested verification containment, and active
work-packet preflight/post-patch command containment.

## Findings resolved on this draft

- Refused absolute, parent-traversing, and outward-symlink context paths.
- Kept provider-visible file and workspace identities relative.
- Confined repository Agent Card discovery to the selected workspace.
- Added explicit Python build and test metadata plus package inspection.
- Removed active `shell=True` execution from the simple delegation verifier.
- Routed both provider-suggested and steward-configured work-packet checks through
  one bounded argv recipe executor.
- Added an idempotent import-time compatibility guard for the public
  `PatchSandbox` API while preserving callers during the larger refactor.
- Limited each check lane to eight approved recipes.
- Added command, argv, option, path, output, and timeout bounds.
- Stripped inherited credential-bearing environment variables from checks.
- Disabled user-site Python and external pip configuration in check processes.
- Redacted workspace/home topology and common secret shapes from returned output.
- Added argv/stdout/stderr SHA-256 values and byte counts to check receipts.
- Preserved the existing narrow work-packet smoke-test form through an AST-bound
  `import module; assert module.function() == literal` recipe rather than
  reopening arbitrary inline Python.
- Added adversarial tests for shell commands, chaining, traversal, unsafe pytest
  options, sensitive-output redaction, guard installation, and recipe-count
  overflow.

## Validation receipts

Prior exact head `a3289fbf8f1ef3c22e94795842b65081991f7c2c`
passed run `29978864346`: immutable read-only checkout, Python 3.12 install,
source/test compilation, all 150 tests, durable pytest receipt, wheel/sdist
construction, and package inspection.

Provider-command containment head `8a0564302e53ce10aff723b0dca2679862e3a8a0`
reached hosted tests in run `29990363788`; 148 tests passed and four stale
expectations failed. Those expectations assumed arbitrary inline Python or the
old raw command/error representation and were corrected without reopening shell
authority.

No workflow run is currently indexed for exact head
`4988b616ec009b2156e5313143a73a9decde9799`. No green conclusion is carried
forward until compile, complete tests, wheel/sdist construction, and archive
inspection pass at that exact head.

## Changed conclusion

The broader command audit was materially justified. Both delegation lanes had
local execution risk:

1. the provider-controlled verifier accepted worker-suggested shell text; and
2. the work-packet sandbox accepted steward-configured shell strings for both
   preflight and post-patch checks.

The active runtime paths for both lanes now use the same fail-closed bounded
recipe executor with a cleaned environment and redacted digest receipts.

Current classification:

**HOLD — active command paths contained; exact-head CI and legacy-body removal
pending.**

## Open blockers

- The superseded `shell=True` method bodies remain physically present in
  `codexsaver/work_packet.py` and are replaced at package import by the guard.
  They must be deleted in a direct module refactor before public release so
  static scanners and unusual loader paths cannot encounter misleading code.
- Exact-head compile/test/package validation is pending.
- Network egress and stronger process isolation remain policy decisions; the
  cleaned environment is not a network sandbox.
- Orchestration worktrees, patch aggregation records, transcript persistence,
  and future session/recovery records still require topology, credential, and
  retention auditing.
- The repository has no selected source license.
- No PyPI ownership, trusted publishing identity, or package-name availability
  has been verified.
- No authenticated immutable release, checksum set, provenance attestation, or
  consumer-verification receipt exists.
- Global install/update/rollback/removal behavior needs a disposable fixture.
- Provider credential storage and configuration-file permissions need
  cross-platform fixture coverage.
- Live hosted-provider behavior requires explicit credentials and authorization.
- Repository security, private vulnerability reporting, branch policy, secret
  scanning, push protection, and immutable-release settings require
  administrative verification.

## External comparison provenance

Current agent execution systems favor repository-scoped filesystems, explicit
runtime images and user identities, disabled host networking by default where
practical, credential minimization, and provenance-bearing evidence. This draft
adapts those principles to CodexSaver's lightweight verifier through copied
workspaces, a minimal child environment, bounded recipes, no shell, redacted
outputs, and content-addressed receipts. It does not claim container or network
isolation.

Current GitHub release practice supports immutable full-SHA Action references,
artifact attestations, and immutable release assets. The draft pins Actions by
full commit SHA but does not claim an authenticated release.

## Reconsideration triggers

New head or CI result, direct removal of the legacy shell bodies, command-policy
change, sandbox/egress implementation, provider/session evidence change, license
or registry decision, lifecycle fixture, security incident, or explicit steward
request.

## Next action

Obtain an exact-head compile/test/package receipt. Then refactor
`codexsaver/work_packet.py` to contain the bounded methods directly and remove
the compatibility guard plus all legacy `shell=True` code. Continue with the
transcript, worktree, patch-aggregation, and recovery-state audit after that
source cleanup.