# MCP 工具服务

项目提供独立 MCP Server，可通过标准输入输出与兼容 MCP 的客户端连接。

启动：

```powershell
.\scripts\run-mcp.ps1
```

或：

```bash
python -m backend.mcp_server
```

客户端配置示例见项目根目录的 `.mcp.json.example`。

## Tools

| 工具 | 用途 |
|---|---|
| `search_medical_entities` | 全文检索与向量混合召回 |
| `expand_medical_entity` | 展开实体的一跳或二跳知识关系 |
| `assess_symptoms` | 症状风险分级和急症识别 |
| `medication_options` | 非处方对症参考与禁忌过滤 |

## Resource

- `zhiheng://graph/stats`：当前 Neo4j 节点、关系和实体类型统计。

工具声明为只读，不直接暴露用户健康档案。回答编排产生的工具调用会写入会话 trace，用于评测和答辩展示。
