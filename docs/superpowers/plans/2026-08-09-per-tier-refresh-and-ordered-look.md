# 单卡换一换与穿衣顺序展示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让“AI 换一换”只重新生成被点击的 Look，并把 3–6 件单品按从头到脚的穿衣顺序纵向展示。

**Architecture:** 后端新增可选 `refresh_tier`，在带 `force_refresh` 的单卡请求中只调用一次目标 tier 的 M3，复用另外两档并保持响应仍为三档；前端把 `refresh_tier` 透传并只合并目标 tier。展示层新增纯函数排序副本，不改变 API、历史或反馈顺序。

**Tech Stack:** FastAPI/Pydantic/SQLAlchemy、MiniMax tool-call、React/TypeScript、Node test runner、Vitest-free fetch contract tests、Tailwind CSS。

## Global Constraints

- 仅允许 `refresh_tier=safe|fresh|stretch` 与 `force_refresh=true` 组合触发单卡刷新。
- 单卡刷新失败时不得写入新 history、删除旧 history 或覆盖其它 Look。
- 视觉排序只作用于渲染副本；反馈仍使用 API 返回的原始 `look.items` 顺序。
- Look 必须保持 3–6 件且包含上装、下装、鞋履；不新增数据库表、队列或依赖。
- MiniMax 凭据只留在后端；修改代码、接口或 UI 时同步更新 `docs/SPEC.md` 与 `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`。

---

### Task 1: Lock the new contract with failing tests

**Files:**
- Modify: `backend/tests/test_recommend.py`
- Modify: `backend/tests/test_schemas.py` (if present; otherwise keep schema assertions in `test_recommend.py`)
- Modify: `frontend/scripts/location-context.test.mjs`
- Modify: `frontend/scripts/api-contract.test.mjs`

**Interfaces:**
- Backend `RecommendRequest.refresh_tier: Literal["safe", "fresh", "stretch"] | None`.
- Frontend `loadDailyRecommendation({ refreshTier })` sends `refresh_tier` only when supplied.
- Frontend `orderLookItems(items)` returns a new array and never mutates `items`.

- [ ] **Step 1: Write the failing backend tests**

  Add tests that instantiate `RecommendRequest(refresh_tier="safe", force_refresh=True)`, stub `propose` to fail if called, stub `propose_tier` to return one target look, and assert the response keeps the old `fresh`/`stretch` history IDs while only `safe` gets a new history row. Add a second test where `propose_tier` raises and assert no new history row is committed. Add schema tests rejecting `refresh_tier="unknown"` and `refresh_tier` without `force_refresh`.

- [ ] **Step 2: Write the failing frontend tests**

  Extend the location contract test to call `loadDailyRecommendation({ forceRefresh: true, refreshTier: "fresh" })` and assert `refresh_tier: "fresh"`; extend the layout test with hat, scarf, coat, top, bottom, shoes and bag and assert `orderLookItems` returns that order while the source IDs remain unchanged. Assert `ScreenToday.tsx` passes `refreshTier: tier` and contains the vertical flow class.

- [ ] **Step 3: Run the focused tests and verify RED**

  Run `uv run --project backend pytest -q backend/tests/test_recommend.py -k 'refresh_tier or single_tier'` and `npm test -- --test-name-pattern='refresh|order|vertical'` from `frontend`; expected failures are missing schema/one-tier implementation and missing helper/propagation.

---

### Task 2: Implement target-tier backend refresh

**Files:**
- Modify: `backend/src/outfit_ai/schemas.py`
- Modify: `backend/src/outfit_ai/services/stylist.py`
- Modify: `backend/src/outfit_ai/services/validator.py`
- Modify: `backend/src/outfit_ai/services/recommend.py`
- Test: `backend/tests/test_recommend.py`

**Interfaces:**
- `propose_tier(..., tier: Literal["safe", "fresh", "stretch"]) -> ProposedLook`.
- `validate_look(look, candidate_categories, locked_ids=...) -> tuple[bool, str]`.
- `recommend()` returns all three cards; target card is newly recorded, non-target cards are reused.

- [ ] **Step 1: Add the request field and one-look tool schema**

  Add `refresh_tier` to `RecommendRequest`. In `stylist.py`, add a `ProposedSingleLook` wrapper with exactly one `ProposedLook`, a `propose_one_look` function schema, and `propose_tier` that reuses `stylist_context` and calls `chat_multimodal` once with a tier-specific system prompt. Reject malformed or wrong-tier tool calls with `LLMResponseError`.

- [ ] **Step 2: Extract single-look validation**

  Move the common 3–6 item, known-ID, unique-ID, locked-ID, and required-category checks into `validate_look`; have `validate_looks` call it and retain the three-tier uniqueness check. The target path must validate only its target look against candidates and the locked IDs.

