# Outfit-AI · 实现规格与执行计划（交付给 Codex）

> 本文件是**后端构建的唯一真相源**：架构、数据模型、API 契约、模块规格、执行计划、边界。
> 配套：[`CLAUDE.md`](../CLAUDE.md)=项目规范（必读）；[`README.md`](../README.md)=概览；[`docs/design.md`](./design.md)=前端 UI-UX 设计。
> 文档不重复——架构/数据/API 只在此处定义，CLAUDE.md 与 README 仅引用。

---

## 0. 文档地图
| 文件 | 角色 |
|---|---|
| `CLAUDE.md` | 规范：技术栈、目录约定、命令、安全红线、YAGNI |
| `README.md` | 概览 + 快速开始 |
| `docs/SPEC.md`（本文件） | **后端构建真相源** |
| `docs/design.md` | 前端 UI-UX 设计（Phase 6 前 brainstorm） |
| `.env.example` | 环境变量 |

## 1. 现状盘点（Codex 接手前先看）
已就位：`CLAUDE.md`/`README.md`/`.gitignore`/`.env.example`/`docs/SPEC.md`/`docs/design.md`；`backend/pyproject.toml`、`backend/src/outfit_ai/__init__.py`、`config.py`、`db.py`（基础脚手架，可改可重写）；`frontend/`（uni-app Vue3+Vite+TS 模板）。
待实现：`models.py`、`schemas.py`、`routers/*`、`services/*`、`workers/*`、`main.py`、前端 4 页面、测试。

## 2. 已锁定决策（勿再争论，需改先问 novel）
| 项 | 决策 |
|---|---|
| 后端 | Python 3.11 + FastAPI **同步** + SQLAlchemy 2.0 sync + **SQLite**；后台任务用 `BackgroundTasks` |
| LLM | **MiniMax-M3**，`base_url=https://api.minimaxi.com/v1`，OpenAI SDK 兼容，复用 mmx key |
| 结构化输出 | M3 不支持 `response_format:json_object`/Responses API → **tool use** 强制 schema（识图与造型师都用） |
| **推荐引擎** | **品味驱动（多模态造型师）**，见 §4。**已废弃** OutfAI 规则评分方案 |
| 天气 | Open-Meteo（免 key） |
| 数据 | 4 张 SQLite 表：profile(含 taste_memo) / wardrobe_items / outfit_history / feedback（**已删 learned_weights**） |
| 前端 | uni-app Vue3+Vite+TS，v0 跑 `dev:h5` |
| 用户模型 | **单用户 v0**，`USER_ID=local`，不做鉴权 |
| 项目许可 | MIT（待 novel 终确） |

## 3. 边界
### 3.1 v0 范围内
单品上传 + AI 属性提取 + 人工确认；Style DNA 引导式生成；品味备忘录；天气/场合/心情输入；Safe/Fresh/Stretch 三档推荐（造型师品味驱动）；锁定/换一件/反馈/今天穿了；近期重复规避；搭配图。
### 3.2 不做（YAGNI）
GNN、FAISS、多模态 RAG、虚拟试衣、3D、Postgres、Redis/arq、Alembic、多用户鉴权、社交、自动购物、月度审核、公式检测、**数值权重学习表**、打包/OutfitPlans。
### 3.3 安全红线（沿用全局）
不删文件/目录、不改 git 历史、不改 `.env`/keys、不做 DB 破坏性变更、不 `git push`/rebase/reset、不装全局依赖、不公开发布。密钥绝不进代码/日志/提交；MiniMax key 只从 env 读，前端永不可见。
### 3.4 Codex 决策权
- **可自由决定**：函数内部实现、命名（保持模块一致）、错误文案、测试夹具、内部工具拆分。
- **必须问 novel**：新增依赖、改锁定决策、改表结构语义、单文件 >800 行、触碰 `.env`/部署配置。

---

## 4. 核心架构：品味驱动推荐（多模态造型师）

> 时尚是主观品味，规则公式产不出"懂你"的推荐。规则退居硬护栏，品味判断全交 LLM。

