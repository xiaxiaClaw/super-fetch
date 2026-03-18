import sys
import os
import json
import asyncio
from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright

try:
    import playwright_stealth
except ImportError:
    playwright_stealth = None

REAL_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def format_session_data(session_file: str, target_url: str = "") -> dict:
    """读取并统一格式化 session 为 Playwright 格式，支持 Cookie-Editor 导出文件和旧版扁平字典"""
    default_state = {"cookies": [], "origins":[]}
    if not session_file or not os.path.exists(session_file):
        return default_state

    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. 如果已经是 Playwright 原生格式，直接返回
        if isinstance(data, dict) and "cookies" in data:
            return data

        pw_state = {"cookies": [], "origins":[]}

        # 2. 如果是 Cookie-Editor 导出的格式 (JSON Array)
        if isinstance(data, list):
            print(f"[*] 🍪 检测到 Cookie-Editor 导出格式，正在自动转换为标准格式...", file=sys.stderr)
            for c in data:
                same_site = str(c.get("sameSite", "Lax")).capitalize()
                if same_site in ["No_restriction", "None"]: same_site = "None"
                elif same_site == "Unspecified": same_site = "Lax"
                if same_site not in["Strict", "Lax", "None"]: same_site = "Lax"

                pw_state["cookies"].append({
                    "name": c.get("name", ""),
                    "value": c.get("value", ""),
                    "domain": c.get("domain", ""),
                    "path": c.get("path", "/"),
                    "expires": c.get("expirationDate", -1), 
                    "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", False),
                    "sameSite": same_site
                })
        
        # 3. 如果是旧版扁平字典 {"cookie_name": "cookie_value"}
        elif isinstance(data, dict):
            print(f"[*] 🍪 检测到旧版扁平 Cookie 格式，正在自动转换为标准格式...", file=sys.stderr)
            target_domain = urlparse(target_url).netloc if target_url else ""
            for k, v in data.items():
                pw_state["cookies"].append({
                    "name": k, "value": v, "domain": target_domain,
                    "path": "/", "expires": -1, "httpOnly": False,
                    "secure": False, "sameSite": "Lax"
                })
        else:
            return default_state

        # 将转换后的标准格式覆盖写入原文件
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(pw_state, f, indent=2, ensure_ascii=False)

        return pw_state
    except Exception as e:
        print(f"[!] Session 文件读取或转换失败: {e}", file=sys.stderr)
        return default_state


