# Outfit-AI · 当前后端与 API 规格

> 本文件是**当前后端构建的唯一真相源**：架构、数据模型、API 契约、模块规格与边界。最后核对：2026-08-12。
> 配套：[`CLAUDE.md`](../CLAUDE.md)=项目规范（必读）；[`README.md`](../README.md)=概览；[`CURRENT_FRONTEND_INTEGRATION.md`](./frontend/CURRENT_FRONTEND_INTEGRATION.md)=当前前端事实源。
> 文档不重复——架构/数据/API 只在此处定义，CLAUDE.md 与 README 仅引用。

---

## 0. 文档地图
| 文件 | 角色 |
|---|---|
| `CLAUDE.md` | 规范：技术栈、目录约定、命令、安全红线、YAGNI |
| `README.md` | 概览 + 快速开始 |
| `docs/SPEC.md`（本文件） | **当前后端构建真相源** |
| `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` | **当前前端页面、入口、功能与 API 映射** |
| `docs/design.md` / 旧 Stitch PRD | 历史设计资料，已归档 |
| `.env.example` | 环境变量 |

## 1. 当前状态

- FastAPI、SQLAlchemy、SQLite、后台识图任务、MiniMax 服务、测试均已实现。
- 前端已直接采用用户确认的 Stitch React ZIP，共五个页面；详见当前前端事实源。
- 旧 Vue/uni-app 源码与旧 H5 smoke 脚本已删除，当前前端只有 React 运行链。
- 本地运行数据写入 SQLite 与上传目录；v0 仍是单用户、无鉴权。
- 当前自动化基线：后端 76 个测试、前端 9 个 API 测试及 Stitch 视觉契约检查，另有 TypeScript 与生产构建检查。

## 2. 已锁定决策（勿再争论，需改先问 novel）
| 项 | 决策 |
|---|---|
| 后端 | Python 3.11 + FastAPI **同步** + SQLAlchemy 2.0 sync + **SQLite**；后台任务用 `BackgroundTasks` |
| LLM | **MiniMax-M3**，OpenAI SDK 兼容调用；Key 与区域解析复用 mmx 配置 |
| 结构化输出 | M3 造型师使用 **tool use** 强制 schema；VLM 文本响应由 Pydantic 校验 |
| **推荐引擎** | **品味驱动（文本造型师）**，见 §4。**已废弃** OutfAI 规则评分方案 |
| 天气 | Open-Meteo（免 key） |
| 数据 | 5 张 SQLite 表：profile / wardrobe_items / style_references / outfit_history / feedback |
| 前端 | 用户确认的 Stitch ZIP 原版 React 19 + Vite 6 + Tailwind CSS 4，v0 跑 `npm run dev` |
| 用户模型 | **单用户 v0**，`USER_ID=local`，不做鉴权 |
| 项目许可 | MIT（待 novel 终确） |

## 3. 边界
### 3.1 v0 范围内
真实衣物上传、去背景、VLM 属性提取与确认；参考 Look 和长期 Style DNA；天气、季节、场景与心情；Safe/Fresh/Stretch 三档真实衣橱推荐；收藏、评分、反馈和历史；不依赖真实衣橱的三张灵感图。
### 3.2 不做（YAGNI）
GNN、FAISS、多模态 RAG、虚拟试衣、3D、Postgres、Redis/arq、Alembic、多用户鉴权、社交、自动购物、月度审核、公式检测、**数值权重学习表**、打包/OutfitPlans。
### 3.3 安全红线（沿用全局）
不删文件/目录、不改 git 历史、不改 `.env`/keys、不做 DB 破坏性变更、不 `git push`/rebase/reset、不装全局依赖、不公开发布。密钥绝不进代码/日志/提交；后端优先读 `MINIMAX_API_KEY`，否则只读复用 `~/.mmx/config.json`，前端永不可见。
### 3.4 Codex 决策权
- **可自由决定**：函数内部实现、命名（保持模块一致）、错误文案、测试夹具、内部工具拆分。
- **必须问 novel**：新增依赖、改锁定决策、改表结构语义、单文件 >800 行、触碰 `.env`/部署配置。

---

## 4. 核心架构：品味驱动推荐（文本造型师）

