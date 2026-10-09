# Outfit-AI · 当前后端与 API 规格

> 本文件是**当前后端构建的唯一真相源**：架构、数据模型、API 契约、模块规格与边界。最后核对：2026-09-04。
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
- 本地运行数据默认写入 `~/.outfit-ai/outfit_ai.db` 与 `~/.outfit-ai/uploads`，跨 worktree 保持稳定；`DATABASE_URL`、`UPLOAD_DIR` 可覆盖且路径会展开为绝对路径。v0 仍是单用户、无鉴权。
- 当前自动化基线包括后端测试、前端 API/视觉契约测试、TypeScript 与生产构建检查。

## 2. 已锁定决策（勿再争论，需改先问 novel）
| 项 | 决策 |
|---|---|
| 后端 | Python 3.11 + FastAPI **同步** + SQLAlchemy 2.0 sync + **SQLite**；后台任务用 `BackgroundTasks` |
| LLM | **MiniMax-M3**，OpenAI SDK 兼容调用；Key 与区域解析复用 mmx 配置 |
| 结构化输出 | M3 造型师使用 **tool use** 强制 schema；VLM 文本响应由 Pydantic 校验 |
| **推荐引擎** | **品味驱动（文本造型师）**，见 §4。**已废弃** OutfAI 规则评分方案 |
| 天气 | Open-Meteo（免 key） |
| 数据 | 6 张 SQLite 表：profile / wardrobe_items / style_references / outfit_history / feedback / feedback_events |
| 前端 | 用户确认的 Stitch ZIP 原版 React 19 + Vite 6 + Tailwind CSS 4，v0 跑 `npm run dev` |
| 用户模型 | **单用户 v0**，`USER_ID=local`，不做鉴权 |
| 本地存储 | 默认 `~/.outfit-ai/`；支持 `DATABASE_URL`、`UPLOAD_DIR` 环境覆盖 |
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
   │   confirmed items → 天气/季节/手动覆盖过滤(Open-Meteo) → locked 强制保留
   │   → 按使用次数、最近使用时间和未使用优先级确定候选顺序
   │   → 计算 Safe/Fresh/Stretch 的低暴露覆盖目标
   │   （不随机截断；凑不齐 top+bottom+shoes → 明确报错）
   ▼ STAGE 2 · 文本造型师（LLM 品味）     services/stylist.py
   │   输入：候选单品的已验证属性 / Style DNA / 品味备忘录 /
   │        参考 Look 分析 / 天气+季节+场景+心情 / 最近 Look / [LOCKED] 标注
   │   任务：仅用这些真实单品，组装 Safe(舒适区)/Fresh(风格内新组合)/Stretch(适度推边界)
   ▼ STAGE 3 · 校验（规则兜底）           services/validator.py
   │   item_id 必须在候选集(防幻觉) · 单套 3–6 件且无重复 · 含 top+bottom+shoes
   │   失败 → 错误回灌重试一次（MAX_ATTEMPTS=2，port ai-closet）
   ▼
