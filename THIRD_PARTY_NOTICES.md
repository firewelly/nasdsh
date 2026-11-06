# 第三方组件声明（THIRD PARTY NOTICES）

NasDSH 以独立进程/静态文件方式聚合并分发以下开源组件。各组件的版权归其
作者所有，完整许可证文本可在镜像内对应包目录中查看。

## 运行时组件

| 组件 | 版本 | 许可证 | 用途 / 位置 |
|---|---|---|---|
| DeepSeek Harness (`@deepseek-ai/dsh`) | 0.2.1-rc.5 | MIT | Web / CLI Agent 运行时；上游 https://github.com/deepseek-ai/deepseek-harness ；`/usr/local/lib/node_modules/@deepseek-ai/dsh` |
| dsh-TUI (`@deepseek-harness-tui/dsh-tui`) | 0.18.0 | MIT | 交互式终端界面；上游 https://github.com/ccch1mneyyy/dsh-TUI ；全局包 + `$DSH_HOME/profiles/dsh-tui` |
| xterm.js | vendor | MIT | 浏览器终端；`/srv/www/vendor/xterm.js` |
| xterm-addon-fit | vendor | MIT | 终端自适应；`/srv/www/vendor/addon-fit.js` |
| tmux | Debian 12 包 | ISC | CLI 会话持久化 |
| Node.js | 24.x | MIT 风格 | JavaScript 运行时（node:24-bookworm-slim） |
| Debian GNU/Linux | 12 (bookworm) | 多许可证 | 基础镜像；源码经 deb.debian.org 提供 |

## npm 传递依赖

镜像内安装的 dsh / dsh-TUI 会带入大量 npm 传递依赖（MIT、ISC、Apache-2.0、
BSD 等）。各包 LICENSE 文件保留在 `/usr/local/lib/node_modules/**/LICENSE*`
与 `$DSH_HOME/profiles/dsh-tui/node_modules/**/LICENSE*` 中。

## 品牌说明

- “DeepSeek”、“DeepSeek Harness”、“dsh” 是 DeepSeek 的项目/品牌名称。
  本项目不是 DeepSeek 官方产品；MIT 许可证不包含商标授权。
- “dsh-TUI” 是社区项目（作者 chimney），不是 DeepSeek 官方组件。
- 个人/内部使用无碍；正式对外分发时，请在应用名称/描述中明确
  “内置 DeepSeek Harness”，避免让用户误认为是官方应用。

## 自研代码

NasDSH 自研代码（sessiond.py、前端、打包脚本等）以 MIT 许可证发布，
见项目根目录 `LICENSE`。
