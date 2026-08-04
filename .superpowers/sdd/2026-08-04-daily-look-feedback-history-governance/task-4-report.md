# Task 4 Report — Current Contract Documentation

Status: complete.

- Updated `docs/SPEC.md` for same-day recommendation-set reuse, force refresh, 3–6 item cards, server-confirmed feedback, scoped history retention, and the no-startup-cleanup constraint.
- Updated `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` for dynamic Look and Total Look rendering, confirmed feedback, archive/recent entry points, and affected request/response payloads.
- Reviewed the committed backend/frontend paths (`services/recommend.py`, `services/history.py`, `routers/feedback.py`, schemas, `api.mjs`, `ScreenToday.tsx`, and `ScreenProfile.tsx`); no code or runtime data changed.

Checks: `git diff --check` passed; stale-claim search found no fixed-three-item, single-image taste-memo, required-feedback, or refresh-regeneration claims.

Concern: none. The repository's existing untracked `.playwright-cli/`, `output/`, and plan file remain unstaged.

## Review fix round 1

- Corrected the recommendation contract: ordinary same-day sets reuse unconditionally; prepared sets require the documented location and weather thresholds, and a normal request can generate when no reuse path matches.
- Documented `history({scope,limit})` forwarding and made the partial Total Look rendering/fallback boundary exact.
- Rechecked with `git diff --check`.

## Review fix round 2

- Made the reuse order explicit: ordinary same-day groups precede 06:30 prepared candidates; `force_refresh` bypasses both.
- Corrected history limit forwarding: truthy values are sent, the backend accepts 1–100, and omitted or `0` uses the backend default.
- Rechecked with `git diff --check`.
