# Wardrobe Coverage Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every confirmed, season-eligible wardrobe item available to the stylist, use exposure history to drive Fresh/Stretch coverage, enforce the three-tier boundaries, and add manual season/thickness labels with AND-across-groups wardrobe filtering.

**Architecture:** Keep the existing `guardrail → stylist → validator` pipeline and SQLite history as the only usage fact source. The guardrail will filter only readiness and season eligibility, compute deterministic low-exposure targets, and pass usage context to MiniMax-M3; the validator will reject exact recent Looks, missing Fresh/Stretch targets, and avoidable core-item overlap. The React wardrobe page will use a small pure filter helper so the combination semantics are independently testable without adding a dependency.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy sync, SQLite, pytest; React 19, TypeScript, Vite, Tailwind CSS, Node test scripts.

**Spec:** `docs/superpowers/specs/2026-09-03-wardrobe-coverage-and-filter-design.md`

## Global Constraints

- Use existing `wardrobe_items.seasons_json` and `tags_json`; do not add a table, column, dependency, or numeric weight-learning store.
- Manual season and thickness values submitted after AI recognition are the active values for later filtering and recommendation.
- Season is the hard candidate boundary; thickness is weather context, not a universal cross-category hard filter.
- The UI stores spring/summer/autumn/winter as multi-select values; “四季” is a select-all shortcut, not a fifth stored value.
- Within one wardrobe filter group use OR; across category, season, and thickness groups use AND.
- Safe remains stable; Fresh must include one low-exposure target; Stretch must include a different low-exposure target and a clearer stylistic change.
- Locked items remain mandatory only when ready, confirmed, and season-eligible; locks override coverage and tier-overlap checks but not season eligibility.
- Never write MiniMax credentials to frontend code, docs, logs, or commits.
- Update `docs/SPEC.md` and `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` in the same change as the code.

### Task 1: Add history-derived exposure facts and deterministic candidate selection

**Files:**
- Modify: `backend/src/outfit_ai/services/history.py`
- Modify: `backend/src/outfit_ai/services/guardrail.py`
- Modify: `backend/tests/test_history.py`
- Modify: `backend/tests/test_guardrail.py`

**Interfaces:**
- Produce `get_item_usage_stats(db, user_id, *, local_date=None, lookback_days=30) -> dict[str, dict[str, object]]`, where each value contains `count`, `last_seen`, and `recent` and excludes rows whose `action == "prepared"`.
- Produce `get_recent_look_keys(db, user_id, *, local_date, lookback_days=30) -> set[tuple[str, ...]]`, excluding prepared rows and normalizing each item set by sorted IDs.
- Change `get_recent_item_ids(db, user_id, *, limit=3, skip_shoes=False) -> set[str]` so shoes follow the same recent-item behavior as every other category.
- Change `filter_candidates(items, *, season, locked_ids, recent_item_ids, usage_stats=None, coverage_target_ids=None, limit=15)` to return every ready, confirmed, season-eligible item, sorted by lock status, target status, exposure count, last-seen date, and stable ID; `limit` remains accepted for compatibility but no longer truncates.
- Produce `select_coverage_targets(candidates, usage_stats, *, locked_ids=None, occupied_ids=None, count=2) -> list[str]`, selecting distinct lowest-exposure eligible IDs and preferring different canonical categories when possible.

- [ ] **Step 1: Write the failing history tests.**

```python
def test_usage_stats_ignore_prepared_rows_and_include_shoes() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            OutfitHistory(id="prepared", user_id="local", item_ids_json='["top-1"]', pick_mode="safe", action="prepared"),
            OutfitHistory(id="visible", user_id="local", item_ids_json='["top-1", "shoe-1"]', pick_mode="fresh", action="shown", date=date(2026, 8, 1)),
        ])
        db.commit()
        stats = get_item_usage_stats(db, "local", local_date=date(2026, 8, 1))
        assert stats["top-1"]["count"] == 1
        assert stats["shoe-1"]["count"] == 1
        assert get_recent_item_ids(db, "local", skip_shoes=False) == {"top-1", "shoe-1"}

def test_recent_look_keys_cover_the_last_thirty_days_only() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            OutfitHistory(id="inside", user_id="local", date=date(2026, 8, 1), item_ids_json='["b", "a"]', pick_mode="safe", action="shown"),
            OutfitHistory(id="outside", user_id="local", date=date(2026, 6, 30), item_ids_json='["d", "c"]', pick_mode="safe", action="shown"),
        ])
        db.commit()
        assert get_recent_look_keys(db, "local", local_date=date(2026, 8, 1)) == {("a", "b")}
```

