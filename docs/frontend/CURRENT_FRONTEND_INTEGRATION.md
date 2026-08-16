# Outfit-AI 当前前端与后端集成

> 本文件是当前前端页面、入口、功能和 API 接线的事实源。最后核对：2026-08-09。

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

底部导航有四个主入口：今日、衣橱、灵感、我的。灵感存档是第五个独立页面，从灵感页“查看全部”进入，并继续高亮“灵感”主入口。手机主屏独立网页模式隐藏浏览器刷新按钮；今日页在应用从后台恢复或重新显示时会自动检查当天推荐（30 秒内合并重复事件），侧边导航仍保留“刷新应用”作为手动兜底。

当前导航由 React 本地状态管理，不使用 URL Router；刷新页面回到“今日”。

今日页优先使用浏览器原生 Geolocation 获取当前位置：请求启用高精度、最多复用 5 分钟浏览器位置，坐标按三位小数缓存到 `OUTFIT_AI_LOCATION`，缓存有效期 2 小时；应用自身也会在 8 秒无回调时结束定位等待。侧边栏提供上海、北京快捷项，也可输入任意中国城市，并将 `OUTFIT_AI_CITY` 与 `OUTFIT_AI_LOCATION_MODE=manual` 保存为手动覆盖；手动模式会优先于浏览器定位。点击“自动定位”会立即请求浏览器定位并清除手动模式，界面显示成功、缓存回退或权限失败状态；定位被拒绝、超时或不可用时再依次回退到有效坐标缓存、已保存城市，最后显示“需要定位或选择城市”。

最近一次推荐、收藏显示和评分表单分别使用 `OUTFIT_AI_LATEST_RECOMMENDATION`、`OUTFIT_AI_FAVORITES`、`OUTFIT_AI_LOOK_RATINGS` 的 `localStorage` 作为当前设备的加载中/请求失败界面后备；有对应推荐历史的收藏、评分与“穿过”均先由 `POST /api/feedback` 确认成功才更新页面，失败保留原服务端状态并显示统一网络/服务端错误。`localStorage` 不是业务事实源，也不会阻止今日页向后端校验当日上下文。

## 3. 五个页面

| 页面 | 源文件 | 用户功能 | 主要后端接口 |
|---|---|---|---|
| 今日 | `ScreenToday.tsx` | 按当前定位/后备城市显示实时本地日期、城市、温度、天气和降雨摘要；从真实衣橱生成 Safe / Fresh / Stretch；每套按后端返回的 3–6 件完整展示（含外搭与配饰），手机端按帽子→颈部配饰→外套/叠穿→上装→下装→鞋履→其他配饰的顺序纵向展示；点击任意单品打开详情浮层，显示该单品图片、名称、颜色和品类；“AI 换一换”只替换被点击的 Look，其他卡片保持不变；收藏、打分和反馈仍使用原始 item 顺序 | `GET /api/weather`、`GET /api/style-references`、`POST /api/recommend`、`POST /api/feedback` |
| 衣橱 | `ScreenWardrobe.tsx` | 三列紧凑卡片（手机一屏约六件）；分类为全部/上装/下装/鞋履/配饰；批量或单张上传真实衣物；等待去背景和中文识图后确认并展示单品；点击单品打开在顶部安全区与底部导航上沿之间居中的紧凑详情，统一限制图片展示高度，显示图片、名称、分类和已识别标签，并支持左右滑动切换当前分类中的相邻单品；详情内可编辑识别字段或删除单品，删除前二次确认。 | `GET /api/wardrobe/items`、`POST /api/wardrobe/upload`、`GET /api/wardrobe/{id}/status`、`POST /api/wardrobe/{id}/confirm`、`PATCH /api/wardrobe/{id}`、`DELETE /api/wardrobe/{id}` |
| 灵感 | `ScreenInspiration.tsx` | 移动端内容画布、页眉和底部主导航统一为同一窄版宽度；长期灵感胶片中的上传卡和前两张预览使用紧凑尺寸，减少首屏占用；单次多选上传长期参考 Look；逐张独立分析并汇总成功/失败数量；沉淀 Style DNA；按季节和场景生成三张非衣橱灵感图 | `GET /api/style-references`、`POST /api/style-references/upload`、`GET /api/style-references/{id}/status`、`GET /api/profile`、`POST /api/inspiration/generate` |
| 灵感存档 | `ScreenArchive.tsx` | 移动端内容画布与底部主导航统一为同一窄版宽度；三列紧凑缩略图浏览；卡片标签显示在图片下方且最多显示 2 个，避免文字覆盖图片；点击图片打开在顶部安全区与底部导航上沿之间居中的紧凑预览，最多显示 8 个标签并自动换行；预览支持左右滑动切换当前筛选列表中的相邻图片；失败任务显示“处理失败”；批量选择和删除长期参考 Look | `GET /api/style-references`、`DELETE /api/style-references/{id}` |
| 我的 | `ScreenProfile.tsx` | 查看 Style DNA 色板、最多 7 个核心关键词和最多 3 个独立的近期风格信号；页内管理标签的置顶、隐藏与合并；分别读取 `recent` 和 `archive` 推荐历史。历史、收藏和评分的 AI 品味备忘录按已解析到的单品渲染缩略图网格（完整 Look 为 3–6 件）；仅当零件单品都无法解析时，旧记录才回退其单张拼图，并可收藏、评分或标记穿过 | `GET/PUT /api/profile`、`GET /api/wardrobe/items`、`GET /api/history?scope=`、`POST /api/feedback` |

