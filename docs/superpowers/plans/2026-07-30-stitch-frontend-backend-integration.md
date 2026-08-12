# Stitch Frontend and MiniMax Image Integration Plan

> **执行修正（2026-07-30）：** 不再把 ZIP 转译为 uni-app。前端直接采用用户确认的 ZIP 原版 React/Vite/Tailwind 源码，仅增加 FastAPI 接线；下文涉及 Vue/uni-app 的步骤均为过期记录。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Google AI Studio / Stitch 导出的移动端视觉移植到现有 uni-app + Vue 3，并接通真实衣橱推荐、长期参考 Look 和独立 MiniMax 灵感生图。

**Architecture:** 保留现有 FastAPI、SQLAlchemy、SQLite 和 uni-app 技术栈。Stitch 的 React/Tailwind 代码只作为页面结构、视觉 token 和交互参考；所有 MiniMax 调用仍由后端代理，前端只调用 `/api/*`。新增一张 `style_references` 表和两个资源路由，不引入任务队列、对象存储或新的前端状态库。

**Tech Stack:** Python 3.11, FastAPI sync, SQLAlchemy 2.0, SQLite, httpx, Pillow, rembg, MiniMax VLM/image-01/MiniMax-M3, uni-app, Vue 3, TypeScript.

## Global Constraints

- 主文本模型固定为 `MiniMax-M3`。
- 真实衣物和参考 Look 的识图固定走 `POST /v1/coding_plan/vlm`。
- 独立灵感图固定走 `image-01` 的 `POST /v1/image_generation`，一次只生成一张且不自动重试。
- 真实衣物上传后本地去背景；参考 Look 保留完整场景，不去背景。
- MiniMax Key 只由后端读取：`MINIMAX_API_KEY` 优先，再只读 `MMX_CONFIG_DIR/config.json` 或 `~/.mmx/config.json`。
- 不修改 `.env`、用户 Key、`~/.mmx/config.json`，不推送远端，不部署生产。
- 真实推荐只使用已确认衣橱 item_id；候选不按利用率或闲置时间排序。
- Stitch ZIP 的暖米白、砖红、藏青、编辑手帐视觉以用户本次指定为准，覆盖旧 PRD 的冷白/cobalt 方向。
- 所有新增非平凡逻辑先写失败测试，再写最小实现。

---

