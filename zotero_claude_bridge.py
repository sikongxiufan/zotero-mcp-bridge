#!/usr/bin/env python3
"""
Zotero MCP Bridge - Claude Code Integration
使用 FastMCP 代理 Zotero HTTP MCP 服务器。
"""
import json
import asyncio
import requests
import sys
import types
from typing import Any, get_type_hints
from mcp.server.fastmcp import FastMCP

import os

TARGET_URL = os.environ.get("ZOTERO_MCP_URL", "http://192.168.123.106:23120/mcp")


def zotero_rpc(method: str, params: dict) -> dict:
    """向 Zotero MCP 服务器发送 JSON-RPC HTTP 请求"""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    resp = requests.post(TARGET_URL, data=body,
                        headers={"Content-Type": "application/json"}, timeout=60)
    return json.loads(resp.text)


def get_zotero_tools() -> list:
    """获取 Zotero 工具列表及 schema"""
    result = zotero_rpc("tools/list", {})
    return result.get("result", {}).get("tools", [])


def build_tool_function(tool_name: str, tool_schema: dict):
    """
    为 Zotero 工具创建异步函数。
    参数签名从 inputSchema 构建，使 FastMCP 能正确解析参数。
    """
    props = tool_schema.get("inputSchema", {}).get("properties", {})
    required = tool_schema.get("inputSchema", {}).get("required", [])

    # 构建参数名称、类型注解和默认值
    # 关键：required 参数必须在 optional 参数之前
    required_params = []
    optional_params = []
    for pname, pspec in props.items():
        ptype = pspec.get("type", "string")
        is_required = pname in required
        default = ... if is_required else None

        type_map = {
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        py_type = type_map.get(ptype, str)

        param_info = (pname, py_type, default)
        if is_required:
            required_params.append(param_info)
        else:
            optional_params.append(param_info)

    all_params = required_params + optional_params
    param_names = [p[0] for p in all_params]
    param_types = [p[1] for p in all_params]
    param_defaults = [p[2] for p in all_params]

    doc = tool_schema.get("description", "")

    # 使用 types.FunctionType 动态创建函数
    # 构建闭包变量
    _tool_name = tool_name
    _param_names = param_names
    _doc = doc

    async def tool_func(*args, **kwargs) -> str:
        # 合并位置参数和关键字参数
        bound = {}
        for i, val in enumerate(args):
            if i < len(_param_names):
                bound[_param_names[i]] = val
        bound.update(kwargs)

        result = zotero_rpc("tools/call", {
            "name": _tool_name,
            "arguments": bound
        })
        if "error" in result:
            return json.dumps({"error": result["error"]}, ensure_ascii=False)
        content = result.get("result", {}).get("content", [])
        if content:
            text = content[0].get("text", "")
            try:
                parsed = json.loads(text)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, TypeError):
                return text
        return json.dumps(result.get("result", {}), ensure_ascii=False, indent=2)

    # 设置函数元数据
    tool_func.__name__ = tool_name
    tool_func.__doc__ = doc

    # 使用 inspect 构建签名
    import inspect
    sig_params = []
    for i, (pname, ptype, pdefault) in enumerate(zip(param_names, param_types, param_defaults)):
        if pdefault is ...:
            sig_params.append(inspect.Parameter(pname, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=ptype))
        else:
            sig_params.append(inspect.Parameter(pname, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=ptype, default=pdefault))
    tool_func.__signature__ = inspect.Signature(sig_params)

    return tool_func


def build_server() -> FastMCP:
    """构建 FastMCP 服务器，注册所有 Zotero 工具"""
    mcp = FastMCP(
        "zotero-proxy",
        instructions=(
            "Search and manage your Zotero library. "
            "Use search_library for finding articles, get_content for PDF text, "
            "search_annotations for highlights. Write operations require user confirmation."
        )
    )

    try:
        tools = get_zotero_tools()
        print(f"[Bridge] Fetched {len(tools)} tools from Zotero", file=sys.stderr)

        for tool in tools:
            name = tool["name"]
            try:
                func = build_tool_function(name, tool)
                mcp.add_tool(func, name=name, description=tool.get("description", ""))
            except Exception as e:
                print(f"[Bridge] Warning: tool '{name}' failed: {e}", file=sys.stderr)

        print(f"[Bridge] Registered {len(tools)} tools", file=sys.stderr)
    except Exception as e:
        print(f"[Bridge Error] {e}", file=sys.stderr)

    return mcp


if __name__ == "__main__":
    server = build_server()
    asyncio.run(server.run_stdio_async())
