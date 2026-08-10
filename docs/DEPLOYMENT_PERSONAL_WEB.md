# Outfit-AI 个人使用部署

当前先部署为私有 HTTPS Web（手机浏览器可添加到主屏幕），暂不做 App Store 或微信小程序发布。这样可以保留已确认的 React 视觉与交互，也不需要先支付应用商店年费；真正的离线 PWA 壳等功能稳定后再加。

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

## 本地验收命令

```bash
cd backend && uv run uvicorn outfit_ai.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run build
```

实际云端发布尚未执行：当前没有指定 VPS、域名、DNS 或服务器密钥，因此本文件是可执行方案而不是“已部署”声明。

## 平台取舍（2026-08-10 核对）

| 方案 | 免费情况 | 中国大陆访问 | 与当前项目的匹配度 | 结论 |
|---|---|---|---|---|
| 国内轻量云主机（腾讯云 Lighthouse 等） | 通常是新用户试用/代金券，不承诺永久免费 | 国内地域最稳；正式域名服务需按要求备案 | 可直接运行 FastAPI、SQLite、rembg 和本地图片目录 | **第一阶段推荐** |
| Vercel | 前端免费层可用，Python/FastAPI Functions 可部署 | 访问质量需实测，不应假设大陆稳定 | 函数文件系统不适合 SQLite/media；上传与长 AI 请求也有函数限制 | 只适合静态前端预览 |
| Cloudflare Pages + Workers | Pages/Workers 有免费额度 | `pages.dev` 在大陆不可用；China Network 是 Enterprise 独立订阅且需 ICP | Pages 适合静态前端；当前 FastAPI/rembg/SQLite 不能直接搬到 Workers | 不作为当前后端方案 |
| Supabase Free | 500 MB Postgres、1 GB Storage；闲置项目会暂停 | 没有中国大陆 region，最近通常选新加坡 | 适合未来的 Postgres + 对象存储；需要改 SQLAlchemy 配置和图片存储 | 第二阶段再评估 |
| 腾讯云 CloudBase 免费体验 | 目前每账号一个免费体验环境，资源点和续期有明确限制 | 国内产品，访问更友好 | 需要适配 CloudBase 数据库/云函数/云托管，不是当前 FastAPI 的零改动部署 | 若转小程序再评估 |

严格意义上“永久免费、国内稳定、同时支持 FastAPI + 持久化数据库 + 图片存储”的一体化免费方案目前不现实。当前个人使用的最低成本路径是：国内轻量云主机 + 持久化 SQLite + 同机图片目录；后续多人使用再换 PostgreSQL 和对象存储。

## 后续形态

- iOS：等功能稳定后再用 Capacitor 包装现有 React；提交 App Store 需要 Apple Developer Program 会员。
- 微信小程序：需要重写/适配页面层和微信登录、审核、云存储等能力，不能假设当前 React Web 可零改动发布。
