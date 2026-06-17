# Fork Notes — Zheke32174/CodexSaver

This fork of `fendouai/CodexSaver` is maintained for the Fixxia hive (English-language operator). Goal: zero non-English prose in the codebase while preserving every functional capability of upstream.

Forked from upstream commit `5ec347e docs: unify v3.6 pi agent setup` on 2026-06-16.

## What changed in this fork (prose-only)

| File | Change | Why |
|---|---|---|
| `README.md` | Removed the `中文文档` link to `README_zh.md`. | English-only audience. |
| `README_zh.md` | **Deleted** the entire 455-line Chinese README. | Redundant with `README.md`. |
| `SPEC.md` | `Codex's心智模型 clean` → `Codex's mental model clean` | Mid-sentence Chinese phrase. |
| `docs/SPEC_v2.md` | `-强化 ...` → `- Enforce ...` (line 267) | Single bullet half-translated upstream. |

## What was **deliberately left alone** (would have broken features)

These pieces look like "Chinese text in source" but are **functional code or test fixtures**, not stale prose:

- **`codexsaver/policy.py` — multilingual classifier keywords.** Lists like `["migration", ..., "迁移", "入库"]` route Chinese-language prompts to the right risk tier. Deleting the Chinese terms removes Chinese-prompt routing entirely. Kept.
- **`codexsaver/work_graph.py` — multilingual task-kind keywords.** Same pattern (`["implement", ..., "实现", "新增"]`). Kept.
- **`codexsaver/installer.py` — multilingual installer keyword set.** Same pattern. Kept.
- **`codexsaver/provider.py:STYLE_PRESETS["wenyan"]` — Classical-Chinese system prompt preset.** One of four user-selectable styles (`default`, `terse`, `ultra`, `wenyan`). Removing it deletes a selectable feature. Not the default. Kept.
- **`scripts/run_v2_benchmark.py` — `Create Chinese v2 note` benchmark case.** The benchmark name + goal sentence are intentionally Chinese: this case verifies CodexSaver's `zh_docs` work-kind end-to-end. Translating breaks the test. Kept.

## Rebasing from upstream

```bash
git remote add upstream https://github.com/fendouai/CodexSaver.git
git fetch upstream
git checkout main && git merge upstream/main
# resolve conflicts in the 4 prose files above
```

The prose changes are localized; rebases should be clean unless upstream renames `README_zh.md` or rewrites SPEC.md's intro paragraph.

## How CodexSaver is used in this hive

- Installed editable per `pyproject.toml`.
- MCP entry: `mcp__codexsaver__*` (status as of 2026-06-16: disconnected this session per a deferred-tools notice; reconnects on next session).
- Cost ledger via `codexsaver.delegate_task` / `orchestrate_task` / `run_specialist`.
