# 知衡健康

面向传智杯比赛的可信医疗问答与个人健康智能体。项目复用本机现有 Neo4j 中文医疗知识图谱，以“实体识别 → 图谱多跳检索 → DeepSeek 受约束生成 → 急症规则校验”为核心链路，同时提供连续健康档案、个人趋势识别、智能分诊、对话记忆和 3D 图谱探索。

## 已实现能力

- Neo4j 医疗知识图谱：复用现有 141,178 个节点、684,564 条关系，不覆盖原数据。
- 医疗实体检索：创建独立全文检索索引，支持疾病、药品、症状、检查、科室等实体。
- 可解释问答：每次回答展示命中实体、关系类型、证据数量、分诊等级和生成模式。
- 混合检索：Neo4j 全文索引叠加 80,955 个医疗实体的本地中文字符向量召回，并按症状、病因、检查、治疗等意图过滤关系。
- 逐条引用：回答中的 `[E1]` 引用可点击查看主体、关系、客体和 Neo4j 来源。
- DeepSeek 严格问答：仅依据图谱证据与用户信息回答，禁止编造剂量、诊断和文献。
- 多模态分析：支持 JPG、PNG、WebP 图片，使用 DeepSeek Vision 描述可见的皮肤、伤口、报告文字或药品包装信息，不将图片写入数据库。
- 智能设备读数导入：可上传智能手表、健康 App 截图或直接拍照，识别血压、心率、血糖、血氧、睡眠、体重和步数并预填体征表单；识别结果需用户核对后保存。
- 解剖级定位：男女分别使用独立三维解剖数据，可搜索、分层透视和自由框选，识别气管、肝段、胃肠、泌尿及生殖等细分结构。
- 咽喉深部：提供口腔、舌、腭、扁桃体、咽肌、喉软骨、会厌、声带和上段气管的展开视图，可按具体结构继续点击。
- 体态预览：可调整体表饱满度并保持内部器官位置不变；同时压低女性胸部区域的粒子亮度。
- 无障碍显示：用户菜单内可切换小、标准、大、特大四档界面字号，设置保存在当前浏览器。
- 健康证据护照：按时间轴汇总体征、风险检测和咨询记录，支持复制摘要及打印/保存 PDF。
- 真实体验反馈：内置 5 级体验问卷，可统计评分、易用性和帮助程度，用于后续用户验证。
- 游客快速体验：登录页提供“游客快速体验”，直接进入林知夏种子档案，无需注册或邮箱。
- 邮件账户服务：注册成功后发送账户通知；忘记密码通过 6 位邮箱验证码重置，验证码 10 分钟有效且一码一用。
- 健康报告邮件：健康证据护照和就诊前摘要可手动发送至当前账号绑定的邮箱。
- MCP 工具层：提供独立标准 MCP Server，开放实体检索、关系展开、症状分诊和非处方药参考工具。
- 多轮上下文：SQLite 持久化会话、消息、摘要和风险等级，刷新或重新登录后仍可继续。
- 对话自动归档：“我的空间”按内科、外科、耳鼻喉科、皮肤科等专科自动分类历史对话。
- 个人健康档案：过敏史、基础疾病、长期用药、家族史与身体指标统一管理。
- 连续健康分析：识别血压、心率、血糖、血氧、睡眠趋势及连续偏离。
- 健康生活建议：结合健康档案、最近体征和当前不适，生成一日三餐参考、减少食物清单与低风险活动建议；特殊疾病、孕期和高风险场景会先提示咨询专业人员。
- 智能症状分诊：独立规则引擎识别胸痛伴呼吸困难、卒中样表现、意识障碍、严重过敏等红旗信号。
- 非处方用药参考：按症状匹配咽部、感冒、过敏、腹泻等 OTC 对症选项，展示规格、参考价格、禁忌和实时比价入口；急症与孕期自动停止药品推荐。
- 3D 分层知识图谱：一级实体居中、二级直接关系环状展开、三级关联向外扩散；全部节点显示名称，支持拖拽、缩放、暂停旋转与点击查看。
- 可收起输入框：对话输入框固定在页面底部，长回答不会把它挤出屏幕，可随时隐藏或展开。
- 响应式高端界面：无需 Node、CDN 或在线字体，断网也能正常展示。
- 亮暗主题与页面历史：设置中可切换亮色/暗色模式，顶部“返回上一步”支持恢复之前打开的页面和对话。
- 隐私优先：健康档案与会话保存在本机 SQLite，不写入医疗知识图谱。

## 技术架构

系统由四个主要部分组成：

1. **浏览器前端**：原生 ES Modules、CSS、Canvas 和 Three.js。负责对话、健康档案、趋势分析、3D 知识图谱和男女分层解剖展示。
2. **FastAPI 应用层**：统一处理认证、会话、输入校验、问答编排、图片识别、邮件和静态资源。
3. **医疗知识图谱**：Neo4j 存储疾病、症状、检查、治疗、科室等实体和关系，并提供全文检索索引。
4. **模型与安全层**：DeepSeek 根据受约束的图谱证据生成回答；急症规则、引用校验和输出复核独立于模型运行。