> 时尚是主观品味，规则公式产不出"懂你"的推荐。规则退居硬护栏，品味判断全交 LLM。

### 4.1 两阶段 + 校验
```
[推荐请求: occasion, scene?, mood?, season?, style_note?, reference_ids?, city?, locked_item_ids?]
   │
   ▼ STAGE 1 · 硬护栏（规则，确定、便宜）  services/guardrail.py
   │   confirmed items → 天气/季节过滤(Open-Meteo) → locked 强制保留
   │   → 近期重复规避(最近 item_id，跳过 shoes) → 随机保留合格候选
   │   （不按闲置率或利用率排序；凑不齐 top+bottom+shoes → 明确报错）
   ▼ STAGE 2 · 文本造型师（LLM 品味）     services/stylist.py
   │   输入：候选单品的已验证属性 / Style DNA / 品味备忘录 /
   │        参考 Look 分析 / 天气+季节+场景+心情 / 最近 Look / [LOCKED] 标注
   │   任务：仅用这些真实单品，组装 Safe(舒适区)/Fresh(风格内新组合)/Stretch(适度推边界)
   ▼ STAGE 3 · 校验（规则兜底）           services/validator.py
   │   item_id 必须在候选集(防幻觉) · 单套无重复 · 含 top+bottom+shoes
   │   失败 → 错误回灌重试一次（MAX_ATTEMPTS=2，port ai-closet）
   ▼
返回三卡 + 落 outfit_history(action=shown)
```
**规则只活在 Stage 1（过滤）与 Stage 3（校验），"哪套好看"全归 Stage 2 造型师。**
编排：`services/recommend.py` 串起 guardrail→stylist→validator（含重试）。

### 4.2 文本造型师调用契约（services/stylist.py）
- 模型：MiniMax-M3；通过 OpenAI SDK 调用 `/v1/chat/completions`。
- 结构化输出：**tool use** 强制 schema（`tool_choice` 强制调 `propose_looks`），解析 `tool_calls[0].function.arguments` → Pydantic。
- tool schema：`propose_looks(looks:[{tier:"safe"|"fresh"|"stretch", item_ids:[str], reason, weather_fit, occasion_fit}])`；prompt 要求恰好三档各一。
- 图像分工：真实衣物和参考 Look 先由 MiniMax VLM 提取结构化属性；M3 只读取这些文本属性，不重复消耗识图额度。
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

### 5.3 `style_references`
`id`(PK) · `user_id` · `image_path` · `status`(pending/analyzing/ready/failed) · `attempt_count` · `analysis_json` · `ai_raw_response`? · `added_at`

参考 Look 保留完整场景，不执行 rembg；VLM 分析成功后再由 M3 合并进长期 Style DNA。只有包含可见风格证据的非空 VLM 分析才可复用；旧空结果或无效 JSON 在重试时必须重新识图，不能被标记为成功。

### 5.4 `outfit_history`
`id`(PK) · `user_id` · `date` · `occasion`? · `mood`? · `weather_summary`? · `temp`? · `outfit_name`? · `item_ids_json` · `pick_mode`(safe/fresh/stretch) · `reason`? · `collage_path`? · `action`(shown/saved/skipped/worn) · `user_rating`? · `wore_it`(Bool)
（**已删 `base_score`**——规则评分产物，新架构无此数）
索引：`(user_id,date)`、`(user_id,action)`

### 5.5 `feedback`
`id`(PK) · `user_id` · `date` · `items_worn_json` · `occasion`? · `occasion_type`? · `sentiment`? · `compliments_json` · `didnt_work`? · `learnings`?
索引：`(user_id,date)`、`(user_id,occasion_type,date)`

> **已移除** `learned_weights` 表（数值权重学习表，与品味驱动设计冲突）。

---

