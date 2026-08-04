# Task 3 · Frontend Look feedback and history governance

## Delivered

- `frontend/src/lib/api.mjs`
  - Translates fetch/network failures to `网络连接失败，请检查网络后重试`; non-2xx server `detail` messages remain unchanged.
  - Maps each recommendation item into `items` and `lookItems`, preserving all returned 3–6 items.
  - Adds scoped `api.history({ scope, limit })`, `mapHistoryLook()` (including `historyId`, rating, scope, wear state and legacy `collage_path` fallback), and `confirmFeedback()` as the shared confirmation/rollback boundary.
- `frontend/src/types.ts`
  - Adds optional history identity, full Look data, rating, scope and wear fields without removing legacy image support.
- `ScreenToday.tsx`
  - Replaces three fixed item indexes with dynamic item-card rendering.
  - Like and rating writes await `/api/feedback`; local state/localStorage changes only after success. Failed writes preserve the prior view and show the translated error.
- `ScreenProfile.tsx`
  - Loads both `archive` and `recent` history scopes, maps their full Look records, and exposes favorite, rating and wore-it actions through the same confirmation path.
  - The taste memo’s rating cards show all available Total Look thumbnails; legacy records retain the prior single-image fallback.
- `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`
  - Documents the server-confirmed feedback behavior, dynamic Today Look rendering, and scoped history actions.

## Focused coverage

`frontend/scripts/api-contract.test.mjs` now verifies network-error translation, scoped-history query construction, full 3–6 item recommendation mapping, history/legacy collage mapping, and server-confirmed feedback rollback behavior.

## Validation

From `frontend/` with the bundled Node runtime:

```text
npm test      PASS — Stitch contract + 27 tests
npm run lint  PASS — tsc --noEmit
npm run build PASS — Vite production build
```

## Scope and caveat

No DB, credentials, backend files, `.playwright-cli/`, or `output/` files were changed. Validation is contract/type/build level; no logged-in browser or live backend/DB mutation was run.
