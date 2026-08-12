# MiniMax 图片能力与长期穿搭灵感设计

日期：2026-07-28
状态：已确认，待实施计划

## 1. 目标

本次改造建立两项相互独立的产品能力：

1. **真实衣橱穿搭推荐**：从长期 Style DNA、当次参考 Look、季节和场景出发，只使用用户衣橱中真实存在的单品生成 Safe / Fresh / Stretch 推荐，帮助用户重新发现已有衣物的搭配价值。
2. **独立穿搭灵感图**：不依赖真实衣橱，按长期 Style DNA、当次参考 Look、季节和场景生成新的穿搭视觉，用于换季购物、新风格探索和未来需求判断。

用户不需要手工填写抽象的 `style` 或 `preference`。这些信息主要从杂志截图、达人 Look 等长期参考图片中提取；仅当用户有明确要求时，才补充可选文字说明。

## 2. 非目标

本次不做：

- 虚拟试衣或真实人物换装；
- 保证灵感图中的单品与真实衣橱一致；
- 从灵感图自动生成购物清单或商品链接；
- 按衣物利用率、穿着次数或闲置时间优先推荐；
- 灵感图片收藏夹的删除、归档或复杂管理；
- 新增 Redis、任务队列、对象存储或第三方去背景 API。

## 3. 模型职责

| 能力 | 实现 |
|---|---|
| 真实衣物属性识别 | MiniMax VLM 图片接口：`POST /v1/coding_plan/vlm` |
| 穿搭参考图分析 | MiniMax VLM 图片接口：`POST /v1/coding_plan/vlm` |
| 文本推理、Style DNA 合并、真实衣橱搭配 | `MiniMax-M3`，保留现有 OpenAI-compatible tool call |
| 独立穿搭灵感图 | MiniMax `image-01`：`POST /v1/image_generation` |
| 真实衣物去背景 | 本地 `rembg.remove()` |

`MiniMax-M3` 不再直接接收衣物图片。图片只在上传时由 VLM 分析一次，后续推荐使用经过校验的文字属性，从而控制 VLM 日额度消耗。

参考实现：

