# Upload and Inspiration Bugfix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix MiniMax reasoning-wrapped JSON, iPhone MPO/JPG wardrobe uploads, multi-image inspiration uploads, and compact tap-to-preview inspiration browsing.

**Architecture:** Keep API routes and dependencies unchanged. Fix provider/image compatibility once at the shared backend boundaries, then make the two focused React interaction changes inside the existing Stitch screens.

**Tech Stack:** Python 3.11, FastAPI, Pillow, pytest, React 19, TypeScript, Vite, Tailwind CSS, Node contract tests.

## Global Constraints

- Do not change the Stitch ZIP page structure, navigation, or overall visual language.
- Do not add dependencies, database changes, API routes, or frontend MiniMax credentials.
- Update `docs/SPEC.md` and `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` with the final behavior.

---

### Task 1: MiniMax JSON compatibility

**Files:**
- Modify: `backend/tests/test_llm.py`
- Modify: `backend/src/outfit_ai/services/llm.py`

**Interfaces:**
- Consumes: `generate_json(system, user, schema_hint, max_attempts=2)`.
- Produces: the same function accepting an object embedded after MiniMax reasoning text or inside a JSON code fence.

- [ ] Add `test_generate_json_extracts_object_after_reasoning` with a fake completion containing `<think>reasoning</think>\n{"prompt":"valid"}`.
- [ ] Run `cd backend && uv run pytest tests/test_llm.py::test_generate_json_extracts_object_after_reasoning -q`; verify it fails with `LLMResponseError`.
- [ ] Add the smallest balanced-object extraction helper in `llm.py`, then pass the extracted object to the existing Pydantic adapter.
- [ ] Run `cd backend && uv run pytest tests/test_llm.py -q`; verify the new and existing invalid-object tests pass.

### Task 2: iPhone MPO/JPG and generic MIME compatibility

**Files:**
- Modify: `backend/tests/test_wardrobe_flow.py`
- Modify: `backend/src/outfit_ai/services/storage.py`
- Modify: `backend/src/outfit_ai/routers/wardrobe.py`

**Interfaces:**
- Consumes: multipart `UploadFile` and `LocalStorage.save(upload)`.
- Produces: standard `.jpg` output for Pillow `MPO`, while damaged or unsupported images still fail.

- [ ] Add a storage regression test using generated MPO bytes and an upload regression test whose valid JPEG has `application/octet-stream`.
- [ ] Run both targeted tests; verify MPO is rejected by the format whitelist and generic MIME is rejected with `415`.
- [ ] Map Pillow `MPO` to `.jpg`/`JPEG` and let content validation in `LocalStorage.save()` decide generic MIME uploads.
- [ ] Run `cd backend && uv run pytest tests/test_wardrobe_flow.py -q`; verify all wardrobe tests pass.

### Task 3: Multi-image inspiration upload

**Files:**
- Modify: `frontend/scripts/stitch-contract.mjs`
- Modify: `frontend/src/components/ScreenInspiration.tsx`

**Interfaces:**
- Consumes: existing `api.uploadReference`, `api.referenceStatus`, `waitForReady`.
- Produces: one file chooser with `multiple=true`, independent per-file settlement, one final success/failure summary.

- [ ] Add source contract assertions for `input.multiple = true` and independent settlement.
- [ ] Run `cd frontend && npm test`; verify the new assertions fail.
- [ ] Update `handleUploadInspiration()` to upload all selected files with `Promise.allSettled`, reload successful references once, and report result counts.
- [ ] Run `cd frontend && npm test && npm run lint`; verify the contract and TypeScript checks pass.

### Task 4: Compact archive and tap-to-restore preview

**Files:**
- Modify: `frontend/scripts/stitch-contract.mjs`
- Modify: `frontend/src/components/ScreenArchive.tsx`

**Interfaces:**
- Consumes: existing `previewItem` state and reference card data.
- Produces: three-column mobile thumbnails and a full-image overlay closed by clicking the enlarged image.

- [ ] Add source contract assertions for a three-column mobile grid, fixed thumbnail crop, and image-click close handler.
- [ ] Run `cd frontend && npm test`; verify the new assertions fail.
- [ ] Replace the mobile masonry layout with `grid-cols-3`, use fixed `aspect-[3/4] object-cover` thumbnails, reduce badges to corner labels, and close the overlay from the enlarged image click without navigation.
- [ ] Run `cd frontend && npm test && npm run lint && npm run build`; verify all frontend checks pass.

### Task 5: Documentation and end-to-end verification

**Files:**
- Modify: `docs/SPEC.md`
- Modify: `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`

**Interfaces:**
- Consumes: final verified behavior from Tasks 1–4.
- Produces: current backend and frontend facts matching the implementation.

- [ ] Document reasoning-wrapped JSON parsing and MPO/JPG upload compatibility in `docs/SPEC.md`.
- [ ] Document multi-select inspiration upload and compact tap-to-preview archive behavior in the frontend fact source.
- [ ] Run `cd backend && uv run ruff check src tests && uv run pytest -q`.
- [ ] Run `cd frontend && npm test && npm run lint && npm run build`.
- [ ] Reload the app at `390 × 844`, verify the inspiration file chooser is multiple, verify the archive has three columns, and verify preview opens and closes on image click.
- [ ] Review `git diff --check` and commit only the intended code, tests, and current documentation.
