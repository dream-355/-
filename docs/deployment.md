# 分享与部署

本项目包含 FastAPI、SQLite 和 Neo4j，不能只上传 `index.html`。访问者必须能够访问正在运行的 Web 服务和 Neo4j 所在的主机。

## 方案一：同一 Wi-Fi 局域网访问

适合比赛现场、宿舍或办公室内的其他电脑、平板和手机。

1. 启动 Docker Desktop，并确认 Neo4j 容器运行。
2. 关闭当前占用 8000 端口的服务。
3. 在项目目录打开 PowerShell：

```powershell
.\share-lan.ps1
```

4. 将脚本显示的地址发给同一局域网的朋友，例如：

```text
http://192.168.31.217:8000/
```

5. Windows 首次询问防火墙权限时，允许“专用网络”。

限制：电脑必须开着、服务不能关闭，对方必须和你在同一个 Wi-Fi。公网无法直接访问该局域网地址。

## 方案二：临时公网链接（推荐用于快速演示）

Cloudflare Quick Tunnel 不需要 Cloudflare 账号，也不需要 GitHub 账号。它把本机 `127.0.0.1:8000` 临时映射成公网 HTTPS 链接。

1. 保持本项目 Web 服务和 Neo4j 运行。
2. 安装 `cloudflared`：

```powershell
winget install --id Cloudflare.cloudflared -e
```

3. 重新打开 PowerShell，执行：

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

4. 终端会输出一个类似下面的地址：

```text
https://random-words.trycloudflare.com
```

5. 将访问地址发给朋友，在登录页点击“游客快速体验”。

限制：

- 每次重启隧道都会生成新链接；
- 你的电脑必须保持开机且服务不停止；
- 关闭命令窗口后链接立即失效；
- 不要把含有真实个人健康信息的环境公开给陌生人。

## 方案三：长期公网部署

如果希望不依赖你的电脑、链接长期有效，需要一台云服务器。推荐配置：

- Ubuntu 22.04 / 24.04；
- 最低 2 核 CPU、4 GB 内存、40 GB 磁盘；建议创建 2 GB Swap；
- Docker Engine；
- 一个已备案域名（健康类公网服务强烈建议使用 HTTPS）。

这一步需要云服务器账号；不需要把密码发到聊天中，后续使用 SSH 密钥登录。域名不是技术上的强制项，但没有域名时 Caddy 无法自动签发受信任 HTTPS 证书，不建议直接使用 HTTP 收集健康信息。

### 2 核 4 GB 内存优化

4 GB 实例可以运行评测和少量并发访问。首次登录服务器后可创建 2 GB Swap：

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

生产配置默认使用 `768m` 初始堆、`1g` 最大堆和 `512m` Neo4j 页缓存。若升级到 8 GB 内存，可在 `.env` 中提高：

```dotenv
NEO4J_HEAP_INITIAL=1g
NEO4J_HEAP_MAX=2g
NEO4J_PAGECACHE=1g
```

4 GB 适合比赛演示和少量用户；如果以后增加本地 OCR、向量模型或较多并发，建议升级到 8 GB。

### 1. 先在本机导出 Neo4j

这会短暂停止本机 Neo4j，导出完成后自动重新启动：

```powershell
.\scripts\export-neo4j.ps1
```

成功后生成：

```text
neo4j_backup/neo4j.dump
```

不要直接复制 `D:\neo4j-new\data`，Neo4j 数据目录不是跨机器可移植的备份格式。

### 2. 上传项目

在云服务器上安装 Docker Engine，然后通过 Git 仓库或 SFTP 上传代码。至少需要上传：

```text
backend/
frontend/
scripts/import-neo4j.sh
Dockerfile
docker-compose.prod.yml
Caddyfile
requirements.txt
neo4j_backup/neo4j.dump
```

不要上传本机的 `.env` 和 `data/qihuang.db`。

### 3. 配置服务器环境

在服务器项目目录执行：

```bash
cp .env.production.example .env
nano .env
```

必须修改：

- `DOMAIN`：解析到服务器公网 IP 的域名；
- `NEO4J_PASSWORD`：新的强密码；
- `APP_SECRET`：至少 32 位随机字符串；
- `DEEPSEEK_API_KEY`：你的模型 Key。

### 4. 导入知识图谱

首次先启动 Neo4j 初始化数据目录：

```bash
docker compose -f docker-compose.prod.yml up -d neo4j
sleep 20
chmod +x scripts/import-neo4j.sh
./scripts/import-neo4j.sh
```

导入脚本会停止 Neo4j、载入 `neo4j.dump`、然后重新启动全部服务。