- [`jonnykate/ai-closet/tools/remove_bg.py`](https://github.com/jonnykate/ai-closet/blob/main/tools/remove_bg.py)：本地 `rembg` 去背景模式，MIT。
- [MiniMax CLI](https://platform.minimaxi.com/docs/token-plan/minimax-cli)：VLM、图片生成和 Token Plan 使用方式。
- [MiniMax Token Plan](https://platform.minimaxi.com/docs/guides/pricing-token-plan)：当前非文本模型按日配额规则。

## 4. 认证与配置

后端直接调用 MiniMax 接口，不执行 `mmx` 子进程。

认证读取顺序：

1. `MINIMAX_API_KEY` 环境变量；
2. `MMX_CONFIG_DIR/config.json`；
3. `~/.mmx/config.json`。

配置文件只读，读取 `api_key`、`region` 和可选 `base_url`。环境变量始终优先，便于部署覆盖。默认 CN 地址为 `https://api.minimaxi.com`。

安全要求：

- Key 不进入日志、异常正文、数据库、API 响应或前端；
- 外部服务错误统一转换为用户可理解的脱敏错误；
- 不修改 `~/.mmx/config.json`；
- JSON 配置无效或 Key 缺失时明确返回“未配置 MiniMax API Key”。

## 5. 数据模型

新增第五张表 `style_references`，不修改现有四张表字段。

| 字段 | 类型 | 用途 |
|---|---|---|
| `id` | String PK | 参考图 ID |
| `user_id` | String | v0 固定为 `local` |
| `image_path` | Text | 原始参考图片路径 |
| `status` | String | `pending/analyzing/ready/failed` |
| `attempt_count` | Integer | 手动重试次数 |
| `analysis_json` | Text | 已校验的 VLM 风格分析 |
| `ai_raw_response` | Text nullable | 脱敏后的原始响应或失败摘要 |
| `added_at` | DateTime | 添加时间 |

索引：

- `(user_id, status)`
- `(user_id, added_at)`

参考图默认永久加入长期灵感库。图片保留完整场景，不做去背景。VLM 分析结构至少包含：

- `style_keywords`
- `palette`
- `silhouettes`
- `layering`
- `materials`
- `seasons`
- `scenes`
- `notable_elements`

Style DNA 继续保存在 `profile`。新参考图分析成功后，M3 将“旧 Style DNA + 新分析”合并为更新后的长期档案，允许同时保留多个风格方向，不把用户压缩成单一标签。

## 6. 真实衣物上传流程

```text
上传原图
  → 文件边界校验
  → 保存原图并创建 wardrobe_item(pending)
  → 后台任务抢占为 analyzing
  → 本地 rembg 生成透明 PNG
  → VLM 读取原图并返回 ClothingAttributes JSON
  → Pydantic 校验
  → 原子写入属性并标记 ready
```

处理顺序先 `rembg`、后 VLM：

- 去背景失败不会浪费一次 VLM 调用；
- VLM 失败时保留原图和透明图，手动重试时跳过已完成的去背景步骤；
- 任一步未完成都不标记 `ready`。

透明图使用确定性派生文件名，例如原图 `abc.jpg` 对应 `abc.nobg.png`。数据库继续只保存原图 `image_path`。统一路径助手决定：

- `ready` 状态的衣橱、造型师候选和拼图使用透明图；
- `pending/analyzing/failed` 状态使用原图预览；
- 删除真实衣物时同时删除原图和透明图。

## 7. 长期灵感图片流程

```text
上传杂志截图或达人 Look
  → 保存完整原图并创建 style_reference(pending)
  → 后台任务抢占为 analyzing
  → VLM 返回 StyleReferenceAnalysis JSON
  → Pydantic 校验
  → 保存 analysis_json，状态保持 analyzing
  → M3 合并长期 Style DNA
  → 同一事务更新 profile、标记 ready
```

若 VLM 已成功但 M3 合并失败，保留已校验的 `analysis_json`。手动重试从 M3 合并继续，不重复调用 VLM。

新上传的参考图：

- 默认写入长期灵感库；
- 在当前页面自动选中，作为当次偏好；
- 后续也可从灵感库选择一张或多张参考图；
- 没有选中参考图时，仅使用长期 Style DNA。

## 8. 真实衣橱推荐

推荐请求增加：

- `reference_ids: list[str]`
- `style_note: str | None`
- `season: str | None`
- `scene: str`

其中：

- `reference_ids` 指向本次偏好的长期灵感图片；
- `style_note` 只用于用户主动提出特定要求；
- `season` 默认从天气推导，可为未来季节手动覆盖；
- `scene` 替代前端“场合”文案，内部仍可映射到现有 `occasion` 字段，避免修改历史表。

候选流程：

1. 只取已确认真实衣物；
2. 按季节、场景、锁定单品和近期重复做硬过滤；
3. 不计算利用率分数，不优先闲置衣物；
4. 文本候选较少时全部交给 M3；
5. 超过安全上限时保留锁定单品，并从其余合格衣物中随机抽取；
6. M3 依据长期 Style DNA、当次参考图分析、天气和场景生成 Safe / Fresh / Stretch；
7. 继续校验真实 `item_id`、单套无重复、类别完整和锁定单品。

随机性只影响合格候选抽取，不替代 Style DNA 的品味判断。

推荐结果展示真实透明衣物图和真实拼图，不调用 `image-01`。

## 9. 独立穿搭灵感图

独立接口不接收真实衣橱 ID：

```http
POST /api/inspiration/generate
```

请求：

```json
{
  "reference_ids": ["..."],
  "style_note": null,
  "season": "autumn",
  "scene": "通勤"
}
```

流程：

1. 读取长期 Style DNA；
2. 读取所选参考图的结构化分析；
3. M3 生成适合 `image-01` 的绘图 Prompt；
4. 调用 `image-01`，每次只生成一张；
5. 校验响应图片并保存到本地媒体目录；
6. 返回 `image_url`。

每次用户主动点击都生成一个新变体。不自动重试，不基于相同 Prompt 做强制缓存，以免阻止用户探索变化。前端在请求期间禁用按钮，避免重复点击浪费额度。

灵感图不写入 `outfit_history`，也不声称图中衣物已存在于真实衣橱。

## 10. API

### 长期灵感库

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/style-references/upload` | 上传长期灵感图片 |
| GET | `/api/style-references` | 查询长期灵感库 |
| GET | `/api/style-references/{id}/status` | 查询分析状态 |
| POST | `/api/style-references/{id}/retry` | 手动重试失败任务 |

### 真实衣橱推荐

保留 `POST /api/recommend`，扩展请求体，不新增第二套推荐接口。

### 独立灵感图

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/inspiration/generate` | 生成一张不依赖真实衣橱的穿搭灵感图 |

## 11. 前端

现有“推荐”页顶部增加双模式切换，不新增第五个底部 Tab：

- **我的衣橱**：真实衣物推荐；
- **灵感探索**：独立 `image-01` 生图。

两种模式共用：

- 长期灵感图片选择器；
- “添加参考 Look”上传入口；
- 季节选择；
- 场景选择；
- 可选文字要求。

“我的衣橱”继续展示 Safe / Fresh / Stretch 三档真实单品卡。“灵感探索”展示生成图片，并固定标注“AI 灵感图 · 不代表衣橱已有单品”。

## 12. 错误与额度

- VLM、M3、`image-01` 与 `rembg` 错误使用不同内部异常类型，对前端统一脱敏；
- VLM 或 `rembg` 失败保留上传原图并标记 `failed`；
- Style DNA 合并失败不写入半成品 profile；
- `image-01` 失败不影响真实衣橱推荐；
- 额度不足时返回明确的可重试业务错误，不自动再次调用；
- VLM 和 `image-01` 均只在用户可见操作触发时消费额度；
- 不在后台静默刷新或批量重新分析历史图片。

## 13. 测试与验收

### 自动化

- 认证：环境变量优先、mmx 配置回退、无效配置、错误脱敏；
- VLM：JSON 提取、Markdown 包裹、Pydantic 校验、错误响应；
- 去背景：生成透明 PNG、确定性路径、幂等重试；
- 长期灵感：状态机、VLM 结果复用、Style DNA 原子合并；
- 推荐：参考图权限、季节/场景传递、随机候选不使用利用率排序、真实 ID 校验；
- 生图：Prompt 构建、单图保存、额度错误、不自动重试；
- 路由：上传、轮询、重试、双模式接口；
- 前端：typecheck 和生产构建。

### 实际接口验证

使用测试素材完成一次端到端验证：

1. 上传一张真实衣物图，确认透明图与结构化属性；
2. 上传一张穿搭参考图，确认长期 Style DNA 更新；
3. 生成一次真实衣橱 Safe / Fresh / Stretch 推荐；
4. 生成一张独立穿搭灵感图；
5. 确认 Key 未出现在日志、响应和提交中。

实际验证预计消耗两次 VLM 调用和一次 `image-01` 调用。执行前不修改 Key 或 mmx 配置。

## 14. 实施边界

- 新增 `rembg` 依赖已获批准；
- 新增 `style_references` 表已获批准；
- MiniMax 认证采用 env 优先、mmx 配置只读回退已获批准；
- 主文本模型固定为 `MiniMax-M3`；
- 不修改 `.env`、Key 或 `~/.mmx/config.json`；
- 不做生产部署、远程推送或破坏性数据变更。
