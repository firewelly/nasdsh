#!/bin/bash
# ============================================================================
# 导出 Docker 离线镜像包（x86_64）
# 用法:  tools/export-image.sh [版本号]     # 默认读 src/project.yaml 的 version
# 产物:  dist/nasdsh-<ver>-docker-amd64.tar.gz (+ .sha256)
# 导入:  docker load -i nasdsh-<ver>-docker-amd64.tar.gz
# ============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
VERSION="${1:-$(grep -E '^version:' "$ROOT/src/project.yaml" | awk '{print $2}' | tr -d '"')}"
IMAGE="nasdsh:${VERSION}"
OUT_DIR="$ROOT/dist"

mkdir -p "$OUT_DIR"
docker image inspect "$IMAGE" >/dev/null || {
  echo "❌ 本机没有镜像 $IMAGE；先 docker build -t $IMAGE -f core/Dockerfile core"
  exit 1
}

echo "==> docker save $IMAGE（gzip，约 1-3 分钟）"
docker save "$IMAGE" | gzip -c > "$OUT_DIR/nasdsh-${VERSION}-docker-amd64.tar.gz"
shasum -a 256 "$OUT_DIR/nasdsh-${VERSION}-docker-amd64.tar.gz" \
  > "$OUT_DIR/nasdsh-${VERSION}-docker-amd64.tar.gz.sha256"
ls -lh "$OUT_DIR/"nasdsh-${VERSION}-docker-amd64.tar.gz*
echo "导入: docker load -i nasdsh-${VERSION}-docker-amd64.tar.gz"
