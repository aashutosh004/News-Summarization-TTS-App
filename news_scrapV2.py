import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
import sys
from urllib.parse import urlparse, urljoin

def scrape_company_articles(company_name, max_articles=10):
    """
    Scrape articles related to the given company name using BeautifulSoup.
    
    Args:
        company_name (str): The name of the company to search for
        max_articles (int): Maximum number of articles to fetch
    
    Returns:
        list: List of dictionaries containing article data
    """
    articles = []
    attempted_urls = set()  # Track URLs we've already tried
    
    # Format company name for URL
    search_term = company_name.replace(' ', '+')
    
    # Try different search engines and news sites to find articles
    search_urls = [
        f"https://www.google.com/search?q={search_term}+news&num=30",
        f"https://news.google.com/search?q={search_term}",
        f"https://www.bing.com/news/search?q={search_term}&qft=interval%3D%227%22&form=PTFTNR",
        f"https://www.reuters.com/search/news?blob={search_term}",
        f"https://www.bloomberg.com/search?query={search_term}",
        f"https://finance.yahoo.com/quote/{search_term}/news",
        f"https://seekingalpha.com/search?q={search_term}",
        f"https://www.fool.com/search/?q={search_term}"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'referer': 'https://www.google.com/'
    }
    
    # Try to get max_articles from all sources
    for search_url in search_urls:
        if len(articles) >= max_articles:
            break
            
        try:
            print(f"Searching: {search_url}")
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract article links from search results
                article_links = extract_links_from_search(soup, search_url)
                
                # Remove duplicates
                article_links = list(dict.fromkeys(article_links))
                
                # Filter out already attempted URLs
                article_links = [link for link in article_links if link not in attempted_urls]
                
                # Scrape content from each article link
                for link in article_links:
                    if len(articles) >= max_articles:
                        break
                    
                    # Add to attempted URLs
                    attempted_urls.add(link)
                    
                    try:
                        # Validate URL
                        if not is_valid_url(link):
                            continue
                            
                        article_data = scrape_article_content(link, company_name)
                        if article_data:
                            articles.append(article_data)
                            print(f"✅ Scraped article {len(articles)}/{max_articles}: {article_data['title'][:50]}...")
                            
                            # Random delay to avoid rate limiting
                            time.sleep(random.uniform(1, 2))
                        else:
                            print(f"⚠️ Skipped irrelevant or invalid article: {link}")
                    except Exception as e:
                        print(f"❌ Error scraping article {link}: {str(e)}")
            
            # Random delay between search sources
            time.sleep(random.uniform(2, 3))
            
        except Exception as e:
            print(f"❌ Error with search URL {search_url}: {str(e)}")
    
    print(f"Found {len(articles)}/{max_articles} articles")
    return articles[:max_articles]