返回三卡 + 落 outfit_history(action=shown)
```
**规则只活在 Stage 1（过滤）与 Stage 3（校验），"哪套好看"全归 Stage 2 造型师。**
编排：`services/recommend.py` 串起 guardrail→stylist→validator（含重试）。

### 4.2 文本造型师调用契约（services/stylist.py）
- 模型：MiniMax-M3；通过 OpenAI SDK 调用 `/v1/chat/completions`。
- 结构化输出：**tool use** 强制 schema（`tool_choice` 强制调 `propose_looks` 或单卡刷新时的 `propose_one_look`），解析 `tool_calls[0].function.arguments` → Pydantic。
- tool schema：普通请求使用 `propose_looks(looks:[{tier:"safe"|"fresh"|"stretch", item_ids:[str], reason, weather_fit, occasion_fit}])`；单卡刷新使用 `propose_one_look(look:{tier,item_ids,reason,weather_fit,occasion_fit})`，且 tier 必须与请求一致；`reason` 为一句话搭配思路，长度 1–50 个字符，偶发超长输入会在校验前压缩为完整首句或带省略号的短句。MiniMax 偶尔将 `item_ids` 数组包装为 `{ "item": [...] }`，解析层只展开该已知包装形态，随后仍执行完整校验。
- 图像分工：真实衣物和参考 Look 先由 MiniMax VLM 提取结构化属性；M3 只读取这些文本属性，不重复消耗识图额度。
- system prompt：造型师人格 + 硬规则（只用给定单品、三档各一、不重复近期 Look、locked 必含）；Safe 优先低风险与高利用率，Fresh 至少使用一个天气有效的低暴露单品，Stretch 使用不同的低暴露单品并明确说明突破点。候选充足时三档不共用任意单品，并由校验器检查颜色、版型或风格标签差异，避免只做配饰替换。候选上下文单独提供 `thickness`：高温高湿优先轻薄，低温优先适中或厚实，轻薄单品只有在叠穿成立时才使用；缺失厚薄标签不视为适中。
- 失败重试：Stage 3 校验不过或 M3 未返回有效工具调用 → 错误回灌再调一次；两次失败时，若仅违反“三档不共用/风格差异”这类质量增强规则，而类别、真实 item_id、锁定单品、覆盖目标和近 30 天完整 Look 去重等硬护栏全部通过，则降级返回完整三档并记录 warning；硬护栏失败仍抛错给前端。造型师优先读取工具调用，模型改用普通文本回复时自动从文本中提取同等 JSON 作为兜底。每日预生成最多整体执行 3 次，每次失败回滚事务。

### 4.3 品味备忘录（taste memo）—— "越用越懂"的载体（services/taste_memo.py）
- **是什么**：LLM 维护的自然语言档案，记录"我对你品味的理解"。段落：偏好的颜色/调色板、偏好的版型/廓形、常用搭配公式、忌讳项、近期想突破的方向、从反馈学到的东西。
- **存哪**：`profile.taste_memo`(Text) + `taste_memo_updated_at` + `feedback_since_refresh`(计数器) + `taste_memo_last_change` + `taste_memo_source_feedback_ids_json` + `taste_memo_source_event_ids_json` + `taste_memo_refresh_status/error` + `taste_memo_revision`(手动修正版本栅栏)。`feedback` 表保存稳定的 `history_id`、最终 `action/rating`、`created_at`、`updated_at` 及喜欢/不喜欢/想调整三类信号；`feedback_events` 表保存每次真实可学习变化的不可变事件快照。
- **怎么更新**：只有最终事实发生真实变化且包含可学习信号时，`POST /api/feedback` 才增加计数、更新时间戳并插入一条 `feedback_events`；同一 history 重复收藏、取消、穿过或重复评分不会重复计数，评分编辑和动作变化会分别形成可学习事件。达到后端返回的 `feedback_batch_size=4` 后由 `BackgroundTasks` 刷新，批次按 `feedback_events.event_at` 取样；同一 history 的多次真实变化可组成同一批。旧版 feedback 行没有事件时，刷新前按其最终事实回填一条 `legacy-{feedback_id}` 等价事件。成功清零并记录本轮变化、来源 feedback/event id；失败保留计数并公开 `failed/error`，可由 retry 接口再次执行。手动修正会递增 `taste_memo_revision`，在途刷新使用版本栅栏，不能覆盖手动修正或清掉其后的待学习反馈。另有 `POST /api/profile/taste-memo/refresh` 手动触发。v0 不上 cron。
- **冷启动**：onboarding 由 Style DNA + 风格样例图 LLM 生成初版 memo。
- **版本**：v0 直接覆盖更新；旧版归档留作后期"风格漂移"分析（YAGNI，先不做）。

---

## 5. 数据模型（写 `backend/src/outfit_ai/models.py`）
> 抽象自 `googlarz/fashion-skill`（CC BY 4.0，**仅字段结构，不抄 prompt**）。JSON 列用 `Text` 存 JSON 字符串。

### 5.1 `profile`（Style DNA + 品味备忘录，1 行/用户）
`user_id`(PK) · `body_json`(Text) · `color_season`? · `color_undertone`? · `palette_json` · `style_keywords_json` · `avoids_json` · `preferred_colors_json`（onboarding 结构化偏好，喂造型师作上下文） · `preferred_styles_json` · `brand_sizes_json` · `city`? · `climate`? · `occasions_json` · `budget_*_cents` ×3 · `learned_from_feedback_json` · `formulas_json` · `last_profile_refresh`? · **`taste_memo`**(Text) · **`taste_memo_updated_at`**(DateTime?) · **`feedback_since_refresh`**(Integer default 0) · `taste_memo_last_change` · `taste_memo_source_feedback_ids_json` · `taste_memo_source_event_ids_json` · `taste_memo_refresh_status/error` · **`taste_memo_revision`**(Integer default 0)

不新增学习权重表：`learned_from_feedback_json` 继续兼容旧版 `list[str]`（直接作为 `learnings` 读取），新版为以下 version-1 封套；损坏数据安全回退为空值。反馈事实与刷新状态使用上文列出的加法式 SQLite 列迁移。

```json
{"version":1,"learnings":[],"recent_style_signals":[],"style_tag_preferences":{"pinned":[],"hidden":[],"aliases":{}},"last_location":null}
```

`learnings` 保持原有公开字段 `learned_from_feedback`。Profile 另公开 `recent_style_signals`、`style_tag_preferences` 与 `last_location`；字符串去重且保序，`pinned` 与 `recent_style_signals` 最多各 3 个。

### 5.2 `wardrobe_items`（含上传状态机）
`id`(PK) · `user_id` · `name`? · `category`? · `primary_color`? · `secondary_color`? · `material`? · `fit`? · `formality`? · `style_json` · `tags_json` · `seasons_json` · `occasions_json` · `versatility`? · `brand`? · `size`? · `image_path` · `status`(pending/analyzing/ready/failed) · `attempt_count` · `ai_raw_response`? · `duplicate_of`? · `duplicate_confidence`? · `confirmed_by_user`(Bool) · `added_at`
索引：`(user_id,category)`、`(user_id,status)`、`(user_id,confirmed_by_user)`

### 5.3 `style_references`
`id`(PK) · `user_id` · `image_path` · `status`(pending/analyzing/ready/failed) · `attempt_count` · `analysis_json` · `ai_raw_response`? · `added_at`

参考 Look 保留完整场景，不执行 rembg；VLM 分析成功后再由 M3 合并进长期 Style DNA。只有包含可见风格证据的非空 VLM 分析才可复用；旧空结果或无效 JSON 在重试时必须重新识图，不能被标记为成功。

### 5.4 `outfit_history`
`id`(PK) · `user_id` · `date` · `occasion`? · `mood`? · `weather_summary`? · `temp`? · `outfit_name`? · `item_ids_json` · `pick_mode`(safe/fresh/stretch) · `reason`? · `collage_path`? · `context_json`?(Text JSON) · `action`(shown/saved/skipped/worn/prepared) · `user_rating`? · `wore_it`(Bool)
（**已删 `base_score`**——规则评分产物，新架构无此数）
索引：`(user_id,date)`、`(user_id,action)`

`context_json` 仅在保存带上下文的推荐时写入；其对象键固定为 `latitude`、`longitude`（均为粗略坐标）、`city`、`target_date`、`weather`、`local_date`、`prepared_at`、`prepared`、`recommendation_set_id`、`recommendation_set_created_at`、`weather_fit`、`occasion_fit`、`wardrobe_risk`、`missing_categories`。一次成功生成的 Safe/Fresh/Stretch 三档共享一个 `recommendation_set_id`；同一天的普通请求只复用最新**完整**三档组，旧行没有 set id 时才按每档最新记录兼容回退。完整 `force_refresh=true` 请求另建一组；带 `refresh_tier=safe|fresh|stretch` 的单卡刷新只调用 M3 生成目标档，并在当前完整普通组（无普通组时为 prepared 组）中追加目标档最新 history，另外两档原记录与 history_id 不变；没有完整组时返回明确的重新加载错误，不退化为三档生成。任何不完整或生成失败的组均不可复用，单卡失败不写入新 history。`prepared=true` 标记由每日预生成写入，即使之后用户操作把 `action` 改为 `shown` 或 `worn`，当天仍可作为 prepared 候选；普通 `shown` 推荐不会带此标记。`prepared` action 是每日预生成的内部历史状态，不是反馈接口可提交的用户操作。应用启动不因本功能迁移、改写或清理既有用户数据；运行期保留清理只在成功写入新推荐后执行，且仅作用于 §6.6 定义的临时记录。

### 5.5 `feedback`
`id`(PK) · `user_id` · `history_id`?（推荐 identity） · `date` · `items_worn_json` · `action`? · `rating`? · `created_at` · **`updated_at`** · `occasion`? · `occasion_type`? · `sentiment`? · `positive_signals_json` · `negative_signals_json` · `adjustment_signals_json` · `compliments_json`（兼容正向字段） · `didnt_work`? · `learnings`? · `wore_it`
索引：`(user_id,date)`、`(user_id,occasion_type,date)`；有 history identity 的反馈按 `user_id + history_id` 更新最终事实，不按同日单品集合猜关联。

### 5.6 `feedback_events`（不可变学习事件账本）
`id`(PK) · `feedback_id` · `user_id` · `history_id`? · `date` · `event_at` · `items_worn_json` · `action`? · `rating`? · `occasion`? · `occasion_type`? · `sentiment`? · `positive_signals_json` · `negative_signals_json` · `adjustment_signals_json` · `didnt_work`? · `learnings`? · `wore_it`
索引：`(user_id,event_at)`、`(feedback_id,event_at)`。每行对应一次真实、可学习的最终事实变化；应用只插入和查询，不更新或删除。刷新按 `event_at` 倒序取样并要求事件数等于 `feedback_since_refresh`；legacy feedback 没有事件时，首次刷新前回填一条 `legacy-{feedback_id}` 等价事件，回填保留原 history、动作、评分和信号，不复制重复提交。

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
| POST | `/api/profile/taste-memo/retry` | 刷新失败后保留待学习反馈并重试 | 202 `{ok:true}` |
| POST | `/api/profile/taste-memo/correct` | 用户纠正服务端自然语言 memo | 200 `Profile` |

`Profile` 保持既有字段，并新增 `recent_style_signals:list[str]`、`style_tag_preferences:{pinned:list[str],hidden:list[str],aliases:object}`、`last_location:object|null`、`feedback_batch_size`、`feedback_remaining`、`taste_memo_last_change`、`taste_memo_source_feedback_ids`、`taste_memo_source_event_ids`、`taste_memo_refresh_status/error`、`taste_memo_revision`。旧客户端仍可只提交既有字段，未提交的新字段会保留现有值；普通 Profile PUT 不拥有也不能覆盖 `taste_memo` 及其服务端状态字段。

### 6.3 recommend
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| GET | `/api/weather?city=&latitude=&longitude=&target_date=` | 输入经纬度先四舍五入至三位再用于 Open-Meteo、Nominatim、缓存和下游上下文；`target_date` 只能是今天至未来 14 天，天气从 16 日 forecast 的 daily 数组选择目标日；多城市候选返回 409 `{message,candidates:[{name,latitude,longitude,...}]}`，不能静默采用第一项；反向地理编码在市辖区/县场景优先显示上级直辖市名称，手动城市保留用户输入；天气内存缓存 30min，反查城市缓存 24h，反查失败不影响天气 | 200 `{temp,feels_like,condition,humidity,wind_speed,is_daytime,temp_max,temp_min,city,target_date,local_date,timezone,precipitation,rain,precipitation_probability_max,precipitation_sum,rain_window}` |
| POST | `/api/recommend` | body `{occasion,scene?,mood?,season?,style_note?,reference_ids?[],city?,latitude?,longitude?,target_date?,local_date?,locked_item_ids?[],force_refresh?:false,refresh_tier?:safe|fresh|stretch}`；`target_date` 只能是今天至未来 14 天；显式城市不继承 Profile 旧坐标。每套 Look 为 3–6 件，必须含 top+bottom+shoes，叠穿和配饰按需加入、不凑数；普通请求先复用绑定同一城市/目标日期的完整三档组，再按 prepared 的坐标、温度带和降雨阈值判断复用，否则 guardrail→stylist→validator；缺少合适鞋履时仍可返回最近似完整 Look，并通过 `wardrobe_risk` 说明风险；`force_refresh=true` 且带 `refresh_tier` 时只生成目标档并复用另外两档 | 200 `{weather,safe,fresh,stretch}`；城市候选冲突时 409 `{message,candidates}` |

核心类别约束（`services/validator.py` 硬护栏）：`outerwear`/`bottom`/`shoes` 三类每档每类最多 1 件单品，`top` 类别最多 2 件单品。两件上装是否构成合理的“轻薄内层 + 外层”由造型师根据体感温度、候选单品的 `category`、`thickness` 和风格判断，不再按 `t-shirt`/`shirt` 等类别名硬判：春秋衬衫外穿、薄针织搭配衬衫/外套以及外套搭配内搭均可成立；高温或单件已足够保暖时不强制增加内搭。如使用 `outerwear` 但没有 `top`，validator 拒绝并提示“含外套但缺少内搭上装”。这些硬护栏位于 `strict_quality` 之外，降级路径（`strict_quality=False`）仍会校验。

城市候选分级：城市文本先查 Open-Meteo；唯一结果直接使用。多结果时用 Nominatim 的行政区结果消歧，仍无法判断时，只有同一省市区县内的近名结果（如海拉尔的各种青年点/站点）才取默认坐标；跨省同名候选（如不同省的朝阳区）返回 409 让用户选择。Open-Meteo 无结果时支持“北京朝阳区”“上海宝山区”“天津津南区”这类完整区县输入并交给 Nominatim。省份输入不使用全省平均天气；当前内置“内蒙古/内蒙古自治区”返回海拉尔区、额尔古纳市、阿尔山市、呼和浩特市候选。

`recommend` 卡片结构（**无 base_score**）：
```json
{"history_id":"...","items":[{"id","name","category","image_url","primary_color"}],
 "reason":"...","weather_fit":"...","occasion_fit":"...",
 "pick_mode":"safe|fresh|stretch","wardrobe_risk":"...",
 "missing_categories":[]}
