# Outfit-AI · 前端 UI/UX 设计

> **方向已锁定（2026-07-27）：Warm Editorial · 移动优先。**
> 气质参考：`https://getdesign.md/claude/design-md`（Claude 设计系统：terracotta 强调 + 米白底 + 衬线/无衬线配对 + 编辑式留白）。
> 移动端化：保留气质，版式/布局按手机（最终微信小程序 + App）重做。目标端：微信小程序 / App / H5（uni-app 一套代码）。
> 配套：[`SPEC.md`](./SPEC.md)（后端/API/数据）、[`CLAUDE.md`](../CLAUDE.md)（web 设计质量标准）。

## 1. 视觉方向：Warm Editorial · 移动优先
像一本**个人造型师的暖调编辑式 lookbook**——衣服照片当主角，terracotta 点睛，衬线/无衬线配对，克制留白。不是通用工具 app 的卡片堆砌。

## 2. 设计 token
### 色彩
| token | 值 | 用途 |
|---|---|---|
| `--bg` | `#FAF8F4` | 暖米白底 |
| `--ink` | `#1F1B16` | 暖近黑主文字 |
| `--ink-2` | `#6E665C` | 暖灰次要文字 |
| `--accent` | `#C76A43` | terracotta：CTA / 激活态 / 关键数字（克制用） |
| `--accent-soft` | `#E8D5C8` | 状态药丸 / 选中底 |
| `--surface` | `#F1ECE3` | 卡片底 |
| `--line` | `#E5DED2` | 分割线 / 边 |

暗色主题 v0 不做（全局规则：勿默认深色），后期再加。

### 字体（v0 纯系统，包体优先）
- 标题：PingFang SC Semibold + 系统衬线回退（数字/英文可显衬线感）
- 正文：PingFang SC / `-apple-system` / Inter（系统无衬线）
- 层级：大号 Semibold 标签 + 数字；正文行高 ~1.5
- 不引入网络字体；后期想要更强编辑味再评估衬线展示字（如 Fraunces/Newsreader）

### 间距 / 圆角 / 阴影 / 动效
- 间距：8 的倍数（8/16/24/32），留白充足但不浪费（移动屏稀缺）
- 圆角：卡片 16px、按钮 12px/胶囊、药丸 999px
- 阴影：柔 `0 4px 16px rgba(31,27,22,0.06)`，或仅 `--line` 细边
- 动效：仅 `transform`/`opacity`；120–240ms；`cubic-bezier(0.16,1,0.3,1)`；尊重 `prefers-reduced-motion`

## 3. 页面设计
### 通用骨架
- 顶部极简标题栏（Semibold 页名 + 可选右操作）
- 内容单栏满宽
- 底部 Tab（4）：**衣橱 / 推荐 / 风格 / 历史**；激活态 terracotta
- 主操作置拇指区（底部 sticky）

### wardrobe（衣橱）
- 单品 **2 列网格**：大照片卡 + 类别标签；点进详情/编辑
- 右下 **FAB 上传**（`uni.chooseMedia`）
- 上传中：卡片占位 + `pending→analyzing→ready/failed` 药丸
- 空态："再加几件适合今天的单品" 暖提示

### profile（风格）
- **Style DNA**：编辑式排版（颜色季节/偏好/忌讳…），像在读档案
- **品味备忘录（taste_memo）**：卡片化自然语言档案 + "刷新我的品味" 按钮
- onboarding：样例图上传 → Style DNA 草稿 → 编辑确认

### recommend（推荐）★
- 顶部：今日天气/场合/心情 一行摘要
- 三档**纵向堆叠大卡**：
  - 档位标签 Safe/Fresh/Stretch（Semibold + terracotta 点缀）
  - **搭配拼图 hero**（单品纵向拼接）
  - reason / weather_fit / occasion_fit（正文）
  - 操作行：锁定 / 换一件 / 反馈 / 今天穿了
- 凑不齐三档 → 少出卡 + 提示，**不编造**

### history（历史）
- Look 时间线（日期 + 拼图缩略 + 场合 + 反馈标记）

## 4. 关键组件
- **三档推荐卡**（见 §3 recommend）
- **单品卡**：照片 + 类别/颜色标签 + 状态药丸
- **状态药丸**：pending/analyzing/ready/failed（`accent-soft` 底 + `ink` 字）
- **上传 FAB + 识别中骨架**
- **Style DNA / memo 编辑器**：表单 + 标签芯片
- **底部 Tab + sticky 操作栏**

## 5. 交互与动效
- 三卡纵向滚动；锁定后该卡置顶高亮
- 反馈：轻触 → 底部 action sheet（喜欢/不喜欢/换一件/今天穿了）
- 加载：**骨架屏**（暖底），非转圈
- 空态/错误态都有暖文案

## 6. 可访问性
对比度达 AA · 触控热区 ≥44px · 键盘/焦点可见 · `prefers-reduced-motion` · 中文行高/字距舒适

## 7. 多端约束
- **微信小程序**：主包 ≤2MB（图片全 OSS/CDN，不打包）；合法域名白名单 + HTTPS；无 DOM；CSS 简单 class 化（无 `*` 通配、慎用复杂选择器）；动效仅 transform/opacity
- **App**：uni-app 编译；图片走 OSS
- **H5（v0 开发端）**：`dev:h5` 调试，CSS 最自由但须兼顾小程序限制

## 8. 参考库
- 气质基准：`https://getdesign.md/claude/design-md`
- 待补（novel 自行收集）：dunhill 官网/小程序视觉、MR PORTER/SSENSE 编辑页、Whering/Cladwell 等穿搭 app
