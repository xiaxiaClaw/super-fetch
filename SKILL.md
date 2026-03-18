---
name: super-fetch
description: 高性能网页抓取工具，将网页转换为干净的 Markdown。支持 JavaScript 渲染、会话保持、登录态保存。跨平台 Windows/macOS/Linux。
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
```

## 会话规则

| 命令                                  | 说明                                |
| ------------------------------------- | ----------------------------------- |
| `python fetch.py <url>`               | 独立会话，无状态                    |
| `python fetch.py <url> -s`            | 使用默认会话 `session.json`         |
| `python fetch.py <url> -s my.json`    | 使用指定会话 `my.json`              |
| `python fetch.py <url> -i`            | 交互模式，自动保存到 `session.json` |
| `python fetch.py <url> -i -s my.json` | 交互模式，保存到指定会话            |

## 引擎选择

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

## SOP：登录/验证码处理

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

**注意事项：**

- 会话文件包含敏感 Cookie，请勿提交到 Git
- 定期重新登录，Cookie 可能过期
- 不同网站使用不同的会话文件，避免 Cookie 污染

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

## 链接反查与数据库清理

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

| 参数            | 简写 | 默认         | 说明                                          |
| --------------- | ---- | ------------ | --------------------------------------------- |
| `--engine`      | `-e` | `playwright` | 抓取引擎：`playwright`（默认）/ `cffi`        |
| `--interactive` | `-i` | false        | 交互模式，弹出浏览器                          |
| `--full`        | `-f` | false        | 全量提取，不过滤                              |
| `--session`     | `-s` | -            | 会话文件：无参用 `session.json`，或指定文件名 |
| `--wait`        | `-w` | 3            | 渲染等待秒数                                  |
| `--max-chars`   | `-m` | 50000        | 最大输出字符                                  |
| `--proxy`       | `-p` | -            | 代理地址                                      |
| `--retries`     | `-r` | 2            | 重试次数                                      |
| `--output`      | `-o` | -            | 保存二进制文件                                |

## 数据存储

- **目录**: `~/.openclaw/super-fetch/`（Windows: `%USERPROFILE%\.openclaw\super-fetch\`）
- `links.db` - 链接代号映射
- `*.json` - 会话文件
