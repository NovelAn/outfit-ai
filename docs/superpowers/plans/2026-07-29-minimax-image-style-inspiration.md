# MiniMax Image and Style Inspiration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MiniMax VLM garment/reference analysis, local background removal, a persistent long-term style reference library, Style-DNA-driven real-wardrobe recommendations, and an independent `image-01` inspiration mode.

**Architecture:** Keep MiniMax-M3 as the text model. Add one shared HTTP boundary for Token Plan VLM and `image-01`, with environment credentials taking priority over read-only mmx config fallback. Store style references in one new SQLite table, process uploads through existing `BackgroundTasks`, and expose both product modes inside the existing recommendation page.

**Tech Stack:** Python 3.11+, FastAPI sync, SQLAlchemy 2.0, SQLite, Pydantic 2, httpx, Pillow, `rembg[cpu]>=2.0.77,<3`, uni-app, Vue 3, TypeScript, Vite, pytest, Playwright CLI.

## Global Constraints

- Main text model remains `MiniMax-M3`.
- Image understanding uses `POST /v1/coding_plan/vlm`; image generation uses `POST /v1/image_generation` with `image-01`.
- Credential priority is `MINIMAX_API_KEY` → `MMX_CONFIG_DIR/config.json` → `~/.mmx/config.json`.
- Never log, persist, return, or commit the API key; never modify `.env` or mmx config.
- Wardrobe photos keep the original and gain a deterministic transparent `.nobg.png`; reference Looks keep the complete original image.
- VLM and image generation do not retry automatically; retries require a visible user action.
- Recommendations never prioritize utilization or wear count; style matching dominates and randomization only varies eligible candidates.
- Inspiration images do not use wardrobe item IDs and do not enter outfit history.
- Keep the existing four-tab mobile information architecture and Warm Editorial design tokens.
- Do not touch unrelated untracked `images/` or `output/playwright/` artifacts.

---

## File Map

**Create**

- `backend/src/outfit_ai/services/minimax.py` — credentials, endpoint normalization, VLM and image HTTP calls.
- `backend/src/outfit_ai/services/background.py` — deterministic no-background path and local `rembg` processing.
- `backend/src/outfit_ai/workers/style_reference.py` — reference-image state machine and Style DNA merge.
- `backend/src/outfit_ai/routers/style_references.py` — long-term reference upload/list/status/retry API.
- `backend/src/outfit_ai/services/inspiration.py` — M3 prompt construction, `image-01` call, output validation/save.
- `backend/src/outfit_ai/routers/inspiration.py` — independent inspiration generation API.
- `backend/tests/test_minimax.py`
- `backend/tests/test_background.py`
- `backend/tests/test_style_references.py`
- `backend/tests/test_inspiration.py`

**Modify**

- `backend/pyproject.toml`, `backend/uv.lock` — add CPU rembg dependency.
- `backend/src/outfit_ai/config.py` — image/VLM timeout and config path support without storing secrets.
- `backend/src/outfit_ai/models.py` — add `StyleReference`.
- `backend/src/outfit_ai/schemas.py` — reference analysis, reference output, expanded recommendation and inspiration request types.
- `backend/src/outfit_ai/services/llm.py` — use shared credential resolution for M3.
- `backend/src/outfit_ai/services/vision.py` — replace M3 multimodal tool call with VLM JSON extraction.
- `backend/src/outfit_ai/services/storage.py` — delete original plus deterministic derived image.
- `backend/src/outfit_ai/workers/analysis.py` — rembg-before-VLM state machine.
- `backend/src/outfit_ai/services/prompt_builder.py` — reference-aware text contexts and image-generation prompt input.
- `backend/src/outfit_ai/services/taste_memo.py` — merge one validated style reference into long-term Style DNA.
- `backend/src/outfit_ai/services/guardrail.py` — random eligible candidate cap without utilization ranking.
- `backend/src/outfit_ai/services/stylist.py` — remove image blocks and accept reference analyses.
- `backend/src/outfit_ai/services/recommend.py` — resolve reference IDs, season override and processed image URLs.
- `backend/src/outfit_ai/routers/wardrobe.py` — processed-image response and collage paths.
- `backend/src/outfit_ai/routers/recommend.py` — new request errors.
- `backend/src/outfit_ai/main.py` — register the two new routers.
- `backend/tests/test_llm.py`
- `backend/tests/test_models.py`
- `backend/tests/test_vision.py`
- `backend/tests/test_wardrobe_flow.py`
- `backend/tests/test_guardrail.py`
- `backend/tests/test_recommend.py`
- `frontend/src/api/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/pages/recommend/index.vue`
- `frontend/src/pages/wardrobe/index.vue`
- `CLAUDE.md`, `README.md`, `.env.example`, `docs/SPEC.md`, `docs/design.md`

