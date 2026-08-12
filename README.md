# Outfit-AI

个人 AI 衣橱：真实衣物去背景入库，参考 Look 沉淀 Style DNA；每天从真实衣橱给出 **Safe / Fresh / Stretch** 三套穿搭，也可生成不依赖现有单品的未来灵感图。

> v0 跑 H5；前端完整采用用户确认的 Google AI Studio / Stitch React 导出包。

当前实现文档：

- [前端页面、入口、功能与 API 映射](docs/frontend/CURRENT_FRONTEND_INTEGRATION.md)
- [后端、数据模型与 API 规格](docs/SPEC.md)
- [项目开发规则](CLAUDE.md)

## 架构一句话

**识图、生图、文本造型分工**：本地 `rembg` 处理真实衣物，MiniMax VLM 提取衣物与参考 Look 属性，MiniMax-M3 结合 Style DNA 生成真实衣橱搭配，`image-01` 生成独立灵感图；规则只做真实性和天气等硬护栏。

## 快速开始

```bash
# 后端
cd backend
uv sync                                        # 或 pip install -e ".[dev]"
# 可设置 MINIMAX_API_KEY；未设置时只读复用 ~/.mmx/config.json
uvicorn outfit_ai.main:app --reload             # http://localhost:8000/docs

# 前端
cd frontend
npm install
npm run dev                                    # http://localhost:5173
```

要求 Node.js 20 及以上。前端开发服务器会把 `/api` 和 `/media` 代理到 `http://localhost:8000`。

首次上传真实衣物时，`rembg` 会下载约 176MB 的本地去背景模型到 `~/.u2net/`，可能需要 2–3 分钟；模型缓存后，后续衣物无需重复下载。

## 部署前准备

- 后端使用 HTTPS 域名；中国大陆部署提前完成 ICP 备案。
- 生产图片改存阿里云 OSS/CDN；不要把用户图片打进小程序主包。
- 微信小程序/App 上线方案需保留当前 React 界面与交互，不回退旧 uni-app 设计。

## 腾讯云一键部署

当前推荐一台 Ubuntu 24.04 LTS 轻量服务器：Docker 运行 FastAPI，Caddy 托管 React 静态资源并负责 HTTPS，SQLite、上传图片和 rembg 模型缓存使用持久化卷。千牛 Playwright MCP 继续运行在本机已登录 Chrome，不放进 Web 容器。

首次腾讯云 Lighthouse 部署已于 2026-08-12 完成；当前先通过服务器公网 IP 的 HTTP 地址验收，正式域名和 HTTPS 后续再配置。

首次部署（服务器已配置 SSH 公钥后）：

```bash
# 1. 首次只执行一次：初始化 Ubuntu/Docker/UFW
ssh root@SERVER_IP 'mkdir -p /tmp/outfit-ai-bootstrap'
rsync -az scripts/ root@SERVER_IP:/tmp/outfit-ai-bootstrap/scripts/
ssh root@SERVER_IP 'bash /tmp/outfit-ai-bootstrap/scripts/bootstrap-ubuntu.sh'

# 2. 服务器上创建密钥文件（只在服务器填写，不提交）
scp .env.production.example root@SERVER_IP:/tmp/outfit-ai.env.production.example
ssh root@SERVER_IP 'mkdir -p /opt/outfit-ai && cp /tmp/outfit-ai.env.production.example /opt/outfit-ai/.env.production'
# 编辑 /opt/outfit-ai/.env.production，至少填写 MINIMAX_API_KEY 和 DOMAIN

# 3. 本机一条命令构建、同步、启动并检查健康接口
DEPLOY_HOST=root@SERVER_IP ./scripts/deploy.sh
```

`DOMAIN=:80` 只适合临时 IP 验收；正式使用应先把域名 A 记录指向服务器，再将 `DOMAIN` 改为域名，Caddy 会自动申请 HTTPS。不要把 `.env.production`、MiniMax Key、`data/` 或浏览器登录状态同步到服务器代码目录。

## 借鉴与署名

本项目站在三个开源项目肩膀上（源码级调研后选择性 port / 抽象）：

| 来源 | 许可证 | 借鉴 |
|---|---|---|
| [`jonnykate/ai-closet`](https://github.com/jonnykate/ai-closet) | MIT | LLM 调用 / item_id 校验 / 失败重试 / 拼图 / 历史重复规避 |
| [`Gurshaan-Deol/Hangar`](https://github.com/Gurshaan-Deol/Hangar) | MIT | 上传状态机 / Open-Meteo 天气 / AI 属性 schema |
| [`googlarz/fashion-skill`](https://github.com/googlarz/fashion-skill) | CC BY 4.0 | Style DNA 与 4 实体数据模型（仅抽象字段，未复制 prompt） |

## License

MIT（待最终确认）。