核心问答链路：

```text
用户问题
  → 医疗实体识别
  → Neo4j 全文检索与本地字符向量召回
  → 多跳关系证据构建
  → 健康档案和风险规则上下文
  → DeepSeek 受约束生成
  → 急症规则与引用校验
  → 回答、证据链和会话持久化
```

详细设计见 [docs/architecture.md](docs/architecture.md)。

## 快速开始

### 环境要求

- Python 3.12
- Neo4j 5.x（需要访问一个已导入医疗知识图谱的 Neo4j 实例）
- Docker Engine 与 Docker Compose，仅容器部署时需要

Python 依赖清单位于 [requirements.txt](requirements.txt)。项目不依赖 Node.js、CDN 或在线字体。

### 本地运行

复制环境变量模板并填写数据库密码、模型 Key 等配置：

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell 可使用：

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\start.ps1
```

首次运行会自动完成：

1. 创建 SQLite 数据表；
2. 创建演示档案、7 天健康记录与示例对话；
3. 检查并在缺失时创建 Neo4j 全文索引；
4. 加载现有医疗知识图谱。

访问 `http://127.0.0.1:8000/`，登录页提供“游客快速体验”入口。游客种子账号为 `demo@qihuang.local`，仅用于本地演示。

同 Wi-Fi 分享给其他电脑：

```powershell
.\share-lan.ps1
```

外网临时链接、阿里云部署和长期云部署见 [docs/deployment.md](docs/deployment.md) 与 [ALIYUN-DEPLOY.md](ALIYUN-DEPLOY.md)。

## 配置 DeepSeek

在项目根目录的 `.env` 中填写：

```dotenv
DEEPSEEK_API_KEY=你的_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_VISION_MODEL=deepseek-flash
```

重启服务后，页面右上角会从“演示引擎”切换为“已配置”。Key 不会发送到浏览器，也不会写入数据库。

未配置 Key 时，系统自动使用 Neo4j 证据规则引擎，所有核心功能仍可现场演示，不会白屏。配置后若模型请求失败，也会自动降级到同一套安全规则，而不是返回不可信内容。

人体定位模型使用浏览器本地粒子点云渲染，不依赖 Node、CDN 或在线字体；拖动旋转、滚轮与滑块缩放均在本地完成。

真实解剖模型来自 BodyParts3D 和 Human Reference Atlas，均遵循 CC BY 4.0。完整来源、署名与适配记录见 [docs/anatomy-attribution.md](docs/anatomy-attribution.md)。

## 配置邮件服务

注册通知、密码重置验证码和健康报告邮件通过 SMTP 发送。在 `.env` 中配置：

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=no-reply@example.com
SMTP_PASSWORD=邮箱服务商提供的授权码或密码
SMTP_FROM=no-reply@example.com
SMTP_FROM_NAME=知衡健康
SMTP_STARTTLS=true
SMTP_SSL=false
SMTP_TIMEOUT=15
PUBLIC_BASE_URL=https://zhihengcare.icu
```

多数邮箱服务商要求使用 SMTP 授权码，不直接使用网页登录密码。465 端口通常使用 `SMTP_SSL=true`、`SMTP_STARTTLS=false`；587 端口通常使用 `SMTP_STARTTLS=true`、`SMTP_SSL=false`。

未配置 SMTP 时，注册、登录和游客体验仍可使用，但注册通知不会发送，密码找回与报告邮件会返回“邮件服务尚未配置”。游客种子账号使用本地演示邮箱，不支持报告邮件发送。

## 环境变量

项目提供三套模板：

- [.env.example](.env.example)：本地开发
- [.env.production.example](.env.production.example)：域名和 HTTPS 生产部署
- [.env.aliyun.example](.env.aliyun.example)：阿里云公网 IP 评测部署

所有真实密钥只填写在 `.env` 中。`.env` 已被 `.gitignore` 排除，不应提交到仓库。

| 变量 | 必需 | 默认值或示例 | 说明 |
|---|---|---|---|
| `NEO4J_URI` | 是 | `bolt://localhost:7689` | Neo4j Bolt 地址；Compose 部署自动改为容器地址 |
| `NEO4J_USER` | 是 | `neo4j` | Neo4j 用户名 |
| `NEO4J_PASSWORD` | 是 | 无 | Neo4j 密码，必须使用强密码 |
| `NEO4J_DATABASE` | 否 | `neo4j` | 数据库名称 |
| `NEO4J_HEAP_INITIAL` | 否 | `768m` | Neo4j 初始堆大小 |
| `NEO4J_HEAP_MAX` | 否 | `1g` | Neo4j 最大堆大小 |
| `NEO4J_PAGECACHE` | 否 | `512m` | Neo4j 页缓存大小 |
| `DEEPSEEK_API_KEY` | 否 | 空 | DeepSeek API Key；留空时使用本地图谱规则降级 |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com` | OpenAI 兼容 API 地址 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | 文本模型名称 |
| `DEEPSEEK_VISION_MODEL` | 否 | `deepseek-flash` | 图片识别模型名称 |
| `DEEPSEEK_TIMEOUT` | 否 | `45` | 模型请求超时秒数 |
| `SMTP_HOST` | 否 | 空 | SMTP 服务器地址；不使用邮件功能时留空 |
| `SMTP_PORT` | 否 | `587` | SMTP 端口 |
| `SMTP_USERNAME` | 否 | 空 | SMTP 登录用户名 |
| `SMTP_PASSWORD` | 否 | 空 | SMTP 授权码或密码 |
| `SMTP_FROM` | 否 | 空 | 发件人邮箱 |
| `SMTP_FROM_NAME` | 否 | `知衡健康` | 发件人显示名称 |
| `SMTP_STARTTLS` | 否 | `true` | 是否启用 STARTTLS |
| `SMTP_SSL` | 否 | `false` | 是否直接使用 SSL |
| `SMTP_TIMEOUT` | 否 | `15` | SMTP 超时秒数 |
| `PUBLIC_BASE_URL` | 否 | `http://127.0.0.1:8000` | 邮件链接使用的公网地址 |
| `APP_NAME` | 否 | `知衡健康` | 应用显示名称 |
| `APP_SECRET` | 是 | 无 | 登录会话签名密钥，至少 32 位随机字符 |
| `SESSION_DAYS` | 否 | `14` | 登录会话有效天数 |
| `DEMO_MODE` | 否 | `true` | 是否开放游客快速体验 |
| `COOKIE_SECURE` | 否 | `false` | 仅 HTTPS 部署时设为 `true` |
| `AUTH_RATE_LIMIT_PER_MINUTE` | 否 | `10` | 单 IP 每分钟认证请求上限 |
| `REVIEW_LLM_ENABLED` | 否 | `true` | 是否启用模型输出复核 |
| `DOMAIN` | 生产域名部署时 | `example.com` | Caddy 自动申请证书所用域名 |

