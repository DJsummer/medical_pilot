# AI B超报告书写助手

通过医生语音口述检查所见，AI 自动整理、规范化并生成超声报告，**辅助医生快速完成报告书写**。

> 核心定位：**辅助书写**，而非辅助诊断。

## 落地部署（3 步）

```bash
cd /home/jdong/project/AI/medical_pilot
chmod +x scripts/*.sh
./scripts/install.sh    # 首次：装依赖 + 跑测试
./scripts/start.sh      # 启动服务
./scripts/health_check.sh # 自检
```

浏览器打开：**http://127.0.0.1:8900**

详细说明见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## 产品流程

```
医生检查 → 🎙 口述 → ASR → AI 结构化 → 报告生成 → AI 校验 → 医生审核 → 签发
```

## 项目结构

```
medical_pilot/
├── backend/           # FastAPI + LLM + ASR + 报告引擎
├── frontend/          # B超报告单 UI
├── data/              # Schema、Gold、模板、报告存储
├── scripts/           # install / start / stop / health_check
├── docs/              # 架构 + Schema + 部署文档
├── Dockerfile         # 可选容器部署
└── .env               # 百炼 API Key（勿提交）
```

## 日常运维

| 命令 | 说明 |
|------|------|
| `./scripts/start.sh` | 生产启动 |
| `./scripts/stop.sh` | 停止 |
| `./scripts/restart.sh` | 重启 |
| `./scripts/dev_server.sh` | 开发模式（热重载） |
| `python scripts/eval_gold_reports.py` | 模板质量评估 |

## 配置

`.env` 关键项：

- `DASHSCOPE_API_KEY` — 百炼密钥（LLM + ASR 共用）
- `MEDICAL_LLM_MODEL` — 结构化模型（如 `qwen-plus`）
- `MEDICAL_ASR_MODEL` — 语音模型（`qwen3-asr-flash`）
- `MEDICAL_PORT` — 端口（默认 8900）

## 支持检查类型

腹部超声、甲状腺、乳腺、妇科、心脏、血管、浅表淋巴结（工具栏可切换）。

- 书写时间：3 分钟 → **30 秒**
- **医生修改率**（最重要）
- ASR 转写成功率、报告生成成功率