async def fetch_with_curl_cffi(url: str, proxy: str = None, timeout: int = 15, session_file: str = None) -> str:
    """CFFI 引擎：极速请求，支持与 Playwright 格式互通的 Session 持久化"""
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    pw_state = {"cookies": [], "origins":[]}
    cffi_cookies = {} 
    
    if session_file and os.path.exists(session_file):
        pw_state = format_session_data(session_file, url)
        for c in pw_state.get("cookies",[]):
            cffi_cookies[c["name"]] = c["value"]
        if cffi_cookies:
            print(f"[*] 🍪 成功加载并应用 Session 凭证: {os.path.basename(session_file)}", file=sys.stderr)

    async with AsyncSession(impersonate="chrome120", proxies=proxies, timeout=timeout, headers=REAL_HEADERS, cookies=cffi_cookies) as session:
        response = await session.get(url)
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type.startswith("text/") or content_type in ("application/json", "application/xml", "application/javascript"):
            content = response.text
        else:
            content = response.content
        
        # 将 CFFI 产生的新 Cookie 规范化并合并回 Playwright 格式
        if session_file:
            try:
                new_cookies_map = {}
                target_domain = urlparse(url).netloc
                
                # 获取 session 产生的最新 cookies
                actual_cookies = session.cookies.get_dict()
                for k, v in actual_cookies.items():
                    # 简化逻辑：以 name 为核心， domain 默认为当前请求域名
                    new_cookies_map[k] = {
                        "name": k, "value": v, "domain": target_domain,
                        "path": "/", "expires": -1, "httpOnly": False,
                        "secure": False, "sameSite": "Lax"
                    }

                # 合并逻辑：如果旧 cookie 列表中有同名项，则更新它，否则保留旧项，最后加入新项
                merged_dict = {c["name"]: c for c in pw_state.get("cookies", [])}
                merged_dict.update(new_cookies_map)
                
                pw_state["cookies"] = list(merged_dict.values())

                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(pw_state, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[!] 保存 Cookie 状态失败: {e}", file=sys.stderr)
                
        return content, response.headers.get("content-type", "text/html")


async def fetch_with_playwright(url: str, proxy: str = None, timeout: int = 30, session_file: str = None, is_interactive: bool = False, wait: int = 3) -> tuple:
    """Playwright 引擎：全真浏览器，支持人工干预交互与原生会话持久化"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not is_interactive,
            proxy={"server": proxy} if proxy else None,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        context_args = {
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
            "user_agent": REAL_HEADERS["User-Agent"]
        }
        
        if session_file and os.path.exists(session_file):
            pw_state = format_session_data(session_file, url)
            if pw_state and "cookies" in pw_state:
                context_args["storage_state"] = session_file
                print(f"[*] 🎫 注入 Playwright 存储状态: {os.path.basename(session_file)}", file=sys.stderr)
                
        context = await browser.new_context(**context_args)
        
        # 人工干预模式下的 JS 注入逻辑保持不变...
        if is_interactive:
            inject_js = """
            (() => {
                if (window._claw_injected) return;
                window._claw_injected = true;
                const injectBtn = () => {
                    if (document.getElementById('claw-done-btn')) return;
                    const btn = document.createElement('div');
                    btn.id = 'claw-done-btn';
                    btn.innerHTML = '✅ 操作/验证已完成，点击继续';
                    Object.assign(btn.style, {
                        position: 'fixed', zIndex: '2147483647', padding: '15px 25px',
                        background: '#00C853', color: 'white', border: 'none',
                        borderRadius: '8px', fontSize: '16px', fontWeight: 'bold',
                        cursor: 'move', boxShadow: '0 4px 15px rgba(0,0,0,0.4)',
                        userSelect: 'none', transition: 'background 0.2s, transform 0.2s',
                        top: '20px', right: '20px'
                    });
                    btn.onclick = () => { window._fetch_interactive_done = true; btn.innerHTML = '⏳ 正在同步状态...'; btn.style.background = '#FF9800'; };
                    if (document.documentElement) document.documentElement.appendChild(btn);
                };
                setInterval(injectBtn, 1000); 
            })();
            """
            await context.add_init_script(inject_js)
            
        page = await context.new_page()
        
        if playwright_stealth:
            try:
                s_func = getattr(playwright_stealth, 'stealth_async', None) or getattr(playwright_stealth, 'stealth', None)
                if s_func:
                    res = s_func(page)
                    if asyncio.iscoroutine(res): await res
            except Exception: pass
        
        async def route_intercept(route):
            if not is_interactive and route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", route_intercept)
        
        try:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            except Exception:
                print(f"[*] ⚠️ 页面加载较慢，尝试处理已加载的部分...", file=sys.stderr)
            
            await asyncio.sleep(wait)
            
            if is_interactive:
                print(f"\n{'='*60}\n[*] 🛠️ 进入【人工干预模式】！请在弹出窗口操作后点击绿色按钮。\n{'='*60}\n", file=sys.stderr)
                await page.wait_for_function("window._fetch_interactive_done === true", timeout=0)
                await asyncio.sleep(1)
            else:
                try: await page.wait_for_load_state("networkidle", timeout=3000)
                except: pass
                
                content = await page.content()
                if any(cf_kw in content for cf_kw in ["cf-browser-verification", "Just a moment...", "cloudflare"]):
                    print("[*] 🛡️ 触发防爬质询，尝试自动等待绕过...", file=sys.stderr)
                    await asyncio.sleep(5)

            if session_file:
                await context.storage_state(path=session_file)
                # 读取并重新保存一次，确保 ensure_ascii=False
                with open(session_file, 'r', encoding='utf-8') as f:
                    tmp_data = json.load(f)
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(tmp_data, f, indent=2, ensure_ascii=False)
                print(f"[*] 💾 状态已更新至: {os.path.basename(session_file)}", file=sys.stderr)
            
            content = await page.content()
            content_type = await page.evaluate("() => document.contentType || 'text/html'")
            return content, content_type
        finally:
            await browser.close()


async def fetch_target(url: str, engine: str, proxy: str, retries: int, session_file: str, is_interactive: bool, wait: int = 3, timeout: int = 30):
    """引擎调度中心"""
    last_err = ""
    for attempt in range(retries):
        try:
            if engine == 'playwright':
                return await fetch_with_playwright(url, proxy, timeout, session_file, is_interactive, wait)
            else:
                return await fetch_with_curl_cffi(url, proxy, timeout, session_file)
        except Exception as e:
            last_err = str(e)
            print(f"[*] ❌ 引擎 {engine} 失败 (尝试 {attempt+1}/{retries}): {last_err}", file=sys.stderr)
            await asyncio.sleep(1)
            
    # 【关键修复】：增加 ensure_ascii=False，防止错误信息中的中文变成 Unicode 编码
    return json.dumps({"error": f"抓取失败. 最终错误: {last_err}"}, ensure_ascii=False), "text/html"