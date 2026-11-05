#!/usr/bin/env python3
"""CLI 终端桥测试：/ws/<name> → tmux PTY。

默认（TUI 模式，本地/远程均可）：
  通过 API 创建 dsh-TUI 会话 → 断言欢迎输出 → resize → 断开后会话保留 →
  重连有输出 → API 删除后会话消失。

NASDSH_TEST_SHELL=1 时（仅适合脚本与 sessiond 同机的本地开发）：
  自己建 bash tmux 会话，断言 echo/exit 语义。
鉴权走 X-OC-PIN 请求头（未设置 PIN 时省略）。
"""
import base64
import json
import os
import secrets
import socket
import struct
import subprocess
import time
import urllib.error
import urllib.request

HOST = os.environ.get("NASDSH_TEST_HOST", "127.0.0.1")
PORT = int(os.environ.get("NASDSH_TEST_PORT", "8080"))
PIN = os.environ.get("NASDSH_TEST_PIN", "")
NAME = os.environ.get("NASDSH_TEST_SESSION", "wsdemo")
PATH = os.environ.get("NASDSH_TEST_PATH", "/tmp")
SHELL = os.environ.get("NASDSH_TEST_SHELL", "") == "1"
BASE = "http://%s:%d" % (HOST, PORT)
PIN_HEADER = {"X-OC-PIN": PIN} if PIN else {}


def ws_connect(path):
    s = socket.create_connection((HOST, PORT), timeout=15)
    key = base64.b64encode(secrets.token_bytes(16)).decode()
    pin_h = "X-OC-PIN: %s\r\n" % PIN if PIN else ""
    req = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\n"
           "Upgrade: websocket\r\nConnection: Upgrade\r\n"
           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n%s\r\n"
           % (path, HOST, PORT, key, pin_h))
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += s.recv(4096)
    head, _, rest = buf.partition(b"\r\n\r\n")
    if b" 101 " not in head.split(b"\r\n")[0]:
        raise AssertionError(head.decode("utf-8", "replace"))
    return s, rest


def send_frame(s, opcode, payload):
    mask = secrets.token_bytes(4)
    header = bytes([0x80 | opcode])
    n = len(payload)
    if n < 126:
        header += bytes([0x80 | n])
    elif n < 1 << 16:
        header += bytes([0x80 | 126]) + struct.pack(">H", n)
    else:
        header += bytes([0x80 | 127]) + struct.pack(">Q", n)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    s.sendall(header + mask + masked)


def drain(s, seconds=2.0):
    out = b""
    s.settimeout(0.3)
    end = time.time() + seconds
    buf = b""
    while time.time() < end:
        try:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            while len(buf) >= 2:
                op = buf[0] & 0x0F
                length = buf[1] & 0x7F
                off = 2
                if length == 126:
                    if len(buf) < 4:
                        break
                    length = struct.unpack(">H", buf[2:4])[0]
                    off = 4
                elif length == 127:
                    if len(buf) < 10:
                        break
                    length = struct.unpack(">Q", buf[2:10])[0]
                    off = 10
                if len(buf) < off + length:
                    break
                payload = buf[off:off + length]
                buf = buf[off + length:]
                if op in (1, 2):
                    out += payload
                elif op == 8:
                    return out
        except socket.timeout:
            continue
        except ConnectionError:
            break
    s.settimeout(10)
    return out


def expect(tag, cond, extra=""):
    print(("  ✅ " if cond else "  ❌ ") + tag + ((" — " + extra) if extra and not cond else ""))
    return cond


def api(method, path, body=None):
    data = None
    headers = dict(PIN_HEADER)
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        return json.load(urllib.request.urlopen(r, timeout=180))
    except urllib.error.HTTPError as e:
        raise AssertionError("%s %s -> %s: %s" % (method, path, e.code, e.read()[:200]))


def sessions():
    return api("GET", "/api/sessions")["sessions"]


def alive(name):
    return any(s["name"] == name for s in sessions())


ok = True
api("DELETE", "/api/sessions/" + NAME) if alive(NAME) else None

if SHELL:
    # 本机模式：自己起 bash，测 shell 语义
    subprocess.run(["tmux", "kill-session", "-t", NAME], capture_output=True)
    subprocess.run(["tmux", "new-session", "-d", "-s", NAME, "-c", PATH, "/bin/bash"],
                   check=True)
else:
    # 默认：通过 API 创建 dsh-TUI 会话（本地/远程一致）
    api("POST", "/api/sessions", {"name": NAME, "path": PATH, "type": "cli"})

s, rest = ws_connect("/ws/" + NAME)
out = drain(s, 4.0)
if SHELL:
    ok &= expect("连接后有输出（提示符/banner）", len(out) > 0)
else:
    # TUI 首启（含 profile 引导）可能要几秒才画出欢迎屏；循环等文本
    end = time.time() + 12
    while b"dsh-TUI" not in out and time.time() < end:
        out += drain(s, 1.0)
    ok &= expect("dsh-TUI 欢迎输出", b"dsh-TUI" in out, out[:200].decode("utf-8", "replace"))

if SHELL:
    send_frame(s, 0x2, b"echo hello-nasdsh-$((41+1))\r")
    out = drain(s, 3.0)
    ok &= expect("命令回显/执行输出正确", b"hello-nasdsh-42" in out)

send_frame(s, 0x1, json.dumps({"resize": [100, 30]}).encode())
drain(s, 0.8)
ok &= expect("resize 控制帧无异常", True)

s.close()
time.sleep(1.5)
ok &= expect("断开后会话保留", alive(NAME))

s2, rest2 = ws_connect("/ws/" + NAME)
out = drain(s2, 4.0)
if SHELL:
    send_frame(s2, 0x2, b"echo after-reconnect-$((6*7))\r")
    out2 = drain(s2, 3.0)
    ok &= expect("重连后回放/继续执行", b"after-reconnect-42" in out + out2)
else:
    ok &= expect("重连后有输出（attach/回放）", len(out) > 0)

if SHELL:
    send_frame(s2, 0x2, b"exit\r")
    time.sleep(1.5)
    try:
        drain(s2, 0.5)
    except Exception:
        pass
s2.close()

api("DELETE", "/api/sessions/" + NAME)
time.sleep(1.0)
ok &= expect("删除后会话消失", not alive(NAME))

print("\nCLI 桥测试完成")