## 4. 前端 API 接线

统一接线层：`frontend/src/lib/api.mjs`。

| 前端方法 | HTTP 接口 | 说明 |
|---|---|---|
| `wardrobe()` | `GET /api/wardrobe/items` | 读取已确认真实衣物 |
| `uploadWardrobe(file)` | `POST /api/wardrobe/upload` | 上传真实衣物 |
| `wardrobeStatus(id)` | `GET /api/wardrobe/{id}/status` | 轮询识图状态 |
| `confirmWardrobe(id,data)` | `POST /api/wardrobe/{id}/confirm` | 确认 AI 属性及用户修改 |
| `updateWardrobe(id,data)` | `PATCH /api/wardrobe/{id}` | 保存用户在衣橱详情中修改的名称、分类、颜色、材质、版型及标签 |
| `deleteWardrobe(id)` | `DELETE /api/wardrobe/{id}` | 删除单品记录、原图和去背景图；前端删除前要求用户确认 |
| `references()` | `GET /api/style-references` | 读取长期参考 Look |
| `uploadReference(file)` | `POST /api/style-references/upload` | 上传完整参考 Look，不去背景 |
| `referenceStatus(id)` | `GET /api/style-references/{id}/status` | 轮询 VLM 分析与 Style DNA 合并状态 |
| `deleteReference(id)` | `DELETE /api/style-references/{id}` | 删除参考 Look 和图片 |
| `profile()` / `saveProfile()` | `GET/PUT /api/profile` | 读取或保存完整 Profile；标签操作保留既有字段，并提交 `style_keywords`、`recent_style_signals` 和 `style_tag_preferences` |
| `weather({city,latitude,longitude})` | `GET /api/weather` | 以同一位置上下文读取本地日期、城市、温度、天气和降雨数据 |
| `recommend(data)` | `POST /api/recommend` | 返回天气及 Safe / Fresh / Stretch 三套真实衣橱推荐；今日页会把已获取天气的本地 `local_date` 传入，使普通 recommendation set 复用不依赖服务器时区。普通非 prepared 完整组按同一天无条件复用；prepared 组另受位置、温度带和降雨阈值校验，未命中时仍可在不传 `force_refresh` 的情况下新生成。单卡换装传 `force_refresh:true, refresh_tier:"safe|fresh|stretch"`，后端只生成目标档并返回另外两档原卡片 |
| `feedback(data)` | `POST /api/feedback` | 保存收藏、跳过、穿着或评分反馈；`action` 可省略以仅提交 `rating: 1..5`。已有 Look 的持久反馈必须含服务端 `history_id`，成功后才更新 UI |
| `history({scope,limit} = {})` | `GET /api/history?scope=recent|archive&limit=` | truthy 的 `limit` 会转发，后端接受范围为 1–100；省略或传 `0` 时不带该参数，使用后端默认 `20`。`recent` 读取临时记录，`archive` 读取收藏、穿过或高评分存档；每项含 `scope`、`rating` |
| `generateInspiration(data)` | `POST /api/inspiration/generate` | 一次返回三张独立灵感图 |

