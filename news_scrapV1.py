import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
import sys

def scrape_company_articles(company_name):
    """
    Scrape 10 articles related to the given company name using BeautifulSoup.
    
    Args:
        company_name (str): The name of the company to search for
    
    Returns:
        list: List of dictionaries containing article data
    """
    articles = []
    
    # Format company name for URL
    search_term = company_name.replace(' ', '+')
    
    # Try different search engines and news sites to find articles
    search_urls = [
        f"https://www.google.com/search?q={search_term}+news",
        f"https://news.google.com/search?q={search_term}",
        f"https://www.bing.com/news/search?q={search_term}",
        f"https://www.reuters.com/search/news?blob={search_term}",
        f"https://www.bloomberg.com/search?query={search_term}"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml'
    }
    
    # Continue until we have 10 articles or tried all sources
    for search_url in search_urls:
        if len(articles) >= 10:
            break
            
        try:
            print(f"Searching: {search_url}")
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract article links from search results (different for each site)
                article_links = []
                
                # Google search patterns
                if "google.com/search" in search_url:
                    for g in soup.find_all('div', class_='g'):
                        a_tags = g.find_all('a')
                        for a in a_tags:
                            href = a.get('href', '')
                            if href.startswith('http') and 'google' not in href:
                                article_links.append(href)
                
                # Google News patterns
                elif "news.google.com" in search_url:
                    for article in soup.find_all('article'):
                        a_tag = article.find('a')
                        if a_tag and a_tag.get('href'):
                            # Google News uses relative URLs
                            href = a_tag.get('href')
                            if href.startswith('./'):
                                href = 'https://news.google.com' + href[1:]
                            article_links.append(href)
                
                # Bing News patterns
                elif "bing.com/news" in search_url:
                    for article in soup.find_all('div', class_='news-card'):
                        a_tag = article.find('a')
                        if a_tag and a_tag.get('href'):
                            article_links.append(a_tag.get('href'))
                
                # Reuters patterns
                elif "reuters.com" in search_url:
                    for article in soup.find_all('div', class_='search-result'):
                        a_tag = article.find('a')
                        if a_tag and a_tag.get('href'):
                            href = a_tag.get('href')
                            if not href.startswith('http'):
                                href = 'https://www.reuters.com' + href
                            article_links.append(href)
                
                # Bloomberg patterns
                elif "bloomberg.com" in search_url:
                    for article in soup.find_all('article'):
                        a_tag = article.find('a')
                        if a_tag and a_tag.get('href'):
                            href = a_tag.get('href')
                            if not href.startswith('http'):
                                href = 'https://www.bloomberg.com' + href
                            article_links.append(href)
                
                # Remove duplicates and limit to what we need
                article_links = list(dict.fromkeys(article_links))
                
                # Scrape content from each article link
                for link in article_links:
                    if len(articles) >= 10:
                        break
                    
                    try:
                        article_data = scrape_article_content(link, company_name)
                        if article_data:
                            articles.append(article_data)
                            print(f"Scraped article {len(articles)}: {article_data['title'][:50]}...")
                            
                            # Random delay to avoid rate limiting
                            time.sleep(random.uniform(1, 3))
                    except Exception as e:
                        print(f"Error scraping article {link}: {str(e)}")
            
            # Random delay between search sources
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            print(f"Error with search URL {search_url}: {str(e)}")
    
    return articles[:10]  # Ensure we return at most 10 articles

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
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title - try different common patterns
            title = None
            title_tags = soup.find('h1') or soup.find('title')
            if title_tags:
                title = title_tags.get_text().strip()
            
            # If no title found, skip this article
            if not title:
                return None
                
            # Check if article is relevant to the company
            if not is_relevant_to_company(soup, company_name):
                return None
            
            # Extract content - try different common patterns for article body
            content = ""
            
            # Method 1: Look for article tag
            article_tag = soup.find('article')
            if article_tag:
                paragraphs = article_tag.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs])
            
            # Method 2: Look for common content div classes
            if not content:
                for class_name in ['content', 'article-body', 'story-body', 'post-content', 'entry-content']:
                    content_div = soup.find('div', class_=re.compile(class_name, re.I))
                    if content_div:
                        paragraphs = content_div.find_all('p')
                        content = ' '.join([p.get_text().strip() for p in paragraphs])
                        break
            
            # Method 3: Just get all paragraphs if specific containers weren't found
            if not content:
                # Get all p tags but exclude those in headers, footers, navs
                excluded_sections = ['header', 'footer', 'nav', 'aside', 'style', 'script']
                for tag in soup.find_all(excluded_sections):
                    tag.decompose()
                    
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs])
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content).strip()
            
            # If content is too short, it's probably not a real article
            if len(content) < 100:
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

def is_relevant_to_company(soup, company_name):
    """
    Check if the article is relevant to the company.
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        company_name (str): Company name to check for
    
    Returns:
        bool: True if relevant, False otherwise
    """
    # Extract all text
    text = soup.get_text().lower()
    company_pattern = re.compile(r'\b' + re.escape(company_name.lower()) + r'\b')
    
    # Count occurrences of exact company name
    count = len(company_pattern.findall(text))
    
    # If company name is mentioned at least twice, consider it relevant
    return count >= 2

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
    
    print(f"Searching for articles about {company_name}...")
    articles = scrape_company_articles(company_name)
    
    if articles:
        save_to_json(articles, company_name)
        print(f"Successfully scraped {len(articles)} articles about {company_name}")
    else:
        print(f"No articles found for {company_name}")

if __name__ == "__main__":
    main()