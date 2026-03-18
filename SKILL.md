---
name: super-fetch
description: 高性能网页抓取与正文提取核心引擎。支持智能噪音过滤、Token 极限压缩（链接代号化）、多格式持久化会话管理（支持 Cookie-Editor）以及人工干预模式。适用于需要规避反爬检测、处理验证码、远程授权或在长上下文中维持高效信息密度的场景。
version: 1.0.0
user-invocable: true
---

# Super Fetch (Core Engine)

这是 OpenClaw 的底层抓取基座。它负责将复杂的 HTML 转化为极简、高信息密度的 Markdown，并利用 SQLite 数据库管理链接映射以极大地节省 LLM Token 上下文。

## 路径与状态管理 (Path & State)

Agent 应当优先使用以下预设路径：
- **脚本目录**: `~/.openclaw/skills/super-fetch/` (或 `~/.openclaw/<workspace>/skills/super-fetch/`)
- **链接数据库**: `~/.openclaw/skills/super-fetch/links.db` (存储有效期 3 天)
- **默认会话文件**: `~/.openclaw/skills/super-fetch/session.json`

**关于凭证与登录状态 (session.json)：**
该引擎具备**自适应凭证解析**能力，支持用户直接将以下三种格式粘贴入 `session.json` 中，系统会自动将其格式化为全引擎通用的标准状态：
1. **Playwright 原生格式** (带 localStorage 支持，最高权限)。
2. **Cookie-Editor 插件导出格式** (JSON 数组格式，最适合用户远程辅助登录)。
3. **扁平字典格式** (如 `{"cookie_name": "value"}`)。

## 核心指令集 (Commands)

### 1. `fetch.py` (获取与解析)
**功能**：抓取 URL、绕过反爬、清洗噪音并输出含代号的高密度 Markdown 内容。
```bash
python ~/.openclaw/skills/super-fetch/fetch.py "<URL>"[参数]
```
**常用参数**：
- **(默认)**: Smart 模式，自动评分提取正文，剔除导航、页脚、广告。
- `-f, --full`: **全量模式**。当默认提取丢失了关键信息（如菜单、页脚、评论区）时使用。
- `-e playwright`: **全真浏览器模式**。绕过强力反爬（Cloudflare）或加载动态渲染 (SPA) 内容。
- `-i, --interactive`: **人工干预模式**。弹出无头浏览器窗口处理验证码、滑块或引导用户手动登录。（强制使用 playwright 引擎）。
- `-o, --output <path>`: **下载文件**。当目标 URL 为二进制文件（PDF、图片、视频、压缩包等）时，直接保存到指定路径。
- `-w, --wait <秒>`: **渲染等待**。增加 JS 渲染时间（默认 3 秒）。

### 2. `get_link.py` (内存与代号管理)
**功能**：解析页面中的链接代号（如 `@k9-1`），或清理数据库释放空间。
```bash
# 反查具体代号 (支持传入多个)
python ~/.openclaw/skills/super-fetch/get_link.py @k9-1 @k9-5

# 精准清理指定命名空间 (Agent 任务结束的必做步骤)
python ~/.openclaw/skills/super-fetch/get_link.py --clear k9
```

---

## Agent 标准操作流 (SOP)

为了保证高效能与低 Token 消耗，Agent 必须严格遵循以下执行步骤：

### 第一步：初次抓取
优先使用极速轻量级抓取，且不加多余参数：
```bash
python fetch.py "https://example.com"
```
**异常与重试策略：**
- **返回 403 / Just a moment (Cloudflare) / 抓取失败**：改用 `python fetch.py "<URL>" -e playwright`。
- **返回内容过少 / 缺少关键导航**：改用 `python fetch.py "<URL>" --full`。
- **遇到严格验证码或需复杂登录**：执行 `python fetch.py "<URL>" -i` 并提示用户：“已为您弹出浏览器，请手动完成验证/登录。完成后点击页面右上角绿色按钮。”

### 第二步：处理链接代号 (Token 压缩准则)
解析返回的 Markdown 后，页面内所有链接已被替换为如 `[标题](@k9-1)` 的格式。
- **绝对禁止**：一次性反查页面中所有的代号。
- **正确做法**：仅当你决定深入阅读特定的条目（如某篇相关新闻、下一页按钮）时，调用 `get_link.py @k9-1` 获取真实的 URL，再对该真实 URL 发起新的 `fetch.py`。
- **回答用户时**：除非用户明确要求提供完整 URL，否则在回答中可直接保留代号（如：“参考来源见 @a1-1”），不要做无谓的展开。

### 第三步：下载二进制数据 (按需)
如果你识别到目标是一个多媒体或文档资源（如 `.pdf`, `.mp4`），请直接使用 `-o` 参数避免控制台乱码：
```bash
python fetch.py "https://arxiv.org/pdf/2509.19088.pdf" -o paper.pdf
```

### 第四步：清理内存 (任务收尾)
分析当前页面或任务流结束后，从输出结果的顶部找到 `命名空间: <ns>`（例如 `k9`），主动清理数据库：
```bash
python get_link.py --clear k9
```

## 决策与故障排除准则 (Guidelines)

1. **登录失效处理**：如果抓取结果显示“请登录”或用户态丢失，提醒用户：“由于权限限制无法查看，您可以利用 Cookie-Editor 插件导出 Cookie 并粘贴至 `session.json` 中，或者让我开启 `-i` 人工干预模式为您弹出登录窗口。”
2. **多页面状态共享**：所有的 `fetch.py` 调用默认自动使用并更新 `session.json`。Agent 不需要显式传递 Cookie 即可在同一站点的不同子页面间维持会话。
3. **内容截断**：默认输出上限为 50000 字符，如遇超长文本需结合 grep 或分段读取技巧进行后续处理。