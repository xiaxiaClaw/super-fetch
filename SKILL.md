---
name: super-fetch
description: 高性能网页抓取工具，将网页转换为干净的 Markdown。支持 JavaScript 渲染、会话保持、登录态保存、批量并发抓取。跨平台 Windows/macOS/Linux。
---

# Super Fetch

## 快速开始

```bash
# 抓取单个网页（输出 Markdown,其中链接会用代号表示）
python fetch.py https://example.com -s

# 抓取多个网页（批量并发）
python fetch.py https://example.com/page1 https://example.com/page2 -s

# 从文件读取 URL 列表并将结果保存
python fetch.py -F urls.txt -o results.json

# 需要登录时（弹出浏览器手动操作）
python fetch.py https://example.com -i

# 从链接代号查询真实URL（注意区分图片链接和网址链接）
python get_link.py @abc-12

# 清理链接数据库（指定命名空间）
python get_link.py clear abc
```

## 核心概念

### 两种模式

| 触发方式 | 模式 | 说明 |
|---------|------|------|
| 单个 URL | 单 URL 模式 | 输出 Markdown 到终端 |
| 多个 URL 或 `-F` | 批量并发模式 | 输出 JSON 结果 |

### 会话（Session）

会话用于保存登录状态，避免重复登录。

```bash
# 无会话（每次独立）
python fetch.py https://example.com

# 使用默认会话 session.json
python fetch.py https://example.com -s

# 使用指定会话
python fetch.py https://example.com -s my_site.json

# 创建会话（弹出浏览器手动登录）
python fetch.py https://example.com -i
```

## 批量抓取

### 基本用法

```bash
# 直接传入多个 URL
python fetch.py https://url1.com https://url2.com https://url3.com

# 从文件读取（每行一个 URL）
cat > urls.txt << 'EOF'
https://example.com/page1
https://example.com/page2
https://example.org/article
EOF
python fetch.py -F urls.txt

# 导出结果到 JSON（-o：多URL时用于保存爬取结果/单URL时用于下载文件）
python fetch.py -F urls.txt -o results.json
```

### 调优参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `-c` | 5 | 并发数（防爬严就降，反之升） |
| `--domain-delay-min` | 2.0 | 同域名最小间隔（秒） |
| `--domain-delay-max` | 5.0 | 同域名最大间隔（秒） |

```bash
# 保守模式（防爬严格）
python fetch.py -F urls.txt -c 2 --domain-delay-min 3 --domain-delay-max 6

# 激进模式（内部网站）
python fetch.py -F urls.txt -c 20 --domain-delay-min 0.5 --domain-delay-max 1
```

### 引擎选择

| 引擎 | 速度 | 适用场景 |
|------|------|----------|
| `playwright`（默认） | 中 | JS 渲染、动态内容、需要登录 |
| `cffi` | 快 | 纯静态页面、API、文件下载 |

```bash
# 默认 playwright（绝大多数场景）
python fetch.py -F urls.txt

# 用 cffi（纯静态页更快）
python fetch.py -F urls.txt -e cffi
```

## 登录与验证码

### 交互模式（推荐）

```bash
# 1. 弹出浏览器，手动完成登录
python fetch.py https://example.com -i

# 2. 右上角点击"✅ 完成操作"保存会话

# 3. 后续自动使用会话
python fetch.py https://example.com/private -s
```

### 导入已有 Cookie

适用于无法本地打开浏览器、或使用他人登录态的场景。

1. 安装浏览器插件 [Cookie-Editor](https://cookie-editor.com/)
2. 登录目标网站，导出 JSON
3. 保存到 `~/.openclaw/super-fetch/my_cookies.json`
4. 使用：`python fetch.py https://example.com -s my_cookies.json`

## 常见用法

```bash
# 等待 JS 渲染（动态内容）
python fetch.py https://example.com -w 5

# 下载文件（二进制用 cffi）
python fetch.py https://example.com/file.pdf -e cffi -o ./file.pdf

# 全量提取（不过滤广告等噪音）
python fetch.py https://example.com --full

# 使用代理
python fetch.py https://example.com -p http://127.0.0.1:7890
```

## 链接反查

抓取微博/知乎等平台搜索结果时，链接会变成代号（如 `@abc-12`），需反查获取真实 URL。
请在查询完链接后及时清理数据库

```bash
# 反查多个代号
python get_link.py @abc-12 @abc-15 @abc-20

# 完整流程示例
python fetch.py "https://s.weibo.com/weibo?q=关键词" -s session.json -w 5
# 输出中链接是 @abc-12 这样的代号

python get_link.py @abc-12  # 获取真实 URL

# 清理数据库
python get_link.py --clear        # 清空全部
python get_link.py --clear @abc-12 # 删除单个
```

## 参数参考

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--engine` | `-e` | playwright | 引擎：playwright / cffi |
| `--full` | `-f` | false | 全量提取 |
| `--session` | `-s` | - | 会话文件 |
| `--wait` | `-w` | 3 | 渲染等待秒数 |
| `--proxy` | `-p` | - | 代理地址 |
| `--retries` | `-r` | 2 | 重试次数 |
| `--output` | `-o` | - | 单 URL：下载文件 / 批量：JSON |
| `--interactive` | `-i` | false | 交互模式（仅单 URL） |
| `--max-chars` | `-m` | 50000 | 最大字符数（仅单 URL） |
| `--file` | `-F` | - | URL 文件路径（仅批量） |
| `--concurrency` | `-c` | 5 | 并发数（仅批量） |
| `--silent` | - | false | 静默模式（仅批量） |

## 数据存储

- 目录：`~/.openclaw/super-fetch/`
- `links.db` - 链接代号映射
- `*.json` - 会话文件

## 项目结构

```
super-fetch/
├── fetch.py           # 统一入口
├── fetch_engines.py    # 抓取引擎
├── fetch_parser.py     # HTML 解析
├── core.py             # 共享工具
└── get_link.py        # 链接反查
```
