---
name: super-fetch
description: 高性能网页抓取工具，将网页转换为干净的 Markdown。支持 JavaScript 渲染、会话保持、登录态保存、批量并发抓取。跨平台 Windows/macOS/Linux。
---

# Super Fetch

## 快速开始

```bash
# 基础抓取
python fetch.py https://example.com

# 交互模式（登录）
python fetch.py https://example.com -i

# 使用会话
python fetch.py https://example.com -s
python fetch.py https://example.com -s my_session.json

# 批量并发抓取（直接传多个 URL）
python fetch.py https://url1.com https://url2.com https://url3.com

# 批量并发抓取（从文件读取）
python fetch.py -F urls.txt
```

## 模式自动识别

`fetch.py` 会自动根据参数判断模式：

| 触发方式 | 模式 | 默认引擎 |
|---------|------|---------|
| 单个 URL + 无 -F | **单 URL 模式** | playwright |
| 多个 URL / -F | **批量并发模式** | cffi |

## 单 URL 模式

### 会话规则

| 命令                                  | 说明                                |
| ------------------------------------- | ----------------------------------- |
| `python fetch.py <url>`               | 独立会话，无状态                    |
| `python fetch.py <url> -s`            | 使用默认会话 `session.json`         |
| `python fetch.py <url> -s my.json`    | 使用指定会话 `my.json`              |
| `python fetch.py <url> -i`            | 交互模式，自动保存到 `session.json` |
| `python fetch.py <url> -i -s my.json` | 交互模式，保存到指定会话            |

### 引擎选择

| 引擎         | 速度  | 适用场景                                                       |
| ------------ | ----- | -------------------------------------------------------------- |
| `playwright` | 默认  | 绝大多数场景：JS 渲染、动态内容、登录、验证码等                |
| `cffi`       | ⚡ 快 | 仅用于下载二进制文件或极其简单的静态页面/API或不限制爬虫的网页 |

```bash
# 默认用 playwright 即可
python fetch.py https://example.com

# 需要等待渲染
python fetch.py https://example.com -w 5

# 仅下载文件时用 cffi
python fetch.py https://example.com/file.pdf -e cffi -o ./file.pdf
```

## 批量并发模式

支持多 URL 并发抓取，内置完善的防反爬虫策略。

### 快速使用

```bash
# 方式一：直接传多个 URL
python fetch.py https://url1.com https://url2.com https://url3.com

# 方式二：从文件读取（每行一个 URL）
python fetch.py -F urls.txt

# 输出结果到 JSON 文件
python fetch.py -F urls.txt -o results.json
```

### 防反爬虫配置

| 参数 | 默认 | 说明 |
|------|------|------|
| `-c, --concurrency` | 3 | 最大并发数（建议 2-5） |
| `--domain-delay-min` | 2.0 | 同一域名最小间隔（秒） |
| `--domain-delay-max` | 5.0 | 同一域名最大间隔（秒） |
| `--jitter` | 0.5 | 额外随机抖动上限（秒） |

```bash
# 保守模式（防爬严格的网站）
python fetch.py -F urls.txt \
  -c 2 \
  --domain-delay-min 5 \
  --domain-delay-max 10

# 激进模式（内部网站或不限制的网站）
python fetch.py -F urls.txt \
  -c 10 \
  --domain-delay-min 0.5 \
  --domain-delay-max 1
```

### 引擎选择

批量模式支持两种引擎，**并发实现方式不同**：

| 引擎 | 并发方式 | 推荐场景 |
|------|---------|---------|
| `playwright` (默认) | PlaywrightPool 单 Browser + 多 Context | 绝大多数场景（JS 渲染、动态内容） |
| `cffi` | curl_cffi AsyncSession 原生并发 | 纯静态页面、API、追求极致速度 |

```bash
# playwright（默认，推荐）
python fetch.py -F urls.txt

# cffi（仅纯静态页用）
python fetch.py -F urls.txt -e cffi
```

> **Playwright 并发原理**：复用单个 Browser 进程，为每个请求创建独立的 BrowserContext，
> 既实现了真正的并发，又保持了 Cookie 隔离，资源占用远低于启动多个 Browser。

