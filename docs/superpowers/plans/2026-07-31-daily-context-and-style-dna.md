# Daily Context and Style DNA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically use the user's date, coarse location, city, temperature and rain forecast for daily recommendations, reuse a 06:30 prepared Safe/Fresh/Stretch set, and keep Style DNA colors and tags accurate and manageable.

**Architecture:** The React client uses native geolocation and sends rounded coordinates to the existing FastAPI boundary. FastAPI remains the single owner of reverse geocoding, Open-Meteo data, prepared recommendation reuse and Style DNA curation; SQLite keeps the existing five tables, adding one nullable history context column and a backward-compatible JSON envelope inside the existing profile field.

**Tech Stack:** React 19, browser Geolocation API, Vite 6, Node test runner, FastAPI sync, Pydantic, SQLAlchemy 2.0, SQLite, httpx, pytest, Open-Meteo, Nominatim.

## Global Constraints

- Preserve the user-approved Stitch React five-screen visual baseline and current navigation.
- Do not add frontend or backend dependencies.
- Do not expose MiniMax credentials or precise location; round coordinates to three decimals before storage or transmission.
- Do not add a database table; add only nullable `outfit_history.context_json`.
- Keep existing `/api/weather`, `/api/recommend` and `/api/profile` clients backward compatible.
- Use Nominatim only through the backend, cache reverse results for 24 hours, identify the application with a non-stock `User-Agent`, and display OpenStreetMap attribution.
- Do not install a system cron or modify macOS `launchd`; provide the scheduler-safe CLI and document the exact 06:30 command.
- Update `docs/SPEC.md`, `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`, and `README.md` in the implementation commits that change their facts.

---

### Task 1: Complete weather, rain and reverse-city context

**Files:**
- Modify: `backend/src/outfit_ai/services/weather.py`
- Modify: `backend/tests/test_weather.py`
- Modify: `backend/src/outfit_ai/routers/recommend.py`
- Modify: `backend/tests/test_main.py`
- Modify: `docs/SPEC.md`

**Interfaces:**
- Produces: `get_weather(city: str | None = None, *, latitude: float | None = None, longitude: float | None = None) -> WeatherData`
- Produces: `WeatherData.city`, `local_date`, `timezone`, `precipitation`, `rain`, `precipitation_probability_max`, `precipitation_sum`, `rain_window`
- Consumes: existing `GET /api/weather` query parameters without changing their names

- [ ] **Step 1: Write failing weather parsing tests**

Add a fake `httpx.Client` response covering forecast and reverse-geocode calls:

```python
class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return self

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, forecast, reverse):
        self.forecast = forecast
        self.reverse = reverse

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url, **kwargs):
        return FakeResponse(self.reverse if "nominatim" in url else self.forecast)


def test_weather_returns_local_date_city_and_rain(monkeypatch) -> None:
    forecast = {
        "timezone": "Asia/Shanghai",
        "current": {
            "time": "2026-07-31T08:00",
            "temperature_2m": 27.1,
            "apparent_temperature": 30.2,
            "relative_humidity_2m": 81,
            "weather_code": 61,
            "wind_speed_10m": 8.0,
            "is_day": 1,
            "precipitation": 0.2,
            "rain": 0.2,
        },
        "hourly": {
            "time": ["2026-07-31T08:00", "2026-07-31T09:00", "2026-07-31T10:00"],
            "precipitation_probability": [20, 60, 70],
        },
        "daily": {
            "time": ["2026-07-31"],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [25.0],
            "precipitation_probability_max": [70],
            "precipitation_sum": [5.4],
        },
    }
    reverse = {"features": [{"properties": {"geocoding": {"city": "上海市"}}}]}
    monkeypatch.setattr(
        weather.httpx,
        "Client",
        lambda **kwargs: FakeClient(forecast, reverse),
    )

    result = weather.get_weather(latitude=31.230, longitude=121.474)

    assert result.city == "上海市"
    assert result.local_date.isoformat() == "2026-07-31"
    assert result.timezone == "Asia/Shanghai"
    assert result.precipitation_probability_max == 70
    assert result.precipitation_sum == 5.4
    assert result.rain_window == "09:00–10:00"
```