def is_valid_url(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def extract_links_from_search(soup, search_url):
    """Extract article links from a search page based on the source"""
    article_links = []
    
    # Google search patterns
    if "google.com/search" in search_url:
        # Method 1: Look for 'g' class divs
        for g in soup.find_all('div', class_='g'):
            a_tags = g.find_all('a')
            for a in a_tags:
                href = a.get('href', '')
                if href.startswith('http') and 'google' not in href:
                    article_links.append(href)
        
        # Method 2: Look for results with h3 headers (newer Google)
        if not article_links:
            for h3 in soup.find_all('h3'):
                if h3.parent and h3.parent.name == 'a':
                    href = h3.parent.get('href', '')
                    if href.startswith('http') and 'google' not in href:
                        article_links.append(href)
                elif h3.parent and h3.parent.find('a'):
                    href = h3.parent.find('a').get('href', '')
                    if href.startswith('http') and 'google' not in href:
                        article_links.append(href)
    
    # Google News patterns
    elif "news.google.com" in search_url:
        for article in soup.find_all(['article', 'div'], class_=re.compile(r'NiLAwe|DHQ5pf')):
            a_tag = article.find('a')
            if a_tag and a_tag.get('href'):
                href = a_tag.get('href')
                if href.startswith('./'):
                    href = 'https://news.google.com' + href[1:]
                elif href.startswith('/'):
                    href = 'https://news.google.com' + href
                article_links.append(href)
    
    # Bing News patterns
    elif "bing.com/news" in search_url:
        for article in soup.find_all(['div', 'article'], class_=re.compile(r'news-card|newsitem|newsArticle')):
            a_tag = article.find('a')
            if a_tag and a_tag.get('href'):
                article_links.append(a_tag.get('href'))
        
        # Alternative pattern
        if not article_links:
            for a in soup.find_all('a', class_=re.compile(r'title|headline')):
                href = a.get('href', '')
                if href and 'bing' not in href:
                    if not href.startswith('http'):
                        base = urlparse(search_url)
                        href = f"{base.scheme}://{base.netloc}{href}"
                    article_links.append(href)
    
    # Reuters patterns
    elif "reuters.com" in search_url:
        base_url = "https://www.reuters.com"
        for article in soup.find_all(['div', 'li'], class_=re.compile(r'search-result|story-content|media-story-card')):
            a_tag = article.find('a')
            if a_tag and a_tag.get('href'):
                href = a_tag.get('href')
                if not href.startswith('http'):
                    href = urljoin(base_url, href)
                article_links.append(href)
    
    # Bloomberg patterns
    elif "bloomberg.com" in search_url:
        base_url = "https://www.bloomberg.com"
        for article in soup.find_all(['article', 'div'], class_=re.compile(r'story|storyItem|searchResult')):
            a_tag = article.find('a')
            if a_tag and a_tag.get('href'):
                href = a_tag.get('href')
                if not href.startswith('http'):
                    href = urljoin(base_url, href)
                article_links.append(href)
    
    # Yahoo Finance patterns
    elif "yahoo.com" in search_url:
        for article in soup.find_all(['div', 'li'], class_=re.compile(r'NewsArticle|js-stream-content')):
            a_tag = article.find('a')
            if a_tag and a_tag.get('href'):
                href = a_tag.get('href')
                if not href.startswith('http'):
                    href = urljoin("https://finance.yahoo.com", href)
                article_links.append(href)
    
    # Seeking Alpha patterns
    elif "seekingalpha.com" in search_url:
        for article in soup.find_all(['div', 'li'], class_=re.compile(r'search-results-item|article-item')):
            a_tag = article.find('a')
            if a_tag and a_tag.get('href'):
                href = a_tag.get('href')
                if not href.startswith('http'):
                    href = urljoin("https://seekingalpha.com", href)
                article_links.append(href)
    
    # Motley Fool patterns
    elif "fool.com" in search_url:
        for article in soup.find_all(['div', 'li'], class_=re.compile(r'article|search-result')):
            a_tag = article.find('a')
            if a_tag and a_tag.get('href'):
                href = a_tag.get('href')
                if not href.startswith('http'):
                    href = urljoin("https://www.fool.com", href)
                article_links.append(href)
    
    # Generic method for any site
    if not article_links:
        # Find all links with news-related words in text or URL
        for a in soup.find_all('a'):
            href = a.get('href', '')
            text = a.get_text().lower()
            if href.startswith('http') and (
                'article' in href or 'news' in href or 
                'story' in href or 'press' in href or
                'article' in text or 'news' in text
            ):
                article_links.append(href)
    
    return article_links

def scrape_article_content(url, company_name):
    """
    Scrape content from a specific article URL
    
    Args:
        url (str): URL of the article
        company_name (str): Name of the company to validate relevance
    
    Returns:
        dict: Article data including title and content
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title - try more patterns
            title = extract_title(soup)
            
            # If no title found, skip this article
            if not title:
                return None
                
            # Check if article is relevant to the company
            if not is_relevant_to_company(soup, company_name):
                return None
            
            # Extract content using advanced methods
            content = extract_content(soup)
            
            # If content is too short, it's probably not a real article
            if not content or len(content) < 100:
                return None
                
            return {
                "company_name": company_name,
                "title": title,
                "content": content,
                "url": url
            }
        
        return None
    
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        return None

def extract_title(soup):
    """Extract article title using multiple methods"""
    # Method 1: Look for headline or title tags
    for tag_name in ['h1', 'h2']:
        for class_name in ['headline', 'title', 'article-title', 'entry-title', 'post-title']:
            title_tag = soup.find(tag_name, class_=re.compile(class_name, re.I))
            if title_tag:
                return title_tag.get_text().strip()
    
    # Method 2: Just get the first h1
    h1 = soup.find('h1')
    if h1:
        return h1.get_text().strip()
    
    # Method 3: Look at title tag
    title_tag = soup.find('title')
    if title_tag:
        # Remove site name often added after dashes or pipes
        title_text = title_tag.get_text().strip()
        title_parts = re.split(r' [-|] ', title_text, 1)
        return title_parts[0].strip()
    
    # Method 4: Look for meta title
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title.get('content').strip()
    
    return None

def extract_content(soup):
    """Extract article content using multiple advanced methods"""
    content = ""
    
    # Remove unwanted elements
    for unwanted in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'aside']):
        unwanted.decompose()
    
    # Method 1: Look for article tag
    article_tag = soup.find('article')
    if article_tag:
        paragraphs = article_tag.find_all('p')
        if paragraphs:
            content = ' '.join([p.get_text().strip() for p in paragraphs])
    
    # Method 2: Look for common content div classes
    if not content:
        content_classes = [
            'content', 'article-body', 'story-body', 'post-content', 
            'entry-content', 'article-content', 'story-content',
            'main-content', 'body-content', 'article__body'
        ]
        
        for class_name in content_classes:
            content_div = soup.find(['div', 'section'], class_=re.compile(class_name, re.I))
            if content_div:
                paragraphs = content_div.find_all('p')
                if paragraphs:
                    content = ' '.join([p.get_text().strip() for p in paragraphs])
                    break
    
    # Method 3: Find the div with the most paragraph tags
    if not content:
        div_p_counts = {}
        for div in soup.find_all('div'):
            p_count = len(div.find_all('p'))
            if p_count > 0:
                div_p_counts[div] = p_count
        
        if div_p_counts:
            main_content_div = max(div_p_counts.items(), key=lambda x: x[1])[0]
            paragraphs = main_content_div.find_all('p')
            content = ' '.join([p.get_text().strip() for p in paragraphs])
    
    # Method 4: Just get all paragraphs if specific containers weren't found
    if not content:
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text().strip() for p in paragraphs])
    
    # Clean up content
    content = re.sub(r'\s+', ' ', content).strip()
    
    return content

def is_relevant_to_company(soup, company_name):
    """
    Check if the article is relevant to the company using advanced methods.
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        company_name (str): Company name to check for
    
    Returns:
        bool: True if relevant, False otherwise
    """
    # Extract all text
    text = soup.get_text().lower()
    
    # Create patterns for company name variations
    patterns = [
        re.compile(r'\b' + re.escape(company_name.lower()) + r'\b'),  # Exact match
        re.compile(r'\b' + re.escape(company_name.lower().replace(' ', '')) + r'\b')  # No spaces
    ]
    
    # Add ticker symbol pattern if company name looks like it could be one
    if len(company_name) <= 5 and company_name.isalpha():
        patterns.append(re.compile(r'\$' + re.escape(company_name.upper())))
    
    # Count total occurrences across all patterns
    total_count = sum(len(pattern.findall(text)) for pattern in patterns)
    
    # Check if company name is in title (higher relevance)
    title_tag = soup.find('title')
    title_relevance = False
    if title_tag:
        title_text = title_tag.get_text().lower()
        title_relevance = any(pattern.search(title_text) for pattern in patterns)
    
    # If company mentioned in title or at least twice in text, consider it relevant
    return title_relevance or total_count >= 2

def save_to_json(articles, company_name):
    """
    Save the scraped articles to a JSON file
    
    Args:
        articles (list): List of article dictionaries
        company_name (str): Name of the company
    """
    filename = f"{company_name.replace(' ', '_')}_articles.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({"articles": articles}, f, indent=4, ensure_ascii=False)
    
    print(f"Saved {len(articles)} articles to {filename}")

def main():
    if len(sys.argv) > 1:
        company_name = ' '.join(sys.argv[1:])
    else:
        company_name = input("Enter company name to search for: ")
    
    print(f"🔍 Searching for articles about {company_name}...")
    articles = scrape_company_articles(company_name, max_articles=10)
    
    if articles:
        save_to_json(articles, company_name)
        print(f"✅ Successfully scraped {len(articles)} articles about {company_name}")
    else:
        print(f"❌ No articles found for {company_name}")

if __name__ == "__main__":
    main()