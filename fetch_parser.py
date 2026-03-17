import os
import re
import sqlite3
import random
import string
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import markdownify

try:
    import lxml
    FAST_PARSER = 'lxml'
except ImportError:
    FAST_PARSER = 'html.parser'

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "links.db")

def init_db():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS links 
                        (id TEXT PRIMARY KEY, url TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute("DELETE FROM links WHERE created_at <= datetime('now', '-3 days')")

def process_links_to_ids(soup, base_url):
    init_db()
    base_parsed = urlparse(base_url)
    base_netloc = base_parsed.netloc
    session_prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=2))
    
    links_data = []
    link_counter = 1
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href or href.startswith(('javascript:', 'mailto:', '#')): continue
        href_parsed = urlparse(href)
        if href_parsed.netloc == base_netloc:
            rel_path = href_parsed.path or "/"
            if href_parsed.params: rel_path += f";{href_parsed.params}"
            if href_parsed.query: rel_path += f"?{href_parsed.query}"
            if href_parsed.fragment: rel_path += f"#{href_parsed.fragment}"
            href = rel_path
        
        link_id = f"{session_prefix}-{link_counter}"
        links_data.append((link_id, href))
        a['href'] = f"@{link_id}"
        link_counter += 1
        
    if links_data:
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                conn.executemany("INSERT OR REPLACE INTO links (id, url) VALUES (?, ?)", links_data)
        except Exception: pass
    return session_prefix

def calculate_node_score(node):
    """根据文本长度、链接密度和关键词计算节点得分"""
    text = node.get_text(strip=True)
    text_len = len(text)
    if text_len < 20: return 0
    
    # 计算链接密度 (链接文本长度 / 总文本长度)
    link_text_len = sum(len(a.get_text(strip=True)) for a in node.find_all('a'))
    link_density = link_text_len / text_len if text_len > 0 else 1
    
    # 链接密度过高通常是导航或侧边栏 (常见于 0.5 以上)
    if link_density > 0.6: return 0
    
    score = text_len * (1 - link_density)
    
    # 关键词加分/扣分
    cls_id = (str(node.get('class', '')) + str(node.get('id', ''))).lower()
    positive = ['article', 'content', 'main', 'body', 'post', 'entry', 'topic']
    negative = ['sidebar', 'footer', 'nav', 'menu', 'aside', 'comment', 'ad', 'share', 'related']
    
    for word in positive:
        if word in cls_id: score *= 1.5
    for word in negative:
        if word in cls_id: score *= 0.2
        
    return score

def extract_page_content(html: str, url: str, full_mode: bool = False):
    """采用评分算法的高精度提取"""
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    html = re.sub(r'<(style|script|noscript|svg|canvas|video|audio|iframe|meta|link|template)[^>]*>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    soup = BeautifulSoup(html, FAST_PARSER)
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    
    if full_mode:
        target_node = soup.body if soup.body else soup
    else:
        # 1. 预清理：直接删除绝对不需要的标签
        for noise in soup.select('nav, header, footer, aside, .nav, .footer, .header, .sidebar, .ad, script, style'):
            noise.decompose()
        
        # 2. 评分寻找最佳容器
        candidates = []
        # 搜索所有可能是容器的标签
        for tag in soup.find_all(['div', 'article', 'main', 'section']):
            score = calculate_node_score(tag)
            if score > 0:
                candidates.append((score, tag))
        
        if candidates:
            # 取分最高者
            candidates.sort(key=lambda x: x[0], reverse=True)
            target_node = candidates[0][1]
        else:
            target_node = soup.body if soup.body else soup

    # 3. 链接转换
    ns = process_links_to_ids(target_node, url)
            
    # 4. Markdown 转换
    try:
        # 移除空链接和图片，保持 Markdown 极度纯净
        md_content = markdownify.markdownify(
            str(target_node), 
            heading_style="ATX", 
            strip=['img', 'video', 'audio']
        )
    except Exception:
        md_content = target_node.get_text(separator='\n\n', strip=True)

    # 5. 后置清洗：多余换行、空格、无效代号
    md_content = re.sub(r'\n{3,}', '\n\n', md_content) 
    md_content = re.sub(r'\[\s*\]\(@[^\)]+\)', '', md_content) 
    md_content = re.sub(r'(\n) +| +( \n)', r'\1', md_content)
    md_content = md_content.strip()
    
    return title, md_content, ns