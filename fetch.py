#!/usr/bin/env python3
import argparse
import sys
import json
import asyncio
import os
from urllib.parse import urlparse

from fetch_engines import fetch_target
from fetch_parser import extract_page_content


def get_data_dir():
    """跨平台获取数据目录"""
    home = os.path.expanduser("~")
    return os.path.join(home, ".openclaw", "super-fetch")


# 统一数据根目录
DATA_DIR = get_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)


def resolve_session_path(session_arg):
    if not session_arg:
        return None
    # 如果是绝对路径或当前路径已存在该文件，直接使用
    if os.path.isabs(session_arg) or os.path.exists(session_arg):
        return session_arg
    # 否则，强制定位到数据目录下
    return os.path.join(DATA_DIR, session_arg)


def setup_asyncio():
    """跨平台设置 asyncio 事件循环"""
    if sys.platform == "win32":
        # Windows 上使用 ProactorEventLoop 以支持 subprocess
        try:
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
        except (AttributeError, NotImplementedError):
            pass


def main():
    setup_asyncio()

    parser = argparse.ArgumentParser(description="Super Fetch - 高性能抓取基座")
    parser.add_argument("url", help="目标 URL")
    parser.add_argument(
        "--engine",
        "-e",
        choices=["cffi", "playwright"],
        default="playwright",
        help="抓取引擎：playwright（默认）/ cffi（仅用于下载文件或简单静态页）",
    )
    parser.add_argument("--interactive", "-i", action="store_true", help="人工干预模式")
    parser.add_argument("--full", "-f", action="store_true", help="全量模式")
    parser.add_argument(
        "--session",
        "-s",
        nargs="?",
        const="session.json",
        help="Session 文件名：无参用 session.json，或指定文件名",
    )
    parser.add_argument("--wait", "-w", type=int, default=3, help="渲染等待秒数")
    parser.add_argument(
        "--max-chars", "-m", type=int, default=50000, help="最大输出字符数"
    )
    parser.add_argument("--proxy", "-p", help="代理设置")
    parser.add_argument("--retries", "-r", type=int, default=2, help="失败重试次数")
    parser.add_argument("--output", "-o", help="输出二进制文件路径")

    args = parser.parse_args()

    if not urlparse(args.url).scheme:
        print(json.dumps({"error": "无效的 URL"}, ensure_ascii=False))
        sys.exit(1)

    # 交互模式逻辑锚点：-i 自动强制开启 playwright，且默认使用 session.json（如果未指定）
    if args.interactive:
        args.engine = "playwright"
        if args.session is None:
            args.session = "session.json"

    # 路径解析
    session_path = resolve_session_path(args.session) if args.session else None

    print(f"[*] 🚀 任务启动: {args.url}", file=sys.stderr)
    if session_path:
        print(f"[*] 🎫 使用会话: {session_path}", file=sys.stderr)

    try:
        # 增加 timeout 参数确保 LLM 调用不会无限期挂起
        result = asyncio.run(
            fetch_target(
                args.url,
                args.engine,
                args.proxy,
                args.retries,
                session_path,
                args.interactive,
                args.wait,
                30,
            )
        )
        # 解构返回的元组 (content, content_type)
        html, content_type = (
            result if isinstance(result, tuple) else (result, "text/html")
        )
    except Exception as e:
        print(json.dumps({"error": f"运行异常: {str(e)}"}, ensure_ascii=False))
        sys.exit(1)

    # 二进制处理：处理图片、PDF 等非 HTML 资源
    if content_type:
        binary_types = (
            "application/pdf",
            "image/",
            "audio/",
            "video/",
            "application/zip",
        )
        if any(content_type.startswith(bt) for bt in binary_types):
            if args.output:
                with open(args.output, "wb" if isinstance(html, bytes) else "w") as f:
                    f.write(html)
                print(f"[*] ✅ 文件已保存: {args.output}", file=sys.stderr)
                sys.exit(0)
            else:
                print(
                    json.dumps(
                        {"error": f"二进制内容 ({content_type}) 需 -o 参数"},
                        ensure_ascii=False,
                    )
                )
                sys.exit(1)

    # HTML 转码与错误检查
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="ignore")

    if isinstance(html, str) and html.startswith('{"error"'):
        print(html)
        sys.exit(1)

    print(f"[*] 📝 提取内容...", file=sys.stderr)
    title, markdown, ns = extract_page_content(html, args.url, full_mode=args.full)

    # 结构化输出
    header = f"# {title}\n" if title else ""
    session_info = os.path.basename(session_path) if session_path else "无"
    meta = f"> [系统提示] 命名空间: {ns} | 会话: {session_info}\n\n"

    final_output = (header + meta + markdown)[: args.max_chars]
    print(final_output)


if __name__ == "__main__":
    main()
