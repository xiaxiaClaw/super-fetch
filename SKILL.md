---
name: super-fetch
description: 高性能网页抓取工具，将网页转换为干净的 Markdown。支持 JavaScript 渲染、会话保持、登录态保存、批量并发抓取。跨平台 Windows/macOS/Linux。
---

# Super Fetch

高性能网页抓取工具，支持 JS 渲染、登录态保存、批量并发。

## 快速开始

```bash
# 抓取单个网页（使用默认会话，链接用代号表示）
python fetch.py https://example.com -s

# 批量抓取多个网页（使用默认会话）
python fetch.py https://example.com/page1 https://example.com/page2 -s

# 从文件读取 URL 列表并保存结果到results.json（多URL时使用-o保存查询结果到json）
python fetch.py -F urls.txt -o results.json

# 需要用户手动交互时弹出浏览器手动操作（如登录/验证码），登陆状态默认保存到默认会话中
python fetch.py https://example.com -i

# 通过链接代号查询真实URL
python get_link.py @abcd-123

# 按照命名空间清理数据库
python get_link.py --clear abcd

# 下载文件（单URL时使用-o下载文件）
python fetch.py "https://avatars.githubusercontent.com/u/252820863?s=48&v=4" -o "img.jpg" 
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
python fetch.py https://example.com         # 独立会话
python fetch.py https://example.com -s      # 使用默认会话
python fetch.py https://example.com -i      # 创建会话（弹出浏览器）
```

## 详细文档

- [常见用法](references/usage.md) - 单 URL 抓取、文件下载、引擎选择
- [批量抓取](references/batch.md) - 并发配置、调优参数、输出格式
- [会话与登录](references/session.md) - 交互模式、Cookie 导入
- [链接反查](references/link-lookup.md) - 代号反查、数据库清理
- [参数参考](references/parameters.md) - 完整参数说明

## 项目结构

```
super-fetch/
├── fetch.py           # 统一入口
├── fetch_engines.py    # 抓取引擎
├── fetch_parser.py     # HTML 解析
├── core.py             # 共享工具
├── get_link.py        # 链接反查
└── references/         # 详细文档
    ├── usage.md
    ├── batch.md
    ├── session.md
    ├── link-lookup.md
    └── parameters.md
```

## 数据存储

- 目录：`~/.openclaw/super-fetch/`
- `links.db` - 链接代号映射
- `*.json` - 会话文件
