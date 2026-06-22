"""RepoMind daemon client - 向 daemon 发送请求"""

import json
import urllib.request

DEFAULT_PORT = 19832


def is_daemon_running(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> bool:
    url = f"http://{host}:{port}/"
    body = json.dumps({"command": "ping", "args": {}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("ok") is True
    except Exception:
        return False


def request(command: str, args: dict = None, host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> dict:
    url = f"http://{host}:{port}/"
    body = json.dumps({"command": command, "args": args or {}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        return {"error": f"Cannot connect to daemon on {host}:{port}. Is it running? (python cli.py serve)"}


def request_streaming(command: str, args: dict = None, on_event=None,
                      host: str = "127.0.0.1", port: int = DEFAULT_PORT):
    url = f"http://{host}:{port}/"
    body = json.dumps({"command": command, "args": args or {}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = None
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if on_event:
                    on_event(event)
                if event.get("event") == "result":
                    result = event.get("data")
                elif event.get("event") == "error":
                    return {"error": event.get("error", "unknown error")}
            return {"ok": True, "result": result} if result else {"error": "no result received"}
    except urllib.error.URLError:
        return {"error": f"Cannot connect to daemon on {host}:{port}. Is it running? (python cli.py serve)"}