### Task 1: MiniMax 图片调用与去背景基础能力

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/src/outfit_ai/config.py`
- Create: `backend/src/outfit_ai/services/minimax_images.py`
- Create: `backend/src/outfit_ai/services/background.py`
- Modify: `backend/src/outfit_ai/services/vision.py`
- Modify: `backend/src/outfit_ai/services/storage.py`
- Modify: `backend/src/outfit_ai/workers/analysis.py`
- Test: `backend/tests/test_minimax_images.py`
- Test: `backend/tests/test_background.py`
- Modify: `backend/tests/test_vision.py`
- Modify: `backend/tests/test_wardrobe_flow.py`

**Interfaces:**
- Produces: `resolve_minimax_access() -> MiniMaxAccess`
- Produces: `describe_image(path: str | Path, prompt: str) -> str`
- Produces: `generate_image(prompt: str) -> bytes`
- Produces: `background_path(path: str | Path) -> Path`
- Produces: `ensure_background_removed(path: str | Path) -> Path`
- Produces: `display_image_path(item: WardrobeItem) -> Path`

- [ ] **Step 1: Write failing provider/auth tests**

```python
def test_access_prefers_environment_key(monkeypatch, tmp_path):
    monkeypatch.setenv("MINIMAX_API_KEY", "env-key")
    monkeypatch.setenv("MMX_CONFIG_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text('{"api_key":"file-key","region":"cn"}')
    assert resolve_minimax_access().api_key == "env-key"


def test_vlm_extracts_markdown_wrapped_json(monkeypatch, image_path):
    monkeypatch.setattr(
        minimax_images,
        "describe_image",
        lambda *_: (
            "```json\n"
            '{"name":"白衬衫","category":"top","primary_color":"白色",'
            '"styles":[],"tags":[],"seasons":[],"occasions":[]}'
            "\n```"
        ),
    )
    attributes, _ = extract(image_path)
    assert attributes.category == "top"
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `cd backend && uv run pytest tests/test_minimax_images.py tests/test_vision.py -q`

Expected: FAIL because the access resolver and direct VLM client do not exist.

- [ ] **Step 3: Implement the minimal provider client**

Implement:

```python
@dataclass(frozen=True)
class MiniMaxAccess:
    api_key: str
    base_url: str


def describe_image(path, prompt):
    return _post_json(
        "/v1/coding_plan/vlm",
        {"prompt": prompt, "image_url": image_data_url(path)},
    )["content"]


def generate_image(prompt):
    payload = _post_json(
        "/v1/image_generation",
        {
            "model": "image-01",
            "prompt": prompt,
            "aspect_ratio": "3:4",
            "n": 1,
            "response_format": "base64",
        },
    )
    return base64.b64decode(payload["data"]["image_base64"][0], validate=True)
```

Map 401/403, 429/quota, timeout, malformed JSON and nonzero `base_resp.status_code` to short Chinese exceptions without including credentials or raw provider bodies.

- [ ] **Step 4: Write failing background tests**

```python
def test_background_path_is_deterministic(tmp_path):
    source = tmp_path / "item.jpg"
    assert background_path(source) == tmp_path / "item.nobg.png"


def test_display_path_uses_transparent_image_only_when_ready(tmp_path):
    source = tmp_path / "item.jpg"
    transparent = tmp_path / "item.nobg.png"
    transparent.write_bytes(b"png")
    assert display_image_path(SimpleNamespace(image_path=str(source), status="ready")) == transparent
```

- [ ] **Step 5: Run tests and confirm RED**

Run: `cd backend && uv run pytest tests/test_background.py tests/test_wardrobe_flow.py -q`

Expected: FAIL because deterministic background helpers do not exist.

- [ ] **Step 6: Implement idempotent local background removal**

Use `rembg.remove(source_bytes)` once when `<stem>.nobg.png` is absent, validate the output with Pillow, and write via a sibling temporary file followed by `Path.replace()`. Update worker order to background removal first, then VLM. Use the transparent path for ready previews, collage and recommendation images; delete both files only after DB deletion commits.

- [ ] **Step 7: Verify Task 1**

Run: `cd backend && uv sync && uv run pytest tests/test_minimax_images.py tests/test_background.py tests/test_vision.py tests/test_wardrobe_flow.py -q`

Expected: all selected tests PASS.

---

### Task 2: Long-term references, Style DNA merge, recommendation context, and inspiration image API

**Files:**
- Modify: `backend/src/outfit_ai/models.py`
- Modify: `backend/src/outfit_ai/db.py`
- Modify: `backend/src/outfit_ai/schemas.py`
- Create: `backend/src/outfit_ai/services/style_references.py`
- Create: `backend/src/outfit_ai/workers/style_references.py`
- Create: `backend/src/outfit_ai/routers/style_references.py`
- Create: `backend/src/outfit_ai/services/inspiration.py`
- Create: `backend/src/outfit_ai/routers/inspiration.py`
- Modify: `backend/src/outfit_ai/services/prompt_builder.py`
- Modify: `backend/src/outfit_ai/services/stylist.py`
- Modify: `backend/src/outfit_ai/services/recommend.py`
- Modify: `backend/src/outfit_ai/routers/recommend.py`
- Modify: `backend/src/outfit_ai/main.py`
- Test: `backend/tests/test_style_references.py`
- Test: `backend/tests/test_inspiration.py`
- Modify: `backend/tests/test_recommend.py`
- Modify: `backend/tests/test_models.py`

**Interfaces:**
- Produces: `StyleReference` table with pending/analyzing/ready/failed state.
- Produces: `POST /api/style-references/upload`
- Produces: `GET /api/style-references`
- Produces: `GET /api/style-references/{id}/status`
- Produces: `POST /api/style-references/{id}/retry`
- Produces: `POST /api/inspiration/generate`
- Extends: `POST /api/recommend` with `reference_ids`, `style_note`, `season`, and `scene`.

- [ ] **Step 1: Write failing model and state-machine tests**

```python
def test_schema_has_style_references_table():
    Base.metadata.create_all(engine)
    assert "style_references" in inspect(engine).get_table_names()


def test_reference_retry_reuses_existing_analysis(monkeypatch, reference):
    reference.analysis_json = '{"style_keywords":["克制"]}'
    monkeypatch.setattr(vision, "analyze_reference", fail_if_called)
    process_reference(reference.id)
    assert reference.status == "ready"
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `cd backend && uv run pytest tests/test_models.py tests/test_style_references.py -q`

Expected: FAIL because the table and routes do not exist.

- [ ] **Step 3: Implement the reference resource**

Add the approved table and four routes. Validate VLM output with:

```python
class StyleReferenceAnalysis(BaseModel):
    style_keywords: list[str]
    palette: list[str]
    silhouettes: list[str]
    layering: list[str]
    materials: list[str]
    seasons: list[str]
    scenes: list[str]
    notable_elements: list[str]
```

The worker claims only `pending`; it skips VLM when `analysis_json` is already valid. Merge the old profile and the new analysis through `MiniMax-M3`, then update profile and mark the reference ready in one DB transaction.

- [ ] **Step 4: Write failing recommendation and inspiration tests**

```python
def test_recommend_passes_selected_reference_analysis_to_stylist(monkeypatch):
    request = RecommendRequest(reference_ids=["ref-1"], scene="通勤")
    recommend(db, request)
    assert captured["references"][0]["style_keywords"] == ["极简"]


def test_inspiration_generates_one_saved_image(monkeypatch, tmp_path):
    monkeypatch.setattr(minimax_images, "generate_image", lambda _: VALID_JPEG)
    result = generate(db, InspirationRequest(scene="周末"))
    assert result["image_url"].startswith("/media/")
```

- [ ] **Step 5: Run tests and confirm RED**

Run: `cd backend && uv run pytest tests/test_recommend.py tests/test_inspiration.py -q`

Expected: FAIL because request context and inspiration generation are missing.

- [ ] **Step 6: Implement text-only styling and one-image generation**

Load only ready reference analyses owned by the local user. Replace wardrobe image messages in the stylist call with validated item attributes plus selected reference analyses. Preserve item-id validation and Safe/Fresh/Stretch history. Build a single image prompt through `generate_json`, call `generate_image` once, validate with Pillow, save under the existing media root, and return a visible disclaimer with `image_url`.

- [ ] **Step 7: Verify Task 2**

Run: `cd backend && uv run pytest tests/test_models.py tests/test_style_references.py tests/test_recommend.py tests/test_inspiration.py -q`

Expected: all selected tests PASS.

---

### Task 3: Port the Stitch mobile UI to uni-app and connect real APIs

**Files:**
- Modify: `frontend/src/pages.json`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/recommend/index.vue`
- Modify: `frontend/src/pages/wardrobe/index.vue`
- Create: `frontend/src/pages/inspiration/index.vue`
- Modify: `frontend/src/pages/profile/index.vue`
- Modify: `frontend/src/pages/history/index.vue`
- Modify: `frontend/scripts/smoke-h5.mjs`

**Interfaces:**
- Consumes: existing wardrobe/profile/recommend/feedback/history APIs and Task 2 reference/inspiration APIs.
- Produces: bottom tabs `今日 / 衣橱 / 灵感 / 我的`.
- Produces: actual API-backed Stitch screens without React, Tailwind, Gemini, localStorage mocks or remote demo image dependencies.

- [ ] **Step 1: Extend the smoke check so the current UI fails**

Assert the H5 build contains the four tab labels, the inspiration route, the authenticity disclaimer, and no old raw `request:fail` copy.

Run: `cd frontend && npm run build:h5 && npm run smoke:h5`

Expected: FAIL because the inspiration page and new navigation are absent.

- [ ] **Step 2: Port the shared visual system**

Translate the selected Stitch visual language into existing global CSS:

```css
:root {
  --paper: #fbf9f4;
  --ink: #1b1c19;
  --navy: #162839;
  --rust: #9a442a;
  --line: #e4e2dd;
  --muted: #74777d;
}
```

Use native uni-app elements, 44px touch targets, safe-area padding, visible focus, and reduced-motion support. Do not add a UI library or icon package.

- [ ] **Step 3: Rebuild the four primary screens**

- `今日`: weather/context header, selected reference filmstrip, Safe/Fresh/Stretch editorial stacks, feedback actions.
- `衣橱`: summary strip, category filter, two-column image grid, upload/recognition/confirmation states.
- `灵感`: long-term Look filmstrip, upload/status selection, season/scene/style note, one generated 3:4 image with persistent authenticity label.
- `我的`: compact Style DNA summary, editable profile, taste memo, and an entry to outfit history.

Use the existing history page as the profile-linked archive rather than a fifth bottom tab.

- [ ] **Step 4: Connect API types and upload helpers**

Add `StyleReference`, `InspirationRequest`, and `InspirationResult` types; add reference upload/poll/retry and inspiration generation methods. Change network errors to `无法连接造型服务，请检查网络后重试`, while preserving specific backend `detail` messages.

- [ ] **Step 5: Run frontend checks**

Run:

```bash
cd frontend
npm run type-check
npm run build:h5
npm run smoke:h5
```

Expected: all commands exit 0.

- [ ] **Step 6: Run real mobile browser verification**

Start backend and H5, then verify at 390×844:

- all four tabs navigate;
- bottom nav does not cover primary actions;
- wardrobe empty/data/upload states render;
- reference upload control is visible;
- today and inspiration are visibly distinct;
- generated inspiration area always carries the authenticity disclaimer;
- backend-offline errors are user-facing Chinese copy.

Capture final screenshots under `output/playwright/`.

---

### Task 4: Full verification and documentation alignment

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/design.md`
- Modify: `README.md`

- [ ] **Step 1: Update only stale architecture statements**

Document VLM/image-01/rembg responsibilities, the fifth table, the four-tab navigation, and the selected Stitch visual direction. Preserve licensing attribution.

- [ ] **Step 2: Run full backend and frontend verification**

Run:

```bash
cd backend
uv run pytest
uv run ruff check .
uv run python -m outfit_ai.services.recommend

cd ../frontend
npm run type-check
npm run build:h5
npm run smoke:h5
```

Expected: all commands exit 0 with no test failures.

- [ ] **Step 3: Review scope and secrets**

Run:

```bash
git diff --check
git status --short
git diff --stat
git diff | rg -n "sk-[A-Za-z0-9]|MINIMAX_API_KEY="
```

Expected: no whitespace errors, no secrets, no changes to `.env` or `~/.mmx/config.json`, and unrelated untracked assets remain untouched.
