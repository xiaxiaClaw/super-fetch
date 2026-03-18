import os
import re
import sqlite3
import random
import string
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import markdownify

# 统一数据目录
DATA_DIR = os.path.expanduser("~/.openclaw/super-fetch")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "links.db")

def init_db():
    """初始化链接数据库，并执行概率性清理"""
    try:
        with sqlite3.connect(DB_PATH, timeout=15) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS links 
                            (id TEXT PRIMARY KEY, url TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            if random.random() < 0.05:
                conn.execute("DELETE FROM links WHERE created_at <= datetime('now', '-7 days')")
    except Exception as e:
        import sys
        print(f"[*] ⚠️ 数据库初始化异常: {e}", file=sys.stderr)

def process_links_to_ids(soup: BeautifulSoup, base_url: str):
    """将 A 标签和 IMG 标签的链接转化为代号，并存入数据库"""
    init_db()
    ns = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    links_data = []
    counter = 1
    
    # 同时处理链接和图片
    for tag in soup.find_all(['a', 'img']):
        attr = 'href' if tag.name == 'a' else 'src'
        link = tag.get(attr)
        
        if not link or link.startswith(('javascript:', 'mailto:', '#', 'data:')):
            continue
            
        abs_url = urljoin(base_url, link)
        link_id = f"{ns}-{counter}"
        tag[attr] = f"@{link_id}"
        links_data.append((link_id, abs_url))
        counter += 1
        
    if links_data:
        try:
            with sqlite3.connect(DB_PATH, timeout=15) as conn:
                conn.executemany("INSERT OR REPLACE INTO links (id, url) VALUES (?, ?)", links_data)
        except: pass
    return ns

def calculate_node_score(node):
    """简单的正文提取算法"""
    text = node.get_text(strip=True)
    if len(text) < 25: return 0
    
    # 链接密度过滤
    links = node.find_all('a')
    link_len = sum(len(a.get_text(strip=True)) for a in links)
    density = link_len / len(text) if len(text) > 0 else 1
    if density > 0.5: return 0
    
    score = len(text) * (1 - density)
    # 关键词加分
    identity = (str(node.get('class', '')) + str(node.get('id', ''))).lower()
    if any(k in identity for k in ['article', 'content', 'main', 'post']): score *= 1.5
    if any(k in identity for k in ['nav', 'footer', 'sidebar', 'comment']): score *= 0.1
    return score

def extract_page_content(html: str, url: str, full_mode: bool = False):
    """解析 HTML 并转化为结构化 Markdown"""
    # 预清洗
    html = re.sub(r'<(script|style|noscript|svg|canvas|video|iframe)[^>]*>.*?</\1>', '', html, flags=re.I|re.S)
    
    soup = BeautifulSoup(html, 'html.parser')
    title = (soup.title.string if soup.title else "Untitled Page").strip()
    
    if full_mode:
        root = soup.body if soup.body else soup
    else:
        # 移除显而易见的噪音
        for noise in soup.select('nav, footer, header, aside, .nav, .footer, .sidebar, .ad'):
            noise.decompose()
        
        candidates = []
        for tag in soup.find_all(['div', 'article', 'section', 'main']):
            score = calculate_node_score(tag)
            if score > 0: candidates.append((score, tag))
        
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            root = candidates[0][1]
        else:
            root = soup.body if soup.body else soup

    ns = process_links_to_ids(root, url)
    
    try:
        markdown = markdownify.markdownify(str(root), heading_style="ATX")
    except:
        markdown = root.get_text(separator='\n\n', strip=True)

    # 清洗多余换行
    markdown = re.sub(r'\n{3,}', '\n\n', markdown).strip()
    return title, markdown, ns