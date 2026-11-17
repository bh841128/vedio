# 部署到 grok.windory.xyz

前提：域名 A 记录已指向本服务器公网 IP，服务器有公网 80/443 端口。

## 1. 代码与密钥
```bash
sudo mkdir -p /opt/vedio && sudo cp -r . /opt/vedio
# 个人凭证写在 .env（仅 root/www-data 可读，绝不入库）
sudo tee /opt/vedio/.env >/dev/null <<'ENV'
XAI_API_KEY=你的密钥
MOCK_MODE=0
XAI_VIDEO_MODEL=grok-video-1
ENV
sudo chmod 600 /opt/vedio/.env
```

## 2. 后端服务
```bash
sudo cp deploy/vedio.service /etc/systemd/system/vedio.service
sudo systemctl daemon-reload
sudo systemctl enable --now vedio
curl http://127.0.0.1:8000/api/v1/health   # -> {"status":"ok"}
```

## 3. Nginx + HTTPS
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/grok.windory.xyz
sudo ln -sf /etc/nginx/sites-available/grok.windory.xyz /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d grok.windory.xyz   # 自动签发 + 配置 HTTPS + 续期
```

## 4. 验证
浏览器打开 https://grok.windory.xyz/ ，和 `https://grok.windory.xyz/api/v1/health`。

说明：xAI Key 属责任人个人凭证，按运行卡片「去配置」或上面 .env 步骤配置；Key 只在服务端，不下发前端。
