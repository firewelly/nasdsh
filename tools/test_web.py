#!/usr/bin/env python3
"""共享 dsh web 反代测试：/w/ 前缀 HTTP + WebSocket + token 交换。

流程：
  1. GET /api/web/launch → 302 带 token 到 /w/
  2. 代理 token 交换 → 拿到 dsh Cookie，落到 /w/
  3. 校验 index HTML、相对资源、WebSocket 101
  4. /api/web/stop → /api/sessions 中 @web alive=false
  5. /api/web/restart → alive=true
"""
import base64
import http.cookiejar
import json
import os
import re
import secrets
import socket
import sys
import urllib.error
import urllib.request

HOST = os.environ.get("NASDSH_TEST_HOST", "127.0.0.1")
PORT = int(os.environ.get("NASDSH_TEST_PORT", "18080"))
PIN = os.environ.get("NASDSH_TEST_PIN", "")
BASE = "http://%s:%d" % (HOST, PORT)
PIN_HEADER = {"X-OC-PIN": PIN} if PIN else {}

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


raw = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar),
                                  NoRedirect)


def expect(tag, cond, extra=""):
    print(("  ✅ " if cond else "  ❌ ") + tag + ((" — " + extra) if extra and not cond else ""))
    return cond


def req(path, method="GET", body=None, headers=None, follow=True):
    h = dict(PIN_HEADER)
    h.update(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    opener_ = opener if follow else raw
    try:
        return opener_.open(r, timeout=120)
    except urllib.error.HTTPError as e:
        if follow:
            raise
        return e


def ws_probe(path, timeout=15):
    cookie = "; ".join("%s=%s" % (c.name, c.value) for c in jar)
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    key = base64.b64encode(secrets.token_bytes(16)).decode()
    headers = [
        "GET %s HTTP/1.1" % path,
        "Host: %s:%d" % (HOST, PORT),
        "Upgrade: websocket",
        "Connection: Upgrade",
        "Sec-WebSocket-Key: %s" % key,
        "Sec-WebSocket-Version: 13",
    ]
    if cookie:
        headers.append("Cookie: %s" % cookie)
    if PIN:
        headers.append("X-OC-PIN: %s" % PIN)
    s.sendall(("\r\n".join(headers) + "\r\n\r\n").encode())
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
    status = data.split(b"\r\n", 1)[0].decode("utf-8", "replace")
    s.close()
    return status


def web_alive():
    data = json.load(req("/api/sessions"))
    for s in data["sessions"]:
        if s.get("name") == "@web":
            return bool(s.get("alive"))
    return False


ok = True
# 确保从干净状态开始
req("/api/web/stop", "POST", follow=True)

r = req("/api/web/launch", follow=False)
loc = r.headers.get("Location", "")
ok &= expect("launch 返回 302 + token", r.status == 302 and "/w/?token=" in loc, loc)

r = req(loc, follow=False)
ok &= expect("token 交换成功", r.status in (200, 303), str(r.status))
cookie_names = [c.name for c in jar]
ok &= expect("拿到 dsh 会话 Cookie", any(n.startswith("dsh-auth-") for n in cookie_names),
             str(cookie_names))

r = req("/w/")
html = r.read().decode("utf-8", "replace")
ok &= expect("代理返回 dsh index", "<title>DeepSeek Harness</title>" in html,
             html[:120])
ok &= expect("index 使用相对 base", '<base href="./">' in html)

m = re.search(r'src="(\./assets/[^"]+\.js)"', html)
asset_ok = False
if m:
    asset_url = "/w/" + m.group(1).lstrip("./")
    ra = req(asset_url)
    asset_ok = ra.status == 200 and "javascript" in (ra.headers.get("Content-Type") or "")
ok &= expect("静态资源可经 /w/ 前缀加载", asset_ok, m.group(1) if m else "no asset found")

status = ws_probe("/w/api/remote.mux")
ok &= expect("WebSocket 升级返回 101", " 101 " in status, status)

r = req("/w", follow=False)
ok &= expect("/w 无尾斜杠会重定向到 /w/", r.status in (301, 302, 307, 308)
             and r.headers.get("Location") == "/w/", str(r.status))

req("/api/web/stop", "POST")
ok &= expect("停止后 @web alive=false", not web_alive())

req("/api/web/restart", "POST")
ok &= expect("重启后 @web alive=true", web_alive())

req("/api/web/stop", "POST")
print("\n共享 Web 反代测试" + ("通过" if ok else "失败"))
sys.exit(0 if ok else 1)
