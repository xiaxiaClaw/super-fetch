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

async def fetch_with_curl_cffi(url: str, proxy: str = None, timeout: int = 15, session_file: str = None) -> str:
    """CFFI 引擎：极速请求，支持与 Playwright 格式互通的 Session 持久化"""
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    # 统一使用 Playwright 兼容的 state 结构
    pw_state = {"cookies": [], "origins": []}
    cffi_cookies = {} 
    
    if session_file and os.path.exists(session_file):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if isinstance(data, dict) and "cookies" in data:
                # 1. Playwright 标准格式
                pw_state = data
                for c in data["cookies"]:
                    cffi_cookies[c["name"]] = c["value"]
                print(f"[*] 🍪 成功加载 Session 凭证: {os.path.basename(session_file)}", file=sys.stderr)
            else:
                # 2. 兼容旧版扁平字典格式并自动升级
                cffi_cookies = data
                target_domain = urlparse(url).netloc
                for k, v in data.items():
                    pw_state["cookies"].append({
                        "name": k, "value": v, "domain": target_domain,
                        "path": "/", "expires": -1, "httpOnly": False,
                        "secure": False, "sameSite": "Lax"
                    })
                print(f"[*] 🍪 加载旧版 Cookie 格式 (已自动执行转换)", file=sys.stderr)
        except Exception as e:
            print(f"[!] 读取 Session 文件失败: {e}", file=sys.stderr)

    async with AsyncSession(impersonate="chrome120", proxies=proxies, timeout=timeout, headers=REAL_HEADERS, cookies=cffi_cookies) as session:
        response = await session.get(url)
        response.raise_for_status()
        
        # 根据 content-type 判断返回内容
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type.startswith("text/") or content_type in ("application/json", "application/xml", "application/javascript"):
            content = response.text
        else:
            # 二进制内容（PDF、图片等）
            content = response.content if hasattr(response, 'content') else response.text.encode() if isinstance(response.text, str) else response.text
        
        # 将 CFFI 产生的新 Cookie 规范化并合并回 Playwright 格式
        if session_file:
            try:
                new_cookies_map = {}
                target_domain = urlparse(url).netloc
                
                # 从 cookiejar 提取完整属性
                if hasattr(session.cookies, 'jar'):
                    for cookie in session.cookies.jar:
                        new_cookies_map[(cookie.name, cookie.domain)] = {
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": cookie.domain or target_domain,
                            "path": cookie.path or "/",
                            "expires": cookie.expires if cookie.expires else -1,
                            "httpOnly": cookie.has_nonstandard_attr('httponly') or cookie.has_nonstandard_attr('HttpOnly') or False,
                            "secure": cookie.secure,
                            "sameSite": "Lax"
                        }
                else:
                    for k, v in session.cookies.get_dict().items():
                        new_cookies_map[(k, target_domain)] = {
                            "name": k, "value": v, "domain": target_domain,
                            "path": "/", "expires": -1, "httpOnly": False,
                            "secure": False, "sameSite": "Lax"
                        }

                # 合并新旧 Cookie
                merged_cookies = []
                for old_c in pw_state["cookies"]:
                    key = (old_c["name"], old_c.get("domain", target_domain))
                    if key in new_cookies_map:
                        merged_cookies.append(new_cookies_map.pop(key))
                    else:
                        merged_cookies.append(old_c)
                        
                merged_cookies.extend(new_cookies_map.values())
                pw_state["cookies"] = merged_cookies

                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(pw_state, f, indent=2)
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
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    check_data = json.load(f)
                if isinstance(check_data, dict) and "cookies" in check_data:
                    context_args["storage_state"] = session_file
                    print(f"[*] 🎫 注入 Playwright 存储状态: {os.path.basename(session_file)}", file=sys.stderr)
                else:
                    print(f"[!] 警告: Session 格式不兼容，将以干净会话启动。", file=sys.stderr)
            except Exception as e:
                print(f"[!] 读取状态文件失败: {e}", file=sys.stderr)
                
        context = await browser.new_context(**context_args)
        
        # 终极版：可拖拽人工干预按钮脚本
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
                        userSelect: 'none', transition: 'background 0.2s, transform 0.2s'
                    });
                    
                    if (window._claw_btn_pos) {
                        btn.style.left = window._claw_btn_pos.left;
                        btn.style.top = window._claw_btn_pos.top;
                    } else {
                        btn.style.top = '20px'; btn.style.right = '20px';
                    }
                    
                    let isDragging = false;
                    let startX, startY, initialLeft, initialTop;
                    
                    btn.onmousedown = (e) => {
                        isDragging = true;
                        startX = e.clientX; startY = e.clientY;
                        const rect = btn.getBoundingClientRect();
                        initialLeft = rect.left; initialTop = rect.top;
                        btn.style.transition = 'none';
                        e.preventDefault();
                    };
                    
                    window.addEventListener('mousemove', (e) => {
                        if (!isDragging) return;
                        let newLeft = initialLeft + (e.clientX - startX);
                        let newTop = initialTop + (e.clientY - startY);
                        btn.style.left = newLeft + 'px';
                        btn.style.top = newTop + 'px';
                        btn.style.right = 'auto';
                        window._claw_btn_pos = { left: btn.style.left, top: btn.style.top };
                    });
                    
                    window.addEventListener('mouseup', () => { isDragging = false; btn.style.transition = 'background 0.2s, transform 0.2s'; });
                    
                    btn.onclick = (e) => {
                        window._fetch_interactive_done = true;
                        btn.innerHTML = '⏳ 正在同步状态...';
                        btn.style.background = '#FF9800';
                    };
                    
                    if (document.documentElement) document.documentElement.appendChild(btn);
                };
                
                document.addEventListener('DOMContentLoaded', injectBtn);
                setInterval(injectBtn, 1000); 
            })();
            """
            await context.add_init_script(inject_js)
            
        page = await context.new_page()
        
        # 应用 Stealth 防止被检测为机器人
        if playwright_stealth:
            try:
                s_func = getattr(playwright_stealth, 'stealth_async', None) or getattr(playwright_stealth, 'stealth', None)
                if s_func:
                    res = s_func(page)
                    if asyncio.iscoroutine(res): await res
            except Exception: pass
        
        # 资源拦截逻辑 (非干预模式下拦截多媒体节省流量/时间)
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
                print(f"\n{'='*60}", file=sys.stderr)
                print(f"[*] 🛠️ 进入【人工干预模式】！", file=sys.stderr)
                print(f"[*] 1. 请在弹出的窗口中自由操作（登录、过验证、点击等）", file=sys.stderr)
                print(f"[*] 2. 完成后，点击页面右上角绿色按钮即可继续", file=sys.stderr)
                print(f"{'='*60}\n", file=sys.stderr)
                await page.wait_for_function("window._fetch_interactive_done === true", timeout=0)
                await asyncio.sleep(1)
            else:
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except: pass
                
                # Cloudflare 检测与自动等待
                content = await page.content()
                if any(cf_kw in content for cf_kw in ["cf-browser-verification", "Just a moment...", "cloudflare"]):
                    print("[*] 🛡️ 触发防爬质询，尝试自动等待绕过...", file=sys.stderr)
                    await asyncio.sleep(5)
                
                # 多次滚动触发懒加载
                for i in range(2):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)

            if session_file:
                await context.storage_state(path=session_file)
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
                return await fetch_with_curl_cffi(url, proxy, session_file)
        except Exception as e:
            last_err = str(e)
            print(f"[*] ❌ 引擎 {engine} 失败 (尝试 {attempt+1}/{retries}): {last_err}", file=sys.stderr)
            await asyncio.sleep(1)
            
    return json.dumps({"error": f"抓取失败. 最终错误: {last_err}"}), "text/html"