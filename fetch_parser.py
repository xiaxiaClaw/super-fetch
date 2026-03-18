import os
import re
import sqlite3
import random
import string
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import markdownify

try:
    import lxml
    FAST_PARSER = 'lxml'
except ImportError:
    FAST_PARSER = 'html.parser'

# 数据库路径：保存在脚本同级目录
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "links.db")

def init_db():
    """初始化数据库并清理过期（>3天）的数据"""
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS links 
                            (id TEXT PRIMARY KEY, url TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            conn.execute("DELETE FROM links WHERE created_at <= datetime('now', '-3 days')")
    except Exception as e:
        import sys
        print(f"[!] SQLite 初始化失败: {e}", file=sys.stderr)

def process_links_to_ids(soup: BeautifulSoup, base_url: str):
    """提取链接并转换为带独立命名空间的代号，如 @k9-1"""
    init_db()
    
    # 随机生成 2 位前缀作为命名空间
    session_prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=2))
    
    links_data = []
    link_counter = 1
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href or href.startswith(('javascript:', 'mailto:', '#')): 
            continue
            
        # 【关键修复】：利用 urljoin 强制将所有链接（相对路径或绝对路径）转换为完整的绝对路径
        absolute_href = urljoin(base_url, href)
            
        link_id = f"{session_prefix}-{link_counter}"
        links_data.append((link_id, absolute_href))
        
        # 替换 HTML 中的链接为代号
        a['href'] = f"@{link_id}"
        link_counter += 1
        
    if links_data:
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                conn.executemany("INSERT OR REPLACE INTO links (id, url) VALUES (?, ?)", links_data)
        except Exception as e:
            import sys
            print(f"[!] 链接代号入库失败: {e}", file=sys.stderr)
            
    return session_prefix

def calculate_node_score(node):
    """正文识别评分算法：基于文本密度和标签权重"""
    text = node.get_text(strip=True)
    text_len = len(text)
    if text_len < 30: return 0
    
    # 计算链接密度
    link_text_len = sum(len(a.get_text(strip=True)) for a in node.find_all('a'))
    link_density = link_text_len / text_len if text_len > 0 else 1
    
    # 链接密度过高通常是导航、页脚或侧边栏
    if link_density > 0.6: return 0
    
    # 基础分 = 文本长度 * 纯净度
    score = text_len * (1 - link_density)
    
    # 根据 Class/ID 关键词调整权重
    cls_id = (str(node.get('class', '')) + str(node.get('id', ''))).lower()
    positive = ['article', 'content', 'main', 'post', 'entry', 'topic', 'body']
    negative = ['sidebar', 'footer', 'nav', 'menu', 'aside', 'comment', 'ad', 'share', 'related']
    
    for word in positive:
        if word in cls_id: score *= 1.5
    for word in negative:
        if word in cls_id: score *= 0.2
        
    return score

def extract_page_content(html: str, url: str, full_mode: bool = False):
    """智能提取页面内容，清洗无用干扰"""
    # 1. 预清洗
    html = re.sub(r'<(style|script|noscript|svg|canvas|video|iframe|meta|link)[^>]*>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    soup = BeautifulSoup(html, FAST_PARSER)
    title = (soup.title.string if soup.title else "Untitled").strip()
    
    if full_mode:
        target_node = soup.body if soup.body else soup
    else:
        # 硬过滤已知噪音区域
        for noise in soup.select('nav, header, footer, aside, .nav, .header, .footer, .sidebar, .ad, .menu'):
            noise.decompose()
        
        # 递归寻找得分最高的内容容器
        candidates = []
        for tag in soup.find_all(['div', 'article', 'main', 'section']):
            score = calculate_node_score(tag)
            if score > 0:
                candidates.append((score, tag))
        
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            target_node = candidates[0][1]
        else:
            target_node = soup.body if soup.body else soup

    # 2. 转换链接并获取命名空间
    ns = process_links_to_ids(target_node, url)
            
    # 3. 转换为 Markdown (移除图片)
    try:
        md_content = markdownify.markdownify(str(target_node), heading_style="ATX", strip=['img', 'video', 'audio'])
    except Exception:
        md_content = target_node.get_text(separator='\n\n', strip=True)

    # 4. 后置格式美化
    md_content = re.sub(r'\n{3,}', '\n\n', md_content) 
    md_content = re.sub(r'\[\s*\]\(@[^\)]+\)', '', md_content) # 移除空代号链接
    md_content = md_content.strip()
    
    return title, md_content, ns