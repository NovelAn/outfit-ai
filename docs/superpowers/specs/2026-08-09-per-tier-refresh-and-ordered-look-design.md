# 单卡换一换与穿衣顺序展示设计

## 背景

当前“AI 换一换”按钮虽然位于单个 Look 模块内，但请求使用全局 `force_refresh`，后端会重新生成 Safe/Fresh/Stretch 三套，导致未点击的模块也变化，并承担不必要的 M3 等待时间。

当前 3–6 件单品只按返回数组切成主视觉和缩略轨，未按人类穿衣顺序展示，帽子、外套、鞋履等容易被拆散。

## 已确认目标

1. 点击某个 Look 的“AI 换一换”只重新生成当前 Look；其他两套保持不变。
2. 单卡刷新失败时只影响当前卡片，不覆盖其他卡片或已确认状态。
3. 展示顺序模拟从上到下穿衣：帽子 → 围巾/丝巾等颈部配饰 → 外套/叠穿 → 上装 → 下装 → 鞋履 → 其他配饰。
4. 展示排序只作用于前端视觉副本；原始 API item 顺序、history ID、反馈 item ID 不变。
5. 每个推荐模块允许更高的垂直空间，优先保证顺序清晰和整体可读性。

## 方案

### 单卡刷新

`POST /api/recommend` 增加可选 `refresh_tier: safe|fresh|stretch`。普通请求保持原有同日复用逻辑；带 `force_refresh=true` 与 `refresh_tier` 时，仅为目标 tier 调用 M3，另外两档从当前有效 recommendation set 复用。响应仍返回三档完整卡片，便于前端保持现有数据模型。

后端只为目标 tier 写入新的 history 记录，并保留其他两档的 history；失败不写入新记录、不清理历史、不改变缓存。前端只替换目标 tier，目标卡片显示独立 loading，其他卡片保持可交互。

### 穿衣顺序

新增纯前端 `presentationOrder`/排序 helper，基于 `category` 与中文/英文单品名识别头部和颈部配饰。排序仅生成 `visualItems` 副本：

```text
head accessory 10
neck accessory 20
outerwear 30
top 40
bottom 50
shoes 60
other accessory 70
```

用垂直 editorial flow 展示 visualItems，每件保留点击详情能力；不再把第 4 件以后默认缩成孤立小方块。视觉容器提高模块高度，并在相邻单品间使用轻量连接/留白表达穿衣层级。

## 验证

- 后端测试：目标 tier 刷新只新增一条对应 history；未点击 tier 的 history ID 与 item IDs 不变；M3 失败不写入。
- 前端测试：请求包含 `refresh_tier`；只更新目标 tier；排序覆盖帽子、围巾、外套、上装、下装、鞋履和未来未知配饰；反馈仍使用原 item 顺序。
- 移动端验证：3、4、5、6 件 Look 在 390×844 视口按从上到下顺序展示，模块高度可滚动，其他 Look 不跳变。

## 非目标

- 不改变 Style DNA、衣橱标签或推荐评分模型。
- 不引入队列、Redis、流式 LLM 或新的数据库表。
- 不修改已有用户历史数据，不迁移真实数据库。
