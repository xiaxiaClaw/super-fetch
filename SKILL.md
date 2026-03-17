---
name: super-fetch
description: 高性能网页抓取与正文提取核心引擎。支持智能噪音过滤、Token 极限压缩（链接代号化）、持久化会话管理以及人工干预模式。适用于需要规避反爬检测、处理验证码或在长上下文中维持高效信息密度的场景。
version: 1.0.0
user-invocable: true
---

# Super Fetch (Core Engine)

这是 OpenClaw 的底层抓取基座。它负责将复杂的 HTML 转化为极简、高信息密度的 Markdown，并利用 SQLite 数据库管理链接映射以节省 Token。

## 📂 路径规范 (Path Constants)

Agent 应当优先使用以下预设路径：
- **脚本目录**: `~/.openclaw/skills/super-fetch/`
- **默认会话文件**: `~/.openclaw/skills/super-fetch/session.json` (自动读写，存放所有登录凭证)
- **链接数据库**: `~/.openclaw/skills/super-fetch/links.db`

或者存放在`~/.openclaw/<workspace>/skills/`中

## 🛠 核心指令集

### 1. `fetch.py` (获取与解析)
**功能**：抓取 URL 并输出清洗后的内容。
```bash
python ~/.openclaw/skills/super-fetch/fetch.py "<URL>" [参数]
```
- **默认 (Smart 模式)**: 自动评分提取正文，剔除导航、页脚、广告。
- `-f, --full`: **全量模式**。当默认提取丢失了关键信息（如菜单、页脚联系方式）时使用。
- `-e playwright`: **浏览器模式**。绕过强力反爬或加载动态渲染内容。
- `-i, --interactive`: **人工干预模式**。弹出浏览器窗口处理验证码、滑块或手动登录。执行此模式时强制使用 playwright 引擎。
- `-s, --session`: **会话文件**。默认自动使用同目录下的 `session.json`。
- `-o, --output`: **下载文件**。当目标 URL 返回二进制内容（PDF、图片、视频等）时，保存为指定文件路径。
- `-w, --wait`: **渲染等待**。Playwright 额外等待秒数（默认 3 秒）。
- `-m, --max-chars`: **最大字符数**。输出内容上限（默认 50000）。
- `-p, --proxy`: **代理设置**。如 `http://127.0.0.1:7890`。
- `-r, --retries`: **重试次数**。失败重试次数（默认 2）。

### 2. `get_link.py` (反查与内存管理)
**功能**：解析代号（如 `@x1-5`）或清理数据库空间。
```bash
# 反查具体代号 (支持多个)
python ~/.openclaw/skills/super-fetch/get_link.py <ID1> <ID2>

# 精准清理指定命名空间 (推荐，任务结束必做)
python ~/.openclaw/skills/super-fetch/get_link.py --clear <namespace>
```

---

## 📥 下载二进制文件

当需要下载 PDF、图片、视频等二进制文件时，使用 `-o/--output` 参数：

```bash
# 下载 PDF 论文
python ~/.openclaw/skills/super-fetch/fetch.py "https://arxiv.org/pdf/2509.19088.pdf" -o paper.pdf

# 下载图片
python ~/.openclaw/skills/super-fetch/fetch.py "https://picsum.photos/800/600" -o image.jpg

# 下载视频
python ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/video.mp4" -o video.mp4
```

**支持的类型**：PDF、DOCX、XLSX、图片(jpg/png/gif)、视频(mp4/webm)、音频(mp3/wav)、压缩包(zip/rar/7z) 等。

---

## 🛡️ 人工干预流程 (Manual Intervention)

当遇到 Cloudflare 质询、验证码拦截或需要手动登录时：

1. **执行干预指令**:
   ```bash
   python ~/.openclaw/skills/super-fetch/fetch.py "<URL>" --interactive
   ```
2. **引导用户**: 告知用户：“已为您弹出浏览器，请手动完成验证/操作。完成后点击页面右上角绿色按钮。”
3. **状态持久化**: 用户点击按钮后，凭证将自动保存至默认 `session.json`，后续抓取将自动维持该状态。

---

## 🔄 Agent 标准操作流 (SOP)

1. **初始执行**: 优先使用 `python fetch.py "<URL>"`。
2. **处理链接代号**:
   - 解析返回的 Markdown，识别条目代号（如 `[标题](@k9-1)`）。
   - **Token 准则**: 不要反查所有代号。仅当你决定深入阅读特定条目时，调用 `get_link.py` 获取真实 URL。
3. **异常处理**:
   - 若返回 403 或验证提示：转入 **人工干预流程**。
   - 若正文提取不全：增加 `--full` 参数重试。
   - 若内容为空：尝试 `-e playwright -w 8` 增加渲染时间。
4. **清理记录**: 分析任务完成后，提取输出中的 `命名空间: <ns>`，执行 `get_link.py --clear <ns>`。

---

## 💡 决策准则 (Guidelines)

- **默认 Session 策略**: 始终使用默认的 `session.json` 进行 Cookie 持久化。这使得 Agent 可以在不同网站间维持登录身份。
- **命名空间识别**: 代号格式为 `@命名空间-序号`。清理时只需传入短前缀（如 `get_link.py --clear k9`）。
- **Token 敏感**: 除非用户明确要求完整地址，否则在回复中应保留代号（如：“参考内容见 @a1-1”），以节省上下文空间。

---
**注意**: 所有链接映射记录将在数据库中保留 3 天。确保脚本路径 `~/.openclaw/skills/super-fetch/` 及其子目录具备读写权限。