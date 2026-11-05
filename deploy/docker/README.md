# Docker 部署（通用，任何 x86_64 Docker 主机）

不依赖 UGOS/fnOS 应用框架，直接用 Docker/Compose 跑 NasDSH。

## 1. 准备镜像

二选一：

```bash
# A) 本地构建（需要能访问 npm 镜像源；见 core/Dockerfile）
docker build -t nasdsh:0.1.0 -f core/Dockerfile core

# B) 导入离线镜像包（在已构建的机器上生成）
tools/export-image.sh            # 产物 dist/nasdsh-<ver>-docker-amd64.tar.gz
docker load -i nasdsh-0.1.0-docker-amd64.tar.gz
```

## 2. 配置并启动

```bash
cd deploy/docker
cp .env.example .env
vim .env                          # 至少改 DATA_PATH / PROJECTS_PATH
docker compose up -d
docker compose logs -f nasdsh     # 看到 [sessiond] listening 即就绪
```

打开 `http://<主机IP>:12704`（端口取 `.env` 的 `NASDSH_PORT`）。

## 3. 升级

```bash
docker build -t nasdsh:0.2.0 -f core/Dockerfile core   # 或 docker load 新包
sed -i 's/NASDSH_VERSION=.*/NASDSH_VERSION=0.2.0/' .env
docker compose up -d              # 数据在 DATA_PATH，升级不丢
```

## 4. 数据说明

```
${DATA_PATH}/
├── dsh-home/          # DSH_HOME（profiles、.credentials.yaml、sessions/）
├── home/              # HOME（dsh-TUI 设置、Workspace 快捷链接 projects/）
├── logs/web.log       # 共享 dsh web 进程日志（0600）
└── .term_pin          # 访问口令（0600，设置 TERM_PIN 后生成）
```

删除容器不影响数据；`docker compose down` 也不影响，`down -v` 也不会（未用命名卷）。
彻底清除 = 删除 `DATA_PATH` 目录 + 容器。
