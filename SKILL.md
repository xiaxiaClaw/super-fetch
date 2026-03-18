---
name: super-fetch
description: 高性能网页抓取与正文提取引擎。支持智能正文精简、链接代号化、Session 持久化、人工干预模式。适用于需要规避反爬、登录验证或提取结构化内容的场景。
version: 2.0.0
user-invocable: true
---

# Super Fetch

OpenClaw 高性能网页抓取基座，将复杂 HTML 转化为极简 Markdown。

## 核心特性

- **双引擎切换**：cffi（极速）/ playwright（浏览器）
- **智能正文提取**：自动识别主要内容，过滤噪音
- **链接代号化**：将页面链接转为 `@k9-1` 格式，节省 Token
- **Session 持久化**：自动保存/加载登录状态
- **人工干预模式**：弹窗处理验证码、滑动登录
- **二进制下载**：支持 PDF/图片等直接保存

## 文件结构

```
~/.openclaw/skills/super-fetch/
├── fetch.py           # 主程序入口
├── fetch_engines.py   # 抓取引擎（cffi/playwright）
├── fetch_parser.py    # 内容解析与正文提取
├── get_link.py        # 链接代号反查工具
├── session.json       # 登录状态存储（自动管理）
├── links.db           # 链接映射数据库
└── SKILL.md           # 本文档
```

## 快速开始

```bash
# 基本抓取（自动选择引擎）
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com"

# 使用指定引擎
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com" -e cffi
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com" -e playwright
```

## 参数详解

### fetch.py 主程序

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `url` | - | 目标 URL（必填） | - |
| `--engine` | `-e` | 抓取引擎：`cffi`（极速）或 `playwright`（浏览器） | `cffi` |
| `--interactive` | `-i` | 人工干预模式，弹出浏览器窗口处理验证码/登录 | `false` |
| `--full` | `-f` | 全量模式，保留页面全部文本，不做智能精简 | `false` |
| `--session` | `-s` | Session 文件路径 | `./session.json` |
| `--wait` | `-w` | Playwright 渲染等待秒数 | `3` |
| `--max-chars` | `-m` | 输出最大字符数 | `50000` |
| `--proxy` | `-p` | 代理地址，如 `http://127.0.0.1:7890` | - |
| `--retries` | `-r` | 失败重试次数 | `2` |
| `--output` | `-o` | 保存二进制文件（PDF/图片等） | - |

### get_link.py 链接反查

```bash
# 反查单个代号
python3 ~/.openclaw/skills/super-fetch/get_link.py @k9-1

# 反查多个代号
python3 ~/.openclaw/skills/super-fetch/get_link.py @k9-1 @k9-2 @ab-3

# 清理指定命名空间（如 k9 开头的所有链接）
python3 ~/.openclaw/skills/super-fetch/get_link.py --clear k9

# 清空全部链接数据库
python3 ~/.openclaw/skills/super-fetch/get_link.py --clear
```

## 使用场景

### 场景 1：简单网页抓取

```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://news.example.com/tech"
```

### 场景 2：需要登录的页面

```bash
# 第一次：使用人工干预模式登录
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/user" -i

# 之后：自动使用保存的 session
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/user"
```

### 场景 3：处理验证码/滑动验证

```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/login" -i
```

> 弹窗后手动完成验证，点击绿色按钮继续。

### 场景 4：下载 PDF/图片

```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/report.pdf" -o /tmp/report.pdf
```

### 场景 5：强制浏览器渲染（JS 页面）

```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/spa" -e playwright
```

### 场景 6：全量抓取（不过滤内容）

```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com" -f
```

## Session 格式支持

自动识别并转换三种 Session 格式：

1. **Playwright 格式**（原生）：`{"cookies": [...], "origins": [...]}`
2. **Cookie-Editor 导出格式**（JSON 数组）
3. **旧版扁平格式**：`{"cookie_name": "cookie_value"}`

## 依赖安装

```bash
pip install curl_cffi playwright beautifulsoup4 markdownify
playwright install chromium
```

或使用 uvx 临时运行：

```bash
uvx --with curl-cffi --with playwright --with beautifulsoup4 --with markdownify python ~/.openclaw/skills/super-fetch/fetch.py "https://example.com"
```

## 注意事项

- Session 和链接数据库保存在本地，**请勿上传**到 GitHub
- 人工干预模式记得点击绿色按钮确认完成
- 抓取受限网站请遵守 robots.txt 和服务条款
- Session 有时效性，过期后需要重新登录