### 4.1 两阶段 + 校验
```
[推荐请求: occasion, mood, city?, locked_item_ids?]
   │
   ▼ STAGE 1 · 硬护栏（规则，确定、便宜）  services/guardrail.py
   │   confirmed items → 天气/季节过滤(Open-Meteo) → locked 强制保留
   │   → 近期重复规避(最近 3 套 item_id，跳过 shoes) → 封顶 ~12–15 件
   │   （按"最近未穿 + 贴合今日天气"裁剪；凑不齐 top+bottom+shoes → 少出卡）
   ▼ STAGE 2 · 多模态造型师（LLM 品味）   services/stylist.py
   │   输入：候选单品照片(base64)+属性 / Style DNA / 品味备忘录 /
   │        天气摘要+场合+心情 / 最近 5–7 套 Look / [LOCKED] 标注
   │   任务：仅用这些真实单品，组装 Safe(舒适区)/Fresh(风格内新组合)/Stretch(适度推边界)
   ▼ STAGE 3 · 校验（规则兜底）           services/validator.py
   │   item_id 必须在候选集(防幻觉) · 单套无重复 · 含 top+bottom+shoes
   │   失败 → 错误回灌重试一次（MAX_ATTEMPTS=2，port ai-closet）
   ▼
返回三卡 + collage + 落 outfit_history(action=shown)
```
**规则只活在 Stage 1（过滤）与 Stage 3（校验），"哪套好看"全归 Stage 2 造型师。**
编排：`services/recommend.py` 串起 guardrail→stylist→validator（含重试）。

### 4.2 多模态造型师调用契约（services/stylist.py）
- 模型：MiniMax-M3，OpenAI SDK，`base_url=https://api.minimaxi.com/v1`。
- 结构化输出：**tool use** 强制 schema（`tool_choice` 强制调 `propose_looks`），解析 `tool_calls[0].function.arguments` → Pydantic。与识图属性提取同模式。
- tool schema：`propose_looks(looks:[{tier:"safe"|"fresh"|"stretch", item_ids:[str], reason, weather_fit, occasion_fit}])`；prompt 要求恰好三档各一。
- 图像：候选单品照片作 `image_url` 内容块（base64 data URL），每件压到 ≤~500KB、合计 ≤15 件（控 64MB 请求上限与 token 成本）。
- system prompt：造型师人格 + 硬规则（只用给定单品、三档各一、不重复近期 Look、locked 必含）。
- 失败重试：Stage 3 不过 → 错误回灌再调一次；两次失败抛错给前端。

### 4.3 品味备忘录（taste memo）—— "越用越懂"的载体（services/taste_memo.py）
- **是什么**：LLM 维护的自然语言档案，记录"我对你品味的理解"。段落：偏好的颜色/调色板、偏好的版型/廓形、常用搭配公式、忌讳项、近期想突破的方向、从反馈学到的东西。
- **存哪**：`profile.taste_memo`(Text) + `taste_memo_updated_at` + `feedback_since_refresh`(计数器)。`feedback` 表与 `outfit_history.action` 是刷新输入。
- **怎么更新**：触发式——`POST /api/feedback` 时 `feedback_since_refresh += 1`，到 **8** 触发一次 LLM 刷新（读旧 memo + 新反馈 → 输出新 memo），`BackgroundTasks` 执行，刷新后计数清零。另有 `POST /api/profile/taste-memo/refresh` 手动触发。v0 不上 cron。
- **冷启动**：onboarding 由 Style DNA + 风格样例图 LLM 生成初版 memo。
- **版本**：v0 直接覆盖更新；旧版归档留作后期"风格漂移"分析（YAGNI，先不做）。

---

## 5. 数据模型（写 `backend/src/outfit_ai/models.py`）
> 抽象自 `googlarz/fashion-skill`（CC BY 4.0，**仅字段结构，不抄 prompt**）。JSON 列用 `Text` 存 JSON 字符串。

### 5.1 `profile`（Style DNA + 品味备忘录，1 行/用户）
`user_id`(PK) · `body_json`(Text) · `color_season`? · `color_undertone`? · `palette_json` · `style_keywords_json` · `avoids_json` · `preferred_colors_json`（onboarding 结构化偏好，喂造型师作上下文） · `preferred_styles_json` · `brand_sizes_json` · `city`? · `climate`? · `occasions_json` · `budget_*_cents` ×3 · `learned_from_feedback_json` · `formulas_json` · `last_profile_refresh`? · **`taste_memo`**(Text) · **`taste_memo_updated_at`**(DateTime?) · **`feedback_since_refresh`**(Integer default 0)

### 5.2 `wardrobe_items`（含上传状态机）
`id`(PK) · `user_id` · `name`? · `category`? · `primary_color`? · `secondary_color`? · `material`? · `fit`? · `formality`? · `style_json` · `tags_json` · `seasons_json` · `occasions_json` · `versatility`? · `brand`? · `size`? · `image_path` · `status`(pending/analyzing/ready/failed) · `attempt_count` · `ai_raw_response`? · `duplicate_of`? · `duplicate_confidence`? · `confirmed_by_user`(Bool) · `added_at`
索引：`(user_id,category)`、`(user_id,status)`、`(user_id,confirmed_by_user)`

