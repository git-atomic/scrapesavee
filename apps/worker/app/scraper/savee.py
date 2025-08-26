"""
Production-ready Savee.com scraper
"""
import asyncio
from typing import List, Optional, Set

from .core import SaveeSession, ScrapedItem
from ..logging_config import setup_logging

logger = setup_logging(__name__)


class SaveeScraper:
    """Production-ready Savee.com scraper"""
    
    def __init__(self):
        self.seen_items: Set[str] = set()
        
    async def scrape_listing(self, url: str, max_items: int = 50) -> List[ScrapedItem]:
        """Scrape a Savee listing page"""
        items = []
        
        async with SaveeSession() as session:
            try:
                logger.info(f"Scraping listing: {url}")
                
                # Navigate to the page
                await session.page.goto(url, wait_until='networkidle')
                
                # Wait for content to load
                await session.page.wait_for_selector('.item', timeout=10000)
                
                # Scroll to load more items
                await self._scroll_and_load(session.page, max_items)
                
                # Extract item links
                item_links = await session.page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('.item a');
                        return Array.from(items).map(a => a.href).filter(href => href.includes('/i/'));
                    }
                """)
                
                logger.info(f"Found {len(item_links)} item links")
                
                # Process each item
                for i, item_url in enumerate(item_links[:max_items]):
                    if item_url in self.seen_items:
                        continue
                        
                    try:
                        item = await self._scrape_item(session, item_url)
                        if item:
                            items.append(item)
                            self.seen_items.add(item_url)
                            
                        # Rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error scraping item {item_url}: {e}")
                        continue
                        
                    if i % 10 == 0:
                        logger.info(f"Processed {i+1}/{len(item_links)} items")
                        
            except Exception as e:
                logger.error(f"Error scraping listing {url}: {e}")
                
        logger.info(f"Scraped {len(items)} items from {url}")
        return items
        
    async def _scroll_and_load(self, page, max_items: int):
        """Scroll the page to load more items"""
        previous_height = 0
        scroll_attempts = 0
        max_scrolls = max_items // 20
        
        while scroll_attempts < max_scrolls:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            current_height = await page.evaluate("document.body.scrollHeight")
            
            if current_height == previous_height:
                load_more = await page.query_selector('.load-more, .btn-load-more')
                if load_more:
                    await load_more.click()
                    await asyncio.sleep(2)
                else:
                    break
                    
            previous_height = current_height
            scroll_attempts += 1
            
    async def _scrape_item(self, session: SaveeSession, item_url: str) -> Optional[ScrapedItem]:
        """Scrape a single item page"""
        try:
            await session.page.goto(item_url, wait_until='networkidle')
            await session.page.wait_for_selector('.media-container, .image-container', timeout=5000)
            
            # Extract item data
            item_data = await session.page.evaluate("""
                () => {
                    const data = {};
                    
                    data.external_id = window.location.pathname.split('/').pop();
                    
                    const titleEl = document.querySelector('h1, .title, .item-title');
                    data.title = titleEl ? titleEl.textContent.trim() : null;
                    
                    const descEl = document.querySelector('.description, .item-description');
                    data.description = descEl ? descEl.textContent.trim() : null;
                    
                    const authorEl = document.querySelector('.author, .username');
                    data.author = authorEl ? authorEl.textContent.trim() : null;
                    
                    const imgEl = document.querySelector('img.main-image, .media-container img');
                    const videoEl = document.querySelector('video');
                    
                    if (videoEl) {
                        data.media_type = 'video';
                        data.media_url = videoEl.src;
                        data.thumbnail_url = videoEl.poster || (imgEl ? imgEl.src : null);
                    } else if (imgEl) {
                        data.media_type = 'image';
                        data.media_url = imgEl.src || imgEl.getAttribute('data-src');
                        data.thumbnail_url = imgEl.src;
                        data.width = imgEl.naturalWidth;
                        data.height = imgEl.naturalHeight;
                    }
                    
                    const tagElements = document.querySelectorAll('.tag, .hashtag');
                    data.tags = Array.from(tagElements).map(el => el.textContent.trim().replace('#', ''));
                    
                    return data;
                }
            """)
            
            if not item_data.get('external_id') or not item_data.get('media_url'):
                return None
                
            # Get file size
            file_size = await self._get_media_size(session, item_data['media_url'])
            
            return ScrapedItem(
                external_id=item_data['external_id'],
                title=item_data.get('title'),
                description=item_data.get('description'),
                media_type=item_data['media_type'],
                media_url=item_data['media_url'],
                thumbnail_url=item_data.get('thumbnail_url'),
                source_url=item_url,
                author=item_data.get('author'),
                tags=item_data.get('tags', []),
                width=item_data.get('width'),
                height=item_data.get('height'),
                file_size=file_size
            )
            
        except Exception as e:
            logger.error(f"Error scraping item {item_url}: {e}")
            return None
            
    async def _get_media_size(self, session: SaveeSession, media_url: str) -> Optional[int]:
        """Get file size of media URL"""
        try:
            async with session.session.head(media_url) as response:
                content_length = response.headers.get('content-length')
                return int(content_length) if content_length else None
        except Exception:
            return None
            
    async def scrape_user_profile(self, username: str, max_items: int = 100) -> List[ScrapedItem]:
        """Scrape a user's profile"""
        url = f"https://savee.com/{username}"
        return await self.scrape_listing(url, max_items)
        
    async def scrape_trending(self, max_items: int = 50) -> List[ScrapedItem]:
        """Scrape trending items"""
        url = "https://savee.com/pop"
        return await self.scrape_listing(url, max_items)
        
    async def scrape_home(self, max_items: int = 50) -> List[ScrapedItem]:
        """Scrape home feed"""
        url = "https://savee.com/"
        return await self.scrape_listing(url, max_items)

