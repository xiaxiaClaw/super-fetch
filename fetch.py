#!/usr/bin/env python3
import argparse
import sys
import json
import asyncio
from urllib.parse import urlparse
from fetch_engines import fetch_target
from fetch_parser import extract_page_content

def main():
    parser = argparse.ArgumentParser(description="Web Fetch Tool - SPEED PRO V10")
    parser.add_argument("url", help="目标 URL")
    parser.add_argument("--engine", "-e", type=str, choices=['cffi', 'playwright'], default='cffi')
    parser.add_argument("--wait", "-w", type=int, default=3)
    parser.add_argument("--full", "-f", action="store_true", help="全量模式：不进行智能评分，抓取 body 全文本")
    parser.add_argument("--max-chars", "-m", type=int, default=50000)
    parser.add_argument("--output", "-o", help="输出路径")
    parser.add_argument("--retries", "-r", type=int, default=2)
    parser.add_argument("--proxy", "-p")
    parser.add_argument("--session", "-s", type=str)
    parser.add_argument("--login", action="store_true")
    
    args = parser.parse_args()
    if not urlparse(args.url).scheme:
        print(json.dumps({"error": "URL 必须包含协议 http/https"}, ensure_ascii=False))
        sys.exit(1)

    if args.login: args.engine = 'playwright'
        
    print(f"[*] ⚡ 获取: {args.url} (模式: {'FULL' if args.full else 'SMART'})", file=sys.stderr)
    
    try:
        html = asyncio.run(fetch_target(args.url, args.engine, args.proxy, args.retries, args.session, args.login, args.wait))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    
    if html.startswith('{"error"'):
        print(html); sys.exit(1)
        
    if args.login:
        print("[*] ✅ 登录操作流结束。", file=sys.stderr); sys.exit(0)
        
    title, markdown, ns = extract_page_content(html, args.url, full_mode=args.full)
    
    header = f"# {title}\n" if title else ""
    meta = f"> [Info] 命名空间: {ns} | 模式: {'全量' if args.full else '智能精简'}\n\n"
    
    final_output = header + meta + markdown
    if len(final_output) > args.max_chars:
        final_output = final_output[:args.max_chars] + "\n\n... [已截断]"

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f: f.write(final_output)
    else:
        print(final_output)

if __name__ == "__main__":
    main()