### 5.3 `outfit_history`
`id`(PK) · `user_id` · `date` · `occasion`? · `mood`? · `weather_summary`? · `temp`? · `outfit_name`? · `item_ids_json` · `pick_mode`(safe/fresh/stretch) · `reason`? · `collage_path`? · `action`(shown/saved/skipped/worn) · `user_rating`? · `wore_it`(Bool)
（**已删 `base_score`**——规则评分产物，新架构无此数）
索引：`(user_id,date)`、`(user_id,action)`

### 5.4 `feedback`
`id`(PK) · `user_id` · `date` · `items_worn_json` · `occasion`? · `occasion_type`? · `sentiment`? · `compliments_json` · `didnt_work`? · `learnings`?
索引：`(user_id,date)`、`(user_id,occasion_type,date)`

> **已移除** `learned_weights` 表（数值权重学习表，与品味驱动设计冲突）。

---

## 6. API 契约（`routers/*`，统一前缀 `/api`）
### 6.1 wardrobe
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| POST | `/api/wardrobe/upload` | multipart `file`；校验 mime/size；落盘+建 item(pending)+触发 BackgroundTask | 201 `{id,status:"pending"}` |
| GET | `/api/wardrobe/{id}/status` | 轻量轮询 | 200 `{id,status,name,attempt_count,attributes?}` |
| GET | `/api/wardrobe/items` | 已确认物品，可按 category 过滤 | 200 `[Item]` |
| GET | `/api/wardrobe/{id}` | 单件 | 200 `Item` |
| PATCH | `/api/wardrobe/{id}` | 改/确认；`confirmed_by_user=true` | 200 `Item` |
| POST | `/api/wardrobe/{id}/retry` | 仅 failed 或 stuck(>10min)；先 enqueue 再 commit | 202 `{id,status}` |
| DELETE | `/api/wardrobe/{id}` | 删物品+图片 | 204 |
| GET | `/api/wardrobe/collage?item_ids=a,b,c` | Pillow 拼图 | 200 `image/png` |

### 6.2 profile
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| GET | `/api/profile` | 取 Style DNA+memo | 200 `Profile` |
| PUT | `/api/profile` | upsert（手动编辑保存） | 200 `Profile` |
| POST | `/api/profile/style-dna/draft` | body `{samples:[url], text}` → LLM 草稿 | 200 `{draft:Profile}` |
| POST | `/api/profile/taste-memo/refresh` | 手动触发 LLM 刷新品味备忘录 | 202 `{ok:true}` |

### 6.3 recommend
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| GET | `/api/weather?city=` | Open-Meteo；内存缓存 30min | 200 `{temp,feels_like,condition,humidity,wind_speed,is_daytime,temp_max,temp_min}` |
| POST | `/api/recommend` | body `{occasion,mood,city?,locked_item_ids?[]}` → guardrail→stylist→validator | 200 `{weather,safe,fresh,stretch}` |

`recommend` 卡片结构（**无 base_score**）：
```json
{"items":[{"id","name","category","image_url","primary_color"}],
 "reason":"...","weather_fit":"...","occasion_fit":"...",
 "pick_mode":"safe|fresh|stretch"}
```

### 6.4 feedback / history
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| POST | `/api/feedback` | body `{history_id?,items_worn[],action:shown/saved/skipped/worn,...}`；写 feedback+更新 outfit_history.action；`feedback_since_refresh++`，到 8 触发 memo 刷新 | 200 `{ok:true}` |
| GET | `/api/history?limit=20` | 近期穿搭 | 200 `[OutfitHistory]` |

---

