<coding_guidelines>

## Personal Agent Policy (anton) — Template for New Projects

This file is a **personal template** that Factory may copy into new project folders as `AGENTS.md` (via `C:\Users\anton\.factory\hooks\ensure-agents-md.ps1`).

It must not override procedural MUST rules from the closest `.factory/AGENTS.md` in the active working directory.

## Scope Boundaries

- This policy governs how I (the agent) should behave when working inside a project.
- It does **not** attempt to change Factory platform behavior (hooks, tool availability, model routing).

## Delegation Boundaries (reduce overhead)

- **Do not delegate** for:
  - pure Q&A
  - trivial file reads without analysis
  - basic navigation commands
  - small edits (see definitions) in low‑risk domains
- **Delegate** when:
  - any multi-file change, or
  - behavior change, or
  - anything in high‑risk domains (auth/crypto/payments/deserialization/shell+exec/network ACL/infra), or
  - user explicitly asks for a deep investigation / review

## Definitions

- **Minor change** = ≤1 file AND (added+deleted) ≤ 30 LOC AND no behavior change AND not in high‑risk domains.
- **Substantial change** = any of:
  - edits to 2+ files, OR
  - (added+deleted) > 30 LOC, OR
  - behavior change (logic/API/UX/security), OR
  - any high‑risk domain touched.

## Documentation Policy (resolves conflict with “don’t update docs unless asked”)

- Default: **Do not create/update documentation** (README, ADRs, guides, wiki) unless the user explicitly asks.
- Exception (policy hygiene): You may update **agent-operational policy files only** (e.g., `AGENTS.md`, `.factory/AGENTS.md`, hook policy text) when required to resolve instruction conflicts or keep enforcement consistent.
- For substantial changes: if user did not ask for docs, prefer a **short in-chat explanation** (what changed + how to verify) instead of committing doc updates.

## Conflict Resolver Policy

When instructions disagree, resolve in this order:
1) System message
2) Closest `.factory/AGENTS.md` procedural MUST rules
3) Closest `AGENTS.md` style/preferences
4) User request (unless it violates above)
5) General best practices

If two rules conflict at the same priority: choose the safer, more reversible option and keep scope minimal.

## Tooling Bootstrap Checks (Windows)

Before relying on tooling, verify availability using `cmd /c "where <tool>"` (not `which`).

Common checks:
- Node: `where node` and `where npm`
- Python: `where python` and `where py`
- GitHub CLI: `where gh`
- Ripgrep: `where rg`

If required tooling is missing:
- Prefer minimal verification using what is available.
- Report missing tools and suggest minimal installation steps.

## Validators Discovery Policy

- Node/JS:
  - If `package.json` exists, run only scripts that exist (e.g. `npm run -s lint`, `npm run -s typecheck`, `npm run -s test`).
  - Do not invent scripts.
- Python:
  - If `pyproject.toml`/`pytest.ini` exists and `python`/`py` is available, run the fastest relevant checks (e.g. `python -m pytest`).
- Avoid full builds unless that is the project’s standard gate.

## Node always-on validator (when npm scripts are missing)

- If `package.json` exists but there are no `lint`/`typecheck`/`test` scripts, run a read-only validator anyway.
- Prefer: `node --check` on relevant `*.{js,cjs,mjs}` files (syntax-only).
- If `package.json` has `name` and `version`, you may additionally run `npm pack --dry-run`.

## Secrets Scan Before Commit/Push (SHOULD; warn-only)

- Before `git commit` or any `git push`, you **SHOULD** scan for secrets (tokens/keys/passwords).
- If a secret is detected: warn and stop to fix it.
- If the user explicitly accepts the risk and asks to proceed, you may proceed (do not silently ignore).

## Artifacts / Temp Files Policy

- Never create/edit/delete anything under `~/.factory/artifacts/`.
- Keep generated temp files under repo-local temp folders or OS temp, and clean them up when done.
- Do not commit build outputs/caches/logs unless the user explicitly asks.

## Definition of Done (DoD)

### Minor change (low risk)
- Behavior matches request
- Run at least one fast relevant validator if available
- No secrets in diffs/logs (redact sensitive strings)
- Provide a short summary and a 1–2 step manual verify note (if applicable)

### Substantial change (medium)
- Run all relevant validators discovered by repo config
- Add/adjust tests when behavior changed (where feasible)
- Prefer a review pass (human or `quality-reviewer`) before finalizing

### High-risk change
- Include `security-auditor` review before finalizing
- If user insists on skipping checks, explicitly record risk acceptance in-chat

## Output / Log Redaction Policy

- Never print secrets (tokens, cookies, auth headers, private keys) or full environment dumps.
- Redact sensitive strings in snippets: `***REDACTED***`.
- Prefer minimal log excerpts needed to diagnose issues.

</coding_guidelines>