灵感参考图批量上传复用现有单文件接口：前端对每张图片分别调用 `uploadReference()` 和 `referenceStatus()`，使用独立结算保证单张失败不影响同批其他图片，完成后只刷新一次灵感库。

识图状态默认每 800ms 轮询一次、最长等待 5 分钟，以覆盖 `rembg` 首次下载本地模型的准备时间；后端同一 API 进程会串行化 rembg 初始化，避免批量上传触发重复模型下载。超过窗口时提示任务仍在后台处理并要求不要重复上传，不再把慢任务误报为识别失败。

衣橱批量导入固定最多同时处理 2 张图片；每张独立执行上传、轮询和确认，单张失败不会中止同批其他图片。处理期间禁用批量导入按钮，并由同步 single-flight guard 忽略重复触发。全部结算后只请求一次权威衣橱列表，并提示成功和失败数量，避免大量图片同时占用 `rembg`、内存和 MiniMax 识图额度。

衣橱展示层把 `outerwear` 归入“上装”、`dress` 归入“下装”，并单列 `accessory` 为“配饰”；后端保留稳定英文类别码，并在确认时将 VLM 常见别名（如 `hat`、`cap`、`baseball cap`）容错归入 `accessory`。VLM 实际读取 rembg 生成的透明 `.nobg.png`；返回的衣物名称、颜色、材质、版型、风格、标签、季节和场景使用简体中文，品牌名和内部 `category` 除外。

衣橱单品详情浮层展示图片、名称、分类和已识别标签，并提供“编辑信息”和“删除单品”入口。编辑沿用后端 PATCH 接口保存用户修正；删除会二次确认，同时删除数据库记录、原图和去背景图。左右滑动预览仍只切换当前分类列表，不会触发修改或删除。

我的页面的色板仅使用统一的名称映射：黑色 `#1B1C19`、白色 `#F7F5EF`、深蓝色 `#162839`、浅蓝色 `#A9C7DD`、灰色 `#8A8D91`、米白色 `#EEE8DA`、米黄色 `#D8C49A`、卡其色 `#B39B72`、棕色 `#7A5337`、绿色 `#647B5B`、红色 `#9A442A`、紫色 `#75627D`。未知颜色只显示文字和中性描边底色，绝不按数组位置猜测颜色。

核心标签摘要最多显示 7 个，近期风格信号作为独立分组最多显示 3 个；置顶标签在各自分组中优先，alias 归一化后同一标签同时 pinned 与 hidden 时仍按 pinned 显示。隐藏标签只在“管理标签”浮层中显示。浮层支持最多置顶 3 个标签、隐藏/恢复，以及选择恰好两个标签并填入一个统一名称来合并。每次确认操作只发起一次完整 Profile 保存；失败时恢复前一份本地状态并显示错误提示。我的页面与侧边栏的学习文案仅基于本地已记录的反馈次数：无反馈时显示“正在学习”，否则显示“已根据 N 次反馈更新”，不展示虚构百分比。

开发环境默认使用相对路径，Vite 将 `/api` 和 `/media` 代理到 `http://localhost:8000`。分离部署时通过 `VITE_API_BASE_URL` 指定后端地址。

今日页会把定位或回退得到的同一 `city` / `latitude` / `longitude` 传给天气和推荐接口；天气栏固定在顶部，底部四项主导航固定在底部并避让 iPhone 安全区，滚动时仍可快速切换页面。上下文就绪后自动请求一次不带 `force_refresh` 的每日推荐；应用从后台恢复或重新显示时，`pageshow` / `visibilitychange` 会在 30 秒节流窗口后再次检查当天推荐。后端先按本地日期无条件复用最近完整的普通 Safe/Fresh/Stretch recommendation set，因此重新打开、导航或天气刷新不会重新生成。每日 06:30 预生成的 prepared 组只是后备候选：仅在不存在普通组时才考虑，且须同时满足距离不超过 20km、温度未跨越 `<=12` / `13–24` / `>=25` 三档、降雨概率同处 50% 阈值的一侧；不命中时即使不传 `force_refresh` 也会新生成。只有用户点击“AI 换一换”才传 `force_refresh: true` 与对应 `refresh_tier`，后端只生成目标档，前端只合并目标卡片，其它卡片、反馈状态和历史 ID 不跳变。并发刷新会合并为一个进行中的请求，过期响应不会覆盖更新结果。天气刷新失败时保留本次会话内上一次成功结果并标注“上次更新”，推荐加载或失败时保留本机缓存作为后备。侧边栏城市按钮不再展示硬编码温度，显示当前实时城市标签，并在城市设置处保留 `© OpenStreetMap contributors` 署名链接。

