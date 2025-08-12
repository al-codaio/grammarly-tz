"""Script to scrape Grammarly help center using cloudscraper to bypass Cloudflare."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import cloudscraper
from bs4 import BeautifulSoup
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrammarlyCloudScraper:
    """Scraper for Grammarly help center using cloudscraper."""
    
    def __init__(self, base_url: str = "https://support.grammarly.com"):
        self.base_url = base_url
        self.visited_urls = set()
        self.articles = []
        
        # Create cloudscraper instance
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
    
    def fetch_page(self, url: str) -> tuple[str, int]:
        """Fetch a page using cloudscraper."""
        try:
            logger.info(f"Fetching: {url}")
            response = self.scraper.get(url, timeout=30)
            return response.text, response.status_code
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return "", 0
    
    def test_access(self):
        """Test if we can access the help center."""
        test_urls = [
            self.base_url,
            f"{self.base_url}/hc/en-us",
            f"{self.base_url}/hc/en-us/categories"
        ]
        
        for url in test_urls:
            content, status = self.fetch_page(url)
            logger.info(f"URL: {url}, Status: {status}, Length: {len(content)}")
            
            if status == 200:
                logger.info("Successfully bypassed Cloudflare!")
                return True
            
            time.sleep(2)
        
        return False
    
    def parse_article(self, url: str) -> Dict[str, Any]:
        """Parse a help article."""
        content, status = self.fetch_page(url)
        
        if status != 200 or not content:
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        
        article = {
            "url": url,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Title
        title_elem = soup.find('h1') or soup.find('h2', class_='article-title') or soup.find('title')
        article["title"] = title_elem.get_text(strip=True) if title_elem else ""
        
        # Content
        content_elem = None
        for selector in ['.article-content', '.article-body', 'article', '.article', 'main']:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if content_elem:
            for script in content_elem(['script', 'style']):
                script.decompose()
            article["content"] = content_elem.get_text(separator='\n', strip=True)
        else:
            article["content"] = ""
        
        # Category
        breadcrumb = soup.select_one('nav[aria-label*="readcrumb"], .breadcrumbs, ol.breadcrumb')
        if breadcrumb:
            items = breadcrumb.find_all(['li', 'a'])
            if len(items) > 1:
                article["category"] = items[-2].get_text(strip=True)
            else:
                article["category"] = "General"
        else:
            article["category"] = "General"
        
        # Tags
        tags = []
        for tag in soup.select('.article-tag, .tag, .label'):
            tag_text = tag.get_text(strip=True)
            if tag_text and tag_text not in tags:
                tags.append(tag_text)
        article["tags"] = tags
        
        return article
    
    def get_article_links(self, page_url: str) -> List[str]:
        """Extract article links from a page."""
        content, status = self.fetch_page(page_url)
        
        if status != 200:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/articles/' in href or '/hc/en-us/articles/' in href:
                if href.startswith('/'):
                    href = self.base_url + href
                elif not href.startswith('http'):
                    href = self.base_url + '/' + href
                
                if href not in self.visited_urls:
                    links.append(href)
        
        return links
    
    def scrape_help_center(self, max_articles: int = None):
        """Scrape the help center."""
        # Test access first
        if not self.test_access():
            logger.error("Cannot bypass Cloudflare protection")
            return []
        
        # Try to get categories
        categories_url = f"{self.base_url}/hc/en-us"
        content, status = self.fetch_page(categories_url)
        
        article_urls = []
        
        if status == 200:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find category and section links
            category_links = []
            section_links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/categories/' in href:
                    full_url = self.base_url + href if href.startswith('/') else href
                    if full_url not in category_links:
                        category_links.append(full_url)
                elif '/sections/' in href:
                    full_url = self.base_url + href if href.startswith('/') else href
                    if full_url not in section_links:
                        section_links.append(full_url)
            
            # Also get sections from each category page
            for category_url in category_links[:]:
                logger.info(f"Getting sections from category: {category_url}")
                cat_content, cat_status = self.fetch_page(category_url)
                if cat_status == 200:
                    cat_soup = BeautifulSoup(cat_content, 'html.parser')
                    for link in cat_soup.find_all('a', href=True):
                        href = link['href']
                        if '/sections/' in href:
                            full_url = self.base_url + href if href.startswith('/') else href
                            if full_url not in section_links:
                                section_links.append(full_url)
                time.sleep(1)
            
            # Combine all links
            all_links = category_links + section_links
            all_links = list(set(all_links))  # Remove duplicates
            
            logger.info(f"Found {len(category_links)} categories and {len(section_links)} sections")
            
            # Get articles from ALL categories and sections
            logger.info("Collecting articles from all categories and sections...")
            for i, url in enumerate(all_links):
                logger.info(f"Processing {i+1}/{len(all_links)}: {url}")
                links = self.get_article_links(url)
                logger.info(f"  Found {len(links)} articles")
                article_urls.extend(links)
                
                if max_articles and len(article_urls) >= max_articles:
                    break
                
                time.sleep(2)
        
        # If no categories, try predefined URLs
        if not article_urls:
            predefined_categories = [
                f"{self.base_url}/hc/en-us/categories/115000091312-Getting-Started",
                f"{self.base_url}/hc/en-us/categories/115000091332-Using-Grammarly",
                f"{self.base_url}/hc/en-us/sections/115001494251-Browser-Extension"
            ]
            
            for category_url in predefined_categories:
                links = self.get_article_links(category_url)
                article_urls.extend(links)
                time.sleep(2)
        
        # Remove duplicates and optionally limit
        article_urls = list(set(article_urls))
        if max_articles:
            article_urls = article_urls[:max_articles]
        
        # Scrape articles
        logger.info(f"Scraping {len(article_urls)} articles...")
        
        for i, url in enumerate(article_urls):
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                logger.info(f"Scraping article {i+1}/{len(article_urls)}: {url}")
                
                article = self.parse_article(url)
                if article and article.get("content"):
                    self.articles.append(article)
                    logger.info(f"Successfully scraped: {article.get('title', 'No title')}")
                
                time.sleep(2)  # Be polite
        
        logger.info(f"Scraped {len(self.articles)} articles successfully")
        return self.articles
    
    def save_articles(self, output_dir: str = "../data/scraped"):
        """Save scraped articles to JSON files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save individual articles
        for i, article in enumerate(self.articles):
            filename = output_path / f"article_{i:04d}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(article, f, indent=2, ensure_ascii=False)
        
        # Save summary
        summary = {
            "total_articles": len(self.articles),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "categories": list(set(a.get("category", "") for a in self.articles)),
            "articles": [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "category": a.get("category", "")
                }
                for a in self.articles
            ]
        }
        
        with open(output_path / "summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.articles)} articles to {output_path}")


def main():
    """Main function to run the scraper."""
    scraper = GrammarlyCloudScraper()
    # Scrape entire help center (no article limit)
    scraper.scrape_help_center(max_articles=None)
    scraper.save_articles()


if __name__ == "__main__":
    main()