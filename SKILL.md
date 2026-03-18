---
name: super-fetch
description: 高性能网页抓取与正文提取引引擎。支持智能正文精简、链接代号化（支持链接+图片）、Session 持久化（自动格式转换）、人工干预模式。适用于规避反爬、登录验证、提取结构化内容等场景。
version: 2.1.0
user-invocable: true
---

# Super Fetch

OpenClaw 网页抓取基座，将 HTML 转化为极简 Markdown。

## 核心特性

| 特性 | 说明 |
|------|------|
| 双引擎 | cffi（极速）/ playwright（浏览器） |
| 智能正文 | 自动识别主要内容，过滤噪音 |
| 链接代号化 | 链接和图片转为 `@abcd-1` 格式，节省 Token |
| Session 持久化 | 自动保存/加载登录状态，支持多种格式 |
| 人工干预 | 弹窗处理验证码/滑动登录 |
| 二进制下载 | PDF/图片等直接保存为文件 |

## 目录结构

```
~/.openclaw/super-fetch/          # 数据目录（自动创建）
├── fetch.py                      # 主程序入口
├── fetch_engines.py              # 抓取引擎
├── fetch_parser.py               # 内容解析
├── get_link.py                   # 链接反查工具
├── session.json                  # 登录状态
└── links.db                      # 链接映射
```

## 快速开始

```bash
# 基本抓取
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com"

# 指定引擎
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com" -e playwright
```

## 参数说明

### fetch.py

| 参数 | 简写 | 说明 | 默认 |
|------|------|------|------|
| `url` | - | 目标 URL（必填） | - |
| `--engine` | `-e` | 引擎：`cffi` / `playwright` | `cffi` |
| `--interactive` | `-i` | 人工干预模式 | false |
| `--full` | `-f` | 全量模式（不过滤） | false |
| `--session` | `-s` | Session 文件名或路径 | 不加载 |
| `--wait` | `-w` | 渲染等待秒数 | 3 |
| `--max-chars` | `-m` | 输出最大字符 | 50000 |
| `--proxy` | `-p` | 代理 `http://host:port` | - |
| `--retries` | `-r` | 重试次数 | 2 |
| `--output` | `-o` | 保存二进制文件 | - |

### get_link.py

```bash
# 反查链接
python3 ~/.openclaw/skills/super-fetch/get_link.py @abcd-1

# 清理命名空间
python3 ~/.openclaw/skills/super-fetch/get_link.py --clear abcd

# 清空数据库
python3 ~/.openclaw/skills/super-fetch/get_link.py --clear
```

## 使用场景

### 1. 简单抓取
```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com"
```

### 2. 登录后访问
```bash
# 第一次：人工干预登录
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/user" -i -s session.json

# 之后：自动使用 session
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/user" -s session.json
```

### 3. 处理验证码
```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/captcha" -i
```

### 4. 下载 PDF
```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/file.pdf" -o /tmp/file.pdf
```

### 5. 强制浏览器渲染
```bash
python3 ~/.openclaw/skills/super-fetch/fetch.py "https://example.com/spa" -e playwright
```

## Session 格式

自动识别转换三种格式：

1. **Playwright 格式**：`{"cookies": [...], "origins": [...]}`
2. **Cookie-Editor 导出**：JSON 数组
3. **旧版扁平**：`{"name": "value"}`

## 依赖安装

```bash
pip install curl_cffi playwright beautifulsoup4 markdownify
playwright install chromium
```

或使用 uvx 临时运行：
```bash
uvx --with curl-cffi --with playwright --with beautifulsoup4 --with markdownify \
  python ~/.openclaw/skills/super-fetch/fetch.py "https://example.com"
```

## 注意事项

- 数据目录：`~/.openclaw/super-fetch/`
- Session 和 links.db 包含隐私，**勿上传 GitHub**
- 人工干预模式点击绿色按钮确认完成
- 遵守目标站点 robots.txt 和服务条款
