# Daily Look Feedback and History Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make daily recommendations deterministic within a local calendar day, support 3–6 item Looks with optional layers/accessories, persist feedback only after server confirmation, and turn history/profile taste feedback into reusable full-Look signals with bounded temporary retention.

**Architecture:** Keep the existing SQLite schema and React/ FastAPI boundaries. Encode recommendation-set identity in `outfit_history.context_json`, reuse the latest complete same-day set unless `force_refresh=true`, and use the existing feedback endpoint for favorite, rating, and wear actions. Keep long-term records and feedback facts; prune only old temporary history during normal recommendation writes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, pytest, Ruff; React 19, TypeScript, Vite, Vitest, ESLint; existing SQLite database and MiniMax integrations.

## Global Constraints

- Work only in `/Users/novel/Projects/outfit-ai/.worktrees/daily-context-style-dna` on the current feature branch.
- Do not delete or migrate the existing real database in this change; pruning is exercised only through application code and isolated test databases.
- Never expose MiniMax credentials in frontend code, documentation, tests, logs, or commits.
- Preserve untracked `.playwright-cli/` and `output/`; do not stage them.
- Update `docs/SPEC.md` and `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` in the same change as the code they describe.

---

## Task 1: Lock the backend contract with failing tests first

- [ ] Extend `backend/tests/test_recommend.py` with tests proving that a normal request reuses the latest complete same-day three-tier recommendation set, including manual-city requests without coordinates, while `force_refresh=true` creates a new set.
- [ ] Extend `backend/tests/test_history.py` with tests for recommendation-set grouping, archive/recent scopes, and pruning only temporary rows older than 14 local days when `wore_it=false` and rating is absent or below 4.
- [ ] Extend `backend/tests/test_feedback.py` with tests for optional actions, 1–5 ratings, explicit favorite, wear preservation, and rating-only feedback.
- [ ] Add a validator/prompt test covering the 3–6 item range and optional layering/accessory guidance.
- [ ] Run the focused suite and confirm the new tests fail before implementation:
  `uv run --project backend pytest -q backend/tests/test_recommend.py backend/tests/test_history.py backend/tests/test_feedback.py backend/tests/test_guardrail.py backend/tests/test_llm.py`.

## Task 2: Implement backend recommendation and history governance

- [ ] Update `backend/src/outfit_ai/schemas.py` so `ProposedLook.item_ids` requires 3–6 unique candidates at the API boundary, and `FeedbackIn.action` is optional with an optional integer `rating` constrained to 1–5.
- [ ] Update `backend/src/outfit_ai/services/validator.py` and `backend/src/outfit_ai/services/prompt_builder.py` to enforce and describe required core coverage plus optional layers/accessories without filler items.
- [ ] Add minimal grouping and cleanup helpers to `backend/src/outfit_ai/services/history.py`: write/read `recommendation_set_id`, select the latest complete local-date set (with a legacy fallback for rows without the id), return archive/recent scopes, and prune only qualifying temporary rows older than 14 local days.
- [ ] Refactor `backend/src/outfit_ai/services/recommend.py` to reuse the selected same-day set before weather/coordinate matching, preserve it across refresh/navigation, bypass it only for `force_refresh=true` or prepared pre-generation, and assign one set id to each Safe/Fresh/Stretch batch.
- [ ] Update `backend/src/outfit_ai/routers/feedback.py` so server state changes are atomic: rating is stored on history, `worn` sets `wore_it` without clearing an existing saved action, and action-less rating events remain valid. Extend history responses with scope and rating fields.
- [ ] Keep existing item-id and category guardrails, and ensure failed LLM generations never create a reusable group or advance retention checkpoints.
- [ ] Run backend focused tests, then the full checks:
  `uv run --project backend pytest -q`
  `uv run --project backend ruff check backend/src backend/tests`.

## Task 3: Make frontend feedback and Look rendering server-confirmed and dynamic

- [ ] Update `frontend/src/lib/api.mjs` to translate network failures into a stable user-facing error, preserve server error details, and map history/Look payloads including `historyId`, `rating`, and every item in a Look.
- [ ] Update `frontend/src/types.ts` with optional history identity, full `lookItems`, rating, and action fields while retaining a single-image fallback for legacy records.
- [ ] Update `frontend/src/components/ScreenToday.tsx` to render 3–6 dynamic item cards (not fixed indexes), keep optional accessories/layers when supplied, and commit like/rating changes only after `/api/feedback` succeeds; on failure restore the prior state and show the translated error.
- [ ] Update `frontend/src/components/ScreenProfile.tsx` so history cards in both archive and recent scopes expose favorite/rating/wear actions through the shared server-confirmed path, and the AI taste memo displays the full Total Look thumbnails with a legacy single-image fallback.
- [ ] Add focused frontend tests in `frontend/scripts/api-contract.test.mjs` (or the existing nearest test file) for network-error translation, dynamic item mapping, feedback rollback, history scope, and full-Look memo data.
- [ ] Run frontend validation:
  `cd frontend && PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm test`
  `cd frontend && PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run lint`
  `cd frontend && PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run build`.

## Task 4: Update the current project contract and integration documentation

- [ ] Update `docs/SPEC.md` with same-day recommendation identity/reuse rules, 3–6 item Look composition, feedback semantics, history scopes/retention, and the no-runtime-cleanup-of-existing-data constraint.
- [ ] Update `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` with dynamic Look rendering, server-confirmed feedback behavior, history archive/recent entry points, full-Total-Look taste memo, and the exact affected API payloads.
- [ ] Search the current docs for stale claims about fixed three-item Looks, refresh-driven regeneration, required feedback actions, or single-image taste memo and correct each occurrence.

## Task 5: Verify the integrated behavior before handoff

- [ ] Start the existing backend and frontend dev servers only if they are not already running, then verify `GET /health`, a weather request, `GET /api/history?scope=recent`, and one normal recommendation request through the frontend proxy.
- [ ] Exercise the same-day flow twice and assert the recommendation-set id and three tier ids remain unchanged; exercise `force_refresh=true` and assert a new set id; verify a manually selected city does not invalidate reuse.
- [ ] Exercise favorite, 1–5 rating, and “today wear” from both Today and History; verify a failed request leaves the prior UI state unchanged and a successful request appears in Favorites/archive.
- [ ] Exercise a 3-item and a 6-item Look and confirm all item tiles render, including optional accessory/layer slots; verify the profile taste memo shows the complete Total Look.
- [ ] Run `git diff --check`, inspect `git status --short`, and confirm only intended source/tests/docs files are tracked. Do not stage `.playwright-cli/` or `output/`.
- [ ] Commit the implementation as one cohesive feature commit after all checks pass.

## Self-review checklist

- [ ] Every approved requirement is mapped to an implementation step and a test.
- [ ] No step contains an unresolved placeholder, unspecified file, or unbounded schema change.
- [ ] API types, backend schemas, frontend mappings, and documentation use the same field names and semantics.
- [ ] The plan does not require deleting current user data or adding a new database migration.