---

### Task 1: MiniMax Credential and Image API Boundary

**Files:**

- Create: `backend/src/outfit_ai/services/minimax.py`
- Create: `backend/tests/test_minimax.py`
- Modify: `backend/src/outfit_ai/config.py`
- Modify: `backend/src/outfit_ai/services/llm.py`
- Modify: `backend/tests/test_llm.py`

**Interfaces:**

- Produces: `credentials() -> tuple[str, str]`
- Produces: `describe_image(image_url: str, prompt: str) -> str`
- Produces: `generate_image(prompt: str, aspect_ratio: str = "3:4") -> bytes`
- Produces: `MiniMaxUnavailableError` and `MiniMaxResponseError`

- [ ] **Step 1: Write credential precedence and redaction tests**

```python
def test_credentials_prefer_environment_setting(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "minimax_api_key", "env-key")
    (tmp_path / "config.json").write_text(
        '{"api_key":"file-key","region":"cn"}', encoding="utf-8"
    )
    monkeypatch.setenv("MMX_CONFIG_DIR", str(tmp_path))

    key, base_url = minimax.credentials()

    assert key == "env-key"
    assert base_url == "https://api.minimaxi.com"


def test_provider_error_does_not_expose_key(monkeypatch):
    monkeypatch.setattr(minimax, "credentials", lambda: ("secret-key", "https://example.test"))
    monkeypatch.setattr(
        minimax.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("secret-key")),
    )

    with pytest.raises(minimax.MiniMaxUnavailableError) as error:
        minimax.describe_image("data:image/png;base64,AA==", "describe")

    assert "secret-key" not in str(error.value)
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
cd backend
uv run pytest tests/test_minimax.py tests/test_llm.py -q
```

Expected: collection/import failure because `services.minimax` and shared credential resolution do not exist.

- [ ] **Step 3: Implement the minimal shared boundary**

Implement these exact behaviors:

```python
def credentials() -> tuple[str, str]:
    if settings.minimax_api_key:
        return settings.minimax_api_key, _base_url(settings.minimax_base_url)
    config_dir = Path(os.environ.get("MMX_CONFIG_DIR", Path.home() / ".mmx"))
    try:
        payload = json.loads((config_dir / "config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    key = payload.get("api_key")
    if not isinstance(key, str) or not key:
        raise MiniMaxUnavailableError("未配置 MiniMax API Key")
    region = payload.get("region", "cn")
    base_url = payload.get("base_url") or (
        "https://api.minimaxi.com" if region == "cn" else "https://api.minimax.io"
    )
    return key, _base_url(base_url)
```

Use one internal `_post(path, payload)` with `Authorization: Bearer ...`, `httpx.post`, a finite timeout, `raise_for_status`, `base_resp.status_code` validation, and provider-detail redaction. `describe_image` returns validated string `content`. `generate_image` requests one base64 image and returns decoded bytes. Do not add a client class or retry layer.

Change `llm.require_api_key()` and `llm.get_client()` to call `credentials()` so M3 gains the same fallback without changing its model or protocol.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_minimax.py tests/test_llm.py -q
uv run ruff check src/outfit_ai/services/minimax.py src/outfit_ai/services/llm.py tests/test_minimax.py
```

Expected: all selected tests pass and ruff reports no errors.

- [ ] **Step 5: Commit**

```bash
git add backend/src/outfit_ai/config.py backend/src/outfit_ai/services/minimax.py backend/src/outfit_ai/services/llm.py backend/tests/test_minimax.py backend/tests/test_llm.py
git commit -m "feat: add MiniMax image API boundary"
```

---

### Task 2: Local Background Removal and Wardrobe Processing

**Files:**

- Create: `backend/src/outfit_ai/services/background.py`
- Create: `backend/tests/test_background.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `backend/src/outfit_ai/services/vision.py`
- Modify: `backend/src/outfit_ai/services/storage.py`
- Modify: `backend/src/outfit_ai/workers/analysis.py`
- Modify: `backend/src/outfit_ai/routers/wardrobe.py`
- Modify: `backend/tests/test_vision.py`
- Modify: `backend/tests/test_wardrobe_flow.py`