```

每次新生成推荐会把粗略经纬度、返回城市、时区和更新时间写入 Profile 的 `last_location`，完整三档会写入同一个 recommendation set id。普通请求会在天气、坐标和 MiniMax Key 校验前复用当地日期最新完整的非 prepared 三档组；`local_date` 由请求提供时优先使用，否则用已保存定位的时区计算本地日期。prepared 组不会遮蔽较早的普通完整组；因此页面导航或重复打开不会重复生成。完整 `force_refresh=true` 和预生成调用都明确跳过这一路径；单卡刷新同样跳过复用检查，但只调用一次目标档 M3，并保留另外两档。prepared 三档仍须满足：距离不超过 20km、温度未跨越 `<=12` / `13–24` / `>=25`、当天降水概率未跨越 50%；命中后按卡片结构重建返回，不调用 MiniMax。预生成调用使用 `history_action="prepared"`。

MiniMax Key 只在 prepared 无法复用、确需生成新搭配时校验；因此未配置 Key 但存在有效 prepared 时仍返回 200，未命中 prepared 时返回 503。prepared 复用的距离校验在请求和 prepared 双方均无坐标（HTTP 部署下浏览器禁用定位 API 的城市回退场景）时跳过，仅检查温度带和降雨阈值；只有一方有坐标时不复用。

每日预生成入口是 `python -m outfit_ai.precompute_daily`：读取 `last_location` 的坐标（否则 Profile `city`），先校验 MiniMax Key，再强制生成并保存 prepared 三档；超时、网络异常或模型工具调用异常最多重试 1 次，每次失败先回滚事务，只有成功结果才写入推荐组；没有位置/城市或衣橱不足时以非零退出且不重试。云端 `scripts/deploy.sh` 会安装 `/etc/cron.d/outfit-ai-precompute`，按 `Asia/Shanghai` 每日 06:30 调用该入口，并用 `flock` 防止运行重叠；执行日志写入 `/var/log/outfit-ai-precompute.log`。本地开发不安装 cron/launchd。

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
| POST | `/api/inspiration/generate` | body `{reference_ids?[],style_note?,season?,scene}`；不使用真实衣橱，生成三张 3:4 灵感图 | 200 `{image_url,looks:[3],disclaimer}` |

### 6.6 feedback / history
| Method | Path | 说明 | 返回 |
|---|---|---|---|
| POST | `/api/feedback` | body `{history_id?,items_worn:[],action?:shown/saved/skipped/worn,rating?:1..5,occasion?,occasion_type?,sentiment?,compliments?:[],negative_signals?:[],adjustment_signals?:[],didnt_work?,learnings?}`；可仅提交 rating；有 `history_id` 时最终 action/rating/极性事实与 history 同一事务提交并写入 `created_at`。`worn` 只置 `wore_it=true`，不会覆盖既有 `saved`，后续收藏、取消或评分也不会清除穿着标记 | 200 `{ok:true}` |
| GET | `/api/history?limit=20&scope=recent|archive` | 不传 scope 保持旧版最近记录兼容；`recent` 为临时记录，`archive` 为收藏、穿过或评分至少 4 的记录；每项返回 `scope` 和 `rating` | 200 `[OutfitHistory]` |

页面上对既有 Look 的收藏、取消收藏、穿过和评分必须带该 Look 的 `history_id`；客户端只能在上表返回 200 后更新显示状态。没有 `history_id` 的本地后备卡不可提交持久反馈。历史重载从服务端 `feedback` 恢复标签和评论，不按日期/单品集合猜测。每个真实变化且可学习的提交才会令 `feedback_since_refresh` 增加，到阈值后异步刷新 taste memo；刷新失败时 Profile 返回可见状态和错误，前端提供重试。

`recent` 精确定义为非 `saved`、未穿过，且未评分或评分低于 4；`archive` 精确定义为 `saved`、已穿过或评分至少 4。普通推荐历史不再因生成新推荐而清理，历史记录用于长期覆盖率、重复 Look 和品味学习；`action=prepared` 的每日预生成内部记录不计入单品使用暴露。失败的 LLM 生成不会写入新组或触发任何历史变化。

---

## 7. 模块规格（文件级，标 port/borrow 来源）
- `services/minimax_images.py`：读取环境变量或 `~/.mmx/config.json`；调用 Coding Plan VLM 与 `image-01`，校验和解码响应；外部 HTTP 客户端不继承本机 SOCKS/HTTP 代理环境。
- `services/llm.py`：MiniMax-M3 tool use 结构化文本生成；普通 JSON 调用兼容纯 JSON、Markdown 代码块及 `<think>` 等前置文本，再由 Pydantic 校验；OpenAI SDK 关闭隐式重试，单次请求 120 秒超时，并记录不含密钥或上游正文的耗时/错误类型日志；统一错误处理且不泄漏 Key；OpenAI HTTP 客户端不继承本机 SOCKS/HTTP 代理环境，避免推荐请求在客户端初始化阶段返回 500。
- `services/vision.py`：VLM 提取 `ClothingAttributes` 和 `StyleReferenceAnalysis`；衣物 prompt 使用短字段模板，`category` 仅允许 `top/bottom/outerwear/dress/shoes/accessory`，`thickness` 仅允许 `轻薄/适中/厚实` 或 `null`，`versatility` 要求为 0–1 数字，其余面向用户的衣物属性使用简体中文（品牌名可保留原文）；响应兼容纯 JSON、单个或多个 Markdown JSON 代码块，并取最后一个有效 JSON。衣物模型只把 VLM 常见语义值 `高/high`、`中/medium`、`低/low` 分别归一为 `0.85`、`0.5`、`0.25`，未知字符串仍拒绝；参考 Look 使用短 JSON 模板并拒绝全空分析。来源：Hangar schema + ai-closet 重试
- `services/background.py`：真实衣物先用 rembg 显式复用 `u2net` 生成透明 PNG；参考 Look 不去背景。模型缓存到 `~/.u2net/`，同一 API 进程只初始化一个会话并串行处理，避免误触发约 1GB 的 Bria 默认模型或批量上传时重复下载。
- `services/guardrail.py`：`filter_candidates(items,season,locked_ids,recent_item_ids,limit=15)->list[Item]`（天气/季节过滤、用户确认覆盖、locked 约束、确定性利用率排序）；`select_coverage_targets()` 为 Fresh/Stretch 选择低暴露覆盖目标。纯规则、可单测
- `services/stylist.py`：`propose(...) -> list[Look]`；`propose_tier(...) -> Look`（M3 文本属性 + 参考分析，tool use；单卡刷新只调用目标档）
- `services/profile_state.py`：profile JSON 封套的兼容解码/编码，以及 pin、hide、alias 后的有效 Style DNA 关键词；有效关键词最多 7 个，alias 归一化后应用 hidden，冲突时 pinned 优先保留。
- `services/validator.py`（**新**）：`validate_looks(looks, candidate_ids)->(ok, error)`（item_id 真实、3–6 件、无重复、含 top+bottom+shoes；候选充足时三档不共用任意单品，并检查颜色、版型或风格标签差异）。来源：ai-closet 校验链，port 为内部自检 + `tests/test_validation.py`
- `services/recommend.py`（**新**，编排）：当日完整 recommendation set 复用、prepared 复用/卡片重建或 guardrail→stylist→validator(重试)→返回三卡；prepared 复用阈值为 20km、三个温度带和 50% 降雨概率
- `precompute_daily.py`：每日 CLI，读取 Profile `last_location` 后强制生成 `prepared` 三档；由生产调度器调用，不安装本地调度
- `services/taste_memo.py`（**新**）：`refresh(user_id,force=False)`（旧 memo + 按 `event_at` 取批的不可变学习事件，事件含 history/action/rating/time/极性 → LLM → 新 memo；legacy feedback 先安全回填等价事件；以 `taste_memo_revision` 防止覆盖手动修正，失败保留计数并记录状态）；`seed(onboarding)`（Style DNA+样例图→初版）
- `db.py`：`_run_additive_migrations()` 仅追加缺失 SQLite 列；有本地备份路径时先保留副本，DDL 在事务内执行，失败可回滚且不删除历史。
- `services/weather.py`：`get_weather(city?,latitude?,longitude?)->WeatherData`；输入/解析出的坐标先统一到三位小数，再用于外部请求、缓存和推荐上下文；返回本地日期/时区、当前降水与雨量、当天降水概率/总量，以及未来 12 小时首段 `>=50%` 的连续降雨窗口。手动城市保留用户输入名称；Nominatim 反向结果若为市辖区/县且上级为直辖市则显示上级市名。Open-Meteo 天气缓存 30min；Nominatim 反查城市缓存 24h，反查失败只返回 `city:null`。天气 HTTP 客户端显式 `trust_env=False`，不继承本机 SOCKS/HTTP 代理环境，避免本地代理配置导致推荐接口在天气阶段返回 500。使用 Nominatim/OpenStreetMap 数据的用户可见界面必须显示 OpenStreetMap attribution。`_WMO_CONDITION` dict。来源：Hangar（删 Redis）
- `services/history.py`：`get_item_usage_stats`（按历史 Look 统计使用次数和最近使用日期）、`get_recent_look_keys`（30 天精确 Look 去重）、`get_recent_item_ids`、`get_recent_outfits(limit=7)`、`get_latest_recommendation_set(local_date)`、`get_prepared_outfits(local_date)`、`get_history_outfits(scope)`、`record_outfit(action, context)`。来源：ai-closet
- `services/collage.py`：`render(images,output_io,item_width=420,padding=6)`。来源：ai-closet（零摩擦 port）
- `services/storage.py`：`Storage` Protocol + `LocalStorage`；按图片字节识别真实格式，iPhone MPO/JPG 读取主画面并重编码为标准 JPEG。
- `services/prompt_builder.py`：Style DNA 草稿、造型师 system/user、memo 刷新 prompts。造型师收到的长期档案只包括应用 pin/hide/alias 后的有效关键词、最近风格信号和 `taste_memo`。来源：ai-closet 结构（适配 chat completions）
- `workers/analysis.py`：真实衣物 BackgroundTask（pending→analyzing→rembg→以 `.nobg.png` 调用 VLM→ready/failed）；AI 返回的厚薄度会写入 `tags_json`，并清理重复的厚薄标签；类别确认会将常见模型别名归一化，例如 `hat`、`cap`、`baseball cap` 归入 `accessory`。
- `workers/style_references.py`：参考 Look BackgroundTask（VLM 分析→M3 合并 Style DNA→ready/failed）；重试只复用有效非空分析，旧空缓存会重新调用 VLM。合并结果的核心关键词最多 7 个（仅可复用且有证据的风格概念，不含单件、场景或季节），最近信号最多 3 个，色板最多 5 个且仅可使用 `黑色、白色、深蓝色、浅蓝色、灰色、米白色、米黄色、卡其色、棕色、绿色、红色、紫色`；alias 先归一化标签，再应用 hidden，最后保留 pin（`pinned > hidden`）。
- `routers/{wardrobe,profile,recommend,feedback,style_references,inspiration}.py`：见 §6
- `main.py`：FastAPI app、CORS、lifespan `init_db()`、挂载 routers、静态托管 `/media`→upload_dir

---

## 8. 当前实现状态

- 数据层：六张 SQLite 表和索引已实现，由 `init_db()` 初始化。`feedback_events` 是不可变学习事件账本，同一 Look 的多次真实修改会分别入库，重复事实不计数。
- 真实衣物：上传、rembg、VLM、轮询、确认、列表、用户可编辑属性和删除已实现；AI 识图会初步返回 `轻薄`、`适中`、`厚实` 或空值，后台统一写入 `tags_json`，用户仍可在详情中手动修正；删除会清理数据库记录、原图与 `.nobg` 图片。当前 schema 不新增厚薄度列，前端把三档厚薄度作为受控标签保存。既有单品不自动回补厚薄度。
- 长期灵感：参考 Look 上传、VLM 分析、M3 合并 Style DNA、列表、重试、删除已实现。
- 推荐：天气与季节硬边界、手动季节/厚薄覆盖、历史利用率覆盖、30 天精确 Look 去重、Safe/Fresh/Stretch 三档边界、M3 造型、单卡 `refresh_tier`、item_id 校验和历史记录已实现；衣橱识图返回的季节标签会在候选过滤时归一化，用户确认值优先。
- 独立灵感：M3 提示词与 `image-01` 三图生成已实现。
- 反馈：收藏/跳过/穿着/评分、历史与 taste memo 批量刷新已实现。
- 前端：Stitch React 五页和统一 API 接线已实现，详见当前前端事实源。

---

## 9. 验收 / Definition of Done
- [x] `init_db()` 建出六张当前表
- [x] 真实衣物上传→去背景→识图→确认
- [x] 参考 Look→Style DNA
- [x] Safe/Fresh/Stretch 仅返回真实候选 item_id
- [x] 独立灵感一次返回三图并带免责声明
- [x] feedback 与 history 闭环
- [x] Q5 feedback provenance、最终事实去重、memo 所有权、失败可重试和幂等加法迁移
- [x] 后端测试、ruff、前端契约测试、TypeScript 和生产构建通过
- [x] Stitch React 五页浏览器走查，控制台无错误
- [ ] 使用用户真实图片与 MiniMax 配额完成一次人工端到端验收
- [ ] 生产对象存储、HTTPS 与部署

## 10. 部署卡点

旅行推荐补充契约：`target_date` 只能是今天至未来 14 天，天气从 Open-Meteo 16 日 forecast 的 daily 数组选择目标日；城市检索返回多个候选时以 409 携带 `candidates`，前端必须让用户选择具体城市/区县，不能静默采用第一项。普通 recommendation set 与 prepared 组都绑定目标日期、城市和粗略坐标，显式城市不会继承 Profile 旧坐标。衣橱当季过滤排除了普通非凉鞋 sneaker 时，非极寒/非雪天可返回最近似完整 Look，并在卡片 `wardrobe_risk` 明示保暖鞋履缺口；极寒或雪天提示雪地靴/户外靴风险。

后端需要 HTTPS；生产图片需从本地目录迁移到对象存储。微信小程序/App 如需上线，另行选择能保留当前 React 界面与交互的容器方案，不回退旧 uni-app 设计。

## 11. 署名（务必保留）
- 数据模型：`Data model inspired by googlarz/fashion-skill (CC BY 4.0)`（仅抽象字段，不抄 prompt）
- 上传状态机/Open-Meteo：`from Gurshaan-Deol/Hangar (MIT)`
- LLM 调用/校验/拼图/历史：`from jonnykate/ai-closet (MIT)`
- ~~推荐算法 OutfAI~~ —— **已废弃**（改品味驱动后不再使用 OutfAI 评分，无需署名）
