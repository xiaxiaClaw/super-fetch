#!/usr/bin/env python3
"""
Web Fetch Tool - SPEED PRO V9 (模块化框架版)
"""

import argparse
import sys
import json
import asyncio
from urllib.parse import urlparse

# 导入拆分后的模块
from fetch_engines import fetch_target
from fetch_parser import extract_page_content

def main():
    parser = argparse.ArgumentParser(description="Web Fetch Tool - 模块化框架版")
    parser.add_argument("url", help="目标 URL")
    parser.add_argument("--engine", "-e", type=str, choices=['cffi', 'playwright'], default='cffi', help="抓取引擎 (cffi / playwright)")
    parser.add_argument("--max-chars", "-m", type=int, default=50000, help="最大字符数")
    parser.add_argument("--output", "-o", help="输出到 TXT/MD 文件")
    parser.add_argument("--retries", "-r", type=int, default=2, help="重试次数")
    parser.add_argument("--proxy", "-p", help="代理 (如 http://127.0.0.1:7890)")
    
    # 状态持久化核心参数
    parser.add_argument("--session", "-s", type=str, help="持久化会话文件路径 (保存/加载 Cookie 及登录状态)")
    parser.add_argument("--login", action="store_true", help="交互式登录模式 (注入悬浮按钮，无限期等待用户操作)")
    
    args = parser.parse_args()
    
    if not urlparse(args.url).scheme:
        print(json.dumps({"error": "无效的 URL，需包含 http/https"}, ensure_ascii=False))
        sys.exit(1)

    if args.login and args.engine != 'playwright':
        print("[!] 提示: --login 模式必须依赖 '--engine playwright'，已自动为您切换。", file=sys.stderr)
        args.engine = 'playwright'
        
    print(f"[*] ⚡ 启动获取: {args.url} [引擎: {args.engine.upper()}]", file=sys.stderr, flush=True)
    
    # 1. 引擎网络请求
    html = asyncio.run(fetch_target(args.url, args.engine, args.proxy, args.retries, args.session, args.login))
    
    if html.startswith('{"error"'):
        print(html)
        sys.exit(1)
        
    if args.login:
        print("[*] ✅ 交互式登录采集完毕。后续抓取请携带 '--session' 参数，无需再加 '--login'。", file=sys.stderr)
        sys.exit(0)
        
    # 2. 页面清洗与解析
    print("[*] 📝 提取页面内容...", file=sys.stderr)
    title, markdown = extract_page_content(html, args.url)
    
    final_output = f"# {title}\n\n{markdown}" if title else markdown
    if len(final_output) > args.max_chars:
        final_output = final_output[:args.max_chars] + "\n\n... [达到字数上限，自动截断]"

    # 3. 数据输出
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(final_output)
        print(f"[+] 📄 成功保存至: {args.output}", file=sys.stderr, flush=True)
    else:
        print(final_output)

if __name__ == "__main__":
    main()