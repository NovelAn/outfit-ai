# Outfit-AI 个人使用部署

当前先部署为私有 HTTPS Web（手机浏览器可添加到主屏幕），暂不做 App Store 或微信小程序发布。这样可以保留已确认的 React 视觉与交互，也不需要先支付应用商店年费；真正的离线 PWA 壳等功能稳定后再加。

## PocketBay：适合先做验证部署

PocketBay 不是数据库或后端框架，而是面向 AI Coding 项目的托管平台。它目前支持 Python Web 服务和自带 Dockerfile 的单容器应用，能自动处理构建、健康检查、HTTPS、域名和日志；动态应用提供项目级 `/data` 持久卷，也可配置托管 PostgreSQL。官方同时说明暂不支持完整 Docker Compose、独立 Worker、Redis、对象存储和多区域部署。详情见 [PocketBay FAQ](https://pocketbay.com/faq)、[部署指南](https://pocketbay.com/docs/deploy) 和 [平台边界](https://pocketbay.com/docs/limitations)。

因此，PocketBay 可以作为 Outfit-AI 的第一版云验证环境：

1. 用一个 Dockerfile 打包前端构建产物和 FastAPI，运行单个 HTTP 容器。
2. 将 `DATABASE_URL` 和 `UPLOAD_DIR` 指向 `/data`，避免重启丢 SQLite 和图片。
3. 用环境变量注入 `MINIMAX_API_KEY`，不上传本机 `.env` 或 `~/.mmx/config.json`。
4. 接受动态应用约 10 分钟无访问后休眠，首次访问和首次 rembg 处理会较慢。

PocketBay 公共测试期目前免费，但官方没有给出中国大陆网络可用性保证；正式使用前必须从你的手机网络实测登录、上传图片、访问 `/media` 和调用 MiniMax。若实测不稳定，切换到国内 Lighthouse/CloudBase，不改变 Docker 镜像。

## 推荐拓扑

```text
手机浏览器/PWA
  → HTTPS 反向代理（Caddy/Nginx）
  → React 静态构建（frontend/dist）
  → FastAPI（uvicorn）
  → 持久化磁盘（SQLite + media）
  → MiniMax API（仅后端读取 MINIMAX_API_KEY）
```

个人自用可以放在一台小型 VPS 或家中可稳定访问的主机上。不要把 SQLite、上传图片或 MiniMax Key 放进静态托管；当前 v0 使用 `USER_ID=local`、本地图片目录和同步图片生成，适合单用户，不适合直接公开分享。

## 上线前必须配置

1. 服务器持久化 `DATABASE_URL` 指向 SQLite 文件，持久化 `UPLOAD_DIR`。
2. 在服务器密钥管理器中设置 `MINIMAX_API_KEY`；不要把本机 `~/.mmx/config.json` 复制到仓库或前端。
3. 用 Caddy/Nginx 配置 HTTPS，并将 `/api`、`/media` 转发到 FastAPI；HTTPS 是手机定位和照片上传的前提。
4. 先运行前端 `npm run build`，再由静态服务器托管 `frontend/dist`。
5. 先用单用户密码/VPN 保护访问；多用户、对象存储、任务队列和登录在功能稳定后再做。

## 腾讯云 Lighthouse：当前可执行的单服务器方案

当前已在仓库中固化一套不依赖 GitHub 的首轮部署脚本：

- `Dockerfile`：Node 20 构建 React，Python 3.11 构建 FastAPI；容器依赖按 `pyproject.toml` 从清华 PyPI 镜像安装，并设置 5 分钟超时、5 次重试和 BuildKit 缓存，避免 `uv.lock` 中的海外文件地址导致中国大陆服务器超时；同一 Docker 构建产物包含前端和后端。
- `compose.yaml`：`app`、Caddy 静态/HTTPS 网关、SQLite/上传目录/rembg 模型缓存持久化卷。
- `deploy/Caddyfile`：同源转发 `/api`、`/media`，其余路径托管 React 并回退到 `index.html`。
- `scripts/bootstrap-ubuntu.sh`：首次初始化 Docker、Compose、Git、rsync 与 UFW，仅允许 22/80/443。
- `scripts/deploy.sh`：通过 SSH + rsync 同步代码，执行 `docker compose up -d --build`，再检查 `/health`。
- `.env.production.example`：服务器环境变量模板；真实 `.env.production` 只留在服务器。

首轮部署步骤：

```bash
ssh root@SERVER_IP 'mkdir -p /tmp/outfit-ai-bootstrap'
rsync -az scripts/ root@SERVER_IP:/tmp/outfit-ai-bootstrap/scripts/
ssh root@SERVER_IP 'bash /tmp/outfit-ai-bootstrap/scripts/bootstrap-ubuntu.sh'
scp .env.production.example root@SERVER_IP:/tmp/outfit-ai.env.production.example
ssh root@SERVER_IP 'mkdir -p /opt/outfit-ai && cp /tmp/outfit-ai.env.production.example /opt/outfit-ai/.env.production'
# 编辑服务器上的 /opt/outfit-ai/.env.production
DEPLOY_HOST=root@SERVER_IP ./scripts/deploy.sh
```

服务器应使用 Ubuntu 24.04 LTS、x86_64，并为 SSH 配置公钥登录；不要把 SSH 私钥、MiniMax Key、浏览器 Cookie 或本机 `~/.mmx/config.json` 复制到仓库。`DOMAIN=:80` 可用于临时 IP 验收，但手机定位、图片上传和正式访问应使用已解析到服务器的 HTTPS 域名。千牛退款/聊天数据项目继续使用本机真实 Chrome + Playwright MCP，由本机任务通过 HTTPS 向服务器导入数据。

这套脚本负责构建、同步、启动和健康检查。2026-08-12 已在腾讯云 Lighthouse 的 Ubuntu 24.04 实例上完成首次部署；真实公网 IP、MiniMax Key 和 `.env.production` 只保留在服务器，不写入仓库。

## 本地验收命令

```bash
cd backend && uv run uvicorn outfit_ai.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run build
```

当前使用 `http://服务器公网IP` 临时验收，尚未配置正式域名和 HTTPS；域名就绪后将 `DOMAIN` 改为域名并重新运行部署脚本。

### 从本机迁移已有数据

本地实际运行数据默认位于 `~/.outfit-ai/`（包括 `outfit_ai.db`、原图和 `.nobg.png` 派生图），不是仓库内的 `backend/data/`。迁移前先停止云端 `app` 容器，备份 Docker volume，再将该目录中的数据库和 `uploads/` 同步到 `outfit-ai_outfit_data` volume，最后启动 Compose 并核对 `wardrobe_items`、`style_references`、`feedback`、`outfit_history` 和 `profile` 计数。不要删除本机源目录；云端替换前必须保留可回滚备份。

## 平台取舍（2026-08-10 核对）

| 方案 | 免费情况 | 中国大陆访问 | 与当前项目的匹配度 | 结论 |
|---|---|---|---|---|
| PocketBay | 公共测试期免费；动态应用会休眠 | 中国大陆可用性需要实测，无官方保证 | 支持 Python/Docker 单容器和 `/data`；不支持 Compose/Worker/Redis | **最快验证** |
| 国内轻量云主机（腾讯云 Lighthouse 等） | 通常是新用户试用/代金券，不承诺永久免费 | 国内地域最稳；正式域名服务需按要求备案 | 可直接运行 FastAPI、SQLite、rembg 和本地图片目录 | **稳定自用推荐** |
| Vercel | 前端免费层可用，Python/FastAPI Functions 可部署 | 访问质量需实测，不应假设大陆稳定 | 函数文件系统不适合 SQLite/media；上传与长 AI 请求也有函数限制 | 只适合静态前端预览 |
| Cloudflare Pages + Workers | Pages/Workers 有免费额度 | `pages.dev` 在大陆不可用；China Network 是 Enterprise 独立订阅且需 ICP | Pages 适合静态前端；当前 FastAPI/rembg/SQLite 不能直接搬到 Workers | 不作为当前后端方案 |
| Supabase Free | 500 MB Postgres、1 GB Storage；闲置项目会暂停 | 没有中国大陆 region，最近通常选新加坡 | 适合未来的 Postgres + 对象存储；需要改 SQLAlchemy 配置和图片存储 | 第二阶段再评估 |
| 腾讯云 CloudBase 免费体验 | 目前每账号一个免费体验环境，资源点和续期有明确限制 | 国内产品，访问更友好 | 需要适配 CloudBase 数据库/云函数/云托管，不是当前 FastAPI 的零改动部署 | 若转小程序再评估 |

严格意义上“永久免费、国内稳定、同时支持 FastAPI + 持久化数据库 + 图片存储”的一体化免费方案目前不现实。当前个人使用的最低成本路径是：国内轻量云主机 + 持久化 SQLite + 同机图片目录；后续多人使用再换 PostgreSQL 和对象存储。

## 后续形态

- iOS：等功能稳定后再用 Capacitor 包装现有 React；提交 App Store 需要 Apple Developer Program 会员。
- 微信小程序：需要重写/适配页面层和微信登录、审核、云存储等能力，不能假设当前 React Web 可零改动发布。