- [ ] **Step 2: Run the history tests and verify the expected failure.**

Run: `cd backend && uv run pytest tests/test_history.py -q`

Expected: FAIL because the new history helpers do not exist and the default recent-item behavior still omits shoes.

- [ ] **Step 3: Implement the minimal history helpers.**

Use the existing SQLAlchemy query style and `_context` helper. Query only this user, ignore `action == "prepared"`, parse malformed `item_ids_json` as an empty list, and use `row.date` for `last_seen`. Keep `prune_temporary_history()` for backward compatibility but do not call it from recommendation code.

- [ ] **Step 4: Run the history tests and verify they pass.**

Run: `cd backend && uv run pytest tests/test_history.py -q`

Expected: PASS.

- [ ] **Step 5: Write failing candidate-selection tests.**

```python
def test_candidate_selection_returns_all_season_eligible_items_without_random_cap() -> None:
    items = [_item(f"top-{index}", "top", '["summer"]') for index in range(20)]
    result = filter_candidates(
        items, season="summer", locked_ids=set(), recent_item_ids=set(), limit=3
    )
    assert len(result) == 20

def test_candidate_selection_prioritizes_unseen_items_and_targets() -> None:
    items = [_item("often", "top", '["summer"]'), _item("seldom", "top", '["summer"]'), _item("unseen", "top", '["summer"]')]
    result = filter_candidates(
        items,
        season="summer",
        locked_ids=set(),
        recent_item_ids=set(),
        usage_stats={"often": {"count": 8, "last_seen": "2026-08-01"}, "seldom": {"count": 1, "last_seen": "2026-08-02"}},
        coverage_target_ids={"unseen"},
    )
    assert [item.id for item in result] == ["unseen", "seldom", "often"]

def test_candidate_selection_treats_empty_or_bad_seasons_as_unrestricted() -> None:
    items = [_item("empty", "top", "[]"), _item("bad", "top", "not-json")]
    result = filter_candidates(items, season="summer", locked_ids=set(), recent_item_ids=set())
    assert {item.id for item in result} == {"empty", "bad"}
```

- [ ] **Step 6: Run the candidate tests and verify the expected failure.**

Run: `cd backend && uv run pytest tests/test_guardrail.py -q`

Expected: FAIL because the current function truncates, ignores exposure facts, and raises on malformed season JSON.

- [ ] **Step 7: Implement deterministic guardrail selection.**

Add safe JSON-list decoding, preserve the existing `spring_autumn` behavior, require readiness and confirmation, exclude only wrong-season items unless the season list is empty, and sort all accepted candidates without sampling. Locked items may sort first only after passing readiness and season checks. Implement target selection with stable tie-breaking and no random module.

- [ ] **Step 8: Run guardrail and history tests.**

Run: `cd backend && uv run pytest tests/test_guardrail.py tests/test_history.py -q`

Expected: PASS, with the old tests updated to the new all-category recent-item and no-cap contract.

- [ ] **Step 9: Commit the history and guardrail slice.**

```bash
git add backend/src/outfit_ai/services/history.py backend/src/outfit_ai/services/guardrail.py backend/tests/test_history.py backend/tests/test_guardrail.py
git commit -m "feat: select wardrobe candidates by coverage"
```

### Task 2: Enforce coverage targets, recent Look rejection, and three-tier prompt boundaries

**Files:**
- Modify: `backend/src/outfit_ai/services/prompt_builder.py`
- Modify: `backend/src/outfit_ai/services/stylist.py`
- Modify: `backend/src/outfit_ai/services/validator.py`
- Modify: `backend/src/outfit_ai/services/recommend.py`
- Modify: `backend/tests/test_validation.py`
- Modify: `backend/tests/test_guardrail.py`
- Modify: `backend/tests/test_recommend.py`
- Modify: `backend/tests/test_llm.py`

