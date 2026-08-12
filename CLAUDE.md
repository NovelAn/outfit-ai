# Outfit-AI · 项目规范

> 个人 AI 衣橱：拍真实衣物入库 → 沉淀可编辑 Style DNA → 结合天气/场合/心情，每天给出**基调稳定又能持续变化**的 Safe/Fresh/Stretch 三套穿搭，并通过反馈越用越懂。终端目标微信小程序 + 手机 App，v0 先跑通 H5。

## 当前事实源

- 后端、数据模型与 API：`docs/SPEC.md`
- 前端页面、入口、功能与 API 映射：`docs/frontend/CURRENT_FRONTEND_INTEGRATION.md`
- 快速启动：`README.md`
- `docs/design.md` 与 `docs/frontend/OUTFIT_AI_FRONTEND_PRD_STITCH.md` 已归档，不得作为当前实现依据。

**文档同步是完成条件：** 页面、交互、API、数据模型、技术栈、依赖或运行命令发生变化时，必须在同一提交更新相应当前文档。代码已经变化但当前文档仍旧，视为未完成。

## 技术栈

- **后端**：Python 3.11 + FastAPI（同步）+ SQLAlchemy 2.0 sync + SQLite。单用户零运维；后台任务用 FastAPI `BackgroundTasks`，不上 Redis/arq。
- **模型分工**：MiniMax-M3 只负责文本造型与 Style DNA 合并；MiniMax VLM 负责衣物/参考 Look 识图；`image-01` 负责独立灵感生图。Key 优先读环境变量，再只读复用 `~/.mmx/config.json`，绝不进前端或代码。
- **天气**：Open-Meteo（免 key）。
- **图像**：真实衣物上传后先用本地 `rembg` 去背景，再调用 MiniMax VLM；Pillow 负责拼图。
- **前端**：用户确认的 Google AI Studio / Stitch ZIP 原版 React 19 + Vite + Tailwind CSS。ZIP 的页面、视觉和交互是唯一前端基准；旧 PRD 和旧 uni-app 页面不得覆盖它。
- **图片存储**：本地目录起步，`storage.py` 抽象接口，生产换阿里云 OSS。

## 核心架构决策：品味驱动推荐（文本造型师）

时尚是主观品味，规则公式再精巧也产不出"懂你"的推荐。规则退居硬护栏，品味判断全交 LLM：

1. **Stage 1 硬护栏（规则）**：confirmed 单品 → 天气/季节过滤 → locked 强制保留 → 近期重复规避（跳鞋子）→ 封顶 ~12–15 件。规则只过滤、**不评分**。
2. **Stage 2 文本造型师（LLM 品味）**：MiniMax-M3 读取经 VLM 提取的候选属性、参考 Look 分析、Style DNA、品味备忘录、天气/场景和近期 Look → 凭品味组装 Safe/Fresh/Stretch 三档。
3. **Stage 3 校验（规则兜底）**：item_id 真实、单套无重复、含 top+bottom+shoes；失败回灌重试一次。
4. **学习 = 品味备忘录**：反馈周期性由 LLM 消化进 `profile.taste_memo`（自然语言档案），下次推荐作上下文。**无数值权重表**。

> 已废弃：OutfAI 规则评分 + epsilon-greedy 方案（太死板，与品味驱动相悖）。详见 `docs/SPEC.md §4`。

## 目录约定

```
backend/src/outfit_ai/   # 后端包（src layout）
  routers/   # HTTP 路由，按资源分文件
  services/  # 业务逻辑/外部依赖（llm/vision/recommender/weather/history/collage/storage）
  workers/   # BackgroundTasks（analysis 状态机）
frontend/src/             # Stitch ZIP 原版 React 前端
  components/ # 今日 / 衣橱 / 灵感 / 灵感库 / 我的
  lib/api.mjs # FastAPI 接线层
docs/                     # SPEC.md + 当前前端集成文档；旧设计文档已归档
~/.outfit-ai/             # 默认运行期产物（uploads/、sqlite），跨 worktree 保存
```

- 文件高内聚低耦合，200–400 行典型，800 上限。逻辑重的模块留一个 `__main__` 自检。
- 不可变优先；显式处理错误；系统边界校验输入（文件上传、LLM 返回 JSON、外部 API）。
- 设计 token / 业务常量提为模块级常量，不散落硬编码。

## 开发命令

```bash
# 后端
cd backend
uv sync                               # 或 pip install -e ".[dev]"
uvicorn outfit_ai.main:app --reload   # http://localhost:8000/docs
pytest                                # 测试
python -m outfit_ai.services.recommender   # recommender 自检

# 前端
cd frontend
npm install
npm run dev                           # http://localhost:5173
npm test && npm run lint && npm run build
```

## 安全红线（沿用全局）

删除文件/目录、改 git 历史、改 `.env`/keys/tokens、DB schema 变更、`git push`/rebase/reset、全局依赖、公开发布——**必须先问**。密钥绝不进代码/日志/提交。

## 署名义务（务必保留）

- 数据模型 inspired by `googlarz/fashion-skill`（**CC BY 4.0**，只抽象字段，不抄 prompt）
- 推荐算法 inspired by `daveonthegit/OutfAI`（MIT）
- LLM/校验/拼图/历史模式 from `jonnykate/ai-closet`（MIT）
- 上传状态机 / Open-Meteo from `Gurshaan-Deol/Hangar`（MIT）

## v0 不做（YAGNI）

GNN、FAISS、多模态 RAG、虚拟试衣、3D、Postgres、Redis/arq、多用户鉴权、社交、自动购物、月度审核、公式检测。需要时再加。

## 部署卡点（小程序上线，尽早准备）

后端 HTTPS 域名 + ICP 备案；图片走对象存储（OSS）。微信小程序/App 如需上线，后续基于已确认的 React 前端单独选择容器方案，不回退旧界面。