**Interfaces:**

- Consumes: `describe_image(image_url, prompt) -> str`
- Produces: `derived_path(path: str | Path) -> Path`
- Produces: `display_path(path: str | Path) -> Path`
- Produces: `remove_background(path: str | Path) -> Path`
- Changes: `vision.extract(path) -> tuple[ClothingAttributes, str]` now uses VLM content JSON.

- [ ] **Step 1: Write failing derived-image and processing-order tests**

```python
def test_remove_background_writes_transparent_derived_png(monkeypatch, tmp_path):
    source = tmp_path / "coat.jpg"
    Image.new("RGB", (8, 8), "white").save(source)
    transparent = BytesIO()
    Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(transparent, "PNG")
    monkeypatch.setattr(background, "remove", lambda data: transparent.getvalue())

    result = background.remove_background(source)

    assert result == tmp_path / "coat.nobg.png"
    with Image.open(result) as image:
        assert image.mode == "RGBA"


def test_analysis_removes_background_before_calling_vlm(monkeypatch, ...):
    calls = []
    monkeypatch.setattr(analysis, "remove_background", lambda path: calls.append("rembg"))
    monkeypatch.setattr(
        analysis,
        "extract",
        lambda path: (calls.append("vlm") or (attributes, '{"ok":true}')),
    )

    analysis.analyze_item(item.id)

    assert calls == ["rembg", "vlm"]
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
cd backend
uv run pytest tests/test_background.py tests/test_vision.py tests/test_wardrobe_flow.py -q
```

Expected: failures because `services.background` is absent and wardrobe analysis does not call it.

- [ ] **Step 3: Add rembg and implement the smallest safe file flow**

Add:

```toml
"rembg[cpu]>=2.0.77,<3",
```

Run `uv lock` to update the existing lockfile. In `background.py`, use `rembg.remove` on bytes, validate the returned bytes with Pillow, write to a sibling temporary file, then atomically `replace()` it as `<stem>.nobg.png`. If the final file already exists and Pillow validates it as RGBA, return it without running rembg again.

Change `vision.extract` to:

1. encode the original image as a data URL;
2. call `describe_image` with `ClothingAttributes.model_json_schema()` in the prompt;
3. strip an optional Markdown JSON fence;
4. call `ClothingAttributes.model_validate_json`;
5. return validated attributes and the raw VLM content.

Change the worker to run `remove_background` before `extract`. Update wardrobe response/collage functions to use `display_path`; pending/failed previews fall back to the original. Update deletion to remove both files.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_background.py tests/test_vision.py tests/test_wardrobe_flow.py tests/test_collage.py -q
uv run ruff check src/outfit_ai/services/background.py src/outfit_ai/services/vision.py src/outfit_ai/workers/analysis.py
```

Expected: selected tests pass and ruff is clean.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/src/outfit_ai/services/background.py backend/src/outfit_ai/services/vision.py backend/src/outfit_ai/services/storage.py backend/src/outfit_ai/workers/analysis.py backend/src/outfit_ai/routers/wardrobe.py backend/tests/test_background.py backend/tests/test_vision.py backend/tests/test_wardrobe_flow.py
git commit -m "feat: remove wardrobe photo backgrounds locally"
```

---

### Task 3: Persistent Long-Term Style Reference Model

**Files:**

- Modify: `backend/src/outfit_ai/models.py`
- Modify: `backend/src/outfit_ai/schemas.py`
- Modify: `backend/tests/test_models.py`
- Create: `backend/tests/test_style_references.py`

**Interfaces:**

- Produces: SQLAlchemy `StyleReference`
- Produces: Pydantic `StyleReferenceAnalysis`
- Produces: Pydantic `StyleReferenceOut`
- Produces: expanded `RecommendRequest`
- Produces: `InspirationRequest`

- [ ] **Step 1: Write failing schema and model tests**

