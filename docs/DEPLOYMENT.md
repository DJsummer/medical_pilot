# AI B超报告书写助手 — 落地部署指南

## 1. 环境要求

| 项 | 要求 |
|----|------|
| OS | Linux（推荐 RHEL/CentOS 9、Ubuntu 22+） |
| Python | 3.9+ |
| 浏览器 | Chrome / Edge（语音 ASR 推荐） |
| 网络 | 可访问百炼 DashScope API |
| 端口 | 默认 `8900`（可改 `MEDICAL_PORT`） |

## 2. 一键安装

```bash
cd /home/jdong/project/AI/medical_pilot
chmod +x scripts/*.sh
./scripts/install.sh
```

编辑 `.env` 填入百炼 API Key（已配置可跳过）。

## 3. 启动 / 停止

```bash
./scripts/start.sh      # 生产模式启动
./scripts/health_check.sh   # 自检
./scripts/stop.sh       # 停止
./scripts/restart.sh    # 重启
```

开发调试（热重载）：

```bash
./scripts/dev_server.sh
```

## 4. Docker 部署（可选）

```bash
docker compose up -d --build
docker compose logs -f
```

报告数据持久化在 `data/reports/`，日志在 `data/logs/`。

## 5. 院内访问

### 本机

http://127.0.0.1:8900

### 局域网其他电脑

http://<服务器IP>:8900

确保防火墙放行 `8900`：

```bash
# firewalld 示例
sudo firewall-cmd --permanent --add-port=8900/tcp
sudo firewall-cmd --reload
```

### 反向代理（推荐生产）

Nginx 示例：

```nginx
server {
    listen 80;
    server_name ultrasound.hospital.local;

    client_max_body_size 30m;  # ASR 音频上传

    location / {
        proxy_pass http://127.0.0.1:8900;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**建议**：仅内网访问，不要公网暴露；API Key 仅存服务器 `.env`。

## 6. systemd 常驻（可选）

```bash
sudo tee /etc/systemd/system/medical-pilot.service << 'EOF'
[Unit]
Description=AI B超报告书写助手
After=network.target

[Service]
Type=simple
User=jdong
WorkingDirectory=/home/jdong/project/AI/medical_pilot
ExecStart=/usr/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8900 --workers 1
EnvironmentFile=/home/jdong/project/AI/medical_pilot/.env
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now medical-pilot
```

## 7. 医生使用流程（试点）

1. 打开浏览器 → 报告单页面
2. 填写患者信息（姓名、门诊号等）
3. 点击 **点击录音** → 口述检查所见 → **结束并转写**
4. 点击 **生成报告**（勾选 LLM）
5. 核对左侧 AI 结构化 + 右侧报告单
6. 修改超声所见 / 超声提示
7. **保存** → **签发**

## 8. 数据与备份

| 路径 | 内容 |
|------|------|
| `data/reports/*.json` | 已保存 / 已签发报告 |
| `data/logs/server.log` | 服务日志 |

定期备份：

```bash
tar czf medical_pilot_backup_$(date +%Y%m%d).tar.gz data/reports data/logs
```

## 9. 试点 KPI 记录

建议每周统计：

- 报告生成成功率
- 医生修改率（修改记录条数 / 报告数）
- ASR 转写可用率
- 平均从口述到签发耗时

## 10. 常见问题

| 问题 | 处理 |
|------|------|
| `Internal Server Error` | 查看 `data/logs/server.log`，确认 `.env` Key 有效 |
| ASR 失败 | 确认 `MEDICAL_ASR_MODEL=paraformer-v2`，Chrome 授权麦克风 |
| LLM 慢 | 可改用 `qwen-plus` 或关闭 LLM 用 Gold 演示 |
| 端口占用 | 改 `.env` 中 `MEDICAL_PORT` 或 `stop.sh` 后重启 |

## 11. 版本信息

- 检查类型：腹部超声（V1）
- Gold Dataset：20 条
- 定位：辅助书写，非辅助诊断
