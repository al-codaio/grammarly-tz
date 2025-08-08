"""Script to scrape Grammarly help center articles."""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import logging
from pathlib import Path


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrammarlyHelpScraper:
    """Scraper for Grammarly help center articles."""
    
    def __init__(self, base_url: str = "https://support.grammarly.com"):
        self.base_url = base_url
        self.session = httpx.AsyncClient(timeout=30.0)
        self.visited_urls = set()
        self.articles = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    async def fetch_page(self, url: str) -> str:
        """Fetch a page and return its content."""
        try:
            response = await self.session.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""
    
    async def parse_article(self, url: str) -> Dict[str, Any]:
        """Parse a help article."""
        content = await self.fetch_page(url)
        if not content:
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract article data
        article = {
            "url": url,
            "scraped_at": datetime.utcnow().isoformat()
        }
        
        # Title
        title_elem = soup.find('h1') or soup.find('h2')
        article["title"] = title_elem.get_text(strip=True) if title_elem else ""
        
        # Content
        content_elem = soup.find('div', class_='article-content') or soup.find('article')
        if content_elem:
            # Remove script and style elements
            for script in content_elem(["script", "style"]):
                script.decompose()
            article["content"] = content_elem.get_text(separator='\n', strip=True)
        else:
            article["content"] = ""
        
        # Category/breadcrumbs
        breadcrumb_elem = soup.find('nav', {'aria-label': 'Breadcrumb'}) or soup.find('ol', class_='breadcrumb')
        if breadcrumb_elem:
            breadcrumbs = [li.get_text(strip=True) for li in breadcrumb_elem.find_all('li')]
            article["category"] = breadcrumbs[-2] if len(breadcrumbs) > 1 else "General"
        else:
            article["category"] = "General"
        
        # Tags
        tags = []
        tag_elements = soup.find_all('a', class_='article-tag') or soup.find_all('span', class_='label')
        for tag in tag_elements:
            tags.append(tag.get_text(strip=True))
        article["tags"] = tags
        
        return article
    
    async def get_article_links(self, page_url: str) -> List[str]:
        """Extract article links from a category or section page."""
        content = await self.fetch_page(page_url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        links = []
        
        # Find article links
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Filter for article links
            if '/articles/' in href or '/hc/en-us/articles/' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in self.visited_urls:
                    links.append(full_url)
        
        return links
    
    async def scrape_help_center(self, max_articles: int = 500):
        """Scrape the help center."""
        # Main categories to explore
        categories = [
            "/hc/en-us/categories/115000091312-Getting-Started",
            "/hc/en-us/categories/115000091332-Using-Grammarly",
            "/hc/en-us/categories/115000091372-Account",
            "/hc/en-us/categories/115000018311-Billing-and-Subscription",
            "/hc/en-us/categories/360000053212-Technical-Issues",
            "/hc/en-us/sections/115001509692-Grammarly-for-Microsoft-Office",
            "/hc/en-us/sections/115001494251-Browser-Extension",
            "/hc/en-us/sections/360007930512-Grammarly-Business"
        ]
        
        # Collect article URLs
        article_urls = []
        for category in categories:
            category_url = urljoin(self.base_url, category)
            logger.info(f"Scraping category: {category_url}")
            links = await self.get_article_links(category_url)
            article_urls.extend(links)
            
            if len(article_urls) >= max_articles:
                break
        
        # Remove duplicates
        article_urls = list(set(article_urls))[:max_articles]
        
        # Scrape articles
        logger.info(f"Scraping {len(article_urls)} articles...")
        tasks = []
        for url in article_urls:
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                tasks.append(self.parse_article(url))
        
        # Process in batches to avoid overwhelming the server
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict) and result.get("content"):
                    self.articles.append(result)
            
            # Be polite
            await asyncio.sleep(1)
        
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
            "scraped_at": datetime.utcnow().isoformat(),
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


async def main():
    """Main function to run the scraper."""
    async with GrammarlyHelpScraper() as scraper:
        await scraper.scrape_help_center(max_articles=100)  # Start with 100 for testing
        scraper.save_articles()


if __name__ == "__main__":
    asyncio.run(main())