## 6. API 契约（`routers/*`，统一前缀 `/api`）
### 6.1 wardrobe
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| POST | `/api/wardrobe/upload` | multipart `file`；按图片实际内容校验格式/尺寸（兼容 iPhone MPO/JPG），落盘为标准 JPEG/PNG/WebP + 建 item(pending) + 触发 BackgroundTask | 201 `{id,status:"pending"}` |
| GET | `/api/wardrobe/{id}/status` | 轻量轮询 | 200 `{id,status,name,attempt_count,attributes?}` |
| GET | `/api/wardrobe/items` | 已确认物品，可按 category 过滤 | 200 `[Item]` |
| GET | `/api/wardrobe/{id}` | 单件 | 200 `Item` |
| PATCH | `/api/wardrobe/{id}` | 改/确认；`confirmed_by_user=true` | 200 `Item` |
| POST | `/api/wardrobe/{id}/confirm` | 前端确认 AI 属性及用户修改 | 200 `Item` |
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
| POST | `/api/recommend` | body `{occasion,scene?,mood?,season?,style_note?,reference_ids?[],city?,latitude?,longitude?,locked_item_ids?[]}` → guardrail→stylist→validator | 200 `{weather,safe,fresh,stretch}` |

`recommend` 卡片结构（**无 base_score**）：
```json
{"items":[{"id","name","category","image_url","primary_color"}],
 "reason":"...","weather_fit":"...","occasion_fit":"...",
 "pick_mode":"safe|fresh|stretch"}
```

### 6.4 style references
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| POST | `/api/style-references/upload` | 上传完整参考 Look；按实际图片内容校验而不依赖浏览器 MIME，触发 VLM 分析和 Style DNA 合并 | 201 `{id,status}` |
| GET | `/api/style-references` | 当前用户长期参考 Look | 200 `[StyleReference]` |
| GET | `/api/style-references/{id}/status` | 轮询分析状态 | 200 `StyleReference` |
| POST | `/api/style-references/{id}/retry` | 仅失败任务可重试 | 202 `{id,status}` |
| DELETE | `/api/style-references/{id}` | 删除记录与上传图片 | 204 |

### 6.5 inspiration
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| POST | `/api/inspiration/generate` | body `{reference_ids?[],style_note?,season?,scene}`；先将所选长期灵感的 VLM 结构化分析与 Style DNA 交给 M3 提炼，再调用 image-01 生成，不使用真实衣橱 | 200 `{image_url,looks,requested_count,generated_count,status,disclaimer}`；部分成功时 `status=partial`，只返回已保存图片 |

### 6.6 feedback / history
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| POST | `/api/feedback` | body `{history_id?,items_worn[],action:shown/saved/skipped/worn,...}`；写 feedback+更新 outfit_history.action；`feedback_since_refresh++`，到 8 触发 memo 刷新 | 200 `{ok:true}` |
| GET | `/api/history?limit=20` | 近期穿搭；除历史字段外返回 `rating` 与按日期/单品集合匹配的 `feedback`（`sentiment`、`compliments`、`didnt_work`、`learnings`） | 200 `[OutfitHistory]` |

---

