#!/bin/bash
# ============================================================================
# 上传源码到 NAS（Mac 上执行；全程 SSH exec + tar 流，不依赖 SFTP）
# 只传源码；docker build / ugcli pack 全在 NAS 上执行。
# 用法:
#   NASDSH_HOST=dxp4800 NASDSH_PASS='...' bash upload.sh
#   （也兼容 OC_HOST / OC_PASS / DXP4800_PASS）
# ============================================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"                       # nas-dsh/
DEST_HOST="${NASDSH_HOST:-${OC_HOST:-dxp4800}}"
DEST_DIR='${HOME}/nasdsh-src'
PASS="${NASDSH_PASS:-${OC_PASS:-${DXP4800_PASS:?需要 NASDSH_PASS（或 OC_PASS / DXP4800_PASS）环境变量（SSH 密码）}}}"

run_ssh() { sshpass -p "$PASS" ssh "$DEST_HOST" "$@"; }

echo "==> 打包 core/ + src/（tar 流，排除垃圾文件）"
cd "$ROOT"
COPYFILE_DISABLE=1 tar czf /tmp/nasdsh-src.tgz --exclude='.DS_Store' \
        --exclude='__pycache__' --exclude='.pytest_cache' --exclude='build_dir' \
        core src tools fnos deploy store

echo "==> 传输源码 → $DEST_HOST:nasdsh-src/"
run_ssh "mkdir -p nasdsh-src"
cat /tmp/nasdsh-src.tgz | run_ssh "cat > nasdsh-src/src.tgz"
run_ssh "cd nasdsh-src && rm -rf core src tools fnos deploy store && tar xzf src.tgz && rm src.tgz && \
         find . -name '._*' -delete 2>/dev/null; \
         chmod -R u+rwX,go+rX . 2>/dev/null; true"

echo "==> 上传完成。下一步（SSH 到 NAS）："
echo "    cd ~/nasdsh-src/src && bash build.sh <build号>"
echo "    首次构建会从 npm 镜像安装 dsh / dsh-TUI，需能访问 registry.npmmirror.com"