### 5. 启动生产服务

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

服务结构：

- `caddy`：公网入口，自动申请域名 HTTPS 证书；
- `app`：FastAPI 与前端；
- `neo4j`：仅容器内网访问，不向公网暴露 7474/7687；
- `zhiheng_data`：SQLite 用户与会话持久卷；
- `neo4j_data`：Neo4j 持久卷。

云防火墙只开放：

- `22`：SSH 管理；
- `80`：HTTP 证书验证与跳转；
- `443`：HTTPS 正式访问。

### 6. 检查

```bash
curl https://你的域名/api/health
docker compose -f docker-compose.prod.yml logs -f --tail=100
```

响应中应包含：

```json
{"ok":true,"neo4j":{"online":true},"deepseek_configured":true}
```

### 7. 后续更新与备份

更新代码后执行：

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

定期备份 Neo4j 和 SQLite。修改代码或环境变量前先完成数据库备份，不要删除 Docker 数据卷。

## 竞赛评审专用：公网 IP，无域名与备案

如果指导老师确认系统只用于竞赛评审、不对外提供长期医疗服务，可以按评审演示模式部署。此模式通过标准 80 端口直接暴露 FastAPI，不启动 Caddy，也不配置域名和 HTTPS。

安全组增加：

| 协议 | 端口 | 来源 |
|---|---|---|
| TCP | 80 | `0.0.0.0/0` |

首次启动：

```bash
cd /opt/qihuang
docker compose -f docker-compose.prod.yml -f docker-compose.trial.yml up -d neo4j
sleep 30
sh scripts/import-neo4j-trial.sh
```

评审链接：

```text
http://服务器公网IP/
```

此模式没有 HTTPS，访问者提交的账户、对话和健康信息会在公网明文传输。评审账号只能使用虚构数据，不要邀请评审人员填写真实健康信息。

### 公网 HTTPS 与在线演示

公网评审演示建议使用 HTTPS，便于安全传输评审账号、会话和图片。可在评审服务器上启动临时 Cloudflare HTTPS 隧道：

```bash
cd /opt/zhiheng
docker compose -f docker-compose.prod.yml -f docker-compose.trial.yml -f docker-compose.https.yml up -d cloudflared
docker compose -f docker-compose.prod.yml -f docker-compose.trial.yml -f docker-compose.https.yml logs cloudflared
```

日志中会出现 `https://xxxx.trycloudflare.com` 地址。直接分享该地址，访问者在登录页点击“游客快速体验”即可。隧道容器持续运行期间链接有效，重新创建容器后可能变化；正式长期方案仍应使用自己的域名和 Caddy HTTPS。

## 更新网页或后端功能

日常修改前端或后端后，不需要重新导出、上传或导入 Neo4j 图谱。在本机生成轻量更新包：

```powershell
.\package-update.ps1
```

把生成的 `zhiheng-app-update.zip` 上传到服务器 `/root`，然后在服务器执行：

```bash
cd /opt/zhiheng
unzip -o /root/zhiheng-app-update.zip -d /opt/zhiheng
sh scripts/update-app.sh
```

更新脚本只重建 `app` 容器。Neo4j、知识图谱、SQLite 用户数据和 `.env` 都会保留。

只有以下情况需要重新导入 Neo4j：

- 更换服务器或数据卷；
- 图谱数据本身需要恢复；
- 删除或损坏了 Neo4j 数据卷。

## 不要直接分享的文件

- `.env`：包含 Neo4j 密码和 DeepSeek API Key；
- `data/qihuang.db`：包含本机用户、健康记录和会话；
- `D:\neo4j-new\data`：Neo4j 本机数据目录，需要先通过 Neo4j 官方方式导出。

如果只是让别人体验界面和演示数据，推荐使用方案一或方案二；如果要把知识图谱部署到别人电脑，需要连同 Neo4j 数据一起迁移，不能只复制 Python 代码。

## 三维解剖资源容量

- `frontend/models` 中男女压缩解剖数据和中文术语表合计约 77 MB；浏览器一次只加载当前选定性别。
- 男性几何约 33.5 MB，女性几何约 39.1 MB（含胃、食管及口咽补充结构），均为预压缩分块，应用服务器只负责静态传输，不在 Python 进程中解压或渲染。
- 几何分块采用一年期 immutable 缓存；同一浏览器再次打开时通常不再重复下载。
- 2 核 8 GB 服务端配置足以承载静态模型传输。主要体验依赖访问者浏览器 WebGL 性能，手机端会自动使用较低像素比。
