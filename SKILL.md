# Web Fetch Tool

网页抓取与 Markdown 转换工具。支持 JS 渲染、反爬绕过及交互式登录状态持久化。

## 环境依赖 (Dependencies)

执行此工具前，需使用 `uv` 安装以下依赖：
```bash
uv pip install playwright curl_cffi playwright-stealth markdownify beautifulsoup4 lxml
playwright install chromium
```

## 引擎选择与使用边界 (-e)

工具包含两种引擎，共用 `session.json` 格式：

1. **`cffi` (默认)**
   - **特点**：极速、低开销 HTTP 请求。
   - **适用场景**：静态页面、普通文章、简单 API 以及仅依赖 Cookie 的简单会话抓取。

2. **`playwright`**
   - **特点**：全真无头浏览器渲染。
   - **必须使用的场景**：
     - 单页应用 (Vue/React) 或需等待 JS 动态加载数据的网页。
     - 遭遇 Cloudflare 5秒盾等强力反爬拦截。
     - **复杂会话维持**：某些网站的登录鉴权依赖 `LocalStorage` 或复杂的 JS 动态 Token 计算。`cffi` 仅支持提取 Cookie，因此在这些网站上，**必须强制使用 `playwright` 引擎来维持登录状态并抓取数据。**

## 会话持久化工作流 (-s, --login)

**步骤 1：交互式建立会话**
执行带有 `--login` 参数的命令 (此模式自动强制调用 Playwright)。程序会弹出浏览器，由用户手工完成登录/人机验证。完成后点击页面注入的“✅ 完成”悬浮按钮，状态将写入 JSON。
```bash
python fetch.py "https://example.com/login" --login -s session.json
```

**步骤 2：携带会话数据抓取**
读取 `session.json` 抓取需鉴权页面。
- **优先测试**：`python fetch.py "https://example.com/data" -e cffi -s session.json`
- **回退机制**：如果使用 `cffi` 抓取返回了未登录状态（或白屏），说明该站点属于复杂鉴权，**后续任务请务必切换为 `playwright` 引擎**：
  `python fetch.py "https://example.com/data" -e playwright -s session.json`

## 参数说明

| 参数 | 简写 | 描述 |
|------|------|------|
| `url` | | 目标 URL (必填) |
| `--engine` | `-e` | 抓取引擎: `cffi` 或 `playwright` (默认: `cffi`) |
| `--session` | `-s` | 会话状态 (Cookie/Storage) JSON 文件的读写路径 |
| `--login` | | 开启图形化交互模式以进行登录。程序将无限期等待用户手工操作 |
| `--max-chars`| `-m` | 截断保护: Markdown 最大字符数 (默认: 50000) |
| `--output` | `-o` | 结果输出至文件，若不指定则打印至 stdout |
| `--retries` | `-r` | 请求失败重试次数 (默认: 2) |
| `--proxy` | `-p` | 网络代理 (例: `http://127.0.0.1:7890`) |