**Interfaces:**
- Extend `stylist_system(locked_ids, tier=None, coverage_targets=None)` with concrete Safe/Fresh/Stretch instructions and locked/season boundaries.
- Extend `stylist_context(candidates, profile, weather, occasion, mood, recent_looks, *, references=None, style_note=None, season=None, scene=None, usage_stats=None, coverage_targets=None)` to serialize per-item `usage_count`, `last_seen`, `unseen`, and target markers.
- Extend `propose()` and `propose_tier()` with optional `usage_stats` and `coverage_targets` keyword arguments, preserving existing callers that omit them.
- Extend `validate_looks(looks, candidate_categories, *, locked_ids=None, coverage_targets=None, recent_look_keys=None)` and `validate_look(look, candidate_categories, *, locked_ids=None, coverage_target=None)` while keeping existing return type `(bool, str)`.

- [ ] **Step 1: Write failing validator tests.**

```python
def test_validator_requires_fresh_and_stretch_coverage_targets() -> None:
    categories = {"top-1": "top", "top-2": "top", "top-3": "top", "bottom-1": "bottom", "bottom-2": "bottom", "bottom-3": "bottom", "shoes-1": "shoes", "shoes-2": "shoes", "shoes-3": "shoes"}
    looks = [_look("safe", ["top-1", "bottom-1", "shoes-1"]), _look("fresh", ["top-2", "bottom-2", "shoes-2"]), _look("stretch", ["top-3", "bottom-3", "shoes-3"])]
    ok, error = validate_looks(
        looks,
        categories,
        coverage_targets={"fresh": "unused-top", "stretch": "unused-bottom"},
    )
    assert not ok
    assert "unused-top" in error or "unused-bottom" in error

def test_validator_rejects_recent_exact_look() -> None:
    categories = {"top-1": "top", "top-2": "top", "top-3": "top", "bottom-1": "bottom", "bottom-2": "bottom", "bottom-3": "bottom", "shoes-1": "shoes", "shoes-2": "shoes", "shoes-3": "shoes"}
    looks = [_look("safe", ["top-1", "bottom-1", "shoes-1"]), _look("fresh", ["top-2", "bottom-2", "shoes-2"]), _look("stretch", ["top-3", "bottom-3", "shoes-3"])]
    recent = {tuple(sorted(looks[0].item_ids))}
    ok, error = validate_looks(looks, categories, recent_look_keys=recent)
    assert not ok
    assert "30" in error

def test_validator_rejects_avoidable_core_overlap_when_three_candidates_exist() -> None:
    categories = {"top-1": "top", "top-2": "top", "top-3": "top", "bottom-1": "bottom", "bottom-2": "bottom", "bottom-3": "bottom", "shoes-1": "shoes", "shoes-2": "shoes", "shoes-3": "shoes"}
    looks = [_look("safe", ["top-1", "bottom-1", "shoes-1"]), _look("fresh", ["top-1", "bottom-2", "shoes-2"]), _look("stretch", ["top-3", "bottom-3", "shoes-3"])]
    ok, error = validate_looks(looks, categories)
    assert not ok
    assert "上装" in error
```

- [ ] **Step 2: Run validator tests and verify the expected failure.**

Run: `cd backend && uv run pytest tests/test_validation.py -q`

Expected: FAIL because validator currently checks only legality and exact set inequality.

- [ ] **Step 3: Implement validator rules.**

Require the target ID in its named tier, reject any sorted item tuple in `recent_look_keys`, and compare top/bottom/shoes IDs pairwise only when the candidate category counts are at least three. Ignore shared locked IDs in the overlap check. Return a concise correction string for the stylist retry.

- [ ] **Step 4: Run validator tests and verify they pass.**

Run: `cd backend && uv run pytest tests/test_validation.py tests/test_guardrail.py -q`

Expected: PASS.

- [ ] **Step 5: Write failing prompt tests.**

```python
def test_stylist_prompt_defines_three_tier_boundaries_and_usage_context() -> None:
    prompt = stylist_system(set(), coverage_targets={"fresh": "a", "stretch": "b"})
    assert "Safe" in prompt and "Fresh" in prompt and "Stretch" in prompt
    assert "低曝光" in prompt
    assert "a" in prompt and "b" in prompt
```