Also add `test_reverse_city_failure_does_not_fail_weather()` and assert `city is None` while temperature and rain remain available.

- [ ] **Step 2: Run the targeted tests and confirm failure**

Run:

```bash
cd backend
uv run pytest tests/test_weather.py -q
```

Expected: FAIL because `WeatherData` lacks the new fields and reverse parsing.

- [ ] **Step 3: Implement the minimal weather extension**

In `weather.py`:

- request current `precipitation,rain`;
- request hourly `precipitation_probability`;
- request daily `precipitation_probability_max,precipitation_sum`;
- keep `timezone=auto` and `forecast_days=1`;
- compute the first contiguous future block within 12 hours where probability is `>=50`;
- call `https://nominatim.openstreetmap.org/reverse` with
  `format=geocodejson`, `zoom=10`, `accept-language=zh-CN`, and
  `User-Agent: Outfit-AI/0.1`;
- catch reverse-geocode errors separately and leave `city=None`;
- cache weather for 30 minutes and reverse-city results for 24 hours using the rounded coordinate key.

The city extractor must prefer `city`, then `locality`, then `county`, then `state` from the
`properties.geocoding` object.

- [ ] **Step 4: Verify route compatibility**

Add a route assertion that `/api/weather?latitude=31.230&longitude=121.474` returns old and new keys:

```python
assert {
    "temp", "feels_like", "condition", "humidity", "wind_speed",
    "is_daytime", "temp_max", "temp_min", "city", "local_date",
    "timezone", "precipitation", "rain",
    "precipitation_probability_max", "precipitation_sum", "rain_window",
} <= response.json().keys()
```

Run:

```bash
uv run pytest tests/test_weather.py tests/test_main.py -q
uv run ruff check src tests
```

Expected: PASS.

- [ ] **Step 5: Update the backend truth source**

Update `docs/SPEC.md` with the exact new response fields, 30-minute weather cache, 24-hour
reverse-city cache, Nominatim boundary and OpenStreetMap attribution requirement.

- [ ] **Step 6: Commit**

```bash
git add backend/src/outfit_ai/services/weather.py backend/src/outfit_ai/routers/recommend.py backend/tests/test_weather.py backend/tests/test_main.py docs/SPEC.md
git commit -m "feat: add location-aware rain context"
```

---

### Task 2: Persist and curate Style DNA without adding a table

**Files:**
- Create: `backend/src/outfit_ai/services/profile_state.py`
- Create: `backend/tests/test_profile_state.py`
- Modify: `backend/src/outfit_ai/schemas.py`
- Modify: `backend/src/outfit_ai/routers/profile.py`
- Modify: `backend/src/outfit_ai/services/style_references.py`
- Modify: `backend/src/outfit_ai/services/prompt_builder.py`
- Modify: `backend/src/outfit_ai/workers/style_references.py`
- Modify: `backend/tests/test_profile.py`
- Modify: `backend/tests/test_style_references.py`
- Modify: `docs/SPEC.md`

**Interfaces:**
- Produces: `decode_profile_state(raw: str) -> dict`
- Produces: `encode_profile_state(*, learnings: list[str], recent_style_signals: list[str], style_tag_preferences: dict, last_location: dict | None) -> str`
- Produces: `active_style_keywords(keywords: list[str], preferences: dict) -> list[str]`
- Produces: Profile API fields `recent_style_signals`, `style_tag_preferences`, `last_location`
- Consumes: legacy `learned_from_feedback_json` arrays and the new version-1 envelope

- [ ] **Step 1: Write failing compatibility and filtering tests**

Create `test_profile_state.py`:

```python
def test_legacy_feedback_array_decodes_without_data_loss() -> None:
    state = decode_profile_state('["偏爱天然材质"]')
    assert state["learnings"] == ["偏爱天然材质"]
    assert state["recent_style_signals"] == []


def test_active_keywords_respect_pin_hide_and_alias() -> None:
    result = active_style_keywords(
        ["日杂休闲", "商务会议", "轻量叠穿", "复古"],
        {
            "pinned": ["复古"],
            "hidden": ["商务会议"],
            "aliases": {"日杂休闲": "日系松弛"},
        },
    )
    assert result == ["复古", "日系松弛", "轻量叠穿"]
```

