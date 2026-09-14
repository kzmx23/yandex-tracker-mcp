"""Проверка, что переконфигурированный сервер стартует и отдаёт новый инструмент.

Спавнит сервер ровно той командой, что прописана в ~/.claude.json
(mcpServers.yandex-tracker), проводит MCP stdio-хендшейк (initialize →
initialized → tools/list) и печатает, есть ли issue_add_attachment среди тулзов.

Запуск:
    uv run --directory . python tests/test_tools_list_handshake.py
"""
import json
import os
import subprocess
import sys


def main() -> int:
    cfg = json.load(open(os.path.expanduser("~/.claude.json"), encoding="utf-8"))
    block = cfg["mcpServers"]["yandex-tracker"]
    cmd = [block["command"], *block["args"]]
    env = {**os.environ, **block.get("env", {})}

    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "selftest", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    stdin = "".join(json.dumps(m) + "\n" for m in msgs)

    proc = subprocess.run(
        cmd, input=stdin, capture_output=True, text=True, env=env, timeout=180
    )
    out = proc.stdout
    tools = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("id") == 2 and "result" in obj:
            tools = [t["name"] for t in obj["result"].get("tools", [])]
    print(f"tools count: {len(tools)}")
    has = "issue_add_attachment" in tools
    print(f"issue_add_attachment present: {has}")
    if not has:
        print("STDERR tail:", proc.stderr[-800:])
        print("tools:", sorted(tools))
        return 1
    print("HANDSHAKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
