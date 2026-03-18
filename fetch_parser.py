import os
import re
import sqlite3
import random
import string
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, Comment
import markdownify


def get_data_dir():
    """跨平台获取数据目录"""
    home = os.path.expanduser("~")
    return os.path.join(home, ".openclaw", "super-fetch")


# 统一数据目录
DATA_DIR = get_data_dir()
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


def remove_base64_images(soup):
    """移除 base64 图片，保留其他图片"""
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src.startswith('data:'):
            img.decompose()


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
        except:
            pass
    return ns


# 噪音关键词（用于 class/id 过滤）- 更保守的列表
NOISE_KEYWORDS = [
    'nav', 'navigation', 'navbar', 'footer', 'sidebar',
    'ad-', '-ad-', 'ads-', '-ads-',
    'cookie', 'consent'
]

# 正文关键词（加分）
CONTENT_KEYWORDS = [
    'article', 'content', 'main', 'post', 'entry'
]


def calculate_content_score(node):
    """
    保守的正文提取算法 - 宁滥勿缺
    """
    # 先移除脚本等噪音元素的影响
    for elem in node(['script', 'style', 'noscript']):
        elem.decompose()

    text = node.get_text(strip=True)
    text_len = len(text)

    # 降低文本长度阈值
    if text_len < 20:
        return 0

    # 1. 计算段落数
    p_count = len(node.find_all('p'))
    li_count = len(node.find_all(['li', 'dd']))
    heading_count = len(node.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
    span_count = len(node.find_all(['span', 'div']))
    block_count = p_count + li_count + heading_count

    # 2. 计算链接密度 - 放宽限制
    links = node.find_all('a')
    link_text_len = sum(len(a.get_text(strip=True)) for a in links)
    link_density = link_text_len / text_len if text_len > 0 else 1

    # 放宽链接密度限制
    if link_density > 0.8:
        return 0

    # 3. 检查 class/id 关键词
    identity = ''
    if node.get('class'):
        identity += ' ' + ' '.join(node.get('class', []))
    if node.get('id'):
        identity += ' ' + node.get('id', '')
    identity = identity.lower()

    # 噪音惩罚 - 更保守
    noise_penalty = 1.0
    for keyword in NOISE_KEYWORDS:
        if keyword in identity:
            noise_penalty *= 0.3
            break

    # 正文加分
    content_bonus = 1.0
    for keyword in CONTENT_KEYWORDS:
        if keyword in identity:
            content_bonus = 1.5
            break

    # 综合评分 - 更简单直接
    base_score = text_len * (1 - link_density * 0.5)

    # 段落加分
    if p_count >= 1:
        base_score *= 1.1
    if p_count >= 3:
        base_score *= 1.2

    score = base_score * content_bonus * noise_penalty
    return score


def get_best_content_node(soup):
    """
    保守策略：优先考虑 body，只移除明显噪音
    """
    # 策略 1: 语义化标签 - 降低门槛
    semantic_tags = ['article', 'main', '[role="main"]']
    for tag in semantic_tags:
        try:
            elem = soup.select_one(tag)
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 50:
                    return elem
        except:
            pass

    # 策略 2: 查找常见的正文容器
    common_selectors = [
        '.post-content', '.entry-content', '.article-content',
        '#post-content', '#entry-content', '#article-content',
        '.content-body', '.post-body', '.article-body',
        '.content', '#content'
    ]
    for selector in common_selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 50:
                    return elem
        except:
            pass

    # 策略 3: 评分算法 - 更宽松
    candidates = []
    for tag in soup.find_all(['div', 'article', 'section', 'main', 'body']):
        score = calculate_content_score(tag)
        if score > 0:
            candidates.append((score, tag))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        # 取最高分
        for score, tag in candidates:
            text = tag.get_text(strip=True)
            if len(text) > 30:
                return tag

    # 策略 4: 直接用 body，只移除最明显的噪音
    if soup.body:
        return soup.body
    return soup


def clean_noise_elements(soup):
    """只移除最明显的噪音元素，保留尽可能多的内容"""
    # 移除注释
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # 只移除最确定的噪音标签
    noise_selectors = [
        'script', 'style', 'noscript', 'svg', 'canvas'
    ]

    for selector in noise_selectors:
        try:
            for elem in soup.select(selector):
                elem.decompose()
        except:
            pass


def extract_page_content(html: str, url: str, full_mode: bool = False):
    """解析 HTML 并转化为结构化 Markdown"""
    # 预清洗
    html = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', '', html, flags=re.I | re.S)

    soup = BeautifulSoup(html, 'html.parser')
    title = (soup.title.string if soup.title else "Untitled Page").strip()

    if full_mode:
        root = soup.body if soup.body else soup
    else:
        # 轻微清理噪音
        clean_noise_elements(soup)
        # 获取最佳内容节点
        root = get_best_content_node(soup)

    # 移除 base64 图片
    remove_base64_images(root)

    ns = process_links_to_ids(root, url)

    try:
        markdown = markdownify.markdownify(str(root), heading_style="ATX")
    except:
        markdown = root.get_text(separator='\n\n', strip=True)

    # 清洗多余换行
    markdown = re.sub(r'\n{3,}', '\n\n', markdown).strip()
    return title, markdown, ns