```python
def test_style_reference_table_persists_analysis():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        row = StyleReference(
            id="ref-1",
            user_id="local",
            image_path="/tmp/look.jpg",
            status="ready",
            analysis_json='{"style_keywords":["Ivy"]}',
        )
        db.add(row)
        db.commit()
        assert db.get(StyleReference, "ref-1").status == "ready"


def test_reference_analysis_requires_style_evidence():
    with pytest.raises(ValidationError):
        StyleReferenceAnalysis()
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
cd backend
uv run pytest tests/test_models.py tests/test_style_references.py -q
```

Expected: import failures for the new model and schemas.

- [ ] **Step 3: Add the model and exact request schemas**

Add `StyleReference` with the fields and indexes from the approved design. Add:

```python
class StyleReferenceAnalysis(BaseModel):
    style_keywords: list[str] = Field(min_length=1)
    palette: list[str] = Field(default_factory=list)
    silhouettes: list[str] = Field(default_factory=list)
    layering: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    seasons: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    notable_elements: list[str] = Field(default_factory=list)


class InspirationRequest(BaseModel):
    reference_ids: list[str] = Field(default_factory=list, max_length=6)
    style_note: str = Field(default="", max_length=1000)
    season: str
    scene: str = Field(min_length=1, max_length=100)
```

Extend `RecommendRequest` with `reference_ids`, `style_note`, `season`, and `scene`, while accepting existing `occasion` clients during the transition. Do not modify existing database columns.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_models.py tests/test_style_references.py -q
uv run ruff check src/outfit_ai/models.py src/outfit_ai/schemas.py
```

Expected: tests and ruff pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/outfit_ai/models.py backend/src/outfit_ai/schemas.py backend/tests/test_models.py backend/tests/test_style_references.py
git commit -m "feat: add long-term style reference model"
```

---

### Task 4: Long-Term Style Reference Upload and Style DNA Merge

**Files:**

- Create: `backend/src/outfit_ai/workers/style_reference.py`
- Create: `backend/src/outfit_ai/routers/style_references.py`
- Modify: `backend/src/outfit_ai/services/taste_memo.py`
- Modify: `backend/src/outfit_ai/services/prompt_builder.py`
- Modify: `backend/src/outfit_ai/main.py`
- Modify: `backend/tests/test_style_references.py`
- Modify: `backend/tests/test_profile.py`

**Interfaces:**

- Consumes: `describe_image(image_url, prompt) -> str`
- Consumes: existing `generate_json(...)`
- Produces: `analyze_style_reference(reference_id: str) -> None`
- Produces: `merge_style_reference(profile, analysis) -> ProfileIn`
- Produces: `/api/style-references` API.

- [ ] **Step 1: Write the failing end-to-end state-machine test**

```python
def test_reference_upload_analysis_and_retry_reuse_vlm(monkeypatch, tmp_path):
    calls = {"vlm": 0}
    monkeypatch.setattr(
        style_worker,
        "extract_style_reference",
        lambda path: (
            calls.__setitem__("vlm", calls["vlm"] + 1)
            or StyleReferenceAnalysis(style_keywords=["Ivy"], palette=["navy"])
        ),
    )
    monkeypatch.setattr(
        style_worker,
        "merge_style_reference",
        lambda profile, analysis: ProfileIn(
            style_keywords=["Ivy"], taste_memo="偏好克制的 Ivy 层次"
        ),
    )

    created = upload_reference(...)
    style_worker.analyze_style_reference(created["id"])

    assert calls["vlm"] == 1
    assert reference.status == "ready"
    assert profile.style_keywords_json == '["Ivy"]'
```

Add a second test where M3 merge fails after `analysis_json` is saved; retry must call M3 again but leave `calls["vlm"] == 1`.

- [ ] **Step 2: Run the reference tests and verify RED**

Run:

```bash
cd backend
uv run pytest tests/test_style_references.py tests/test_profile.py -q
```

Expected: failures because the worker, router and merge function are absent.

- [ ] **Step 3: Implement upload/list/status/retry and atomic profile merge**

Follow the existing wardrobe router and worker patterns:

- validate JPEG/PNG/WebP through `LocalStorage`;
- create `pending`, claim with `UPDATE ... WHERE status='pending' RETURNING id`;
- if `analysis_json` is empty, call VLM once and commit validated JSON while status remains `analyzing`;
- call M3 with old profile plus one new analysis;
- in one transaction, update profile fields and mark reference `ready`;
- on failure, store a 2000-character safe summary and mark `failed`;
- retry changes only `failed` to `pending`.

