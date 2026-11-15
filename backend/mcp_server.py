from __future__ import annotations

import json
import sys
from typing import Any

from backend.config import settings
from backend.graph import medical_graph
from backend.tools import TOOL_SPECS, call_tool


PROTOCOL_VERSION = "2024-11-05"


def response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        return response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {
                    "name": "zhiheng-health",
                    "version": "1.0.0",
                },
            },
        )
    if method == "tools/list":
        return response(request_id, {"tools": TOOL_SPECS})
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            result, elapsed_ms = call_tool(name, arguments)
            return response(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "tool": name,
                                    "elapsed_ms": elapsed_ms,
                                    "data": result,
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ],
                    "isError": False,
                },
            )
        except Exception as exc:
            return response(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
    if method == "resources/list":
        return response(
            request_id,
            {
                "resources": [
                    {
                        "uri": "zhiheng://graph/stats",
                        "name": "医疗知识图谱统计",
                        "mimeType": "application/json",
                    }
                ]
            },
        )
    if method == "resources/read":
        uri = (message.get("params") or {}).get("uri")
        if uri == "zhiheng://graph/stats":
            return response(
                request_id,
                {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(
                                medical_graph.stats(),
                                ensure_ascii=False,
                            ),
                        }
                    ]
                },
            )
        return error(request_id, -32002, "resource not found")
    if method and method.startswith("notifications/"):
        return None
    if method == "ping":
        return response(request_id, {})
    return error(request_id, -32601, "method not found")


def main() -> None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            result = handle_request(message)
            if result is not None:
                sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            sys.stdout.write(
                json.dumps(error(None, -32700, f"parse error: {exc}")) + "\n"
            )
            sys.stdout.flush()


if __name__ == "__main__":
    main()

