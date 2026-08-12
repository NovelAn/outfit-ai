# 衣橱单品编辑与删除 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Stitch React 衣橱详情浮层中加入单品信息编辑和删除入口，复用后端现有 PATCH/DELETE 接口。

**Architecture:** 扩展 `frontend/src/lib/api.mjs` 的单品数据映射与 PATCH 接线，让 `ScreenWardrobe.tsx` 在详情浮层内维护编辑草稿、保存状态和删除确认。厚薄度不新增数据库列，使用 `tags` 中的受控值保存；同步当前前端和后端事实文档。

**Tech Stack:** React 19、TypeScript、Vite、原生 fetch、FastAPI/SQLAlchemy 既有 `WardrobePatch` 与 DELETE 路由、Node 内置测试。

## Global Constraints

- Stitch ZIP 的页面、视觉和交互是唯一前端基准，不恢复旧 Vue/uni-app。
- 不新增依赖，不改数据库 schema，不接触密钥或环境配置。
- 用户可见衣物属性使用简体中文；内部 category 继续使用稳定英文码。
- 删除必须二次确认；失败时不乐观移除，避免界面与后端不一致。
- 同一提交更新相关当前文档；不删除或提交现有 `.playwright-cli/`、`output/` 未跟踪文件。

---

### Task 1: 扩展衣橱 API 映射和更新接线

**Files:**
- Modify: `frontend/src/lib/api.mjs` (`mapWardrobeItem`, `api` wardrobe methods)
- Modify: `frontend/src/types.ts` (`OutfitItem` editable attributes)
- Test: `frontend/scripts/api-contract.test.mjs`

**Interfaces:**
- `mapWardrobeItem(item) -> OutfitItem` must preserve existing card fields and expose editable fields as Chinese/string arrays.
- `api.updateWardrobe(id, data) -> Promise<WardrobeItemResponse>` sends `PATCH /api/wardrobe/{id}` with JSON.
- `api.wardrobe()` continues returning mapped confirmed items.

- [ ] **Step 1: Write the failing API contract tests**

Add assertions that `mapWardrobeItem` preserves `primary_color`, `secondary_color`, `material`, `fit`, `seasons`, `occasions`, `styles`, `tags`, and derives `thickness` from one of `轻薄/适中/厚实` tags. Add a mocked-fetch test that calls `api.updateWardrobe("item-1", {name:"条纹衬衫"})` and asserts method, path, JSON header/body.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `node --test frontend/scripts/api-contract.test.mjs`

Expected: FAIL because the mapper does not expose editable attributes and `api.updateWardrobe` is not defined.

- [ ] **Step 3: Implement the minimal API changes**

Extend `mapWardrobeItem` with the backend response fields while retaining the current mapped card shape. Add:

```js
updateWardrobe: (id, data) => request(`/api/wardrobe/${id}`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
}),
```

Export a small `thicknessFromTags(tags)` helper only if the mapper test needs it; otherwise keep the derivation inline to avoid a one-use abstraction.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `node --test frontend/scripts/api-contract.test.mjs`

Expected: PASS, with the existing API mapping and batch-upload tests unchanged.

- [ ] **Step 5: Commit the API slice**

Run: `git add frontend/src/lib/api.mjs frontend/src/types.ts frontend/scripts/api-contract.test.mjs && git commit -m "feat: expose wardrobe item editing API"`

### Task 2: Add edit and delete interactions to the wardrobe detail modal

**Files:**
- Modify: `frontend/src/components/ScreenWardrobe.tsx` (detail state, modal, save/delete handlers)
- Modify: `frontend/scripts/stitch-contract.mjs` (entry/interaction contract assertions)

**Interfaces:**
- Detail modal uses `selectedItem: OutfitItem | null` and a copied `editDraft` only while editing.
- Save handler calls `api.updateWardrobe(selectedItem.id, payload)` and replaces that item in `items` with `mapWardrobeItem(result)`.
- Delete handler asks for explicit confirmation through an in-modal confirmation state, calls `api.deleteWardrobe(selectedItem.id)`, then removes the item from `items`.

- [ ] **Step 1: Add failing Stitch contract assertions**

Assert that `ScreenWardrobe.tsx` contains the user-facing entry labels `编辑信息`, `删除单品`, `保存修改`, `确认删除`, and the calls `api.updateWardrobe` and `api.deleteWardrobe`.

- [ ] **Step 2: Run the contract and verify it fails**

Run: `node --test frontend/scripts/stitch-contract.mjs`

Expected: FAIL because the current detail modal only has a close button.

- [ ] **Step 3: Implement the modal interactions**

Add controlled fields for name, category, primary/secondary color, material, thickness, fit, seasons, occasions, and styles/tags. Use native `input`, `select`, and comma-separated text fields; keep the existing visual tokens and mobile sizing. On submit, convert the draft to the existing PATCH shape, replacing only the controlled thickness tag while preserving other tags. Use `try/finally` to disable save/delete while requests are active; on errors call `triggerToast` and keep the modal open.

Add a delete confirmation panel inside the same modal. “取消删除” returns to detail; “确认删除” only then calls DELETE. Do not use `window.confirm`, so the interaction remains testable and matches the mobile UI.

- [ ] **Step 4: Run the Stitch contract and frontend tests**

Run: `node --test frontend/scripts/stitch-contract.mjs frontend/scripts/api-contract.test.mjs`

Expected: PASS with the five-screen, compact-grid, upload, and API contracts intact.

- [ ] **Step 5: Commit the UI slice**

Run: `git add frontend/src/components/ScreenWardrobe.tsx frontend/scripts/stitch-contract.mjs && git commit -m "feat: add wardrobe edit and delete actions"`

### Task 3: Synchronize current project documentation and verify the full change

**Files:**
- Modify: `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` (wardrobe user entry and API table)
- Modify: `docs/SPEC.md` (current wardrobe implementation status and PATCH/DELETE behavior)

**Interfaces:**
- Documentation must describe the exact current frontend entry and request methods implemented in Tasks 1–2.

- [ ] **Step 1: Update the current frontend integration document**

Change the wardrobe row and API mapping to state that tapping a card opens details, edit fields are saved through PATCH, and deletion requires in-modal confirmation before DELETE. Record the controlled thickness tags and that image replacement/manual background editing are out of scope.

- [ ] **Step 2: Update the backend specification status**

Keep the existing API routes unchanged, but clarify that PATCH supports the user-editable fields and DELETE removes the record plus original and `.nobg` files; note that thickness is represented in controlled tags for the current schema.

- [ ] **Step 3: Run verification**

Run:

```bash
node --test frontend/scripts/api-contract.test.mjs frontend/scripts/stitch-contract.mjs
cd frontend && npm run lint && npm run build
cd ../backend && uv run ruff check src tests && uv run pytest -q
```

Expected: all Node tests, lint, production build, ruff, and backend tests pass.

- [ ] **Step 4: Review the final diff and commit documentation**

Run: `git diff --check && git status --short && git diff HEAD~2..HEAD --stat`

Then commit only the two current documents:

```bash
git add docs/frontend/CURRENT_FRONTEND_INTEGRATION.md docs/SPEC.md
git commit -m "docs: document wardrobe item editing"
```