## 7. 模块规格（文件级，标 port/borrow 来源）
- `services/minimax_images.py`：读取环境变量或 `~/.mmx/config.json`；调用 Coding Plan VLM 与 `image-01`，校验和解码响应。
- `services/llm.py`：MiniMax-M3 tool use 结构化文本生成；普通 JSON 调用兼容纯 JSON、Markdown 代码块及 `<think>` 等前置文本，再由 Pydantic 校验；统一错误处理且不泄漏 Key。
- `services/vision.py`：VLM 提取 `ClothingAttributes` 和 `StyleReferenceAnalysis`；衣物 `category` 保持英文内部码，其余面向用户的衣物属性使用简体中文（品牌名可保留原文）；参考 Look 使用短 JSON 模板并拒绝全空分析。来源：Hangar schema + ai-closet 重试
- `services/background.py`：真实衣物先用 rembg 生成透明 PNG；参考 Look 不去背景。首次运行会把约 176MB 的 U²-Net 模型下载并缓存到 `~/.u2net/`，因此首件衣物可能需要 2–3 分钟。
- `services/guardrail.py`：`filter_candidates(items,season,locked_ids,recent_item_ids,limit=15)->list[Item]`（天气季节过滤、locked 强留、近期重复规避、随机候选）。纯规则、可单测
- `services/stylist.py`：`propose(...) -> list[Look]`（M3 文本属性 + 参考分析，tool use）
- `services/validator.py`（**新**）：`validate_looks(looks, candidate_ids)->(ok, error)`（item_id 真实、无重复、含 top+bottom+shoes）。来源：ai-closet 校验链，port 为内部自检 + `tests/test_validation.py`
- `services/recommend.py`（**新**，编排）：guardrail→stylist→validator(重试)→返回三卡
- `services/taste_memo.py`（**新**）：`refresh(db,user_id)`（旧 memo + 新 feedback → LLM → 新 memo）；`seed(onboarding)`（Style DNA+样例图→初版）
- `services/weather.py`：`get_weather(city)->WeatherData`；`_WMO_CONDITION` dict。来源：Hangar（删 Redis）
- `services/history.py`：`get_recent_item_ids`（跳 shoes）、`get_recent_outfits(limit=7)`、`record_outfit`。来源：ai-closet
- `services/collage.py`：`render(images,output_io,item_width=420,padding=6)`。来源：ai-closet（零摩擦 port）
- `services/storage.py`：`Storage` Protocol + `LocalStorage`；按图片字节识别真实格式，iPhone MPO/JPG 读取主画面并重编码为标准 JPEG。
- `services/prompt_builder.py`：Style DNA 草稿、造型师 system/user、memo 刷新 prompts。来源：ai-closet 结构（适配 chat completions）
- `workers/analysis.py`：真实衣物 BackgroundTask（pending→analyzing→rembg→VLM→ready/failed）。
- `workers/style_references.py`：参考 Look BackgroundTask（VLM 分析→M3 合并 Style DNA→ready/failed）；重试只复用有效非空分析，旧空缓存会重新调用 VLM。
- `routers/{wardrobe,profile,recommend,feedback,style_references,inspiration}.py`：见 §6
- `main.py`：FastAPI app、CORS、lifespan `init_db()`、挂载 routers、静态托管 `/media`→upload_dir

---

## 8. 当前实现状态

- 数据层：五张 SQLite 表和索引已实现，由 `init_db()` 初始化。
- 真实衣物：上传、rembg、VLM、轮询、确认、列表、删除已实现；迁移旧 SQLite 时，图片字段中的旧绝对路径会按文件名回落到当前 `UPLOAD_DIR`，继续返回去背景 PNG。
- 长期灵感：参考 Look 上传、VLM 分析、M3 合并 Style DNA、列表、重试、删除已实现。
- 推荐：天气、候选硬护栏、M3 Safe/Fresh/Stretch、item_id 校验、历史记录已实现；衣橱识图返回的中文季节标签会在候选过滤时归一化为内部英文季节值。
- 独立灵感：M3 根据长期灵感分析与 Style DNA 生成结构化提示（含视觉锚点与排除项），`image-01` 开启 prompt optimizer；支持 base64/URL 响应和部分成功，不再回退无关静态图片。
- 反馈：收藏/跳过/穿着/评分、历史与 taste memo 批量刷新已实现。
- 前端：Stitch React 五页和统一 API 接线已实现，详见当前前端事实源。

---

## 9. 验收 / Definition of Done
- [x] `init_db()` 建出五张当前表
- [x] 真实衣物上传→去背景→识图→确认
- [x] 参考 Look→Style DNA
- [x] Safe/Fresh/Stretch 仅返回真实候选 item_id
- [x] 独立灵感一次返回三图并带免责声明
- [x] feedback 与 history 闭环
- [x] 后端测试、ruff、前端契约测试、TypeScript 和生产构建通过
- [x] Stitch React 五页浏览器走查，控制台无错误
- [ ] 使用用户真实图片与 MiniMax 配额完成一次人工端到端验收
- [ ] 生产对象存储、HTTPS 与部署

## 10. 部署卡点

后端需要 HTTPS；生产图片需从本地目录迁移到对象存储。微信小程序/App 如需上线，另行选择能保留当前 React 界面与交互的容器方案，不回退旧 uni-app 设计。

## 11. 署名（务必保留）
- 数据模型：`Data model inspired by googlarz/fashion-skill (CC BY 4.0)`（仅抽象字段，不抄 prompt）
- 上传状态机/Open-Meteo：`from Gurshaan-Deol/Hangar (MIT)`
- LLM 调用/校验/拼图/历史：`from jonnykate/ai-closet (MIT)`
- ~~推荐算法 OutfAI~~ —— **已废弃**（改品味驱动后不再使用 OutfAI 评分，无需署名）
