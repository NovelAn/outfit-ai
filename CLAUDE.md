# Outfit-AI · 项目规范

> 个人 AI 衣橱：拍真实衣物入库 → 沉淀可编辑 Style DNA → 结合天气/场合/心情，每天给出**基调稳定又能持续变化**的 Safe/Fresh/Stretch 三套穿搭，并通过反馈越用越懂。终端目标微信小程序 + 手机 App，v0 先跑通 H5。

## 技术栈

- **后端**：Python 3.11 + FastAPI（同步）+ SQLAlchemy 2.0 sync + SQLite。单用户零运维；后台任务用 FastAPI `BackgroundTasks`，不上 Redis/arq。
- **LLM**：MiniMax-M3，CN 端点 `https://api.minimaxi.com/v1`，OpenAI SDK 兼容，复用 mmx CLI 的同一把 key（后端从 env 读，绝不进代码）。识图走 **tool use**；文本走 **prompt 强约束 + json.loads + 失败重试**（M3 不支持 `response_format:json_object`）。
- **天气**：Open-Meteo（免 key）。
- **图像**：Pillow 拼图；rembg 可选。
- **前端**：uni-app + Vue3 + Vite + TS，一套代码出 H5 / 微信小程序 / App。
- **图片存储**：本地目录起步，`storage.py` 抽象接口，生产换阿里云 OSS。

## 核心架构决策：品味驱动推荐（多模态造型师）

时尚是主观品味，规则公式再精巧也产不出"懂你"的推荐。规则退居硬护栏，品味判断全交 LLM：

1. **Stage 1 硬护栏（规则）**：confirmed 单品 → 天气/季节过滤 → locked 强制保留 → 近期重复规避（跳鞋子）→ 封顶 ~12–15 件。规则只过滤、**不评分**。
2. **Stage 2 多模态造型师（LLM 品味）**：MiniMax-M3 看候选单品**照片**+属性 + Style DNA + 品味备忘录 + 天气/场合/心情 + 近期 Look → 凭品味组装 Safe/Fresh/Stretch 三档。
3. **Stage 3 校验（规则兜底）**：item_id 真实、单套无重复、含 top+bottom+shoes；失败回灌重试一次。
4. **学习 = 品味备忘录**：反馈周期性由 LLM 消化进 `profile.taste_memo`（自然语言档案），下次推荐作上下文。**无数值权重表**。

> 已废弃：OutfAI 规则评分 + epsilon-greedy 方案（太死板，与品味驱动相悖）。详见 `docs/SPEC.md §4`。

## 目录约定

```
backend/src/outfit_ai/   # 后端包（src layout）
  routers/   # HTTP 路由，按资源分文件
  services/  # 业务逻辑/外部依赖（llm/vision/recommender/weather/history/collage/storage）
  workers/   # BackgroundTasks（analysis 状态机）
frontend/src/             # uni-app 前端
  pages/     # 每页一个 .vue（wardrobe/profile/recommend/history）
  api/       # uni.request / uni.uploadFile 封装
  stores/    # pinia
docs/                     # design.md（架构与署名）
data/                     # 运行期产物（uploads/、sqlite）—— 不入库
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
npm run dev:h5                        # v0 主开发端
npm run dev:mp-weixin                 # 微信开发者工具打开 dist/dev/mp-weixin
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

后端 HTTPS 域名 + ICP 备案；微信公众平台配 request/uploadFile/downloadFile 合法域名；图片走对象存储（OSS）；前端主包 ≤2MB。
