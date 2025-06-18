"""Universal URL reader that can handle both RSS feeds and regular web pages."""

import feedparser
import httpx
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
from datetime import datetime

from reader.html_to_markdown import extract_content_from_html, is_html_content


class ReaderError(Exception):
    """Custom exception for reader errors."""
    pass


class Reader:
    """A universal reader that can process both RSS feeds and web pages."""
    
    def __init__(
        self,
        user_agent: str = "Reader/1.0",
        timeout: int = 30,
        max_articles: int = 50,
        use_readability: bool = True
    ):
        """Initialize the universal reader.
        
        Args:
            user_agent: User agent string for HTTP requests
            timeout: Request timeout in seconds
            max_articles: Maximum number of articles to process from RSS feeds
            use_readability: Whether to use readability algorithm for HTML content
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_articles = max_articles
        self.use_readability = use_readability
    
    def is_rss_feed(self, content: str, content_type: str = "", url: str = "") -> bool:

        if any(feed_type in content_type.lower() for feed_type in [
            'application/rss+xml',
            'application/atom+xml',
            'application/xml',
            'text/xml'
        ]):
            return True
        
        # Check URL patterns
        if any(pattern in url.lower() for pattern in [
            '/rss', '/feed', '/atom', '.rss', '.xml'
        ]):
            # Additional content check for URLs with feed-like patterns
            content_lower = content[:1000].lower()
            if any(tag in content_lower for tag in [
                '<rss', '<feed', '<atom', 'xmlns="http://www.w3.org/2005/atom'
            ]):
                return True
        
        # Check content for RSS/Atom elements
        content_check = content[:2000].lower()
        rss_indicators = [
            '<rss',
            '<feed',
            '<atom',
            'xmlns="http://www.w3.org/2005/atom',
            'xmlns="http://purl.org/rss/',
            '<channel>',
            '<item>',
            '<entry>'
        ]
        
        return any(indicator in content_check for indicator in rss_indicators)
    
    async def fetch_content(self, url: str) -> Tuple[str, str]:
        """Fetch content from URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (content, content_type)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    follow_redirects=True
                )
                response.raise_for_status()
                return response.text, response.headers.get("content-type", "")
            except httpx.RequestError as e:
                raise ReaderError(f"Failed to fetch {url}: {e}")
            except httpx.HTTPStatusError as e:
                raise ReaderError(f"HTTP error for {url}: {e.response.status_code}")
    
    def process_rss_feed(self, content: str, url: str) -> Dict:
        """Process RSS/Atom feed content.
        
        Args:
            content: RSS/Atom content
            url: Original URL
            
        Returns:
            Dictionary with processed feed data
        """
        try:
            feed = feedparser.parse(content)
            
            if feed.bozo and not feed.entries:
                raise ReaderError(f"Invalid RSS feed: {feed.bozo_exception}")
            
            # Extract feed metadata
            feed_info = {
                'type': 'rss_feed',
                'url': url,
                'title': feed.feed.get('title', 'Unknown Feed'),
                'description': feed.feed.get('description', ''),
                'link': feed.feed.get('link', ''),
                'updated': feed.feed.get('updated', ''),
                'total_entries': len(feed.entries),
                'processed_entries': min(len(feed.entries), self.max_articles),
                'articles': []
            }
            
            # Process articles
            for entry in feed.entries[:self.max_articles]:
                article = {
                    'title': entry.get('title', 'No Title'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'content': self._extract_entry_content(entry),
                    'published': entry.get('published', ''),
                    'author': entry.get('author', ''),
                    'tags': [tag.get('term', '') for tag in entry.get('tags', [])],
                    'id': entry.get('id', entry.get('link', ''))
                }
                feed_info['articles'].append(article)
            
            return feed_info
            
        except Exception as e:
            raise ReaderError(f"Failed to parse RSS feed: {e}")
    
    def _extract_entry_content(self, entry) -> str:
        """Extract content from RSS entry."""
        # Try to get full content first
        if hasattr(entry, 'content') and entry.content:
            for content_item in entry.content:
                if content_item.get('value'):
                    content = content_item['value']
                    if is_html_content(content):
                        return extract_content_from_html(content, self.use_readability)
                    return content
        
        # Fall back to summary
        summary = entry.get('summary', '')
        if summary and is_html_content(summary):
            return extract_content_from_html(summary, self.use_readability)
        
        return summary
    
    def process_web_page(self, content: str, url: str, content_type: str) -> Dict:
        """Process regular web page content.
        
        Args:
            content: Web page content
            url: Original URL
            content_type: HTTP content-type header
            
        Returns:
            Dictionary with processed page data
        """
        try:
            if is_html_content(content, content_type):
                markdown_content = extract_content_from_html(content, self.use_readability)
            else:
                markdown_content = content
            
            # Extract title from HTML if possible
            title = self._extract_page_title(content) if is_html_content(content, content_type) else "Unknown Title"
            
            return {
                'type': 'web_page',
                'url': url,
                'title': title,
                'content_type': content_type,
                'content': markdown_content,
                'original_length': len(content),
                'processed_length': len(markdown_content)
            }
            
        except Exception as e:
            raise ReaderError(f"Failed to process web page: {e}")
    
    def _extract_page_title(self, html_content: str) -> str:
        """Extract title from HTML content."""
        import re
        
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            return title
        
        return "Unknown Title"
    
    async def read(self, url: str) -> Dict:
        """Read and process content from URL.
        
        Args:
            url: URL to read (can be RSS feed or web page)
            
        Returns:
            Dictionary with processed content
        """
        if not url.strip():
            raise ReaderError("URL cannot be empty")
        
        # Ensure URL has scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            # Fetch content
            content, content_type = await self.fetch_content(url)
            
            # Determine content type and process accordingly
            if self.is_rss_feed(content, content_type, url):
                return self.process_rss_feed(content, url)
            else:
                return self.process_web_page(content, url, content_type)
                
        except Exception as e:
            if isinstance(e, ReaderError):
                raise
            raise ReaderError(f"Unexpected error processing {url}: {e}")
    
    def format_output(self, result: Dict) -> str:
        """Format the processed result as readable text.
        
        Args:
            result: Processed result dictionary
            
        Returns:
            Formatted text output
        """
        if result['type'] == 'rss_feed':
            return self._format_rss_output(result)
        else:
            return self._format_page_output(result)
    
    def _format_rss_output(self, result: Dict) -> str:
        """Format RSS feed result."""
        output = []
        output.append(f"# RSS Feed: {result['title']}")
        output.append(f"**URL**: {result['url']}")
        output.append(f"**Description**: {result['description']}")
        output.append(f"**Total Articles**: {result['total_entries']} (showing {result['processed_entries']})")
        output.append("")
        
        for i, article in enumerate(result['articles'], 1):
            output.append(f"## Article {i}: {article['title']}")
            output.append(f"**Link**: {article['link']}")
            output.append(f"**Published**: {article['published']}")
            if article['author']:
                output.append(f"**Author**: {article['author']}")
            if article['tags']:
                output.append(f"**Tags**: {', '.join(article['tags'])}")
            output.append("")
            
            # Use content if available, otherwise summary
            content = article['content'] if article['content'] else article['summary']
            if content:
                output.append(content)
            output.append("")
            output.append("---")
            output.append("")
        
        return '\n'.join(output)
    
    def _format_page_output(self, result: Dict) -> str:
        """Format web page result."""
        output = []
        output.append(f"# {result['title']}")
        output.append(f"**URL**: {result['url']}")
        output.append(f"**Content Type**: {result['content_type']}")
        output.append("")
        output.append(result['content'])
        
        return '\n'.join(output)


# Convenience function for one-off usage
async def read_url(
    url: str,
    user_agent: str = "Reader/1.0",
    timeout: int = 30,
    max_articles: int = 50,
    use_readability: bool = True,
    format_output: bool = True
) -> Union[str, Dict]:
    """Read and process content from URL.
    
    Args:
        url: URL to read
        user_agent: User agent string
        timeout: Request timeout
        max_articles: Max articles for RSS feeds
        use_readability: Use readability for HTML
        format_output: Return formatted string instead of dict
        
    Returns:
        Processed content as string or dictionary
    """
    reader = Reader(
        user_agent=user_agent,
        timeout=timeout,
        max_articles=max_articles,
        use_readability=use_readability
    )
    
    result = await reader.read(url)
    
    if format_output:
        return reader.format_output(result)
    else:
        return result


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_reader():
        urls = [
            "https://feeds.bbci.co.uk/news/rss.xml",  # RSS feed
            "https://www.example.com",  # Regular web page
        ]
        
        for url in urls:
            try:
                print(f"Reading: {url}")
                content = await read_url(url)
                print(content)
                print("=" * 80)
            except ReaderError as e:
                print(f"Error reading {url}: {e}")
    
    asyncio.run(test_reader()) 