- [ ] **Step 6: Run prompt tests and verify the expected failure.**

Run: `cd backend && uv run pytest tests/test_guardrail.py tests/test_llm.py -q`

Expected: FAIL because the system prompt has no concrete tier definitions and the context has no exposure fields.

- [ ] **Step 7: Implement prompt and stylist context changes.**

Keep JSON as the transport format. Add usage facts to each item and explicitly state: Safe is weather-appropriate and familiar; Fresh must use the Fresh target and change one major style dimension; Stretch must use the other target and make a clearer color, silhouette, or formula change. Tell the model not to bypass season eligibility and to explain the difference concretely.

- [ ] **Step 8: Run prompt/LLM tests.**

Run: `cd backend && uv run pytest tests/test_guardrail.py tests/test_llm.py -q`

Expected: PASS.

- [ ] **Step 9: Write failing recommendation integration tests.**

```python
def test_recommend_passes_usage_targets_and_recent_looks_to_stylist(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    captured = {}
    def fake_propose(*args, **kwargs):
        captured.update(kwargs)
        return _looks()
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(recommend_service, "propose", fake_propose)
    with Session(engine) as db:
        db.add_all(_recommendation_items())
        db.commit()
        recommend_service.recommend(db, RecommendRequest(city="上海"))
    assert isinstance(captured["usage_stats"], dict)
    assert set(captured["coverage_targets"]) == {"fresh", "stretch"}

def test_recommend_does_not_prune_old_ordinary_history(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(recommend_service, "propose", lambda *args, **kwargs: _looks())
    with Session(engine) as db:
        db.add_all(_recommendation_items())
        db.add(OutfitHistory(id="old-history", user_id="local", date=date(2026, 1, 1), item_ids_json='["top-1"]', pick_mode="safe", action="shown"))
        db.commit()
        recommend_service.recommend(db, RecommendRequest(city="上海"))
        assert db.get(OutfitHistory, "old-history") is not None
```

- [ ] **Step 10: Run integration tests and verify the expected failure.**

Run: `cd backend && uv run pytest tests/test_recommend.py -q`

Expected: FAIL because recommendation currently does not compute targets/stats, skips shoes in recent IDs, and calls temporary-history pruning after success.

- [ ] **Step 11: Wire the recommendation service.**

Compute `usage_stats`, recent IDs with `skip_shoes=False`, `recent_look_keys` for the request local date, and two coverage targets after candidate filtering. Pass all of them into `propose()` and `validate_looks()`. For single-tier refresh, exclude the other two current card item IDs when selecting the target and validate only the requested tier against its target. Remove both `prune_temporary_history()` calls. Keep same-day reuse and prepared reuse behavior unchanged.

- [ ] **Step 12: Run all backend tests.**

Run: `cd backend && uv run pytest -q`

Expected: PASS.

- [ ] **Step 13: Commit the recommendation slice.**

```bash
git add backend/src/outfit_ai/services/prompt_builder.py backend/src/outfit_ai/services/stylist.py backend/src/outfit_ai/services/validator.py backend/src/outfit_ai/services/recommend.py backend/tests/test_validation.py backend/tests/test_guardrail.py backend/tests/test_recommend.py backend/tests/test_llm.py
git commit -m "feat: improve tier coverage and repeat guards"
```

### Task 3: Add manual season/thickness labels and combination filtering to the wardrobe UI

**Files:**
- Create: `frontend/src/lib/wardrobe-filters.mjs`
- Create: `frontend/scripts/wardrobe-filters.test.mjs`
- Modify: `frontend/src/components/ScreenWardrobe.tsx`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/scripts/stitch-contract.mjs`

**Interfaces:**
- Export `SEASON_OPTIONS = ["春", "夏", "秋", "冬"]` and `THICKNESS_OPTIONS = ["轻薄", "适中", "厚实"]` from `wardrobe-filters.mjs`.
- Export `filterWardrobeItems(items, { category, seasons, thicknesses })`, with same-group OR and cross-group AND; an empty selected group does not filter.
- Export `toggleFilterValue(values, value, allValues)`, where selecting “四季” maps to all four seasons and toggling all four again clears the season filter.

- [ ] **Step 1: Write failing pure-helper tests.**

```javascript
import assert from "node:assert/strict";
import { filterWardrobeItems, toggleFilterValue } from "../src/lib/wardrobe-filters.mjs";