Register the router in `main.py`. Do not add delete/archive endpoints.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_style_references.py tests/test_profile.py -q
uv run ruff check src/outfit_ai/workers/style_reference.py src/outfit_ai/routers/style_references.py src/outfit_ai/services/taste_memo.py
```

Expected: tests and ruff pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/outfit_ai/workers/style_reference.py backend/src/outfit_ai/routers/style_references.py backend/src/outfit_ai/services/taste_memo.py backend/src/outfit_ai/services/prompt_builder.py backend/src/outfit_ai/main.py backend/tests/test_style_references.py backend/tests/test_profile.py
git commit -m "feat: add long-term style reference flow"
```

---

### Task 5: Style-DNA-Driven Real Wardrobe Recommendations

**Files:**

- Modify: `backend/src/outfit_ai/services/guardrail.py`
- Modify: `backend/src/outfit_ai/services/stylist.py`
- Modify: `backend/src/outfit_ai/services/prompt_builder.py`
- Modify: `backend/src/outfit_ai/services/recommend.py`
- Modify: `backend/src/outfit_ai/routers/recommend.py`
- Modify: `backend/tests/test_guardrail.py`
- Modify: `backend/tests/test_llm.py`
- Modify: `backend/tests/test_recommend.py`

**Interfaces:**

- Consumes: `StyleReference.analysis_json`
- Changes: `stylist.propose(..., reference_analyses: list[dict], ...)`
- Changes: `filter_candidates(..., limit=50) -> list[WardrobeItem]`

- [ ] **Step 1: Write failing tests for text-only styling and random candidate variation**

```python
def test_stylist_sends_no_image_content(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        stylist,
        "chat_multimodal",
        lambda messages, **kwargs: captured.setdefault("messages", messages) or response,
    )

    stylist.propose(candidates, profile, weather, "通勤", None, [], set(), [], "")

    assert "image_url" not in json.dumps(captured["messages"])


def test_guardrail_does_not_rank_by_utilization(monkeypatch):
    monkeypatch.setattr(guardrail.random, "sample", lambda values, count: list(reversed(values))[:count])
    result = filter_candidates(items, season="autumn", locked_ids=set(), recent_item_ids=set(), limit=3)
    assert [item.id for item in result] == ["shoes-2", "bottom-2", "top-2"]
```

Add a recommendation test proving foreign, failed, or missing `reference_ids` are rejected before M3 is called.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
cd backend
uv run pytest tests/test_guardrail.py tests/test_llm.py tests/test_recommend.py -q
```

Expected: tests fail because stylist still includes images and recommendation does not resolve references.

- [ ] **Step 3: Implement text-only candidate context**

Remove `image_data_url` from `stylist.py`. Include complete validated item attributes, long-term Style DNA, taste memo, selected reference analyses, season, scene, weather and optional note in `stylist_context`.

Change guardrail behavior:

- preserve all locked items;
- preserve at least top, bottom and shoes where available;
- if eligible count exceeds `limit`, use `random.sample` only on the remaining eligible items;
- do not read outfit wear counts, ratings or utilization.

Resolve only current-user, `ready` reference IDs in `recommend.py`. Use the manual season if provided; otherwise derive it from weather. Return processed wardrobe image URLs.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_guardrail.py tests/test_llm.py tests/test_recommend.py tests/test_validation.py -q
uv run python -m outfit_ai.services.recommend
uv run ruff check src/outfit_ai/services/guardrail.py src/outfit_ai/services/stylist.py src/outfit_ai/services/recommend.py
```

Expected: tests pass, self-check prints `recommend self-check passed`, and ruff is clean.

- [ ] **Step 5: Commit**

```bash
git add backend/src/outfit_ai/services/guardrail.py backend/src/outfit_ai/services/stylist.py backend/src/outfit_ai/services/prompt_builder.py backend/src/outfit_ai/services/recommend.py backend/src/outfit_ai/routers/recommend.py backend/tests/test_guardrail.py backend/tests/test_llm.py backend/tests/test_recommend.py
git commit -m "feat: drive wardrobe looks from style references"
```

---

### Task 6: Independent `image-01` Inspiration Generation

**Files:**

