---
name: super-fetch
description: 高性能网页抓取工具，将网页转换为结构化 Markdown。支持 JavaScript 渲染、会话保持、登录态保存。
---

# Super Fetch

将任意网页转换为干净的 Markdown，保留正文、过滤噪音，支持登录态和 JavaScript 渲染。

## 快速开始

```bash
# 方式一：本地已安装依赖（推荐，快）
python3 ~/.openclaw/skills/super-fetch/fetch.py https://example.com

# 方式二：每次自动装依赖（无需手动装）
uvx --with curl_cffi,playwright,beautifulsoup4,markdownify python3 ~/.openclaw/skills/super-fetch/fetch.py https://example.com
```

## 本地安装依赖（推荐）

首次运行前执行一次，后续调用更快：

```bash
cd /tmp && uv venv fetch-env
source fetch-env/bin/activate
uv pip install curl_cffi playwright beautifulsoup4 markdownify
playwright install chromium
```

之后直接运行：
```bash
source /tmp/fetch-env/bin/activate
python3 ~/.openclaw/skills/super-fetch/fetch.py https://example.com
```

## 核心功能

### 1. 双引擎

| 引擎 | 速度 | 适用场景 |
|------|------|----------|
| `cffi`（默认）| ⚡ 快 | 静态页面、搜索结果、API |
| `playwright` | 🐢 稍慢 | 需 JS 渲染、登录态、动态内容 |

```bash
python3 fetch.py https://news.ycombinator.com -e cffi
python3 fetch.py https://www.zhihu.com -e playwright -w 5
```

### 2. 会话保持（登录态）

```bash
# 首次：交互模式，浏览器弹出，完成登录后点击按钮
python3 fetch.py https://example.com -i -s my_session.json

# 后续：自动使用保存的会话
python3 fetch.py https://example.com/private -s my_session.json
```

### 3. 内容提取

```bash
# 智能提取（默认）：去除导航、侧栏、广告
python3 fetch.py https://example.com

# 全量模式：不过滤
python3 fetch.py https://example.com --full
```

### 4. 链接代号

抓取时自动将链接转为代号，方便阅读：

```
原文: https://example.com/page1
转换: @abcd-1
```

**反查原始链接**：
```bash
python3 ~/.openclaw/skills/super-fetch/get_link.py @abcd-1
python3 ~/.openclaw/skills/super-fetch/get_link.py abcd
```

### 5. 二进制下载

```bash
python3 fetch.py https://example.com/image.png -o /tmp/image.png
```

### 6. 代理

```bash
python3 fetch.py https://example.com -p http://127.0.0.1:7890
```

## 参数说明

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--engine` | `-e` | cffi | 抓取引擎：`cffi` / `playwright` |
| `--interactive` | `-i` | false | 交互模式，弹窗后可登录/操作 |
| `--full` | `-f` | false | 全量提取，不过滤噪音 |
| `--session` | `-s` | session.json | 会话文件路径 |
| `--wait` | `-w` | 3 | playwright 渲染等待秒数 |
| `--max-chars` | `-m` | 50000 | 最大输出字符 |
| `--proxy` | `-p` | - | 代理地址 |
| `--retries` | `-r` | 2 | 失败重试次数 |
| `--output` | `-o` | - | 输出二进制文件 |

## 输出示例

```
# 页面标题
> [系统提示] 命名空间: abcd | 会话: session.json

正文内容...

![图片](@abcd-1)
[链接](@abcd-2)
```

## 数据存储

- **目录**: `~/.openclaw/super-fetch/`
- **links.db**: SQLite，存储链接代号映射
- **session.json**: 默认会话文件