## 登录/验证码处理 (fetch.py)

### 方式一：交互模式（推荐，本地操作）

```bash
# 1. 打开浏览器窗口
python fetch.py https://example.com -i

# 2. 在弹出的浏览器中手动完成：
#    - 输入账号密码登录
#    - 完成验证码（滑动/点选/短信等）
#    - 确保页面跳转到登录后的状态

# 3. 点击页面右上角绿色按钮"✅ 完成操作，点击抓取内容"

# 4. 后续使用已保存的会话
python fetch.py https://example.com/private -s
```

### 方式二：远程导入 Cookie（Cookie-Editor）

适用于：无法在本地打开浏览器、需要使用他人的登录态

**步骤：**

1. 在浏览器（Chrome/Edge/Firefox）中安装 [Cookie-Editor](https://cookie-editor.com/) 插件

2. 登录目标网站，确保登录成功

3. 点击 Cookie-Editor 插件图标 → 点击"Export" → 选择"JSON"格式

4. 将导出的 JSON 内容保存到文件，例如 `my_cookies.json`，放到 `~/.openclaw/super-fetch/` 目录下

5. 直接使用（会自动转换格式）：

```bash
python fetch.py https://example.com -s my_cookies.json
```

**支持的 Cookie 格式：**

- Playwright 原生格式（含 `cookies` 和 `origins`）
- Cookie-Editor 导出的列表格式
- 简单键值对格式 `{"key": "value"}`

## 会话使用规范

| 场景             | 推荐做法                                             |
| ---------------- | ---------------------------------------------------- |
| 日常抓取         | 不使用 `-s`，独立会话                                |
| 单个网站长期使用 | 用 `-i` 创建会话后，后续用 `-s`                      |
| 多个网站/账号    | 用 `-i -s site_a.json`、`-i -s site_b.json` 分别保存 |
| 共享登录态       | 用 Cookie-Editor 导出 JSON 分享                      |
| 批量抓取带会话   | `fetch.py -F urls.txt -s session.json`                |

**注意事项：**

- 会话文件包含敏感 Cookie，请勿提交到 Git
- 定期重新登录，Cookie 可能过期
- 不同网站使用不同的会话文件，避免 Cookie 污染
- 批量抓取时，所有 URL 共享同一个会话

## 常用命令

```bash
# 全量模式（不过滤噪音）
python fetch.py https://example.com --full

# 等待渲染
python fetch.py https://example.com -w 5

# 下载文件（用 cffi）
python fetch.py https://example.com/image.png -e cffi -o ./image.png

# 使用代理
python fetch.py https://example.com -p http://127.0.0.1:7890
```

## 批量抓取完整示例

```bash
# 1. 创建 urls.txt
cat > urls.txt << 'EOF'
https://example.com/page1
https://example.com/page2
https://example.org/article
EOF

# 2. 执行批量抓取，结果输出到 results.json
python fetch.py -F urls.txt -o results.json

# 3. 使用 playwright 引擎（需要 JS 渲染）
python fetch.py -F urls.txt -e playwright -c 2

# 4. 带会话的批量抓取
python fetch.py -F urls.txt -s session.json
```

## 链接反查与数据库清理

### 为什么需要反查链接？

输出的 Markdown 中，所有链接（`<a>` 标签的 `href` 和 `<img>` 标签的 `src`）会被替换为**代号**（格式：`@{namespace}-{number}`，如 `@abcd-1`），这样可以：
- 缩短输出长度
- 避免敏感 URL 直接暴露
- 统一管理链接

需要使用 `get_link.py` 反查代号才能得到真实 URL。

### 反查链接

```bash
# 反查单个链接
python get_link.py @abcd-1

# 反查多个
python get_link.py @abcd-1 @abcd-2
```

### 数据库清理

```bash
# 清空全部（谨慎使用）
python get_link.py --clear

# 删除特定链接
python get_link.py --clear @abcd-1

# 删除某命名空间下所有链接
python get_link.py --clear abcd
```

**清理要求：**

- `links.db` 会自动清理 7 天前的旧数据（5% 概率触发）
- 抓取大量页面后，可手动执行 `--clear` 释放空间
- 清理后无法反查之前的链接代号

## 参数说明

### 统一入口 (fetch.py)

自动识别单 URL 或批量模式。

| 参数                | 简写 | 默认值   | 说明                                          | 适用模式 |
| ------------------- | ---- | ------- | --------------------------------------------- | ------- |
| `--engine`          | `-e` | playwright | 抓取引擎：playwright（默认）/ cffi            | 全部 |
| `--full`            | `-f` | false   | 全量提取，不过滤                              | 全部 |
| `--session`         | `-s` | -       | 会话文件：无参用 `session.json`              | 全部 |
| `--wait`            | `-w` | 3       | 渲染等待秒数                                   | 全部 |
| `--proxy`           | `-p` | -       | 代理地址                                      | 全部 |
| `--retries`         | `-r` | 2       | 重试次数                                      | 全部 |
| `--output`          | `-o` | -       | 单 URL：二进制文件 / 批量：JSON 结果        | 全部 |
| `--interactive`     | `-i` | false   | 交互模式，弹出浏览器                          | 仅单 URL |
| `--max-chars`       | `-m` | 50000   | 最大输出字符                                  | 仅单 URL |
| `--file`            | `-F` | -       | 从文件读取 URL 列表（触发批量模式）           | 仅批量 |
| `--concurrency`     | `-c` | 3       | 最大并发数（建议 2-5）                        | 仅批量 |
| `--domain-delay-min` | -   | 2.0     | 同一域名最小请求间隔（秒）                     | 仅批量 |
| `--domain-delay-max` | -   | 5.0     | 同一域名最大请求间隔（秒）                     | 仅批量 |
| `--jitter`          | -    | 0.5     | 全局随机抖动上限（秒）                         | 仅批量 |
| `--silent`          | -    | false   | 静默模式，只输出最终 JSON                     | 仅批量 |

### 模式判断规则

```bash
# 单 URL 模式
python fetch.py https://example.com              # 单 URL
python fetch.py https://example.com -i           # 单 URL + 交互

# 批量模式（自动识别）
python fetch.py https://url1.com https://url2.com  # 多个 URL
python fetch.py -F urls.txt                        # 用 -F 参数
```

> **引擎默认值**：无论单 URL 还是批量模式，默认都使用 `playwright`。

## 架构说明

### Playwright 并发原理 (fetch_engines.PlaywrightPool)

```
┌─────────────────────────────────────────────────────────────┐
│                     单个 Browser 进程                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Context 1  │  │   Context 2  │  │   Context 3  │... │
│  │  (Page 1)    │  │  (Page 2)    │  │  (Page 3)    │    │
│  │  Cookie 隔离 │  │  Cookie 隔离 │  │  Cookie 隔离 │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

优势：
- 只启动一个浏览器进程，内存占用低
- 每个请求有独立的 Context，Cookie 互不影响
- 支持真正的并发

### 模块依赖关系

```
fetch.py (单 URL 入口)
    └── fetch_engines.fetch_target()
            ├── fetch_with_curl_cffi()
            └── fetch_with_playwright()

fetch_batch.py (批量并发入口)
    ├── fetch_engines.PlaywrightPool (playwright 并发池)
    ├── fetch_engines.fetch_with_curl_cffi() (cffi 直接调用)
    └── fetch_parser.extract_page_content()
```

## 数据存储

- **目录**: `~/.openclaw/super-fetch/`（Windows: `%USERPROFILE%\.openclaw\super-fetch\`）
- `links.db` - 链接代号映射
- `*.json` - 会话文件

## 项目结构

```
super-fetch/
└── super-fetch/      # 代码包
    ├── fetch.py       # 统一入口（单 URL + 批量）
    ├── fetch_batch.py # 批量抓取模块
    ├── fetch_engines.py # 抓取引擎（含 PlaywrightPool）
    ├── fetch_parser.py  # HTML 解析
    └── get_link.py    # 链接反查
```