- Create: `backend/src/outfit_ai/services/inspiration.py`
- Create: `backend/src/outfit_ai/routers/inspiration.py`
- Create: `backend/tests/test_inspiration.py`
- Modify: `backend/src/outfit_ai/services/prompt_builder.py`
- Modify: `backend/src/outfit_ai/main.py`

**Interfaces:**

- Consumes: `generate_json(...)` for one M3 prompt-building call.
- Consumes: `generate_image(prompt, "3:4") -> bytes`.
- Produces: `create_inspiration(db: Session, request: InspirationRequest) -> str`.
- Produces: `POST /api/inspiration/generate -> {"image_url": "/media/..."}`.

- [ ] **Step 1: Write failing service and route tests**

```python
def test_inspiration_uses_style_dna_but_not_wardrobe_items(monkeypatch, tmp_path):
    monkeypatch.setattr(
        inspiration,
        "generate_json",
        lambda *args, **kwargs: {"prompt": "full-body autumn Ivy look"},
    )
    monkeypatch.setattr(inspiration, "generate_image", lambda *args: valid_jpeg_bytes())

    url = inspiration.create_inspiration(db, request, output_dir=tmp_path)

    assert url.startswith("/media/inspiration-")
    assert list(tmp_path.glob("inspiration-*.jpg"))


def test_image_generation_failure_is_not_retried(monkeypatch):
    calls = 0
    def fail(*args):
        nonlocal calls
        calls += 1
        raise MiniMaxUnavailableError("MiniMax 图片生成暂时不可用")
    monkeypatch.setattr(inspiration, "generate_image", fail)

    with pytest.raises(MiniMaxUnavailableError):
        inspiration.create_inspiration(db, request)

    assert calls == 1
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
cd backend
uv run pytest tests/test_inspiration.py -q
```

Expected: import failures because the inspiration service and router are absent.

- [ ] **Step 3: Implement one-image generation**

Validate selected references belong to the current user and are `ready`. Build one M3 JSON result:

```json
{"prompt":"A full-body editorial fashion photograph ..."}
```

The prompt must include style direction, palette, silhouette, layering, season and scene; it must not mention wardrobe item IDs or claim exact product reproduction.

Call `generate_image` exactly once. Validate decoded bytes with Pillow, convert to RGB JPEG if necessary, and save as `inspiration-<uuid>.jpg` under `settings.upload_dir`. Register the router and return 404/422/502/503 errors consistently with existing routers.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_inspiration.py -q
uv run ruff check src/outfit_ai/services/inspiration.py src/outfit_ai/routers/inspiration.py
```

Expected: tests and ruff pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/outfit_ai/services/inspiration.py backend/src/outfit_ai/routers/inspiration.py backend/src/outfit_ai/services/prompt_builder.py backend/src/outfit_ai/main.py backend/tests/test_inspiration.py
git commit -m "feat: generate independent outfit inspiration images"
```

---

### Task 7: Recommendation Page Dual-Mode UI

**Files:**

- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/recommend/index.vue`
- Modify: `frontend/src/pages/wardrobe/index.vue`

**Interfaces:**

- Consumes: style reference list/upload/status/retry endpoints.
- Consumes: expanded `/api/recommend`.
- Consumes: `/api/inspiration/generate`.
- Produces: one page with `wardrobe` and `inspiration` modes.

- [ ] **Step 1: Add frontend types and run typecheck to establish RED**

Add usage in the recommendation page before defining the types:

```ts
const mode = ref<"wardrobe" | "inspiration">("wardrobe");
const references = ref<StyleReference[]>([]);
const selectedReferenceIds = ref<string[]>([]);
const inspirationUrl = ref("");
```

Run:

```bash
cd frontend
npm run type-check
```

Expected: TypeScript errors for missing `StyleReference`, client methods and inspiration result types.

- [ ] **Step 2: Add the minimal typed API surface**

Define:

```ts
export interface StyleReference {
  id: string;
  image_url: string;
  status: AnalysisStatus;
  attempt_count: number;
  analysis?: StyleReferenceAnalysis | null;
}