## 7. 模块规格（文件级，标 port/borrow 来源）
- `services/llm.py`：`get_client()`；`generate_json(system,user,schema_hint,max_attempts=2)->dict`（prompt+json.loads+错误回灌重试）；`chat_multimodal(messages, tools, tool_choice)->resp`（造型师/识图共用）
- `services/vision.py`：`ClothingAttributes` Pydantic；`extract(image_path)->ClothingAttributes`（base64+M3 tool use）。来源：Hangar schema + ai-closet 重试
- `services/guardrail.py`（**新**）：`filter_candidates(db,user_id,weather,locked_ids,history)->list[Item]`（天气/季节过滤、locked 强留、近期重复规避、封顶~15）。纯规则、可单测
- `services/stylist.py`（**新**）：`propose(candidates, profile, memo, weather, occasion, mood, recent_looks, locked_ids)->list[Look]`（M3 多模态 tool use）
- `services/validator.py`（**新**）：`validate_looks(looks, candidate_ids)->(ok, error)`（item_id 真实、无重复、含 top+bottom+shoes）。来源：ai-closet 校验链，port 为内部自检 + `tests/test_validation.py`
- `services/recommend.py`（**新**，编排）：guardrail→stylist→validator(重试)→返回三卡
- `services/taste_memo.py`（**新**）：`refresh(db,user_id)`（旧 memo + 新 feedback → LLM → 新 memo）；`seed(onboarding)`（Style DNA+样例图→初版）
- `services/weather.py`：`get_weather(city)->WeatherData`；`_WMO_CONDITION` dict。来源：Hangar（删 Redis）
- `services/history.py`：`get_recent_item_ids`（跳 shoes）、`get_recent_outfits(limit=7)`、`record_outfit`。来源：ai-closet
- `services/collage.py`：`render(images,output_io,item_width=420,padding=6)`。来源：ai-closet（零摩擦 port）
- `services/storage.py`：`Storage` Protocol + `LocalStorage`；预留 `OSSStorage` 占位
- `services/prompt_builder.py`：Style DNA 草稿、造型师 system/user、memo 刷新 prompts。来源：ai-closet 结构（适配 chat completions）
- `workers/analysis.py`：`analyze_item(item_id)` BackgroundTask（pending→analyzing→ready/failed）。来源：Hangar 状态机（BackgroundTasks 替代 arq）
- `routers/{wardrobe,profile,recommend,feedback}.py`：见 §6
- `main.py`：FastAPI app、CORS、`startup:init_db()`、挂载 routers、静态托管 `/media`→upload_dir

---

## 8. 执行计划（逐阶段，含验收）
- **Phase 1 数据层**：§5 四表 + 索引；`init_db()` 建表。验收：建出 sqlite+四表。
- **Phase 2 照片录入**：`storage.py`/`vision.py`/`workers/analysis.py`/`routers/wardrobe.py`/`schemas.py`。验收：上传→轮询 ready→PATCH 确认→GET items 见属性。
- **Phase 3 天气 + Style DNA + memo 冷启动**：`weather.py`/`prompt_builder.py`/`llm.py`/`taste_memo.seed`/`routers/profile.py`。验收：weather 返回真实值；style-dna/draft 出可编辑草稿；onboarding 生成初版 taste_memo。
- **Phase 4 推荐器** ★：`guardrail.py`/`stylist.py`/`validator.py`/`recommend.py`（含 `__main__` 自检）。验收：`python -m outfit_ai.services.recommend` 自检过；POST recommend 返回三档互异。
- **Phase 5 反馈闭环 + 备忘录刷新**：`routers/feedback.py`、`taste_memo.refresh`、`collage.py`。验收：POST feedback(worn)→`feedback_since_refresh++`；累计 8 触发 memo 刷新；再推荐体现 memo 影响；collage 出 PNG。
- **Phase 6 前端 H5**：见 `docs/design.md`；4 页面 + api 封装 + Pinia。验收：`dev:h5` 跑通全闭环。
- **Phase 7 收尾**：`tests/test_guardrail.py`、`tests/test_validation.py`、README 部署备注。验收：pytest 全绿；e2e 通过。

---

## 9. 验收 / Definition of Done
- [ ] `init_db()` 建出 4 表（含 taste_memo 字段，无 learned_weights）
- [ ] 上传→识图→确认 通（真实衣物图）
- [ ] Style DNA 草稿 + 初版 taste_memo 生成
- [ ] recommend 返回 Safe/Fresh/Stretch 三档互异，含 LLM 文案，无 base_score
- [ ] feedback 累计触发 memo 刷新；再推荐有变化
- [ ] collage 返回 PNG
- [ ] `python -m outfit_ai.services.recommend` 自检通过
- [ ] `pytest` 全绿
- [ ] 前端 H5 全闭环
- [ ] 署名 4 来源保留

## 10. 部署卡点（小程序上线，尽早提醒 novel）
后端 HTTPS 域名 + ICP 备案；微信公众平台配 request/uploadFile/downloadFile 合法域名；图片走阿里云 OSS（`storage.py` 已留接口）；前端主包 ≤2MB。

## 11. 署名（务必保留）
- 数据模型：`Data model inspired by googlarz/fashion-skill (CC BY 4.0)`（仅抽象字段，不抄 prompt）
- 上传状态机/Open-Meteo：`from Gurshaan-Deol/Hangar (MIT)`
- LLM 调用/校验/拼图/历史：`from jonnykate/ai-closet (MIT)`
- ~~推荐算法 OutfAI~~ —— **已废弃**（改品味驱动后不再使用 OutfAI 评分，无需署名）
