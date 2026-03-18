import sys
import os
import json
import asyncio
import tempfile
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

def atomic_write_json(data: dict, filepath: str):
    """原子化写入 JSON，防止高并发下文件损坏"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(filepath), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, filepath)
    except Exception as e:
        if os.path.exists(tmp_path): os.remove(tmp_path)
        raise e

def format_session_data(session_file: str, target_url: str = "") -> dict:
    """自动识别并转换各种 Cookie 格式为 Playwright StorageState 格式"""
    default_state = {"cookies": [], "origins": []}
    if not session_file or not os.path.exists(session_file):
        return default_state

    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and "cookies" in data:
            return data

        pw_state = {"cookies": [], "origins": []}
        if isinstance(data, list):
            # 转换 Cookie-Editor 等插件导出的列表格式
            for c in data:
                same_site = str(c.get("sameSite", "Lax")).capitalize()
                if same_site in ["No_restriction", "None"]: same_site = "None"
                elif same_site not in ["Strict", "Lax", "None"]: same_site = "Lax"

                pw_state["cookies"].append({
                    "name": c.get("name", ""), "value": c.get("value", ""),
                    "domain": c.get("domain", ""), "path": c.get("path", "/"),
                    "expires": c.get("expirationDate", -1), "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", False), "sameSite": same_site
                })
        elif isinstance(data, dict):
            # 转换简单的键值对格式
            target_domain = urlparse(target_url).netloc if target_url else ""
            for k, v in data.items():
                pw_state["cookies"].append({
                    "name": str(k), "value": str(v), "domain": target_domain,
                    "path": "/", "expires": -1, "httpOnly": False,
                    "secure": False, "sameSite": "Lax"
                })
        
        atomic_write_json(pw_state, session_file)
        return pw_state
    except Exception as e:
        print(f"[*] ⚠️ Session 转换警告: {e}", file=sys.stderr)
        return default_state

async def fetch_with_curl_cffi(url: str, proxy: str = None, timeout: int = 15, session_file: str = None) -> tuple:
    proxies = {"http": proxy, "https": proxy} if proxy else None
    pw_state = {"cookies": [], "origins": []}
    cffi_cookies = {}
    
    if session_file and os.path.exists(session_file):
        pw_state = format_session_data(session_file, url)
        for c in pw_state.get("cookies", []):
            cffi_cookies[c["name"]] = c["value"]

    async with AsyncSession(impersonate="chrome120", proxies=proxies, timeout=timeout, headers=REAL_HEADERS, cookies=cffi_cookies) as session:
        response = await session.get(url)
        response.raise_for_status()
        
        # 处理可能的二进制或文本内容
        ctype = response.headers.get("content-type", "").lower()
        if any(t in ctype for t in ["text", "json", "xml", "javascript"]):
            content = response.text
        else:
            content = response.content
        
        if session_file:
            try:
                # 合并更新 Cookie
                target_domain = urlparse(url).netloc
                current_cookies = session.cookies.get_dict()
                merged_dict = {c["name"]: c for c in pw_state.get("cookies", [])}
                for k, v in current_cookies.items():
                    merged_dict[k] = {"name": k, "value": v, "domain": target_domain, "path": "/", "expires": -1, "httpOnly": False, "secure": False, "sameSite": "Lax"}
                pw_state["cookies"] = list(merged_dict.values())
                atomic_write_json(pw_state, session_file)
            except: pass
                
        return content, ctype

async def fetch_with_playwright(url: str, proxy: str = None, timeout: int = 30, session_file: str = None, is_interactive: bool = False, wait: int = 3) -> tuple:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not is_interactive,
            proxy={"server": proxy} if proxy else None,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        context_args = {"viewport": {"width": 1280, "height": 800}, "locale": "zh-CN", "user_agent": REAL_HEADERS["User-Agent"]}
        if session_file and os.path.exists(session_file):
            context_args["storage_state"] = session_file
                
        context = await browser.new_context(**context_args)
        
        # 优化后的注入 JS
        inject_js = """
        (() => {
            function createButton() {
                if (document.getElementById('_claw_btn')) return;
                const btn = document.createElement('div');
                btn.id = '_claw_btn';
                btn.innerHTML = '✅ 完成操作，点击抓取内容';
                Object.assign(btn.style, {
                    position: 'fixed', zIndex: '2147483647', padding: '12px 24px',
                    background: '#00c853', color: 'white', borderRadius: '30px',
                    cursor: 'pointer', boxShadow: '0 4px 15px rgba(0,0,0,0.5)',
                    top: '20px', right: '20px', fontWeight: 'bold', 
                    userSelect: 'none', fontFamily: 'sans-serif', 
                    display: 'block', visibility: 'visible', opacity: '1'
                });
                
                let isDragging = false, hasMoved = false, startX, startY, initX, initY;
                btn.addEventListener('mousedown', (e) => {
                    isDragging = true; hasMoved = false;
                    startX = e.clientX; startY = e.clientY;
                    initX = btn.offsetLeft; initY = btn.offsetTop;
                });
                window.addEventListener('mousemove', (e) => {
                    if (!isDragging) return;
                    const dx = e.clientX - startX, dy = e.clientY - startY;
                    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) hasMoved = true;
                    btn.style.left = (initX + dx) + 'px';
                    btn.style.top = (initY + dy) + 'px';
                    btn.style.right = 'auto';
                });
                window.addEventListener('mouseup', () => { isDragging = false; });
                
                btn.addEventListener('click', (e) => {
                    if (hasMoved) return;
                    window._fetch_interactive_done = true;
                    btn.style.background = '#ff9100'; 
                    btn.innerHTML = '⏳ 正在同步并解析...';
                });
                (document.body || document.documentElement).appendChild(btn);
            }

            // 初始尝试创建
            createButton();
            // 针对 SPA 页面，使用观察器确保按钮不被删掉
            const observer = new MutationObserver(() => {
                if (!document.getElementById('_claw_btn')) createButton();
            });
            observer.observe(document.documentElement, { childList: true, subtree: true });
            
            // 每秒强制检查一次（防止某些极端情况）
            setInterval(createButton, 1000);
        })();
        """
        
        # 1. 预注入
        if is_interactive:
            await context.add_init_script(inject_js)
            
        page = await context.new_page()
        if playwright_stealth:
            try: await playwright_stealth.stealth_async(page)
            except: pass
        
        try:
            # 使用 try-except 包装 goto，防止因某些资源加载失败导致程序崩溃
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout*1000)
            except Exception as e:
                print(f"[*] 页面加载超时或部分失败 (继续尝试注入按钮): {e}")

            if is_interactive:
                # 2. 页面加载后再次手动注入，确保按钮存在
                await page.evaluate(inject_js)
                
                print("[*] 浏览器已打开，请在页面完成操作（如登录、过验证码）后，点击页面右上角的绿色按钮。")
                
                # 等待用户点击按钮
                while True:
                    if page.is_closed():
                        break
                    try:
                        # 检查标志位
                        done = await page.evaluate("window._fetch_interactive_done === true")
                        if done:
                            break
                    except:
                        break # 页面可能已关闭
                    await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(wait)

            if session_file:
                await context.storage_state(path=session_file)
            
            content = await page.content()
            ctype = await page.evaluate("document.contentType || 'text/html'")
            return content, ctype
        finally:
            await browser.close()

async def fetch_target(url, engine, proxy, retries, session_file, is_interactive, wait, timeout=30):
    for i in range(retries):
        try:
            if engine == 'playwright':
                return await fetch_with_playwright(url, proxy, timeout, session_file, is_interactive, wait)
            return await fetch_with_curl_cffi(url, proxy, timeout, session_file)
        except Exception as e:
            if i == retries - 1: raise e
            await asyncio.sleep(1)