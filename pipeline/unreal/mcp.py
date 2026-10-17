"""Client minimal du serveur MCP d'Unreal (éditeur ouvert), pour explorer et inspecter depuis WSL.

    python pipeline/unreal/mcp.py toolsets
    python pipeline/unreal/mcp.py describe <toolset>
    python pipeline/unreal/mcp.py call <toolset> <tool> '{"arg": 1}'

Règle du projet : le MCP sert à explorer. Toute modification retenue est reportée dans un script.
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import CONFIG  # noqa: E402

URL = CONFIG["unreal"]["mcp_url"]
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


class Session:
    def __init__(self, timeout=120):
        self.timeout = timeout
        self.id = 0
        r = self._post({"method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                                           "clientInfo": {"name": "barque", "version": "1"}}})
        self.sid = r.headers.get("Mcp-Session-Id")
        self._post({"method": "notifications/initialized"}, notify=True)

    def _post(self, payload, notify=False):
        body = {"jsonrpc": "2.0", **payload}
        if not notify:
            self.id += 1
            body["id"] = self.id
        headers = dict(HEADERS, **({"Mcp-Session-Id": self.sid} if getattr(self, "sid", None) else {}))
        r = requests.post(URL, json=body, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r

    def request(self, method, params=None):
        data = self._post({"method": method, "params": params or {}}).json()
        if "error" in data:
            raise RuntimeError(json.dumps(data["error"], ensure_ascii=False))
        return data["result"]

    def tool(self, name, arguments=None):
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})

    def call(self, toolset, tool, arguments=None):
        return self.tool("call_tool", {"toolset_name": toolset, "tool_name": tool, "arguments": arguments or {}})


def text(result):
    return "\n".join(c.get("text", json.dumps(c)) for c in result.get("content", []))


if __name__ == "__main__":
    s = Session()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "toolsets"
    if cmd == "toolsets":
        print(text(s.tool("list_toolsets")))
    elif cmd == "describe":
        print(text(s.tool("describe_toolset", {"toolset_name": sys.argv[2]})))
    elif cmd == "call":
        print(text(s.call(sys.argv[2], sys.argv[3], json.loads(sys.argv[4]) if len(sys.argv) > 4 else {})))
