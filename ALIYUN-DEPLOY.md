# 阿里云 2 核 4 GB 部署

本包采用公网 IP 直接访问模式，不配置域名、HTTPS 和 SMTP 邮件服务。注册、登录和游客体验不依赖邮件验证。

## 1. 创建 Swap

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

## 2. 安装 Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
docker --version
docker compose version
```

## 3. 上传并解压

在本机执行，替换服务器 IP：

```bash
scp zhiheng-aliyun-2c4g-20261108.zip root@服务器IP:/root/
```

在服务器执行：

```bash
mkdir -p /opt/zhiheng
unzip -o /root/zhiheng-aliyun-2c4g-20261108.zip -d /opt/zhiheng
cd /opt/zhiheng
cp .env.aliyun.example .env
nano .env
```

必须修改：

- `NEO4J_PASSWORD`
- `APP_SECRET`
- `DEEPSEEK_API_KEY`（可暂时留空，系统会用本地证据规则降级）
- `PUBLIC_BASE_URL`，例如 `http://1.2.3.4`

可将阿里云安全组限制为只开放 `22` 和 `80` 端口。

## 4. 导入知识图谱

```bash
cd /opt/zhiheng
docker compose -f docker-compose.prod.yml -f docker-compose.trial.yml up -d neo4j
sleep 30
sh scripts/import-neo4j-trial.sh
```

首次导入会将本包中的 `neo4j_backup/neo4j.dump` 载入 Docker 数据卷。

## 5. 启动并检查

```bash
cd /opt/zhiheng
docker compose -f docker-compose.prod.yml -f docker-compose.trial.yml up -d --build app
docker compose -f docker-compose.prod.yml -f docker-compose.trial.yml ps
curl http://127.0.0.1/api/health
```

浏览器访问：

```text
http://服务器公网IP/
```

健康接口需显示：

```json
{"ok":true,"neo4j":{"online":true}}
```

## 后续更新

只更新应用代码时：

```bash
cd /opt/zhiheng
unzip -o /root/zhiheng-app-update.zip -d /opt/zhiheng
sh scripts/update-app.sh
```

不要删除 Docker 数据卷，否则会丢失用户数据和图谱。
