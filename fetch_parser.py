import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import markdownify

try:
    import lxml
    FAST_PARSER = 'lxml'
except ImportError:
    FAST_PARSER = 'html.parser'

def minify_links_to_save_tokens(soup: BeautifulSoup, base_url: str):
    """Token 极限压缩器：同域绝对链接转相对链接"""
    base_parsed = urlparse(base_url)
    base_netloc = base_parsed.netloc
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href or href.startswith(('javascript:', 'mailto:', '#')): continue
        href_parsed = urlparse(href)
        if href_parsed.netloc == base_netloc:
            rel_path = href_parsed.path
            if href_parsed.params: rel_path += f";{href_parsed.params}"
            if href_parsed.query: rel_path += f"?{href_parsed.query}"
            if href_parsed.fragment: rel_path += f"#{href_parsed.fragment}"
            if not rel_path: rel_path = "/"
            a['href'] = rel_path

def extract_page_content(html: str, url: str):
    """提取页面内容，清洗无用标签并返回 (标题, Markdown正文)"""
    # 预清洗防御 "样式/脚本穿透"
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    soup = BeautifulSoup(html, FAST_PARSER)
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    
    minify_links_to_save_tokens(soup, url) 
    
    # 扩大清理范围，拦截隐藏域
    for tag_name in ['noscript', 'svg', 'canvas', 'video', 'audio', 'iframe', 'meta', 'link', 'template', 'textarea']:
        for tag in soup.find_all(tag_name):
            tag.decompose()
            
    body_content = soup.body if soup.body else soup

    try:
        md_content = markdownify.markdownify(str(body_content), heading_style="ATX", strip=['img'])
    except Exception:
        md_content = body_content.get_text(separator='\n\n', strip=True)

    # 格式清理
    md_content = re.sub(r'\n{3,}', '\n\n', md_content) 
    md_content = re.sub(r'\[\s*\]\([^\)]+\)', '', md_content) 
    md_content = re.sub(r'(?<=\n) +| +(?=\n)', '', md_content) 
    md_content = re.sub(r'<style[^>]*>.*', '', md_content, flags=re.IGNORECASE)
    md_content = md_content.strip()
    
    return title, md_content