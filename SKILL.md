# Web Fetch Tool (SPEED PRO V9)

一款为 LLM 和 AI Agent 量身打造的现代网页抓取工具。支持强力反爬穿透、会话状态持久化（保持登录）、可视化人机交互验证，并能将复杂的网页精准转换为所见即所得的极简 Markdown。

## 🌟 核心突破与功能

1. **优雅的无限制交互登录 (New!)**
   - **告别倒计时**：使用 `--login` 模式时，程序会在网页右上角自动注入一个**绿色的悬浮按钮**。你有**无限的时间**去输入账号密码、接手机验证码或拖拽滑块。
   - **跨路由防丢**：无论单页应用（Vue/React）如何跳转、重定向，悬浮按钮始终存在。操作完成后点击按钮，程序自动接管并保存凭证。
   - **凭证漫游**：支持在本地带界面的电脑上生成 `session.json`，直接传给无界面的远程 Linux 服务器静默使用（无缝对接云端 AI Agent）。

2. **双引擎与智能防超时 (New!)**
   - **`cffi` 引擎**：基于底层 TLS 握手伪装（默认），极速轻量，适合绝大部分常规 API 或静态页面。
   - **`playwright` 引擎**：全真 Chromium 渲染。**新版加入了智能 DOM 放行机制**，即使遇到知乎、微博等充满无限追踪脚本的网站，也能在 HTML 骨架加载完毕后瞬间抓取，彻底告别 30 秒超时假死。

3. **专为 LLM 优化的解析器**
   - **所见即所得**：完美保留页面层级和所有的超链接 `[文本](链接)`。
   - **防样式穿透**：物理级抹除隐藏在 `<!-- -->`、`<template>`、`<textarea>` 中的恶意 CSS/JS 代码，告别乱码。
   - **Token 极限压缩**：自动将同域名的绝对路径转换为相对路径（如 `https://a.com/b` -> `/b`），大幅节省模型上下文 Token。

## 📦 安装依赖

建议使用 `uv` 创建独立虚拟环境进行管理：

```bash
# 1. 创建并激活虚拟环境
uv venv ~/fetch-venv
source ~/fetch-venv/bin/activate

# 2. 安装 Python 依赖
uv pip install playwright curl_cffi playwright-stealth markdownify beautifulsoup4 lxml

# 3. 安装 Playwright 内置浏览器
playwright install chromium
```

## 🚀 使用方法

### 1. 基础极速抓取 (默认 CFFI)
适合绝大部分普通页面、新闻、博客等。
```bash
python ~/.openclaw/skills/web-fetch-tool/fetch.py "https://example.com"
```

### 2. 强力渲染模式 (Playwright)
当遇到 Cloudflare 质询、白屏、需要等待 JS 加载数据的复杂页面时使用。
```bash
python ~/.openclaw/skills/web-fetch-tool/fetch.py "https://www.baidu.com" -e playwright
```

### 3. 🔐 需要登录的网站抓取 (核心进阶)

如果你需要抓取 Twitter、知乎推荐流、Github 私有仓库等需要登录的页面，请按以下两步操作：

**第一步：交互式建立会话（只需执行一次）**
使用 `--login` 参数。此时电脑会**弹出一个真实的浏览器窗口**。
请在浏览器中自由操作，无论耗时多久、跳转多少次，只要确认登录成功，点击页面右上角的**【✅ 登录/验证完成，点击继续】**绿色按钮即可。程序会自动将凭证保存到指定的 json 文件中。
```bash
python ~/.openclaw/skills/web-fetch-tool/fetch.py "https://github.com/login" -e playwright --login -s github_session.json
```

**第二步：携带状态静默抓取（可无限次执行）**
以后抓取该网站任何页面，只需带上 `-s` 参数，程序将在后台无头静默秒抓。
```bash
python ~/.openclaw/skills/web-fetch-tool/fetch.py "https://github.com/settings/profile" -e playwright -s github_session.json
```

> **💡 远程服务器(Headless) 最佳实践：**
> 如果你的脚本运行在纯命令行的 Linux 服务器上，无法弹出浏览器窗口。你可以**在本地个人电脑（Windows/Mac）上执行第一步**，生成 `session.json` 后，通过 `scp` 等工具传到服务器上，服务器直接执行第二步即可完美运行！

## ⚙️ 参数字典

| 参数 | 简写 | 说明 | 默认值 |
|------|------|--------|--------|
| `url` | 无 | 目标网页的 URL (必填) | 无 |
| `--engine` | `-e` | 网络引擎选择：`cffi` 或 `playwright` | `cffi` |
| `--session` | `-s` | **持久化文件路径**，用于加载或保存 Cookie/登录状态 | 无 |
| `--login` | 无 | **交互登录模式**。注入悬浮按钮，无限期等待用户手工操作 | `False` |
| `--max-chars`| `-m` | 截断保护：允许输出的最大 Markdown 字符数 | `50000` |
| `--output` | `-o` | 将抓取结果写入到指定文件 (如 `result.md`) | `stdout` |
| `--retries` | `-r` | 失败重试次数 | `2` |
| `--proxy` | `-p` | 设置 HTTP/Socks5 代理 (例: `http://127.0.0.1:7890`) | 无 |

## 🌐 网站兼容性参考

- ✅ **极速直连 (CFFI)**：大部分资讯站。
- ✅ **动态渲染 (Playwright)**：搜索引擎, Google, 各种基于 Vue/React 的单页应用。
- ✅ **强反爬/验证码防护站**：知乎, 微博, 各种采用 Cloudflare 5秒盾的网站 (已优化超时免拦截)。
- ✅ **强制登录站**：Twitter, Github, 后台管理系统 (支持多路由跳转与三方 OAuth 登录验证)。
