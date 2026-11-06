#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装包/镜像隐私校验：确认构建产物里不含任何真实凭据值。

用法:
  python3 tools/verify_no_keys.py <pkg.fpk | pkg.tar.gz | docker:镜像tag>

- 待扫对象: .fpk / .tar.gz（可嵌套: fpk → app.tgz → docker-image.tar.gz → 层）
- 凭据值来源（自动探测，可用 --keys-file 追加）:
    /usr/local/apps/@appdata/nasdsh/keys.conf        # fnOS fpk 运行时
    /usr/local/apps/@appdata/nasdsh/pin.conf
    ~/.dsh/.credentials.yaml                          # Mac dsh 凭据库
- 判定:
    * 命中任一"真实凭据值"        → FAIL(exit 2)
    * 仅命中通用密钥样式( sk-… 等) → WARN(exit 0, 打印提示)
构建链（build_fpk.py）会在打包后自动调用本脚本；真实凭据命中会直接构建失败。
"""

import gzip
import os
import re
import sys
import tarfile

CHUNK = 1 << 20
TAIL = 64

GENERIC = [
    ("sk-", re.compile(rb"sk-[A-Za-z0-9_-]{16,}")),
    ("ghp_/gho_", re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("glpat-", re.compile(rb"glpat-[A-Za-z0-9_-]{16,}")),
    ("AKIA", re.compile(rb"AKIA[0-9A-Z]{16}")),
    ("private-key", re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


def load_runtime_secrets(extra):
    vals = set()

    def add(v):
        v = (v or "").strip()
        if len(v) >= 8 and not v.startswith("$"):
            vals.add(v.encode())

    paths = list(extra)
    for p in ("/usr/local/apps/@appdata/nasdsh/keys.conf",
              "/usr/local/apps/@appdata/nasdsh/var/keys.conf",
              "/usr/local/apps/@appdata/nasdsh/pin.conf",
              "/usr/local/apps/@appdata/nasdsh/var/pin.conf",
              "/usr/local/apps/@appdata/nasdsh/data/dsh-home/.credentials.yaml",
              "/data/dsh-home/.credentials.yaml",
              os.path.expanduser("~/.dsh/.credentials.yaml")):
        if os.path.isfile(p):
            paths.append(p)
    for p in paths:
        try:
            for line in open(p, "r", encoding="utf-8", errors="replace"):
                m = re.match(r"^\s*([A-Za-z0-9_-]+)\s*[:=]\s*(\S+)\s*$", line)
                if m and re.match(r"^[A-Z0-9_]+$", m.group(1)):
                    add(m.group(2))
        except OSError:
            continue
    return sorted(vals)


def scan_stream(fh, secrets, found, warned):
    tail = b""
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        buf = tail + chunk
        for s in secrets:
            if s not in found and s in buf:
                found.add(s)
        for name, rx in GENERIC:
            if name not in warned and rx.search(buf):
                warned.add(name)
        tail = buf[-TAIL:]


def scan_bytes(data, secrets, found, warned):
    for s in secrets:
        if s in data:
            found.add(s)
    for name, rx in GENERIC:
        if name not in warned and rx.search(data):
            warned.add(name)


def iter_streams(tar, depth, secrets, found, warned, path):
    if depth > 3:
        return
    for member in tar:
        fh = tar.extractfile(member)
        if fh is None:
            continue
        name = "%s::%s" % (path, member.name)
        if member.name.endswith((".tar.gz", ".tgz")):
            print("  扫描嵌套包 %s" % name)
            with gzip.GzipFile(fileobj=fh, mode="rb") as gz:
                inner = tarfile.open(fileobj=gz, mode="r|")
                iter_streams(inner, depth + 1, secrets, found, warned, name)
        elif member.name.endswith((".tar",)):
            print("  扫嵌套 tar %s" % name)
            inner = tarfile.open(fileobj=fh, mode="r|")
            iter_streams(inner, depth + 1, secrets, found, warned, name)
        elif member.name.endswith(".gz"):
            with gzip.GzipFile(fileobj=fh, mode="rb") as gz:
                print("  扫描压缩流 %s" % name)
                scan_stream(gz, secrets, found, warned)
        elif member.isfile() and member.size < (64 << 20):
            data = fh.read()
            scan_bytes(data, secrets, found, warned)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    extra_keys = []
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i] == "--keys-file" and i + 1 < len(argv):
            extra_keys.append(argv[i + 1])
            i += 2
        else:
            i += 1
    target = args[0] if args else ""
    if not target:
        print(__doc__)
        return 3

    secrets = load_runtime_secrets(extra_keys)
    print("凭据值样本数: %d" % len(secrets))

    found, warned = set(), set()
    if target.startswith("docker:"):
        import subprocess
        import tempfile
        image = target.split(":", 1)[1]
        save = subprocess.Popen(["docker", "save", image], stdout=subprocess.PIPE)
        with tempfile.TemporaryFile() as tmp:
            while True:
                c = save.stdout.read(CHUNK)
                if not c:
                    break
                tmp.write(c)
            tmp.seek(0)
            print("扫描 docker 镜像 %s" % image)
            scan_stream(tmp, secrets, found, warned)
        if save.wait() != 0:
            print("docker save 失败")
            return 3
    elif target.endswith((".fpk", ".tgz", ".tar.gz")):
        with tarfile.open(target, "r:gz") as tar:
            print("扫描 %s" % target)
            iter_streams(tar, 0, secrets, found, warned, os.path.basename(target))
    else:
        print("不支持的输入: %s（.fpk/.tar.gz/docker:tag）" % target)
        return 3

    if found:
        print("❌ FAIL：安装包内发现真实凭据值（%d 个）！禁止分发。" % len(found))
        for s in sorted(found):
            print("   命中凭据前缀: %s…%s" % (s[:4].decode(), s[-4:].decode()))
        return 2
    if warned:
        print("⚠️ WARN：命中通用密钥样式（可能为样例/占位符，请人工复核）:")
        for w in sorted(warned):
            print("   样式: %s" % w)
    print("✅ PASS：未发现任何真实凭据值")
    return 0


if __name__ == "__main__":
    sys.exit(main())