const items = [
  { id: "a", category: "上装", seasons: ["春", "夏"], thickness: "轻薄" },
  { id: "b", category: "下装", seasons: ["夏"], thickness: "适中" },
  { id: "c", category: "下装", seasons: ["秋"], thickness: "厚实" },
];

assert.deepEqual(
  filterWardrobeItems(items, { category: "下装", seasons: ["春", "夏"], thicknesses: ["轻薄", "适中"] }).map((item) => item.id),
  ["b"],
);
assert.deepEqual(toggleFilterValue([], "四季", ["春", "夏", "秋", "冬"]), ["春", "夏", "秋", "冬"]);
assert.deepEqual(toggleFilterValue(["春", "夏", "秋", "冬"], "夏", ["春", "夏", "秋", "冬"]), ["春", "秋", "冬"]);
```

- [ ] **Step 2: Run the helper test and verify the expected failure.**

Run: `cd frontend && node scripts/wardrobe-filters.test.mjs`

Expected: FAIL because the helper file does not exist.

- [ ] **Step 3: Implement the pure helper.**

Match a selected season when an item has any selected season; match a selected thickness only when the item has one of the selected thickness values; preserve item order; treat “全部” and empty groups as unrestricted. Unknown or empty item labels do not match an active label filter.

- [ ] **Step 4: Run the helper test and verify it passes.**

Run: `cd frontend && node scripts/wardrobe-filters.test.mjs`

Expected: PASS.

- [ ] **Step 5: Write the UI changes.**

Replace the text-based season editor with four selectable season chips plus a “四季” shortcut. Keep thickness as a mutually exclusive chip group with “未设置”. Add season and thickness filter chip rows below the category navigation, show an active-filter count and “清除筛选”, and display the explicit no-results state. Use `filterWardrobeItems()` for the grid and current swipe list. Reset category, season, and thickness filters when the page mounts; keep batch select-all scoped to the filtered list.

- [ ] **Step 6: Run the frontend contract test and TypeScript build.**

Run: `cd frontend && npm test && npm run lint && npm run build`

Expected: PASS; the contract must include all four season labels, all three thickness labels, the combination helper, active-filter clearing, and no-results copy.

- [ ] **Step 7: Commit the wardrobe UI slice.**

```bash
git add frontend/src/lib/wardrobe-filters.mjs frontend/scripts/wardrobe-filters.test.mjs frontend/src/components/ScreenWardrobe.tsx frontend/src/types.ts frontend/scripts/stitch-contract.mjs
git commit -m "feat: add wardrobe season and thickness filters"
```

### Task 4: Synchronize current documentation and run release verification

**Files:**
- Modify: `docs/SPEC.md`
- Modify: `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`
- Modify: `README.md` only if the verified runtime or command changes

- [ ] **Step 1: Update backend current spec.**

Replace the old candidate description that says recent shoes are skipped, candidates are capped at 12–15, ordinary history is pruned, and validation only checks distinct sets. Document all-category manual labels, the season/thickness semantics, usage facts from history, coverage targets, exact 30-day Look rejection, and conditional core-item no-overlap.

- [ ] **Step 2: Update frontend current integration.**

Document the three filter groups, OR/AND semantics, “四季” shortcut, thickness override behavior, no-results state, and reset-on-reentry behavior.

- [ ] **Step 3: Run formatting and full verification.**

Run:

```bash
cd backend && uv run ruff check src tests && uv run pytest -q
cd ../frontend && npm test && npm run lint && npm run build
git diff --check
```

Expected: all commands pass and no secrets or unrelated files are changed.

- [ ] **Step 4: Review the final diff and commit documentation.**

```bash
git status --short
git diff --stat
git add docs/SPEC.md docs/frontend/CURRENT_FRONTEND_INTEGRATION.md
git commit -m "docs: document wardrobe coverage recommendation rules"
```

- [ ] **Step 5: Report verification evidence.**

Report the commit IDs, backend/frontend checks, and the exact behavior now covered. Do not claim cloud deployment or mobile-device verification unless separately authorized and completed.
