# vedio — 视频生成平台

H5 前端 + Python 后端 + xAI Grok API，部署到本服务器，域名 `grok.windory.xyz`。

## 结构

```
.
├── backend/          # Python 后端（纯标准库，零第三方依赖）
│   ├── app.py        # HTTP API + 异步任务 worker
│   ├── config.py     # 环境变量配置（模型名/端点全部配置驱动）
│   ├── store.py      # 线程安全的 JSON 文件存储
│   ├── xai_client.py # xAI Grok API 客户端（Text/Image/Video，可 mock）
│   └── __main__.py   # 启动入口
├── frontend/         # H5 单页前端（原生 HTML/CSS/JS，零构建）
│   ├── index.html
│   ├── app.js
│   └── style.css
├── deploy/           # 部署配置（Nginx + systemd）
│   ├── nginx.conf
│   └── vedio.service
├── tests/            # unittest 测试
├── requirements.txt
└── run.sh
```

## 本地运行

```bash
# 后端（默认 MOCK 模式，无需 API Key 即可跑通完整流程）
python3 -m backend
# 或
bash run.sh

# 打开前端：浏览器访问 http://localhost:8000/
```

后端默认监听 `0.0.0.0:8000`，同时托管前端静态文件和 `/api/v1` 接口。

## 接入真实 xAI API

```bash
export XAI_API_KEY=你的密钥
export MOCK_MODE=0
export XAI_VIDEO_MODEL=grok-video-1      # 以 docs.x.ai 当前值为准
export XAI_TEXT_MODEL=grok-3
export XAI_IMAGE_MODEL=grok-2-image
python3 -m backend
```

`XAI_API_KEY` 只存在于服务端环境变量，绝不下发前端、不写入代码库。

## API 契约（前缀 /api/v1）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/generations` | 创建生成任务，`202 {task_id, status}` |
| GET | `/generations/{id}` | 查询任务状态/结果 |
| GET | `/generations?page=&page_size=` | 历史列表 |
| DELETE | `/generations/{id}` | 删除任务，`204` |
| POST | `/prompts/enhance` | 文本增强 |

任务状态机：`queued → processing → succeeded | failed`。

## 测试

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## 部署（grok.windory.xyz）

见 `deploy/README.md`：DNS A 记录 → 服务器公网 IP，Nginx 反代 `/api` 到后端并托管前端，certbot 配 HTTPS。
