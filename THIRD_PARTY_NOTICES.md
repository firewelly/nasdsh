# 第三方组件声明 / Third-Party Notices

NasDSH 以独立进程/静态文件方式聚合并分发以下开源组件。各组件的版权归其作者
所有，完整许可证文本保留在镜像内对应包目录中（`LICENSE` / `LICENSE.md` /
`package.json`）。

NasDSH aggregates and redistributes the open-source components below as separate
processes or static files. Copyright in each component remains with its authors;
the full licence text is retained inside the image in each package directory.

## 自研代码 / Original code

| 项目 | 版权人 | 许可证 | 位置 |
|---|---|---|---|
| NasDSH 自研部分（`sessiond.py`、前端、打包脚本等） | 袁梦龙 (Menglong Yuan, GitHub: @firewelly) | MIT | 项目根目录 `LICENSE` |

## 运行时组件 / Runtime components

| 组件 / Component | 版本 / Version | 许可证 / Licence | 版权与上游 / Copyright & upstream | 位置 / Location |
|---|---|---|---|---|
| DeepSeek Harness (`@deepseek-ai/dsh`) | 0.2.1-rc.5 | MIT | Copyright (c) DeepSeek；<https://github.com/deepseek-ai/deepseek-harness> | `/usr/local/lib/node_modules/@deepseek-ai/dsh` |
| dsh-TUI (`@deepseek-harness-tui/dsh-tui`) | 0.18.0 | MIT | Copyright (c) dsh-TUI 作者（社区项目，chimney / ccch1mneyyy）；<https://github.com/ccch1mneyyy/dsh-TUI> | 全局 node_modules + `$DSH_HOME/profiles/dsh-tui` |
| xterm.js | vendor（随仓库分发） | MIT | Copyright (c) The xterm.js authors；<https://github.com/xtermjs/xterm.js> | `/srv/www/vendor/xterm.js` |
| xterm-addon-fit | vendor | MIT | Copyright (c) The xterm.js authors | `/srv/www/vendor/addon-fit.js` |
| tmux | Debian 12 包 | ISC | Copyright (c) Nicholas Marriott 及贡献者；<https://github.com/tmux/tmux> | Debian 包 |
| Node.js | 24.x（`node:24-bookworm-slim`） | MIT 风格 | Copyright Node.js contributors / OpenJS Foundation；<https://nodejs.org> | 基础镜像 |
| Debian GNU/Linux | 12 (bookworm) | 多许可证 | Debian 项目及各包作者；源码经 <https://deb.debian.org> 提供 | 基础镜像 |

## npm 传递依赖 / Transitive npm dependencies

镜像内安装的 dsh / dsh-TUI 会带入大量 npm 传递依赖（MIT、ISC、Apache-2.0、
BSD 等）。各包 LICENSE 文件保留在
`/usr/local/lib/node_modules/**/LICENSE*` 与
`$DSH_HOME/profiles/dsh-tui/node_modules/**/LICENSE*` 中；各包的版权声明随包
分发，未被修改或移除。

dsh / dsh-TUI pull in many transitive npm dependencies (MIT, ISC, Apache-2.0, BSD,
etc.). Their licence and copyright files are retained under
`/usr/local/lib/node_modules/**` and
`$DSH_HOME/profiles/dsh-tui/node_modules/**`.

## 分发方式与许可兼容性 / Distribution model

- 全部组件以独立进程或未修改的静态文件形式聚合分发，自研部分与第三方组件之间
  不构成衍生作品，无 copyleft 传染；自研代码以 MIT 发布，与上述宽松许可兼容。
- 未修改任何第三方组件的版权声明或许可证文本。

All components are aggregated as separate processes or unmodified static files;
the original code is not a derivative work of them and no copyleft obligation
arises. The original code is MIT-licensed, compatible with the permissive licences
above. No third-party copyright notice or licence text has been modified.

## 品牌说明 / Trademarks

- “DeepSeek”“DeepSeek Harness”“dsh” 是 DeepSeek 的项目/品牌名称。本项目**不是**
  DeepSeek 官方产品，与 DeepSeek 无隶属或合作关系；MIT 许可证不包含商标授权。
  应用名称与简介中已明确标注“内置 DeepSeek Harness”。
- “dsh-TUI” 是社区项目（作者 chimney），不是 DeepSeek 官方组件。
- “UGREEN”“绿联”“UGOS” 是深圳市绿联科技股份有限公司的商标；本项目仅在描述
  兼容性时提及，未使用其标识，也未暗示与绿联存在代理或合作关系。
- “DeepSeek”, “DeepSeek Harness” and “dsh” are DeepSeek's project/brand names.
  This project is **not** an official DeepSeek product and has no affiliation with
  DeepSeek; the MIT licence grants no trademark rights. The app name and
  description explicitly state that it bundles DeepSeek Harness.
- “dsh-TUI” is a community project (author: chimney), not an official DeepSeek
  component.
- “UGREEN”, “UGOS” are trademarks of UGREEN Group; they are referenced only to
  describe compatibility. No UGREEN marks are used and no agency or partnership is
  implied.
