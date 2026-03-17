---
name: super-fetch
description: 高性能网页抓取与正文提取工具。
version: 1.0.0
user-invocable: true
---

# Web Fetch Tool

该技能通过 **文本密度评分算法** 自动提取网页正文，并利用 **SQLite 命名空间系统** 将所有 URL 替换为极简代号（如 `(@x2-1)`），从而在保持网页结构的同时，将 Token 消耗降低 60%-90%。

## 🛠 核心指令集

### 1. `fetch.py` (获取与智能解析)
**基本语法**：
```bash
python {baseDir}/fetch.py "<URL>" [参数]
```
- **默认 (SMART 模式)**：自动识别正文，剔除导航、侧边栏、广告。
- `--full`, `-f`: **全量模式**。当默认模式丢失了关键信息（如菜单、页脚联系方式）时使用。
- `-e playwright`: 浏览器模式。用于绕过 Cloudflare 或抓取动态渲染页面。
- `-w <seconds>`: Playwright 渲染等待时间（默认 3s）。
- `-s <session.json>`: 加载/保存会话 Cookie。
- `--login`: **交互式登录**。告知用户需手动操作浏览器。

### 2. `get_link.py` (反查与内存清理)
**基本语法**：
```bash
# 反查链接 (支持多个)
python {baseDir}/get_link.py <ID1> <ID2>

# 清理指定命名空间的内存 (推荐)
python {baseDir}/get_link.py --clear <namespace>
```

## 🔄 Agent 标准操作流 (SOP)

### 步骤 1：探测与获取
- **优先**执行：`python {baseDir}/fetch.py "<URL>"`。
- **观察逻辑**：
  - 若内容完整且干净 -> 继续分析。
  - 若提示 403 或内容为空 -> 重试并改用 `-e playwright`。
  - 若正文部分被误删 -> 重试并改用 `--full` 参数。

### 步骤 2：处理链接代号
- 在抓取结果中，你会看到 `[文本](@ns-1)` 形式的链接。
- **Token 准则**：不要反查所有链接。只有当你决定跳转到该 URL 或用户明确询问链接时，才执行 `get_link.py`。

### 步骤 3：命名空间清理 (必做)
- 每次抓取都会生成一个 2 字符的命名空间（显示在输出结果的 `[Info]` 中，如 `x2`）。
- **清理逻辑**：一旦你完成了对该页面的分析且不再需要点击其中的链接，**必须**执行 `python {baseDir}/get_link.py --clear <ns>` 来释放数据库空间并保持上下文整洁。

## 💡 决策指南

| 场景 | 推荐引擎 | 模式参数 |
| :--- | :--- | :--- |
| 阅读博客、新闻、技术文档 | `cffi` (默认) | 默认 (Smart) |
| 获取官网联系方式、全站导航 | `cffi` | `--full` |
| 遇到 "Just a moment..." (CF) | `playwright` | 默认 (Smart) |
| 需要登录才能查看的内容 | `playwright` | `--login -s session.json` |

## ⚠️ 安全与注意事项
- **URL 格式**：确保 URL 包含 `http://` 或 `https://`。
- **并发处理**：本工具支持并发。请务必使用 **指定命名空间清理**（如 `--clear k9`）而非全局清理，以防误删其它任务的链接。
- **截断处理**：若页面超长，输出会被自动截断。此时请告知用户并建议通过更具体的 URL 抓取子页面。

---
**提示**：本工具通过 `{baseDir}/links.db` 维护映射，链接记录将在 3 天后自动过期。
```

### 为什么这个 `SKILL.md` 符合最佳实践？

1.  **YAML 元数据**：包含了 `name` 和 `description`，这能让 Claude 在面对多个技能时，一眼识别出这是处理网页的最佳工具。
2.  **{baseDir} 占位符**：符合 OpenClaw 规范，Agent 会自动将其替换为脚本所在的绝对路径，避免路径报错。
3.  **显式的 SOP**：Agent 非常擅长遵循步骤。将“抓取 -> 反查 -> 清理”作为标准流程写进去，可以显著降低 Agent 出错的概率（比如它之前可能会忘了清理数据库）。
4.  **Token 意识**：专门强调了“不要反查所有链接”，这直接对齐了 LLM 使用成本优化的核心痛点。
5.  **故障排除 (Troubleshooting)**：明确告知了何时切换 `playwright` 和 `--full`，让 Agent 具备自愈能力。