# Outfit-AI 当前前端与后端集成

> 本文件是当前前端页面、入口、功能和 API 接线的事实源。最后核对：2026-07-31。

## 1. 前端基准

- 原始视觉与交互基准：用户确认的 Google AI Studio / Stitch ZIP。
- 项目内可执行源码：`frontend/src`。
- 技术栈：React 19、Vite 6、Tailwind CSS 4、TypeScript。
- 旧 `docs/design.md` 和旧 Stitch PRD 是历史资料；旧 uni-app/Vue 源码已从 `frontend` 删除，不得恢复或用于覆盖当前界面。
- MiniMax Key 仅由 FastAPI 后端读取，前端只请求 `/api/*` 和 `/media/*`。

## 2. 应用入口与导航

```text
frontend/index.html
  → frontend/src/main.tsx
    → frontend/src/App.tsx
      → ScreenToday（默认）
      → ScreenWardrobe
      → ScreenInspiration
      → ScreenArchive
      → ScreenProfile
```

底部导航有四个主入口：今日、衣橱、灵感、我的。灵感存档是第五个独立页面，从灵感页“查看全部”进入，并继续高亮“灵感”主入口。

当前导航由 React 本地状态管理，不使用 URL Router；刷新页面回到“今日”。

城市选择、最近一次推荐、收藏显示和评分表单使用 `localStorage` 作为当前设备的界面缓存；有对应推荐历史的收藏与评分仍通过 `POST /api/feedback` 写入后端学习链。`localStorage` 不是业务事实源。

## 3. 五个页面

| 页面 | 源文件 | 用户功能 | 主要后端接口 |
|---|---|---|---|
| 今日 | `ScreenToday.tsx` | 从真实衣橱生成 Safe / Fresh / Stretch；收藏、打分和反馈 | `GET /api/style-references`、`POST /api/recommend`、`POST /api/feedback` |
| 衣橱 | `ScreenWardrobe.tsx` | 批量或单张上传真实衣物；等待去背景和识图；确认并展示单品 | `GET /api/wardrobe/items`、`POST /api/wardrobe/upload`、`GET /api/wardrobe/{id}/status`、`POST /api/wardrobe/{id}/confirm` |
| 灵感 | `ScreenInspiration.tsx` | 单次多选上传长期参考 Look；逐张独立分析并汇总成功/失败数量；沉淀 Style DNA；按季节和场景生成三张非衣橱灵感图 | `GET /api/style-references`、`POST /api/style-references/upload`、`GET /api/style-references/{id}/status`、`GET /api/profile`、`POST /api/inspiration/generate` |
| 灵感存档 | `ScreenArchive.tsx` | 三列紧凑缩略图浏览；点击图片放大、再次点击恢复原网格位置；批量选择和删除长期参考 Look | `GET /api/style-references`、`DELETE /api/style-references/{id}` |
| 我的 | `ScreenProfile.tsx` | 查看和编辑风格关键词、色板、反馈历史、推荐历史和收藏 | `GET/PUT /api/profile`、`GET /api/wardrobe/items`、`GET /api/history` |

## 4. 前端 API 接线

统一接线层：`frontend/src/lib/api.mjs`。

| 前端方法 | HTTP 接口 | 说明 |
|---|---|---|
| `wardrobe()` | `GET /api/wardrobe/items` | 读取已确认真实衣物 |
| `uploadWardrobe(file)` | `POST /api/wardrobe/upload` | 上传真实衣物 |
| `wardrobeStatus(id)` | `GET /api/wardrobe/{id}/status` | 轮询识图状态 |
| `confirmWardrobe(id,data)` | `POST /api/wardrobe/{id}/confirm` | 确认 AI 属性及用户修改 |
| `deleteWardrobe(id)` | `DELETE /api/wardrobe/{id}` | 删除衣物和图片 |
| `references()` | `GET /api/style-references` | 读取长期参考 Look |
| `uploadReference(file)` | `POST /api/style-references/upload` | 上传完整参考 Look，不去背景 |
| `referenceStatus(id)` | `GET /api/style-references/{id}/status` | 轮询 VLM 分析与 Style DNA 合并状态 |
| `deleteReference(id)` | `DELETE /api/style-references/{id}` | 删除参考 Look 和图片 |
| `profile()` / `saveProfile()` | `GET/PUT /api/profile` | 读取或保存 Style DNA |
| `recommend(data)` | `POST /api/recommend` | 返回天气及 Safe / Fresh / Stretch 三套真实衣橱推荐 |
| `feedback(data)` | `POST /api/feedback` | 保存收藏、跳过、穿着或评分反馈 |
| `history()` | `GET /api/history` | 读取近期推荐记录 |
| `generateInspiration(data)` | `POST /api/inspiration/generate` | 一次返回三张独立灵感图 |

灵感参考图批量上传复用现有单文件接口：前端对每张图片分别调用 `uploadReference()` 和 `referenceStatus()`，使用独立结算保证单张失败不影响同批其他图片，完成后只刷新一次灵感库。

开发环境默认使用相对路径，Vite 将 `/api` 和 `/media` 代理到 `http://localhost:8000`。分离部署时通过 `VITE_API_BASE_URL` 指定后端地址。

## 5. 两条核心数据流

### 真实衣橱推荐

```text
衣物上传
→ 本地 rembg 去背景
→ MiniMax VLM 提取属性
→ 用户确认
→ FastAPI 硬护栏筛选
→ MiniMax-M3 结合 Style DNA 和参考 Look 生成三档搭配
→ item_id 校验
→ 前端展示真实衣物图片
→ 反馈写入品味备忘录学习链
```

### 独立灵感生成

```text
长期参考 Look + Style DNA + 季节 + 场景
→ MiniMax-M3 生成图像提示
→ MiniMax image-01 一次生成三张 3:4 图片
→ 前端明确标注“不代表衣橱已有单品”
```

## 6. 本地运行

要求 Node.js 20 及以上、Python 3.11。

```bash
# 终端 1：后端
cd backend
uv sync
uv run uvicorn outfit_ai.main:app --reload

# 终端 2：前端
cd frontend
npm install
npm run dev
```

- 前端：`http://localhost:5173`
- 后端 OpenAPI：`http://localhost:8000/docs`
- 后端健康检查：`http://localhost:8000/health`

## 7. 验证

```bash
cd backend
uv run ruff check src tests
uv run pytest -q

cd ../frontend
npm test
npm run lint
npm run build
```

`frontend/scripts/stitch-contract.mjs` 防止五页结构、四主导航和原版字体依赖被误改；`frontend/scripts/api-contract.test.mjs` 验证后端数据到 Stitch 页面模型的映射和轮询分支。

当前视觉契约还固定以下已确认的移动端行为：灵感上传文件选择器支持多选；灵感存档在手机端使用三列 `3:4` 缩略图；放大图可再次点击关闭。

## 8. 文档同步规则

以下变化必须在同一提交更新本文：

- 页面、入口、导航、交互或空状态；
- 前端调用的 API 路径、请求体或响应结构；
- 技术栈、依赖、环境变量、启动或测试命令；
- ZIP 基准的有意视觉调整。

后端路由、数据模型或架构变化还必须同步 `docs/SPEC.md`；用户入口和运行方式变化还必须同步 `README.md`；项目约束变化还必须同步 `CLAUDE.md` 与 `AGENTS.md`。