- [ ] **Step 3: Add the target-tier branch before full generation**

  In `recommend()`, after profile/items and local-date resolution, find the current ordinary same-day complete set. When `request.force_refresh and request.refresh_tier` and a complete set exists, fetch current weather, build candidates, call `propose_tier` with one retry on validation correction, record only the target look using the existing recommendation-set ID so the latest row for that tier replaces the visible card, and return target card plus `_card()` values for the other two. Do not call `propose`; on any exception leave the session uncommitted and propagate the existing router error. If no current complete set exists, fall through to the existing three-look force-refresh path.

- [ ] **Step 4: Run backend focused tests and full suite**

  Run `uv run --project backend pytest -q backend/tests/test_recommend.py -k 'refresh_tier or single_tier'`, then `uv run --project backend pytest -q` and `uv run --project backend ruff check backend/src backend/tests`; all must pass.

---

### Task 3: Wire frontend target-only refresh and ordered editorial flow

**Files:**
- Modify: `frontend/src/lib/location.mjs`
- Modify: `frontend/src/lib/look-layout.mjs`
- Modify: `frontend/src/components/ScreenToday.tsx`
- Test: `frontend/scripts/location-context.test.mjs`
- Test: `frontend/scripts/api-contract.test.mjs`

**Interfaces:**
- `loadDailyRecommendation({ api, context, weather, forceRefresh, refreshTier })`.
- `orderLookItems(items)` is a pure presentation helper.

- [ ] **Step 1: Implement request propagation and target merge**

  Add `refreshTier` to `loadDailyRecommendation` and conditionally send `refresh_tier`. Update `handleSwapLook(tier)` to pass it and change the success toast to name the selected tier. Update the recommendation state merge so a swap replaces only `liveLooks[tier]`; initial load continues replacing all three. Keep the `swapInFlight` guard and independent `swappingTier` state.

- [ ] **Step 2: Implement human dressing order**

  Replace `compactLookItems` with `orderLookItems`: classify category/name using case-insensitive Chinese/English hints in the order head accessory, neck accessory, outerwear, top, bottom, shoes, other accessory, then stable-sort by rank and original index. Export the helper and leave the input array untouched.

- [ ] **Step 3: Replace the collage with a vertical flow**

  Replace `LookItems`’ two-column collage/rail with a centered `look-flow` column that renders every ordered item in a taller card (approximately 124–148px), uses `object-contain`, and adds a subtle connector between adjacent items. Keep each item button’s click handler and accessible name. Do not change the `items_worn: look.items.map(...)` feedback path.

- [ ] **Step 4: Run frontend tests, lint and build**

  Run `npm test`, `npm run lint`, and `npm run build` from `frontend`; all must pass.

---

### Task 4: Update current API/UI documentation

**Files:**
- Modify: `docs/SPEC.md`
- Modify: `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`

**Interfaces:**
- Document the exact `refresh_tier` request/response behavior and the presentation-only ordering contract.

- [ ] **Step 1: Update backend contract**

  Document `refresh_tier` as optional and valid only with `force_refresh=true`; state that a successful target refresh returns all three cards but creates a new history row only for the target tier, while failures write nothing.

- [ ] **Step 2: Update frontend integration**

  Document `loadDailyRecommendation({ refreshTier })`, target-only state merge, independent loading, and vertical head-to-foot rendering while feedback/history preserve API order.

- [ ] **Step 3: Verify docs against code**

  Run `rg -n "refresh_tier|refreshTier|orderLookItems|look-flow|force_refresh" docs/SPEC.md docs/frontend/CURRENT_FRONTEND_INTEGRATION.md frontend/src backend/src` and manually confirm every claim matches the implementation.

---

### Task 5: Runtime verification and delivery checkpoint

**Files:**
- No production code changes expected.
- Evidence: `output/` or `.playwright-cli/` only if already untracked; do not commit them.

**Interfaces:**
- Runtime behavior must match the API and UI contracts above.

- [ ] **Step 1: Verify API behavior in an isolated temporary SQLite run**

  Start the existing backend/frontend services, use a temporary test database or existing contract fixtures, and confirm normal daily load returns one stable set, target swap changes only the clicked tier, and three-look force refresh remains available only when explicitly requested.

- [ ] **Step 2: Verify mobile layout**

  At 390×844, open Today, capture a 3-item and a 5/6-item Look, confirm items read top-to-bottom and the other two cards do not change after one swap. Confirm the item buttons still open detail and feedback uses the server history ID.

- [ ] **Step 3: Run final checks and report exact status**

  Run backend tests/Ruff and frontend tests/lint/build again after any runtime fix. Report the branch, commits, checks, and any unverified external MiniMax behavior; do not push or merge.