## 目录

```text
backend/
  data/
    entity_catalog.jsonl  向量召回实体目录
  main.py          API、鉴权、问答编排、健康与图谱接口
  graph.py         Neo4j 检索、实体识别、多跳证据构建
  vector_index.py  本地中文字符向量召回
  mcp_server.py    标准 MCP stdio 服务
  tools.py         MCP/Function Calling 共用工具注册表
  llm.py           DeepSeek 调用与可信降级
  medications.py    非处方对症匹配、禁忌过滤与价格快照
  prompts.py       医疗安全系统提示词与上下文模板
  safety.py        急症识别、分诊、健康趋势分析
  db.py            SQLite 持久化与演示数据
frontend/
  index.html       产品入口
  assets/app.js    页面状态与功能编排
  assets/graph3d.js 独立 3D 图谱模块
  assets/modules/body-map.js 人体定位交互与部位解释
  assets/modules/anatomy-atlas.js 真实男女解剖模型、分层透视、搜索与自由框选
  assets/ui-core.js API、图标、格式化和共享交互模块
  assets/styles.css 响应式视觉系统
docs/
  competition.md   国奖答辩亮点、演示脚本与问答准备
  architecture.md  技术架构与数据安全说明
  anatomy-attribution.md 男女三维解剖模型来源、许可与适配记录
tests/
  test_safety.py   急症规则与健康分析验收
  test_retrieval.py 向量召回、意图识别与引用校验
```

## 验收

```powershell
python -m unittest discover -s tests -v
python -m compileall backend
```

如果 Neo4j 图谱节点发生大规模变化，重新生成本地向量目录：

```powershell
python scripts/build_entity_catalog.py
```

接口文档：`http://127.0.0.1:8000/docs`

MCP 使用说明：[docs/mcp.md](docs/mcp.md)。

## 团队信息

| 项目 | 内容 |
|---|---|
| 团队名称 | 待补充 |
| 参赛赛道 | 传智杯 |
| 团队成员 | 待补充 |
| 学校或学院 | 待补充 |
| 指导教师 | 待补充 |
| 联系邮箱 | 待补充 |

## 医疗边界

本系统用于健康科普、风险识别与就医决策支持，不提供确定诊断或处方，不能替代医生。分诊和模型回答均可能出错，出现急症表现应立即拨打 120 或前往急诊。

## 开源项目来源

项目只采用可公开获取的开源代码与自研界面代码，未引入未授权素材：

- [FastAPI](https://github.com/fastapi/fastapi)
- [Uvicorn](https://github.com/encode/uvicorn)
- [Neo4j Python Driver](https://github.com/neo4j/neo4j-python-driver)
- [Neo4j Community](https://github.com/neo4j/neo4j)

详细来源与许可说明见 [docs/architecture.md](docs/architecture.md)。

