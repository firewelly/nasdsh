#!/bin/bash
# ============================================================================
# NasDSH 构建脚本（在 NAS 上执行）
# 上传源码: Mac 上执行 tools/upload.sh → NAS ~/nasdsh-src/
# 用法:     cd ~/nasdsh-src/src && bash build.sh <build号>
# 流程:     docker build(core/) → docker save → ugcli pack
#
# 可选开关（功能测试用，正式打包不要设）：
#   NASDSH_SKIP_SAVE=1   跳过 docker save（不生成 images/*.tar）
#   NASDSH_SKIP_PACK=1   跳过 ugcli check/pack（eq14 等 fnOS 机器没有 ugcli）
# ============================================================================
set -euo pipefail

BUILD="${1:?用法: bash build.sh <build号>}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SRC_DIR")"          # ~/nasdsh-src/（含 core/ src/）
UGCLI="${UGCLI:-$HOME/bin/ugcli}"
VERSION=$(grep -E '^version:' "$SRC_DIR/project.yaml" | awk '{print $2}' | tr -d '"')
SKIP_SAVE="${NASDSH_SKIP_SAVE:-0}"
SKIP_PACK="${NASDSH_SKIP_PACK:-0}"
if [ ! -x "$UGCLI" ]; then
  SKIP_PACK=1
fi

echo "==> [0/4] 存储自检（构建产物勿落 eMMC/系统盘）"
df -h "$ROOT" | tail -1
if [ "$(df -P "$ROOT" | awk 'NR==2{print $6}')" = "/" ]; then
  echo "    ⚠️ 警告: 构建目录位于系统盘（/）——建议放到数据卷（如 /volume2/docker/nasdsh-build）"
fi

echo "==> [1/4] docker build nasdsh:${VERSION}（上下文=$ROOT/core）"
docker build -f "$ROOT/core/Dockerfile" -t "nasdsh:${VERSION}" "$ROOT/core"

echo "==> 冒烟: dsh --version / dsh-tui 版本"
docker run --rm --entrypoint /usr/local/bin/dsh "nasdsh:${VERSION}" --version
docker run --rm --entrypoint /usr/local/bin/node "nasdsh:${VERSION}" -e \
  'console.log("dsh-tui", require("/usr/local/lib/node_modules/@deepseek-harness-tui/dsh-tui/package.json").version)'

if [ "$SKIP_SAVE" != "1" ]; then
  echo "==> [2/4] docker save → src/rootfs_amd64/images/"
  mkdir -p "$SRC_DIR/rootfs_amd64/images"
  rm -f "$SRC_DIR/rootfs_amd64/images/"*.tar
  docker save -o "$SRC_DIR/rootfs_amd64/images/nasdsh-${VERSION}-amd64.tar" \
    "nasdsh:${VERSION}"
  ls -lh "$SRC_DIR/rootfs_amd64/images/"
else
  echo "==> [2/4] 跳过 docker save（NASDSH_SKIP_SAVE=1）"
fi

if [ "$SKIP_PACK" != "1" ]; then
  echo "==> [3/4] ugcli check"
  cd "$SRC_DIR"
  "$UGCLI" check

  echo "==> [4/4] ugcli pack (build $BUILD)"
  "$UGCLI" pack --arch amd64 --build "$BUILD"

  echo "==> 完成。UPK:"
  ls -lh "$SRC_DIR/build_dir/pkgs/upk/" 2>/dev/null || find "$SRC_DIR/build_dir" -name "*.upk" -exec ls -lh {} \;
else
  echo "==> [3/4][4/4] 跳过 ugcli（NASDSH_SKIP_PACK=1 或未找到 $UGCLI）"
  echo "==> 完成（仅镜像 nasdsh:${VERSION}，未打包 upk）"
fi
