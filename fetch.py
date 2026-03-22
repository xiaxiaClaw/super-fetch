#!/usr/bin/env python3
import argparse
import sys
import json
import asyncio
import os
import random
import time
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import List, Optional, Dict

from core import (
    get_data_dir,
    DATA_DIR,
    resolve_session_path,
    setup_asyncio,
    USER_AGENTS,
)
from fetch_engines import (
    fetch_target,
    fetch_with_curl_cffi,
    PlaywrightPool,
)
from fetch_parser import extract_page_content


@dataclass
class FetchResult:
    """单个抓取结果"""
    url: str
    success: bool
    title: str = ""
    markdown: str = ""
    namespace: str = ""
    error: str = ""


class DomainRateLimiter:
    """域名级别的速率限制器 - 防止对同一域名请求过快"""

    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_fetch_time: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, domain: str):
        """等待直到可以安全请求该域名"""
        async with self._lock:
            now = time.time()
            last_time = self.last_fetch_time.get(domain, 0)
            delay = random.uniform(self.min_delay, self.max_delay)
            elapsed = now - last_time

            if elapsed < delay:
                wait_time = delay - elapsed
                self.last_fetch_time[domain] = now + wait_time
                return wait_time
            else:
                self.last_fetch_time[domain] = now
                return 0


