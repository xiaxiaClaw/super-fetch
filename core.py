#!/usr/bin/env python3
"""
Super Fetch Core - 共享工具模块
统一存放跨文件使用的常量、工具函数和配置
"""
import sys
import os
import asyncio


def get_data_dir():
    """跨平台获取数据目录"""
    home = os.path.expanduser("~")
    return os.path.join(home, ".openclaw", "super-fetch")


# 统一数据根目录
DATA_DIR = get_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)

# 数据库路径
DB_PATH = os.path.join(DATA_DIR, "links.db")


def resolve_session_path(session_arg):
    """解析会话文件路径"""
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


# 真实浏览器请求头
REAL_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]
