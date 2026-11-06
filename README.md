# NasDSH —— NAS 上的 DeepSeek Harness 工作台

[简体中文](README.md) | [English](README_EN.md)

> 本项目是 [DeepSeek Harness（dsh）](https://github.com/deepseek-ai/deepseek-harness)
> 面向 **绿联 UGOS Pro** 与 **fnOS** 两款 NAS 系统的**一键安装封装**（X86）。
> 目标：把“在 NAS 上装好、用好、随时用上 dsh”从一堆手工运维变成应用中心里的一次点击。

装好后，在浏览器 / 远程 App 里打开工作台，两种用法：

- **WEB（默认）**：一个共享的 `dsh web` 实例，浏览器里是完整的 dsh 图形界面；
  项目在 dsh 的 **Workspaces** 里添加和切换。关掉 tab 进程仍保留，重开即续。
- **CLI**：每个 tab 一个项目，tmux 会话里直接运行
  [`dsh-TUI`](https://github.com/ccch1mneyyy/dsh-TUI)；关窗保留、重开即续，
  `exit` 结束。

内置 dsh `0.2.1-rc.5` 与 dsh-TUI `0.18.0`，默认使用 BigModel GLM Coding Plan
（`/coding/` 订阅端点）或 DeepSeek 官方路由。

## 为什么需要 NasDSH（痛点）

dsh 本身是给开发者用的 CLI 工具，默认假设你有一台装好 Node 的开发机、用 SSH
登录、能自己排查依赖。NAS 的使用场景完全不同——这正是 NasDSH 要解决的：

| # | 直接在 NAS 上装 dsh 的痛点 | NasDSH 的做法 |
|---|---|---|
| 1 | **依赖地狱**：fnOS / UGOS 的系统 Node 不是 18 就是 25.x 旧版，dsh 需要新版（且依赖 `node:sqlite` 实验特性）；手动换 Node 会动系统环境 | 打包进容器：node:24 + dsh + dsh-TUI + 全部依赖一次装好，不碰 NAS 系统 |
| 2 | **装不上**：NAS 常不出海/无代理，npm 直连 registry 经常超时；每台机器都要折腾镜像源 | fnOS fpk **自带离线 Docker 镜像**，安装全程零联网；UGOS upk 镜像在 NAS 本地构建 |
| 3 | **没有“应用”形态**：装完只是个命令行，没有桌面图标、没有端口声明、没有开机自启、应用中心看不到 | upk/fpk 应用包：桌面图标一点就开，端口统一 12704，随系统启动，应用中心管理升级/卸载 |
| 4 | **交互门槛**：dsh web 默认只监听本机且带启动 token，SSH 里敲完还要自己配反代才能在手机/浏览器用 | sessiond 自动拉起 dsh web 并做 `/w/` 前缀反代，浏览器打开就是完整 UI；手机 App / UGREENlink 远程也能用 |
| 5 | **会话易丢**：SSH 一断 dsh 就没了；换个终端想接着聊找不到历史 | WEB 常驻进程 + CLI 走 tmux：**关窗保留、重开即续**，换设备接上继续 |
| 6 | **多项目混乱**：一个终端开多个项目目录来回 cd，web 只认启动时那个目录 | UI 里按项目建 tab / 用 dsh Workspaces 切换，目录白名单只放行项目盘 |
| 7 | **安全裸奔**：NAS 上的 web 服务直接暴露局域网，谁都能连 | 可选访问口令（challenge-response + HttpOnly Cookie），dsh 自身的 token/Cookie 与 browser-trust fence 原样保留 |
| 8 | **凭据安全**：API Key 手动 export 进 shell 历史 / profile 文件，换机要重配 | 向导填写 → 运行时凭据库（0600），**安装包内不含任何 key**，打包时自动逐层扫描校验 |
| 9 | **升级麻烦**：npm 全局升级会污染系统环境，版本碎片化 | 容器内 `nasdsh-update` 一键升级 / 整包升级换镜像，数据卷不丢 |
| 10 | **中文环境缺失**：NAS 系统经常没有中文 locale，终端里 vim/less 乱码 | 镜像内置 zh_CN.UTF-8 + vim/nano/tmux 配置，浏览器输入法直通 |

一句话：**把“在 NAS 上运维一个 AI 编程 Agent”降级成“从应用中心装一个 App”。**

> 普通 Linux 主机不需要本项目：直接 `npm i -g @deepseek-ai/dsh @deepseek-harness-tui/dsh-tui`
> 即可使用 dsh；本项目的价值是 NAS 应用化的工作台外壳。

## 架构

```
┌─ 浏览器 / UGREEN App（局域网直连 12704，远程走 UGREENlink 应用域名）─┐
│  index.html   tab 栏 + 新建对话框（Web / CLI，默认 Web）              │
│  term.html    xterm.js（CLI 会话，WS → tmux）                         │
│  iframe       /w/（共享 dsh web，项目在 UI 内切 Workspace）           │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP 8080（upk 声明端口 12704 → 容器 8080）
┌──────────────────────────────▼───────────────────────────────────────┐
│ sessiond.py（单进程，Python 3 纯标准库，ThreadingHTTPServer）         │
│  • tab 管理 / 会话 API / 目录浏览                                     │
│  • CLI：WS → PTY → `tmux new -A -s <name>`（会话里跑 dsh-TUI）        │
│  • Web：启动一个共享 `dsh web --host 127.0.0.1 --port <随机>`         │
│  • /w/ 前缀反代（HTTP + WebSocket），Host 原样透传                    │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ docker-compose（is_docker_app upk）
┌──────────────────────────────▼───────────────────────────────────────┐
│ node:24-bookworm-slim                                                │
│  dsh 0.2.1-rc.5 + dsh-TUI 0.18.0 + tmux + git/vim/ripgrep…          │
│  持久数据：${DATA_PATH}:/data（profile/凭据/会话/日志）               │
│  项目目录：安装参数 PATH 按原路径挂载，容器内外路径一致               │
└──────────────────────────────────────────────────────────────────────┘
```

### 为什么 Web 用前缀反代，而不是直接暴露端口

dsh web 的前端使用 `<base href="./">` 和相对资源路径，启动 token 交换后会
`303 → ./`。把 `/w/` 前缀剥离后转发到本地 dsh，浏览器看到的仍是同一个
源（`host:12704`），因此：

- dsh 的签名 Cookie（绑定 host + port）可以直接工作；
- `Host` / `Origin` 原样透传，满足 dsh 的 browser-trust fence；
- 不需要改写 HTML/JS，也不需要在 NAS 上额外暴露一堆端口；
- WebSocket（`/w/api/remote.mux`）由 sessiond 原样转发。

dsh 的启动 token 只出现在 iframe 的首次跳转 URL 里，随后被 dsh 换成 HttpOnly
Cookie 并重定向到干净路径。

## 目录结构

```
nas-dsh/
├── core/                     # 平台无关核心（Docker 构建上下文）
│   ├── Dockerfile            #   node:24 + dsh + dsh-TUI + tmux
│   ├── sessiond.py           #   后端：UI/API/WS→tmux/dsh web 反代
│   ├── www/                  #   前端（xterm.js 已 vendor）
│   ├── dsh-home-template/    #   DSH_HOME 模板（profiles + provider patch）
│   ├── entrypoint.sh         #   数据目录/口令/profile 播种/降权启动
│   ├── bin/nasdsh-update     #   容器内升级 dsh / dsh-TUI
│   └── tmux.conf / profile.d/
├── src/                      # UGOS Pro 打包工程（ugcli → upk）
│   ├── project.yaml          #   spec 2.1, is_docker_app, port 12704
│   ├── rootfs_common/        #   docker-compose.yaml + icon.png
│   ├── rootfs_amd64/images/  #   构建产物（nasdsh-*.tar）
│   └── build.sh              #   只在 NAS 上执行
├── fnos/                     # fnOS 打包工程（fpk，自带离线镜像）
│   ├── build_fpk.py
│   └── fpk_root/             #   manifest / cmd / wizard / config
├── tools/
│   ├── upload.sh             #   Mac → NAS 源码传输
│   ├── verify_no_keys.py     #   安装包隐私校验（逐层扫真实凭据值）
│   ├── test_web.py           #   Web 反代 + token + WebSocket 测试
│   └── test_ws.py            #   CLI 终端桥测试
└── store/                    # 应用中心图标等
```

## 部署方式（二选一）

两种 NAS 应用包共用同一个 `core/`，区别只在分发外壳。
（普通 Linux 主机不需要本项目：直接 `npm i -g @deepseek-ai/dsh @deepseek-harness-tui/dsh-tui`
 即可使用 dsh；本项目的价值是 NAS 应用化的工作台外壳。）

| 方式 | 目标系统 | 产物 | 说明 |
|---|---|---|---|
| **UGOS Pro 应用**（upk） | UGOS Pro（X86） | `src/build_dir/pkgs/upk/*.upk` | 应用中心安装，端口 12704 |
| **fnOS 应用**（fpk） | fnOS ≥0.8.1（X86） | `fnos/dist/nasdsh-fnos-*.fpk` | 应用中心安装，自带离线镜像，端口 12704 |

### UGOS Pro（upk）

官方要求 Linux 打包以保留文件权限，因此**构建在 NAS 上执行**。

```bash
# 1) Mac：上传源码（需要 sshpass）
cd nas-dsh/tools
NASDSH_PASS='你的SSH密码' NASDSH_HOST=<NAS别名或IP> bash upload.sh

# 2) NAS（ssh <用户名>@<NAS_IP>）：构建 + 打包
cd ~/nasdsh-src/src
bash build.sh 1          # build 号递增，不改版本时必须 +1
# 产物：src/build_dir/pkgs/upk/amd64_nasync_com.firewell.nasdsh_0.1.0.0001.upk
```

首次构建会从 npm 镜像安装 dsh / dsh-TUI（镜像内已安装，构建期也需要网络）。
如果 NAS 出网需要代理，在构建命令前 export `HTTP_PROXY` / `HTTPS_PROXY`，或

```bash
docker build --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
             -f core/Dockerfile -t nasdsh:0.1.0 core
```

安装：应用中心 → 设置 → 应用开发设置（首次需上传 `ugdev.sig` 授权）→ 手动安装
选择 upk → 桌面图标「NasDSH 工作台」→ 浏览器/App 打开。

### fnOS（fpk）

```bash
# 在 fnOS 本机（或任一 x86_64 Docker 机器）上：
docker build -f core/Dockerfile -t nasdsh:0.1.0 core
python3 fnos/build_fpk.py            # 产物 fnos/dist/nasdsh-fnos-0.1.0.fpk
# 安装：应用中心手动安装，或 sudo appcenter-cli install-fpk <fpk 路径>
```

安装向导可配置项目根目录、数据目录（建议数据卷）、访问口令与模型 Key；
详细说明见 `fnos/README.md`。fnOS 上项目路径是 `/vol1/...`，sessiond 用
`NASDSH_ROOTS` 放行（fpk 脚本自动按项目根推导）。



## 使用

1. 打开应用，首次会显示隐私政策；同意后进入工作台。
2. 点「＋」→ 选择 **Web 工作台**（默认）或 **CLI 终端**。
   - Web：直接打开共享实例（首次等待几秒启动 dsh web）；进入后点左侧
     **Workspaces → +**，选择器从 **Home → projects → volume1** 进入项目目录
     （entrypoint 已把各挂载卷链接到 `$HOME/projects`），多个项目在同一个
     界面里切换。也可以点路径旁的「Edit path」直接输入绝对路径。
   - CLI：填名称、选项目目录，进入 dsh-TUI；首次会走账号/模型向导。
3. 关闭浏览器标签页不会结束会话：
   - CLI 的 tmux 会话保留，重开 tab 自动 attach；
   - Web 的 dsh web 进程保留，重开 tab 继续用。
4. 关掉的 tab 可以从顶部 **「会话」** 按钮重新打开（显示类型、目录、运行状态）；
   DSH Web 行还有 **重启**（换访问地址/更新 trusted host 时用）和 **结束**。
5. 右键 tab →「结束会话」才会真正杀掉进程 / tmux 会话。

## 模型配置

provider 定义在 `$DSH_HOME/cordis.patch.yml`（首次启动从镜像模板复制），三个
profile（web / headless / dsh-tui）共用。已内置：

| provider | 端点 | API Key 环境变量 |
|---|---|---|
| `deepseek-official` | DeepSeek 官方（dsh 内置） | `DEEPSEEK_API_KEY` |
| `bigmodel-coding-plan` | `https://open.bigmodel.cn/api/coding/paas/v4` | `BIGMODEL_API_KEY` |
| `bailian-coding-plan` | `https://coding.dashscope.aliyuncs.com/v1` | `BAILIAN_API_KEY` |
| `token-plan` | `https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` | `TOKENPLAN_API_KEY` |
| `volcengine-coding-plan` | `https://ark.cn-beijing.volces.com/api/coding/v3` | `VOLCENGINE_API_KEY` |
| `opencode-go` | `https://opencode.ai/zen/go/v1` | `OPENCODE_GO_API_KEY` |
| `xiaomi-mimo` | `https://api.xiaomimimo.com/v1` | `XIAOMI_MIMO_API_KEY` |

- 安装时可填 DeepSeek / BigModel / 百炼 / Token Plan 的 Key（密码字段）；
  在 NAS/远程环境建议直接用 API Key，OAuth 登录的 localhost 回调不一定能回到你的电脑；
- 也可以稍后在 Web 工作台 **Settings → Models** 填写，凭据保存在
  `/data/dsh-home/.credentials.yaml`；
- 默认模型：环境里有 `BIGMODEL_API_KEY` 时用
  `bigmodel-coding-plan/glm-5.3-flash`，否则用 `deepseek-official/deepseek-flash`；
- **BigModel 必须使用 `/coding/` 订阅端点**，不要改成按 token 计费的
  `/api/paas/v4/chat/completions`。

## 数据与持久化

```
${DATA_PATH}/                     # 安装参数 DATA_PATH（建议 SSD 卷）
├── dsh-home/                     # DSH_HOME
│   ├── cordis.patch.yml          #   provider / 默认模型（可编辑）
│   ├── profiles/web|headless|dsh-tui/
│   ├── .credentials.yaml         #   模型凭据（dsh 写入，0600）
│   └── sessions/                 #   会话 JSONL
├── home/                         # HOME（dsh-TUI settings 等）
│   └── projects/                 #   Workspace 选择器快捷入口（→ /volume*, /home）
├── cache/                        # XDG_CACHE_HOME
├── logs/web.log                  # 共享 dsh web 进程的 stdout/stderr
├── .term_pin                     # 访问口令（0600）
└── proxy.env                     # 可选：HTTP_PROXY / NPM_CONFIG_REGISTRY
```

应用升级/重建不会丢数据；容器重启会结束所有运行中的 Web/CLI 进程，但会话记录
仍在 `dsh-home/sessions`，重开 tab 可以继续。

## 安全

- 局域网默认无鉴权（与 NasOC 同策略）；安装参数 `TERMINAL_PIN` 可选口令，
  走 UGREENlink 远程访问时建议设置。
- 口令走 challenge-response 登录 + HttpOnly Cookie，不写入 URL、不驻留进程环境变量。
- dsh web 只监听 `127.0.0.1`，外部只能经 sessiond 的 `/w/` 前缀访问；
  `Host`/`Origin` 原样透传，由 dsh 自己的 browser-trust fence 校验。
- API Key 不写入镜像；安装参数经环境变量注入，或由 dsh 凭据存储持久化。
- 容器内以 uid 1000 / gid 10 运行，数据目录启动时校正属主。
- **凭据不进安装包**：fpk/upk/镜像只含代码；key 只落在运行时（向导 conf/凭据库/env）。
  `fnos/build_fpk.py` 打包后自动跑 `tools/verify_no_keys.py` 对产物逐层扫描真实凭据值，
  命中即失败删除；启动日志对 `-e` 参数脱敏。

## 测试

```bash
# 本地启动（Mac/Linux，需已安装 dsh 与 dsh-tui）
NASDSH_DATA=/tmp/nasdsh-data \
NASDSH_WWW=$PWD/core/www \
NASDSH_ROOTS=/tmp \
NASDSH_PORT=18080 \
python3 -I core/sessiond.py

# Web 反代 / token / WebSocket
NASDSH_TEST_PORT=18080 python3 -I tools/test_web.py

# CLI 终端桥（脚本会自己建一个 bash tmux 会话）
NASDSH_TEST_PORT=18080 NASDSH_TEST_PATH=/tmp python3 -I tools/test_ws.py
```

## 已知限制

- 共享 Web 只有一个 dsh web 进程，实测空闲约 250–400MB 内存；CLI tab 的
  dsh-TUI 也会各占一个 Node 进程。
- Web 与 CLI 共享同一个 `DSH_HOME`。dsh 的 workspace/设置写入是最后写入者
  生效；建议不要同时频繁修改 Web 与 CLI 的全局设置。
- dsh 的浏览器 Cookie 绑定访问时的 `host:port`。sessiond 启动 Web 时会把本机
  局域网 IP 加入 dsh 的 `--trusted-host`；如果还要用 UGREENlink 域名/反代域名
  访问，请把域名写入 `proxy.env` 的 `NASDSH_TRUSTED_HOSTS`（逗号分隔）并重启
  应用，或者从「会话 → DSH Web → 重启」让新地址生效。
- 共享 Web 进程的 cwd 默认取第一个挂载卷；可在 `proxy.env` 里设
  `NASDSH_WEB_CWD=/volume1/projects` 指定默认 Workspace 起点。
- 反代监听是 HTTP；若在外部 TLS 代理后使用，`DSH_WEB_URL` / 部分复制链接可能
  仍是 `http://`，不影响主要交互。
- dsh 仍处于 preview，升级可能带来配置/插件兼容变化；`nasdsh-update` 升级后
  建议新开 tab 验证。
- fnOS 的 fpk 内置 Docker 离线镜像（这是 fnOS 应用的交付机制——fnOS 机器没有
  预装 Node）；普通 Linux 用户请直接安装 dsh，不要用本项目。
- UGOS upk 打包需在 UGOS 机器上执行；两种包运行行为一致（同一 `core/`）。

## 许可与第三方组件

- 自研代码：**MIT**（见 `LICENSE`）
- 聚合分发：dsh（MIT）、dsh-TUI（MIT）、xterm.js / addon-fit（MIT）、
  tmux（ISC）、Node.js（MIT 风格）、Debian 基础镜像（多许可）。全部为独立
  进程/静态文件聚合，无 copyleft 传染；声明见 `THIRD_PARTY_NOTICES.md`。
- “DeepSeek Harness / dsh” 为 DeepSeek 项目品牌；本项目为个人/内部使用，
  正式对外分发建议在应用名中注明“内置 DeepSeek Harness”。
