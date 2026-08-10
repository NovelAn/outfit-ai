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

## 后续形态

- iOS：等功能稳定后再用 Capacitor 包装现有 React；提交 App Store 需要 Apple Developer Program 会员。
- 微信小程序：需要重写/适配页面层和微信登录、审核、云存储等能力，不能假设当前 React Web 可零改动发布。
