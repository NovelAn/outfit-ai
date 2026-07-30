# Outfit-AI

个人 AI 衣橱：真实衣物去背景入库，参考 Look 沉淀 Style DNA；每天从真实衣橱给出 **Safe / Fresh / Stretch** 三套穿搭，也可生成不依赖现有单品的未来灵感图。

> v0 跑 H5；前端完整采用用户确认的 Google AI Studio / Stitch React 导出包。

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

详见 [`docs/design.md`](docs/design.md) 与 [`CLAUDE.md`](CLAUDE.md)。

## 部署前准备

- 后端使用 HTTPS 域名；中国大陆部署提前完成 ICP 备案。
- 生产图片改存阿里云 OSS/CDN；不要把用户图片打进小程序主包。
- 微信小程序/App 上线方案需保留当前 React 界面与交互，不回退旧 uni-app 设计。

## 借鉴与署名

本项目站在三个开源项目肩膀上（源码级调研后选择性 port / 抽象）：

| 来源 | 许可证 | 借鉴 |
|---|---|---|
| [`jonnykate/ai-closet`](https://github.com/jonnykate/ai-closet) | MIT | LLM 调用 / item_id 校验 / 失败重试 / 拼图 / 历史重复规避 |
| [`Gurshaan-Deol/Hangar`](https://github.com/Gurshaan-Deol/Hangar) | MIT | 上传状态机 / Open-Meteo 天气 / AI 属性 schema |
| [`googlarz/fashion-skill`](https://github.com/googlarz/fashion-skill) | CC BY 4.0 | Style DNA 与 4 实体数据模型（仅抽象字段，未复制 prompt） |

## License

MIT（待最终确认）。