export interface InspirationResult {
  image_url: string;
}
```

Add `styleReferences`, `styleReferenceStatus`, `retryStyleReference`, `generateInspiration`, and `uploadStyleReference`. Expand `recommend` request fields. Change `messageOf` so raw `request:fail` becomes `无法连接服务`.

- [ ] **Step 3: Implement the deliberate mobile composition**

Use the existing Warm Editorial tokens, but make the dual mode the page signature:

```text
┌──────────────────────────┐
│ Today’s edit             │
│ 今天想从哪里开始？       │
│ ┌────────┬─────────────┐ │
│ │我的衣橱│ 灵感探索    │ │
│ └────────┴─────────────┘ │
│ 灵感 Look  [＋添加参考] │
│ [ref] [ref] [ref] →     │
│ 季节 · 场景 · 可选要求  │
│                          │
│ mode-specific result     │
└──────────────────────────┘
```

Design requirements:

- keep system fonts and existing warm palette;
- use a restrained “contact-sheet strip” for long-term reference Looks;
- show selected references with a visible terracotta frame and check mark;
- new uploads auto-select and poll until `ready/failed`;
- `wardrobe` mode retains Safe/Fresh/Stretch cards and real item images;
- `inspiration` mode shows one 3:4 editorial image with the fixed label `AI 灵感图 · 不代表衣橱已有单品`;
- disable only the active action while loading;
- preserve 44px touch targets, keyboard focus, `aria-pressed`, and reduced motion;
- do not add gradients, a fifth tab, a modal framework or new frontend dependencies.

- [ ] **Step 4: Run frontend checks and verify GREEN**

Run:

```bash
cd frontend
npm run type-check
npm run build:h5
npm run smoke:h5
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/pages/recommend/index.vue frontend/src/pages/wardrobe/index.vue
git commit -m "feat: add wardrobe and inspiration modes"
```

---

### Task 8: Documentation, Full Verification, and Real Browser Review

**Files:**

- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/SPEC.md`
- Modify: `docs/design.md`

**Interfaces:**

- Consumes: all completed backend and frontend behavior.
- Produces: current project truth, automated evidence, and before/after screenshots.

- [ ] **Step 1: Update project truth without adding secrets**

Document:

- MiniMax-M3 text versus VLM/image-01 responsibilities;
- env-first/mmx-config fallback;
- local rembg behavior and first-run ONNX model download;
- fifth `style_references` table;
- new APIs and double-mode recommendation page;
- real interface smoke commands.

Do not write an actual key, account path beyond `~/.mmx/config.json`, or quota count as a permanent guarantee.

- [ ] **Step 2: Run the complete backend verification**

Run:

```bash
cd backend
uv sync
uv run pytest -q
uv run ruff check .
uv run python -m outfit_ai.services.recommend
```

Expected: all tests pass, ruff is clean, self-check prints `recommend self-check passed`.

- [ ] **Step 3: Run the complete frontend verification**

Run:

```bash
cd frontend
npm run type-check
npm run build:h5
npm run smoke:h5
```

Expected: all commands exit 0.

- [ ] **Step 4: Run one quota-bounded real API smoke**

Start the backend without changing credentials:

```bash
cd backend
uv run uvicorn outfit_ai.main:app --host 127.0.0.1 --port 8000
```

Use one real wardrobe photo and one reference Look supplied or approved by the user:

1. upload the wardrobe photo and poll to `ready`;
2. confirm its transparent `.nobg.png` exists;
3. upload the reference Look and poll to `ready`;
4. call one independent inspiration generation;
5. inspect logs and responses for secret leakage.

Expected consumption: two VLM calls and one `image-01` call. Do not retry automatically.

- [ ] **Step 5: Review in a real mobile browser**

Run the H5 server, then use Playwright CLI at `390x844`:

```bash
npm run dev:h5 -- --host 127.0.0.1
```

Capture:

- `output/playwright/implemented-wardrobe-mode.png`
- `output/playwright/implemented-inspiration-mode.png`

Verify:

- mode switch is visible without scrolling;
- reference strip, selected state and upload action are understandable;
- both modes have useful empty/error/loading states;
- no horizontal overflow;
- bottom tab does not cover the sticky action;
- browser console has no application errors.

- [ ] **Step 6: Commit documentation**

```bash
git add CLAUDE.md README.md .env.example docs/SPEC.md docs/design.md
git commit -m "docs: document style inspiration workflow"
```

- [ ] **Step 7: Final branch review**

Run:

```bash
git status --short
git diff main...HEAD --check
git log --oneline --decorate main..HEAD
```

Expected: only known user-owned `images/` and local Playwright artifacts may remain untracked; the committed diff has no whitespace errors.
