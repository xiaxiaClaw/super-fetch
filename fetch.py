#!/usr/bin/env python3
"""
Super Fetch - 网页抓取基座 PRO
"""

import argparse
import sys
import json
import asyncio
import os
from urllib.parse import urlparse

# 导入核心模块
from fetch_engines import fetch_target
from fetch_parser import extract_page_content

# 获取脚本所在目录作为基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SESSION = os.path.join(BASE_DIR, "session.json")

def main():
    parser = argparse.ArgumentParser(description="Super Fetch - 高性能抓取基座")
    parser.add_argument("url", help="目标 URL")
    parser.add_argument("--engine", "-e", choices=['cffi', 'playwright'], default='cffi', help="抓取引擎")
    parser.add_argument("--interactive", "-i", action="store_true", help="人工干预模式（处理验证码、滑块或手动登录）")
    parser.add_argument("--full", "-f", action="store_true", help="全量模式（关闭智能正文精简，保留页面全部文本）")
    parser.add_argument("--session", "-s", default=DEFAULT_SESSION, help=f"Session 文件路径 (默认: {DEFAULT_SESSION})")
    parser.add_argument("--wait", "-w", type=int, default=3, help="Playwright 渲染额外等待秒数")
    parser.add_argument("--max-chars", "-m", type=int, default=50000, help="最大输出字符数")
    parser.add_argument("--proxy", "-p", help="代理设置 (如 http://127.0.0.1:7890)")
    parser.add_argument("--retries", "-r", type=int, default=2, help="失败重试次数")
    
    args = parser.parse_args()
    
    # 校验 URL
    if not urlparse(args.url).scheme:
        print(json.dumps({"error": "无效的 URL，必须包含 http/https 协议"}, ensure_ascii=False))
        sys.exit(1)

    # 交互模式强制开启 Playwright
    if args.interactive:
        args.engine = 'playwright'
        
    mode_tag = "FULL" if args.full else "SMART"
    print(f"[*] 🚀 任务启动: {args.url}", file=sys.stderr)
    print(f"[*] ⚙️ 配置: 引擎={args.engine.upper()}, 模式={mode_tag}, Session={os.path.basename(args.session)}", file=sys.stderr)
    
    # 1. 执行网络抓取
    try:
        html = asyncio.run(fetch_target(
            args.url, 
            args.engine, 
            args.proxy, 
            args.retries, 
            args.session, 
            args.interactive, 
            args.wait,
            30  # timeout
        ))
    except Exception as e:
        print(json.dumps({"error": f"系统发生未捕获异常: {str(e)}"}, ensure_ascii=False))
        sys.exit(1)
    
    if html.startswith('{"error"'):
        print(html)
        sys.exit(1)
        
    if args.interactive:
        print("[*] ✅ 人工交互流程圆满结束，状态已同步。", file=sys.stderr)
        sys.exit(0)
        
    # 2. 内容解析与精简
    print(f"[*] 📝 正在解析并提取内容...", file=sys.stderr)
    title, markdown, ns = extract_page_content(html, args.url, full_mode=args.full)
    
    # 3. 构建最终输出
    header = f"# {title}\n" if title else ""
    meta = f"> [系统提示] 命名空间: {ns} | 模式: {'全量提取' if args.full else '智能精简'} | 会话: {os.path.basename(args.session)}\n\n"
    
    final_output = header + meta + markdown
    
    # 字符截断逻辑
    if len(final_output) > args.max_chars:
        final_output = final_output[:args.max_chars] + "\n\n... [警告：内容过长，已执行自动截断]"

    # 输出结果
    print(final_output)

if __name__ == "__main__":
    main()