Add profile route tests proving a legacy array is returned as `learned_from_feedback`, and a PUT/GET round trip preserves all three new public fields.

- [ ] **Step 2: Run targeted tests and confirm failure**

Run:

```bash
cd backend
uv run pytest tests/test_profile_state.py tests/test_profile.py -q
```

Expected: FAIL because the helpers and API fields do not exist.

- [ ] **Step 3: Implement the versioned envelope**

Create `profile_state.py` with plain functions, no classes or dependency additions. The canonical decoded shape is:

```python
{
    "version": 1,
    "learnings": [],
    "recent_style_signals": [],
    "style_tag_preferences": {"pinned": [], "hidden": [], "aliases": {}},
    "last_location": None,
}
```

Validation rules:

- deduplicate strings while preserving order;
- cap `pinned` at 3 and `recent_style_signals` at 3;
- cap the active result at 7;
- remove hidden tags after alias normalization;
- malformed data falls back to the safe empty shape;
- a top-level legacy list becomes `learnings`.

Extend `ProfileIn`/`ProfileOut` and profile serialization without changing the public
`learned_from_feedback: list[str]`.

- [ ] **Step 4: Bound Style DNA merge output**

Extend `StyleDnaMerge` with `recent_style_signals: list[str]`. Update the merge prompt and worker so:

- `style_keywords` contains at most 7 evidence-backed, reusable style concepts;
- `recent_style_signals` contains at most 3 newer signals;
- `palette` contains at most 5 names from:
  `黑色、白色、深蓝色、浅蓝色、灰色、米白色、米黄色、卡其色、棕色、绿色、红色、紫色`;
- pinned tags survive;
- hidden tags and aliases are applied after the model response;
- individual garment names, scenes and seasons do not become core keywords.

Update `stylist_context()` to send only the result of
`active_style_keywords(profile_keywords, preferences)`, recent signals and `taste_memo`.

- [ ] **Step 5: Verify the backend behavior**

Add a merge test:

```python
assert merged.style_keywords == ["日系松弛", "轻量叠穿", "复古"]
assert len(merged.recent_style_signals) <= 3
assert set(merged.palette) <= CANONICAL_PALETTE_NAMES
```

Run:

```bash
uv run pytest tests/test_profile_state.py tests/test_profile.py tests/test_style_references.py tests/test_recommend.py -q
uv run ruff check src tests
```

Expected: PASS.

- [ ] **Step 6: Update the backend truth source**

Update `docs/SPEC.md` with the envelope shape, legacy-array compatibility, new public Profile fields,
7/3/5 caps, canonical palette names and the exact inputs sent to the stylist.

- [ ] **Step 7: Commit**

```bash
git add backend/src/outfit_ai/services/profile_state.py backend/src/outfit_ai/schemas.py backend/src/outfit_ai/routers/profile.py backend/src/outfit_ai/services/style_references.py backend/src/outfit_ai/services/prompt_builder.py backend/src/outfit_ai/workers/style_references.py backend/tests/test_profile_state.py backend/tests/test_profile.py backend/tests/test_style_references.py backend/tests/test_recommend.py docs/SPEC.md
git commit -m "feat: curate manageable style DNA"
```

---

### Task 3: Store prepared recommendation context safely

**Files:**
- Modify: `backend/src/outfit_ai/models.py`
- Modify: `backend/src/outfit_ai/db.py`
- Modify: `backend/src/outfit_ai/services/history.py`
- Modify: `backend/src/outfit_ai/schemas.py`
- Modify: `backend/tests/test_models.py`
- Modify: `backend/tests/test_history.py`
- Modify: `docs/SPEC.md`

**Interfaces:**
- Produces: `OutfitHistory.context_json: str | None`
- Produces: `record_outfit(db, user_id, look, *, occasion, mood, weather_summary, temp, action="shown", context=None) -> OutfitHistory`
- Produces: `get_prepared_outfits(db: Session, user_id: str, local_date: date) -> list[OutfitHistory]`
- Consumes: old SQLite files that do not have `context_json`

- [ ] **Step 1: Write failing model, migration and history tests**

Add:

```python
def test_prepared_outfits_require_exactly_three_latest_tiers() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for tier in ("safe", "fresh", "stretch"):
            db.add(
                OutfitHistory(
                    id=tier,
                    user_id="local",
                    date=date(2026, 7, 31),
                    item_ids_json="[]",
                    pick_mode=tier,
                    action="prepared",
                )
            )
        db.commit()
        prepared = get_prepared_outfits(db, "local", date(2026, 7, 31))
        assert [row.pick_mode for row in prepared] == ["safe", "fresh", "stretch"]
        assert all(row.action == "prepared" for row in prepared)
```

Create an old SQLite `outfit_history` table without `context_json`, call the migration helper, and assert
`context_json` appears exactly once in `PRAGMA table_info(outfit_history)` after two calls.

- [ ] **Step 2: Run targeted tests and confirm failure**

Run:

```bash
cd backend
uv run pytest tests/test_models.py tests/test_history.py -q
```

Expected: FAIL because the column and prepared helpers do not exist.

- [ ] **Step 3: Add the nullable column and idempotent SQLite upgrade**

Add `context_json` to the SQLAlchemy model. In `init_db()`, after `create_all`, inspect
`outfit_history`; only for SQLite and only when the column is absent, execute:

```sql
ALTER TABLE outfit_history ADD COLUMN context_json TEXT
```

Keep the migration helper private and independently testable. Do not modify or delete existing rows.

- [ ] **Step 4: Implement prepared history helpers**

`record_outfit()` accepts `action` and serializes `context` with `ensure_ascii=False`.
`get_prepared_outfits()`:

- filters by user, local date and `action="prepared"`;
- takes the latest row per `pick_mode`;
- returns only when all three tiers exist;
- returns tiers in `safe`, `fresh`, `stretch` order;
- otherwise returns `[]`.

- [ ] **Step 5: Verify**

Run:

```bash
uv run pytest tests/test_models.py tests/test_history.py -q
uv run ruff check src tests
```

Expected: PASS.

- [ ] **Step 6: Update the backend truth source**

Update `docs/SPEC.md` with nullable `context_json`, its exact stored keys, `prepared` action semantics,
and the idempotent SQLite add-column behavior.

- [ ] **Step 7: Commit**

```bash
git add backend/src/outfit_ai/models.py backend/src/outfit_ai/db.py backend/src/outfit_ai/services/history.py backend/src/outfit_ai/schemas.py backend/tests/test_models.py backend/tests/test_history.py docs/SPEC.md
git commit -m "feat: persist prepared outfit context"
```

---

### Task 4: Reuse or regenerate daily looks and expose the 06:30 CLI

**Files:**
- Create: `backend/src/outfit_ai/precompute_daily.py`
- Create: `backend/tests/test_precompute_daily.py`
- Modify: `backend/src/outfit_ai/services/recommend.py`
- Modify: `backend/src/outfit_ai/routers/recommend.py`
- Modify: `backend/src/outfit_ai/services/profile_state.py`
- Modify: `backend/tests/test_recommend.py`
- Modify: `docs/SPEC.md`
- Modify: `README.md`

**Interfaces:**
- Produces: `recommend(db: Session, request: RecommendRequest, *, history_action: str = "shown") -> dict`
- Produces: `python -m outfit_ai.precompute_daily`
- Consumes: `RecommendRequest.force_refresh: bool = False`
- Consumes: stored `last_location` from the profile envelope

- [ ] **Step 1: Write failing reuse and invalidation tests**

Add recommendation tests that seed three `prepared` histories and assert `propose()` is not called when:

```python
request = RecommendRequest(
    latitude=31.230,
    longitude=121.474,
    force_refresh=False,
)
```

Assert regeneration occurs for each independent boundary:

- distance from prepared coordinates exceeds 20 km;
- temperature moves between `<=12`, `13–24`, and `>=25`;
- precipitation probability moves from below 50 to at least 50 or the reverse;
- `force_refresh=True`.

Use a deterministic `_haversine_km()` unit test with Shanghai-to-Suzhou greater than 20 km.

- [ ] **Step 2: Run targeted tests and confirm failure**

Run:

```bash
cd backend
uv run pytest tests/test_recommend.py tests/test_precompute_daily.py -q
```

Expected: FAIL because prepared reuse and the CLI are missing.

- [ ] **Step 3: Implement one recommendation path**

Refactor only enough to share response construction:

```python
def recommend(
    db: Session,
    request: RecommendRequest,
    *,
    history_action: str = "shown",
) -> dict:
    """Return reused prepared looks or generate and persist three valid looks."""
```

Flow:

1. fetch current weather;
2. save rounded coordinates, returned city, timezone and update time into `last_location`;
3. unless `force_refresh` or `history_action == "prepared"`, load today's prepared three;
4. reuse them only when all context thresholds pass;
5. mark reused histories `shown` and return reconstructed cards;
6. otherwise run the existing guardrail → stylist → validator chain;
7. record all three with a shared weather/location context and look-specific `weather_fit` /
   `occasion_fit`.

Do not call MiniMax when reuse succeeds.

- [ ] **Step 4: Implement the scheduler-safe CLI**

`precompute_daily.py`:

- opens `SessionLocal`;
- loads Profile and its decoded `last_location`;
- uses stored coordinates when present, otherwise `profile.city`;
- calls `require_api_key()` before generation;
- calls
  `recommend(db, RecommendRequest(city=city, latitude=latitude, longitude=longitude, force_refresh=True), history_action="prepared")`;
- prints one concise success line containing local date and city;
- exits non-zero with a concise error when no location/city or the wardrobe is insufficient.

Self-check through:

```bash
cd backend
uv run python -m outfit_ai.precompute_daily
```

The automated test monkeypatches weather and stylist calls; it must not use the real MiniMax quota.

- [ ] **Step 5: Run backend verification**

Run:

```bash
uv run pytest tests/test_recommend.py tests/test_precompute_daily.py tests/test_history.py -q
uv run pytest -q
uv run ruff check src tests
```

Expected: all tests PASS.

- [ ] **Step 6: Update current scheduling documentation**

Update `docs/SPEC.md` with `force_refresh`, reuse thresholds, prepared response reconstruction and the
CLI. Add this exact production scheduler example to `README.md`:

```cron
30 6 * * * cd /app/backend && uv run python -m outfit_ai.precompute_daily
```

State that the project does not install local cron/launchd and a sleeping computer cannot guarantee
06:30.

- [ ] **Step 7: Commit**

```bash
git add backend/src/outfit_ai/precompute_daily.py backend/src/outfit_ai/services/recommend.py backend/src/outfit_ai/routers/recommend.py backend/src/outfit_ai/services/profile_state.py backend/tests/test_precompute_daily.py backend/tests/test_recommend.py docs/SPEC.md README.md
git commit -m "feat: prepare daily looks at 0630"
```

---

### Task 5: Use native location and live weather in the Stitch frontend

**Files:**
- Create: `frontend/src/lib/location.mjs`
- Create: `frontend/scripts/location-context.test.mjs`
- Modify: `frontend/src/lib/api.mjs`
- Modify: `frontend/src/components/ScreenToday.tsx`
- Modify: `frontend/src/components/SideDrawer.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/scripts/stitch-contract.mjs`
- Modify: `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`

**Interfaces:**
- Produces: `resolveLocationContext({ geolocation, storage, now }) -> Promise<LocationContext>`
- Produces: `api.weather({ city, latitude, longitude })`
- Consumes: localStorage keys `OUTFIT_AI_LOCATION`, `OUTFIT_AI_CITY`
- Consumes: expanded backend `weather` response

- [ ] **Step 1: Write failing location fallback tests**

Create Node tests for these exact outcomes:

```javascript
test("uses rounded current coordinates when permission succeeds", async () => {
  const context = await resolveLocationContext({
    geolocation: fakeGeolocation({ latitude: 31.230416, longitude: 121.473701 }),
    storage: memoryStorage(),
    now: () => new Date("2026-07-31T08:00:00+08:00"),
  });
  assert.equal(context.latitude, 31.23);
  assert.equal(context.longitude, 121.474);
  assert.equal(context.source, "current");
});

test("falls back from denied location to cached coordinates, then manual city", async () => {
  const storage = memoryStorage({
    OUTFIT_AI_LOCATION: JSON.stringify({
      latitude: 31.23,
      longitude: 121.474,
      updatedAt: "2026-07-31T07:30:00.000Z",
    }),
    OUTFIT_AI_CITY: "上海",
  });
  const cached = await resolveLocationContext({
    geolocation: deniedGeolocation(),
    storage,
    now: () => new Date("2026-07-31T08:00:00.000Z"),
  });
  assert.equal(cached.source, "cached");
  storage.removeItem("OUTFIT_AI_LOCATION");
  const manual = await resolveLocationContext({
    geolocation: deniedGeolocation(),
    storage,
    now: () => new Date("2026-07-31T08:00:00.000Z"),
  });
  assert.deepEqual(manual, { city: "上海", source: "manual" });
});
```