class BatchFetcher:
    """批量抓取器 - 支持 cffi 和 playwright 两种引擎的并发"""

    def __init__(
        self,
        concurrency: int = 5,
        domain_min_delay: float = 2.0,
        domain_max_delay: float = 5.0,
        global_jitter: float = 0.5,
    ):
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self.rate_limiter = DomainRateLimiter(domain_min_delay, domain_max_delay)
        self.global_jitter = global_jitter

    def get_random_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    async def _rate_limit_wait(self, url: str, silent: bool = False):
        """统一的速率限制等待"""
        domain = urlparse(url).netloc

        wait_time = await self.rate_limiter.wait(domain)
        if wait_time > 0 and not silent:
            print(f"[*] ⏳ 对 {domain} 限流，等待 {wait_time:.2f}s: {url}", file=sys.stderr)
            await asyncio.sleep(wait_time)

        if self.global_jitter > 0:
            await asyncio.sleep(random.uniform(0, self.global_jitter))

    async def _parse_html(self, html, content_type, url, full_mode) -> FetchResult:
        """解析 HTML 为 Markdown"""
        if content_type and any(
            content_type.startswith(bt)
            for bt in ["application/pdf", "image/", "audio/", "video/", "application/zip"]
        ):
            return FetchResult(
                url=url,
                success=False,
                error=f"不支持的二进制内容: {content_type}",
            )

        if isinstance(html, bytes):
            html = html.decode("utf-8", errors="ignore")

        if isinstance(html, str) and html.startswith('{"error"'):
            err_data = json.loads(html)
            return FetchResult(
                url=url,
                success=False,
                error=err_data.get("error", "未知错误"),
            )

        title, markdown, ns = extract_page_content(html, url, full_mode=full_mode)
        return FetchResult(
            url=url,
            success=True,
            title=title,
            markdown=markdown,
            namespace=ns,
        )

    async def fetch_cffi(
        self,
        url: str,
        proxy: Optional[str],
        timeout: int,
        session_path: Optional[str],
        wait: int,
        full_mode: bool,
        silent: bool = False,
    ) -> FetchResult:
        """使用 cffi 引擎抓取单个 URL"""
        await self._rate_limit_wait(url, silent)

        async with self.semaphore:
            if not silent:
                print(f"[*] 🚀 [cffi] 开始抓取: {url}", file=sys.stderr)

            try:
                html, content_type = await fetch_with_curl_cffi(
                    url, proxy, timeout, session_path
                )

                result = await self._parse_html(html, content_type, url, full_mode)

                if result.success and not silent:
                    print(f"[*] ✅ [cffi] 抓取完成: {url}", file=sys.stderr)
                elif not silent:
                    print(f"[*] ❌ [cffi] 抓取失败: {url} - {result.error}", file=sys.stderr)

                return result

            except Exception as e:
                if not silent:
                    print(f"[*] ❌ [cffi] 抓取异常: {url} - {e}", file=sys.stderr)
                return FetchResult(url=url, success=False, error=str(e))

    async def fetch_all_cffi(
        self,
        urls: List[str],
        proxy: Optional[str],
        retries: int,
        session_path: Optional[str],
        wait: int,
        full_mode: bool,
        silent: bool = False,
    ) -> List[FetchResult]:
        """cffi 引擎批量抓取 - 使用 AsyncSession 原生并发"""

        async def fetch_with_retry(url: str) -> FetchResult:
            last_error = None
            for i in range(retries):
                result = await self.fetch_cffi(
                    url, proxy, 30, session_path, wait, full_mode, silent
                )
                if result.success:
                    return result
                last_error = result.error
                if i < retries - 1:
                    await asyncio.sleep(1)
            return FetchResult(url=url, success=False, error=last_error or "未知错误")

        tasks = [fetch_with_retry(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 处理异常：把抛出的异常转为 FetchResult
        processed = []
        for r in results:
            if isinstance(r, Exception):
                processed.append(FetchResult(url="", success=False, error=str(r)))
            else:
                processed.append(r)
        return processed

    async def fetch_all_playwright(
        self,
        urls: List[str],
        proxy: Optional[str],
        retries: int,
        session_path: Optional[str],
        wait: int,
        full_mode: bool,
        silent: bool = False,
    ) -> List[FetchResult]:
        """playwright 引擎批量抓取 - 使用 PlaywrightPool 复用 Browser"""

        results: List[FetchResult] = []

        async with PlaywrightPool(
            proxy=proxy,
            pool_size=self.concurrency,
            headless=True,
            user_agent=self.get_random_user_agent(),
        ) as pool:

            async def fetch_with_retry(url: str) -> FetchResult:
                await self._rate_limit_wait(url, silent)

                last_error = None
                for i in range(retries):
                    if not silent:
                        print(f"[*] 🚀 [playwright] 开始抓取: {url}", file=sys.stderr)

                    try:
                        html, content_type = await pool.fetch_page(
                            url, 30, session_path, wait
                        )
                        result = await self._parse_html(html, content_type, url, full_mode)

                        if result.success:
                            if not silent:
                                print(f"[*] ✅ [playwright] 抓取完成: {url}", file=sys.stderr)
                            return result
                        last_error = result.error

                    except Exception as e:
                        last_error = str(e)
                        if not silent:
                            print(f"[*] ❌ [playwright] 异常: {url} - {e}", file=sys.stderr)

                    if i < retries - 1:
                        await asyncio.sleep(1)

                return FetchResult(url=url, success=False, error=last_error or "未知错误")

            results = await asyncio.gather(*[fetch_with_retry(url) for url in urls], return_exceptions=True)
            # 处理异常：把抛出的异常转为 FetchResult
            processed = []
            for r in results:
                if isinstance(r, Exception):
                    processed.append(FetchResult(url="", success=False, error=str(r)))
                else:
                    processed.append(r)
            return processed

    async def fetch_all(
        self,
        urls: List[str],
        engine: str = "playwright",
        proxy: Optional[str] = None,
        retries: int = 0,
        session_path: Optional[str] = None,
        wait: int = 2,
        full_mode: bool = False,
        silent: bool = False,
    ) -> List[FetchResult]:
        """统一入口 - 根据引擎选择并发策略"""
        if engine == "playwright":
            return await self.fetch_all_playwright(
                urls, proxy, retries, session_path, wait, full_mode, silent
            )
        else:
            return await self.fetch_all_cffi(
                urls, proxy, retries, session_path, wait, full_mode, silent
            )


def read_urls_from_file(filepath: str) -> List[str]:
    """从文件读取 URL 列表（每行一个 URL）"""
    urls = []
    if not os.path.exists(filepath):
        return urls
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


async def run_single_fetch(args, session_path):
    """单 URL 抓取模式"""
    print(f"[*] 🚀 任务启动: {args.url}", file=sys.stderr)
    if session_path:
        print(f"[*] 🎫 使用会话: {session_path}", file=sys.stderr)

    try:
        result = await fetch_target(
            args.url,
            args.engine,
            args.proxy,
            args.retries,
            session_path,
            args.interactive,
            args.wait,
            30,
        )
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


async def run_batch_fetch(args, session_path):
    """批量并发抓取模式"""
    # 收集 URL
    urls = list(args.urls) if args.urls else []
    if args.file:
        urls.extend(read_urls_from_file(args.file))

    # 去重
    urls = list(dict.fromkeys(urls))

    if not urls:
        print(json.dumps({"error": "请提供 URL（参数或 -F 文件）"}, ensure_ascii=False))
        sys.exit(1)

    # 验证 URL
    valid_urls = []
    for url in urls:
        if urlparse(url).scheme:
            valid_urls.append(url)
        elif not args.silent:
            print(f"[*] ⚠️ 跳过无效 URL: {url}", file=sys.stderr)

    if not valid_urls:
        print(json.dumps({"error": "没有有效的 URL"}, ensure_ascii=False))
        sys.exit(1)

    if not args.silent:
        print(f"[*] 📋 批量抓取任务启动", file=sys.stderr)
        print(f"[*] 🔗 URL 数量: {len(valid_urls)}", file=sys.stderr)
        print(f"[*] 🚦 并发数: {args.concurrency}", file=sys.stderr)
        print(f"[*] 🔧 引擎: {args.engine}", file=sys.stderr)
        print(f"[*] ⏱️  域名间隔: {args.domain_delay_min}-{args.domain_delay_max}s", file=sys.stderr)
        if session_path:
            print(f"[*] 🎫 使用会话: {session_path}", file=sys.stderr)

    # 执行抓取
    fetcher = BatchFetcher(
        concurrency=args.concurrency,
        domain_min_delay=args.domain_delay_min,
        domain_max_delay=args.domain_delay_max,
        global_jitter=args.jitter,
    )

    results = await fetcher.fetch_all(
        valid_urls,
        engine=args.engine,
        proxy=args.proxy,
        retries=args.retries,
        session_path=session_path,
        wait=args.wait,
        full_mode=args.full,
        silent=args.silent,
    )

    # 格式化输出
    output = {
        "total": len(results),
        "success": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "results": [
            {
                "url": r.url,
                "success": r.success,
                "title": r.title,
                "content": r.markdown,
                "namespace": r.namespace,
                "error": r.error,
            }
            for r in results
        ],
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        if not args.silent:
            print(f"[*] 💾 结果已保存到: {args.output}", file=sys.stderr)
    else:
        print(json.dumps(output, ensure_ascii=False))

    # 统计输出
    if not args.silent:
        print(f"\n[*] 📊 完成统计:", file=sys.stderr)
        print(f"[*]   总计: {output['total']}", file=sys.stderr)
        print(f"[*]   成功: {output['success']} ✅", file=sys.stderr)
        print(f"[*]   失败: {output['failed']} ❌", file=sys.stderr)


def main():
    setup_asyncio()

    parser = argparse.ArgumentParser(description="Super Fetch - 高性能抓取基座")

    # 通用参数
    parser.add_argument(
        "--engine",
        "-e",
        choices=["cffi", "playwright"],
        default="playwright",
        help="抓取引擎：playwright（默认）/ cffi",
    )
    parser.add_argument("--full", "-f", action="store_true", help="全量模式")
    parser.add_argument(
        "--session",
        "-s",
        nargs="?",
        const="session.json",
        help="Session 文件名：无参用 session.json，或指定文件名",
    )
    parser.add_argument("--wait", "-w", type=int, default=None, help="渲染等待秒数")
    parser.add_argument("--proxy", "-p", help="代理设置")
    parser.add_argument("--retries", "-r", type=int, default=0, help="失败重试次数")
    parser.add_argument("--output", "-o", help="输出文件路径（批量模式为 JSON，单 URL 为二进制）")

    # 单 URL 模式参数
    single_group = parser.add_argument_group("单 URL 模式")
    single_group.add_argument("url", nargs="?", help="目标 URL（单 URL 模式）")
    single_group.add_argument("--interactive", "-i", action="store_true", help="人工干预模式（仅单 URL）")
    single_group.add_argument("--max-chars", "-m", type=int, default=50000, help="最大输出字符数（仅单 URL）")

    # 批量模式参数
    batch_group = parser.add_argument_group("批量并发模式（使用 -F 或传入多个 URL 触发）")
    batch_group.add_argument("urls", nargs="*", help="目标 URL 列表（批量模式）", metavar="URL")
    batch_group.add_argument("--file", "-F", help="从文件读取 URL 列表（每行一个）")
    batch_group.add_argument("--concurrency", "-c", type=int, default=5, help="最大并发数（默认 5）")
    batch_group.add_argument("--domain-delay-min", type=float, default=2.0, help="同一域名最小请求间隔（秒）")
    batch_group.add_argument("--domain-delay-max", type=float, default=5.0, help="同一域名最大请求间隔（秒）")
    batch_group.add_argument("--jitter", type=float, default=0.5, help="全局随机抖动上限（秒）")
    batch_group.add_argument("--silent", action="store_true", help="静默模式，只输出最终 JSON")

    args = parser.parse_args()

    # 判断是否为批量模式：有 -F 或 urls 不为空
    is_batch_mode = args.file is not None or (args.urls and len(args.urls) > 0)

    # 设置默认值
    if args.wait is None:
        args.wait = 3

    session_path = resolve_session_path(args.session) if args.session else None

    # 交互模式检查
    if args.interactive and is_batch_mode:
        print(json.dumps({"error": "批量模式不支持交互模式 (-i)"}, ensure_ascii=False))
        sys.exit(1)

    # 交互模式逻辑锚点：-i 自动强制开启 playwright，且默认使用 session.json（如果未指定）
    if args.interactive:
        args.engine = "playwright"
        if args.session is None:
            args.session = "session.json"
            session_path = resolve_session_path(args.session)

    if is_batch_mode:
        asyncio.run(run_batch_fetch(args, session_path))
    else:
        # 单 URL 模式：检查 url 参数
        if not args.url:
            parser.print_help()
            print("\n错误：请提供 URL（单 URL 模式）或使用 -F/传入多个 URL（批量模式）", file=sys.stderr)
            sys.exit(1)
        if not urlparse(args.url).scheme:
            print(json.dumps({"error": "无效的 URL"}, ensure_ascii=False))
            sys.exit(1)
        asyncio.run(run_single_fetch(args, session_path))


if __name__ == "__main__":
    main()