今日卡片不假定固定三件：逐项渲染后端 `items` 数组中的全部 3–6 件，必含上装、下装、鞋履；渲染副本由 `orderLookItems()` 稳定排序为从头到脚的纵向 editorial flow，原始 `items` 数组用于反馈与历史。每张返回卡片均带 `history_id`，收藏/取消收藏、评分和“穿过”通过该 id 提交。请求失败时不乐观更新收藏、评分或穿过状态，保留服务端已确认状态并显示统一错误。

受影响请求与响应如下（字段名与 `api.mjs` 一致）：

```json
POST /api/recommend
{"occasion":"日常","city":"上海","latitude":31.23,"longitude":121.47,"local_date":"2026-08-04","force_refresh":true,"refresh_tier":"fresh"}

200
{"weather":{},"safe":{"history_id":"...","items":[{}],"reason":"...","weather_fit":"...","occasion_fit":"...","pick_mode":"safe"},"fresh":{},"stretch":{}}

POST /api/feedback
{"history_id":"...","items_worn":["item-1","item-2","item-3"],"action":"saved"}
// 或仅评分：{"history_id":"...","items_worn":[],"rating":5}

GET /api/history?scope=recent
GET /api/history?scope=archive
200 [{"id":"...","item_ids":["item-1"],"action":"shown","wore_it":false,"rating":null,"scope":"recent"}]
```

“我的”页在加载时分别调用 `history({scope:"archive"})` 与 `history({scope:"recent"})`，合并为历史入口；其他调用可传 `history({scope,limit})`，例如 `history({scope:"archive",limit:20})` 会请求 `/api/history?scope=archive&limit=20`。truthy 的 `limit` 会传入，后端接受范围为 1–100；省略或传 `0` 都使用后端默认 `20`。收藏、评分和“标记穿过”沿用相同 server-confirmed `feedback()` 路径。`recent` 是临时记录，`archive` 是已收藏、已穿过或评分至少 4 的记录；仅后端在成功写入新推荐后清理超过 14 本地日的临时记录，前端不做数据清理。

## 5. 两条核心数据流

### 真实衣橱推荐

```text
衣物上传
→ 本地 rembg 去背景
→ MiniMax VLM 提取属性
→ 用户确认
→ FastAPI 硬护栏筛选
→ MiniMax-M3 结合 Style DNA 和参考 Look 生成三档搭配（单卡换一换只生成目标档）
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
- 本地数据库与上传目录默认位于 `~/.outfit-ai/`，可分别通过 `DATABASE_URL`、`UPLOAD_DIR` 覆盖。

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

`frontend/scripts/stitch-contract.mjs` 防止五页结构、四主导航、原版字体依赖、Profile 的显示上限、标签入口和基于证据的学习文案被误改；`frontend/scripts/api-contract.test.mjs` 验证后端数据到 Stitch 页面模型的映射、轮询分支和 Style DNA 的规范色板映射。

当前视觉契约还固定以下已确认的移动端行为：灵感上传文件选择器支持多选；灵感存档在手机端使用三列 `3:4` 缩略图；放大图可再次点击关闭。

## 8. 文档同步规则

以下变化必须在同一提交更新本文：

- 页面、入口、导航、交互或空状态；
- 前端调用的 API 路径、请求体或响应结构；
- 技术栈、依赖、环境变量、启动或测试命令；
- ZIP 基准的有意视觉调整。

后端路由、数据模型或架构变化还必须同步 `docs/SPEC.md`；用户入口和运行方式变化还必须同步 `README.md`；项目约束变化还必须同步 `CLAUDE.md` 与 `AGENTS.md`。