Use an 8-second geolocation timeout and 24-hour cache validity.

- [ ] **Step 2: Run frontend tests and confirm failure**

Run:

```bash
cd frontend
npm test
```

Expected: FAIL because `location.mjs` and the new test command do not exist.

- [ ] **Step 3: Implement location resolution and weather API mapping**

Use only native browser APIs. `resolveLocationContext()` must:

- try current geolocation;
- persist only three-decimal coordinates and timestamp;
- use valid cached coordinates on denial/timeout;
- then use manual city;
- return `{source: "missing"}` when all are absent.

Add `api.weather()` with `URLSearchParams`, and include `force_refresh` in `api.recommend()` payload only
when true.

- [ ] **Step 4: Replace hardcoded city and weather UI**

In `ScreenToday.tsx`:

- remove `TOKYO / 24°C` and hardcoded temperature mappings;
- resolve location on mount;
- fetch `/api/weather` and show returned `local_date`, city, temperature, condition and rain summary;
- send the same location to recommendation;
- show “需要定位或选择城市” only when no fallback exists;
- retain the last successful weather with an “上次更新” label when refresh fails.

In `SideDrawer.tsx`:

- keep manual city selection as fallback, not the primary source;
- replace hardcoded temperatures with the live selected/current city label;
- add a small `© OpenStreetMap contributors` attribution link near city settings.

- [ ] **Step 5: Verify contracts and build**

Update `stitch-contract.mjs` to assert:

```javascript
assert.doesNotMatch(today, /TOKYO \\/ 24°C/);
assert.match(today, /resolveLocationContext/);
assert.match(today, /precipitation_probability_max/);
assert.match(drawer, /OpenStreetMap contributors/);
```

Run:

```bash
npm test
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 6: Update the frontend fact source**

Update `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` with native geolocation, the exact fallback
order, localStorage keys, live date/weather/rain rendering and OpenStreetMap attribution.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/location.mjs frontend/scripts/location-context.test.mjs frontend/src/lib/api.mjs frontend/src/components/ScreenToday.tsx frontend/src/components/SideDrawer.tsx frontend/package.json frontend/scripts/stitch-contract.mjs docs/frontend/CURRENT_FRONTEND_INTEGRATION.md
git commit -m "feat: use automatic location and live weather"
```

---

### Task 6: Fix the Style DNA profile UI and tag management

**Files:**
- Modify: `frontend/src/components/ScreenProfile.tsx`
- Modify: `frontend/src/lib/api.mjs`
- Modify: `frontend/scripts/api-contract.test.mjs`
- Modify: `frontend/scripts/stitch-contract.mjs`
- Modify: `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`

**Interfaces:**
- Consumes: Profile `style_keywords`, `recent_style_signals`, `style_tag_preferences`, `palette`
- Produces: Profile PUT payload preserving all existing profile fields and the three new fields

- [ ] **Step 1: Add failing palette and profile contract tests**

Export and test a pure color helper:

```javascript
assert.equal(paletteHex("深蓝色"), "#162839");
assert.equal(paletteHex("米黄色"), "#D8C49A");
assert.equal(paletteHex("浅蓝色"), "#A9C7DD");
assert.equal(paletteHex("不存在的颜色"), null);
```

Extend the Stitch contract to require:

- at most seven core keyword chips and a distinct recent-signal group;
- a “管理标签” action;
- “正在学习” / “已根据” copy;
- no `85 + ratingCount * 4` calculation.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
cd frontend
npm test
```

Expected: FAIL because palette mapping and tag management do not exist.

- [ ] **Step 3: Implement the canonical palette**

Use one exact mapping:

```javascript
export const PALETTE_HEX = {
  黑色: "#1B1C19", 白色: "#F7F5EF", 深蓝色: "#162839",
  浅蓝色: "#A9C7DD", 灰色: "#8A8D91", 米白色: "#EEE8DA",
  米黄色: "#D8C49A", 卡其色: "#B39B72", 棕色: "#7A5337",
  绿色: "#647B5B", 红色: "#9A442A", 紫色: "#75627D",
};
```

Unknown names render text with a neutral bordered swatch. Remove index-based fallback colors.

- [ ] **Step 4: Implement the in-page management overlay**

Keep the existing Profile page and add one overlay with:

- core keyword list capped at 7;
- recent signals capped at 3;
- pin toggle capped at 3;
- hide action;
- merge mode selecting exactly two tags and requiring one non-empty canonical name;
- one `saveProfile()` call after each confirmed operation;
- rollback to the prior local state and a visible error toast if saving fails.

Pinned tags display first. Hidden tags appear only inside the management overlay and never in the summary.

Replace the fake score:

```tsx
{ratingCount === 0 ? "正在学习" : `已根据 ${ratingCount} 次反馈更新`}
```

- [ ] **Step 5: Verify frontend behavior**

Run:

```bash
npm test
npm run lint
npm run build
```

Then inspect `ScreenProfile` at 390 × 844:

- “深蓝色 / 米黄色 / 浅蓝色” swatches match their labels;
- summary shows no more than 7 core tags and 3 recent signals;
- pin, hide and merge persist after closing/reopening the overlay;
- no fake percentage is visible.

- [ ] **Step 6: Update the frontend fact source**

Update `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` with the canonical color mapping, 7 core /
3 recent display caps, pin-hide-merge overlay and evidence-based learning copy.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ScreenProfile.tsx frontend/src/lib/api.mjs frontend/scripts/api-contract.test.mjs frontend/scripts/stitch-contract.mjs docs/frontend/CURRENT_FRONTEND_INTEGRATION.md
git commit -m "feat: make style DNA accurate and manageable"
```

---

### Task 7: Run end-to-end verification and audit documentation

**Files:**
- Verify: `docs/SPEC.md`
- Verify: `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`
- Verify: `README.md`

**Interfaces:**
- Verifies: expanded weather response, profile fields, `force_refresh`, `prepared` history action, `context_json`, location privacy, Nominatim attribution, and the scheduler CLI

- [ ] **Step 1: Audit the backend truth source**

Confirm `docs/SPEC.md` contains:

- the exact expanded `WeatherData` fields;
- the version-1 profile envelope and public fields;
- `outfit_history.context_json`;
- `RecommendRequest.force_refresh`;
- prepared reuse thresholds: 20 km, temperature bands, 50% rain boundary;
- `python -m outfit_ai.precompute_daily`.

- [ ] **Step 2: Audit frontend and runtime documentation**

Confirm `CURRENT_FRONTEND_INTEGRATION.md` contains native geolocation, fallback order, localStorage
keys, live weather/rain display, Style DNA management, and the removal of the fake match score.

Confirm `README.md` contains:

```cron
30 6 * * * cd /app/backend && uv run python -m outfit_ai.precompute_daily
```

It must also state that local scheduling is not installed automatically and sleeping computers cannot
guarantee 06:30.

- [ ] **Step 3: Run full automated verification**

Run:

```bash
cd backend
uv run ruff check src tests
uv run pytest -q

cd ../frontend
npm test
npm run lint
npm run build
```

Expected: every command exits 0.

- [ ] **Step 4: Run mobile interaction verification**

With backend and frontend running, use a 390 × 844 mobile viewport and verify:

1. location allowed → current city/date/temp/rain appears;
2. location denied → cached location, then manual city fallback;
3. no fallback → explicit location/city prompt and no Tokyo;
4. prepared result → three cards load without another MiniMax call;
5. changed rain boundary → one regeneration;
6. Profile color, tag pin, hide, merge and reload persistence.

Record any environment limitation separately; do not claim a real 06:30 execution unless a scheduler actually ran it.

- [ ] **Step 5: Confirm a clean scoped diff**

```bash
git status --short
```

Expected: only the user's pre-existing untracked `.playwright-cli/`, prior plan, `images/`, and
`output/` remain; no implementation or current-document changes are uncommitted.
