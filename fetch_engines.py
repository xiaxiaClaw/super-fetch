import sys
import os
import json
import asyncio
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
    """CFFI 引擎：极速请求，支持 Cookie 持久化"""
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    saved_cookies = {}
    if session_file and os.path.exists(session_file):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                saved_cookies = json.load(f)
            print(f"[*] 🍪 成功加载 CFFI Cookie: {session_file}", file=sys.stderr)
        except Exception: pass

    async with AsyncSession(impersonate="chrome120", proxies=proxies, timeout=timeout, headers=REAL_HEADERS, cookies=saved_cookies) as session:
        response = await session.get(url)
        response.raise_for_status()
        
        if session_file:
            try:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session.cookies.get_dict(), f)
            except Exception as e:
                print(f"[!] 保存 CFFI Cookie 失败: {e}", file=sys.stderr)
                
        return response.text

async def fetch_with_playwright(url: str, proxy: str = None, timeout: int = 30, session_file: str = None, is_login_mode: bool = False) -> str:
    """Playwright 引擎：全真浏览器，支持登录交互与原生会话持久化"""
    async with async_playwright() as p:
        headless_mode = not is_login_mode
        browser = await p.chromium.launch(
            headless=headless_mode,
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
                context_args["storage_state"] = session_file
                print(f"[*] 🎫 成功注入 Playwright 登录状态: {session_file}", file=sys.stderr)
            except Exception as e:
                print(f"[!] 读取状态文件失败，将以新会话启动: {e}", file=sys.stderr)
                
        context = await browser.new_context(**context_args)
        
        # 终极防丢可拖拽版：全局悬浮按钮脚本
        if is_login_mode:
            inject_js = """
            (() => {
                if (window._claw_injected) return;
                window._claw_injected = true;
                
                const injectBtn = () => {
                    if (document.getElementById('claw-done-btn')) return;
                    
                    const btn = document.createElement('div');
                    btn.id = 'claw-done-btn';
                    btn.innerHTML = '✅ 登录/验证完成，点击继续';
                    
                    // 基础样式设置 (支持拖拽视觉)
                    btn.style.position = 'fixed';
                    btn.style.zIndex = '2147483647';
                    btn.style.padding = '15px 25px';
                    btn.style.background = '#00C853';
                    btn.style.color = 'white';
                    btn.style.border = 'none';
                    btn.style.borderRadius = '8px';
                    btn.style.fontSize = '16px';
                    btn.style.fontWeight = 'bold';
                    btn.style.cursor = 'move';
                    btn.style.boxShadow = '0 4px 15px rgba(0,0,0,0.4)';
                    btn.style.userSelect = 'none'; // 防止拖拽时选中文本
                    btn.style.transition = 'background 0.2s, transform 0.2s';
                    
                    // 恢复上次拖拽的位置，或者使用默认位置
                    if (window._claw_btn_pos) {
                        btn.style.left = window._claw_btn_pos.left;
                        btn.style.top = window._claw_btn_pos.top;
                    } else {
                        btn.style.top = '20px';
                        btn.style.right = '20px';
                    }
                    
                    // --- 拖拽逻辑实现 ---
                    let isDragging = false;
                    let startX, startY, initialLeft, initialTop;
                    let clickStartX, clickStartY;
                    
                    btn.onmousedown = (e) => {
                        isDragging = true;
                        startX = e.clientX;
                        startY = e.clientY;
                        clickStartX = e.clientX;
                        clickStartY = e.clientY;
                        
                        const rect = btn.getBoundingClientRect();
                        initialLeft = rect.left;
                        initialTop = rect.top;
                        
                        btn.style.transition = 'none'; // 拖拽时取消动画，保证丝滑
                        e.preventDefault();
                    };
                    
                    window.addEventListener('mousemove', (e) => {
                        if (!isDragging) return;
                        
                        let newLeft = initialLeft + (e.clientX - startX);
                        let newTop = initialTop + (e.clientY - startY);
                        
                        // 边缘碰撞检测 (防止拖出屏幕外)
                        newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - btn.offsetWidth));
                        newTop = Math.max(0, Math.min(newTop, window.innerHeight - btn.offsetHeight));
                        
                        btn.style.left = newLeft + 'px';
                        btn.style.top = newTop + 'px';
                        btn.style.right = 'auto'; // 清除 right 属性，交由 left 接管
                        
                        // 记录位置，防止 SPA 路由跳转后复位
                        window._claw_btn_pos = { left: btn.style.left, top: btn.style.top };
                    });
                    
                    window.addEventListener('mouseup', () => {
                        if (isDragging) {
                            isDragging = false;
                            btn.style.transition = 'background 0.2s, transform 0.2s'; 
                        }
                    });
                    
                    // --- 点击判定逻辑 ---
                    btn.onclick = (e) => {
                        // 如果鼠标移动距离大于 5px，判定为拖拽，不触发点击事件
                        const moveDistX = Math.abs(e.clientX - clickStartX);
                        const moveDistY = Math.abs(e.clientY - clickStartY);
                        if (moveDistX > 5 || moveDistY > 5) {
                            return;
                        }
                        
                        window._fetch_login_done = true;
                        btn.innerHTML = '⏳ 正在保存状态...';
                        btn.style.background = '#FF9800';
                        btn.style.cursor = 'wait';
                    };
                    
                    if (document.documentElement) {
                        document.documentElement.appendChild(btn);
                    }
                };
                
                document.addEventListener('DOMContentLoaded', injectBtn);
                setInterval(injectBtn, 1000); 
            })();
            """
            await context.add_init_script(inject_js)
            
        page = await context.new_page()
        
        if playwright_stealth:
            try:
                s_func = getattr(playwright_stealth, 'stealth_async', None) or getattr(playwright_stealth, 'stealth', None)
                if s_func and not callable(s_func):
                    s_func = getattr(s_func, 'stealth_async', None) or getattr(s_func, 'stealth', None)
                if s_func and callable(s_func):
                    stealth_result = s_func(page)
                    if asyncio.iscoroutine(stealth_result): await stealth_result
            except Exception: pass
        
        async def route_intercept(route):
            if not is_login_mode and route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", route_intercept)
        
        try:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            except Exception:
                print(f"[*] ⚠️ 初始加载超时，尝试强行读取当前已渲染内容...", file=sys.stderr)
            
            await asyncio.sleep(2)
            
            if is_login_mode:
                print(f"\n{'='*60}", file=sys.stderr)
                print(f"[*] 🛑 进入无时限手动操作模式！", file=sys.stderr)
                print(f"[*] 1. 请在弹出的浏览器中自由完成【账号登录】或【过验证码】", file=sys.stderr)
                print(f"[*] 2. 无论页面跳转多少次，完成操作后，点击页面上的", file=sys.stderr)
                print(f"[*]    【✅ 登录/验证完成，点击继续】 绿色按钮即可。", file=sys.stderr)
                print(f"[*] 💡 提示：按住该按钮可任意拖拽，避免遮挡网页内容。", file=sys.stderr)
                print(f"{'='*60}\n", file=sys.stderr)
                
                await page.wait_for_function("window._fetch_login_done === true", timeout=0)
                print("[*] 🖱️ 检测到按钮点击，正在保存登录凭证...", file=sys.stderr)
                await asyncio.sleep(1)
            else:
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except:
                    pass
                
                content = await page.content()
                if any(cf_kw in content for cf_kw in ["cf-browser-verification", "Just a moment...", "cloudflare"]):
                    print("[*] 🛡️ 触发防爬质询，尝试自动绕过...", file=sys.stderr)
                    try: 
                        await page.wait_for_selector('body:not(.no-js)', timeout=10000)
                    except: 
                        await asyncio.sleep(4)
                
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await asyncio.sleep(0.5)

            if session_file:
                await context.storage_state(path=session_file)
                print(f"[*] 💾 登录状态/会话已成功保存至: {session_file}", file=sys.stderr)
            
            return await page.content()
        finally:
            await browser.close()

async def fetch_target(url: str, engine: str, proxy: str, retries: int, session_file: str, is_login_mode: bool):
    """调度器入口"""
    last_err = ""
    for attempt in range(retries):
        try:
            if engine == 'playwright':
                return await fetch_with_playwright(url, proxy, session_file=session_file, is_login_mode=is_login_mode)
            else:
                return await fetch_with_curl_cffi(url, proxy, session_file=session_file)
        except Exception as e:
            last_err = str(e)
            print(f"[*] ❌ 引擎 {engine} 请求失败 (尝试 {attempt+1}/{retries}): {last_err}", file=sys.stderr)
            await asyncio.sleep(1)
            
    return json.dumps({"error": f"请求失败. 最终错误: {last_err}"}, ensure_ascii=False)