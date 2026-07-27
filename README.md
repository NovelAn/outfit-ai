# Outfit-AI

个人 AI 衣橱：拍真实衣物入库 → 沉淀可编辑 Style DNA → 结合天气/场合/心情，每天给出**基调稳定又能持续变化**的 **Safe / Fresh / Stretch** 三套穿搭，并通过反馈越用越懂。

> v0 跑 H5；同一套 uni-app 代码未来编译微信小程序 / 手机 App。

## 架构一句话

**多模态造型师 + 硬护栏**：规则只过滤天气/季节/重复（硬护栏，不评分）→ MiniMax-M3 看候选单品**照片** + Style DNA + **品味备忘录**，凭品味组装 Safe/Fresh/Stretch 三档 → 反馈周期性沉淀回品味备忘录，越用越懂。

## 快速开始

```bash
# 后端
cd backend
uv sync                                        # 或 pip install -e ".[dev]"
cp ../.env.example ../.env                     # 填入 MINIMAX_API_KEY
uvicorn outfit_ai.main:app --reload            # http://localhost:8000/docs

# 前端
cd frontend
npm install
npm run dev:h5                                 # http://localhost:5173
```

详见 [`docs/design.md`](docs/design.md) 与 [`CLAUDE.md`](CLAUDE.md)。

## 借鉴与署名

本项目站在三个开源项目肩膀上（源码级调研后选择性 port / 抽象）：

| 来源 | 许可证 | 借鉴 |
|---|---|---|
| [`jonnykate/ai-closet`](https://github.com/jonnykate/ai-closet) | MIT | LLM 调用 / item_id 校验 / 失败重试 / 拼图 / 历史重复规避 |
| [`Gurshaan-Deol/Hangar`](https://github.com/Gurshaan-Deol/Hangar) | MIT | 上传状态机 / Open-Meteo 天气 / AI 属性 schema |
| [`googlarz/fashion-skill`](https://github.com/googlarz/fashion-skill) | CC BY 4.0 | Style DNA 与 4 实体数据模型（仅抽象字段，未复制 prompt） |

## License

MIT（待最终确认）。
