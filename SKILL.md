# Super Fetch - 高性能网页抓取工具

将网页转换为结构化 Markdown，支持 JavaScript 渲染和登录会话保持。

## 快速开始

```bash
# 安装依赖
pip install curl_cffi playwright beautifulsoup4 markdownify

# 最简用法
uvx super-fetch https://example.com

# 需要 JS 渲染时
uvx super-fetch https://example.com -e playwright
```

## 典型场景

### 1. 抓取静态页面（默认）
```bash
# curl_cffi 引擎，速度快
uvx super-fetch https://news.ycombinator.com/
uvx super-fetch https://www.zhihu.com/hot
```

### 2. 抓取需要登录的页面
```bash
# 首次：交互模式登录
uvx super-fetch https://example.com -i -s session.json
# → 浏览器弹出，完成登录后点击绿色按钮

# 后续：自动使用会话
uvx super-fetch https://example.com/private -s session.json
```

### 3. 抓取动态渲染页面
```bash
# playwright 引擎，等待 JS 执行
uvx super-fetch https://example.com -e playwright -w 5
```

### 4. 保存图片/文件
```bash
# 二进制内容必须用 -o 保存
uvx super-fetch https://example.com/image.png -o /tmp/img.png
uvx super-fetch https://example.com/file.pdf -o /tmp/file.pdf
```

### 5. 使用代理
```bash
uvx super-fetch https://example.com -p http://127.0.0.1:7890
```

## 链接代号系统

抓取时自动将链接转换为代号，便于阅读：

```
原文: https://example.com/page1
转换: @abcd-1
```

**反查原始链接**：
```bash
# 查询单个
get_link @abcd-1

# 查询整组
get_link abcd

# 清理数据库
get_link --clear           # 清空全部
get_link --clear abcd    # 清理指定组
```

## 参数说明

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--engine` | `-e` | cffi | 抓取引擎：`cffi` / `playwright` |
| `--interactive` | `-i` | false | 交互模式，弹窗让你先操作 |
| `--full` | `-f` | false | 全量提取，不过滤噪音 |
| `--session` | `-s` | session.json | 会话文件路径 |
| `--wait` | `-w` | 3 | playwright 渲染等待秒数 |
| `--max-chars` | `-m` | 50000 | 最大输出字符 |
| `--proxy` | `-p` | - | 代理地址 |
| `--retries` | `-r` | 2 | 重试次数 |
| `--output` | `-o` | - | 输出二进制文件路径 |

## 会话格式

支持三种 Cookie 格式，自动转换为 Playwright StorageState：
1. Playwright StorageState JSON
2. Cookie-Editor 导出的列表
3. 简单键值对 `{"key": "value"}`

## 数据存储

- **目录**: `~/.openclaw/super-fetch/`
- **links.db**: SQLite，存储链接代号映射

## 依赖

```
curl_cffi
playwright
beautifulsoup4
markdownify
playwright_stealth（可选，反爬虫）
```

安装浏览器：
```bash
playwright install chromium
```
