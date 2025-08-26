"""
Individual item scraper for extracting detailed item information
Handles scraping of specific Savee.com item pages
"""
import asyncio
import json
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

import aiohttp
from playwright.async_api import async_playwright, Page, Browser

from ..config import settings
from ..logging_config import get_logger, PerformanceLogger
from ..models import Source

logger = get_logger(__name__)


class ItemScraper:
    """
    Handles scraping of individual Savee.com item pages
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.base_headers = {
            "User-Agent": settings.SCRAPER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def _ensure_browser(self) -> Browser:
        """Ensure browser is initialized"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows'
                ]
            )
        return self.browser
    
    async def scrape_item(self, item_id: str, source: Optional[Source] = None) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information for a specific item
        
        Args:
            item_id: Unique item identifier
            source: Source configuration (optional)
            
        Returns:
            Dictionary containing item data or None if failed
        """
        with PerformanceLogger(logger, f"scrape_item_{item_id}", item_id=item_id):
            try:
                # Build item URL - customize for Savee.com structure
                item_url = self._build_item_url(item_id, source)
                
                logger.info(
                    f"Scraping item {item_id} from {item_url}",
                    extra={"item_id": item_id, "url": item_url}
                )
                
                browser = await self._ensure_browser()
                page = await browser.new_page()
                
                try:
                    await page.set_extra_http_headers(self.base_headers)
                    
                    # Navigate to item page
                    response = await page.goto(item_url, wait_until="networkidle", timeout=30000)
                    
                    if not response or response.status >= 400:
                        logger.warning(
                            f"Failed to load item page {item_id}: HTTP {response.status if response else 'no response'}",
                            extra={"item_id": item_id, "status": response.status if response else None}
                        )
                        return None
                    
                    # Extract item data
                    item_data = await self._extract_item_data(page, item_id, item_url)
                    
                    if item_data:
                        logger.info(
                            f"Successfully scraped item {item_id}",
                            extra={"item_id": item_id, "has_media": bool(item_data.get("image_url"))}
                        )
                    else:
                        logger.warning(
                            f"No data extracted for item {item_id}",
                            extra={"item_id": item_id}
                        )
                    
                    return item_data
                    
                finally:
                    await page.close()
                    
            except Exception as e:
                logger.error(
                    f"Failed to scrape item {item_id}: {e}",
                    exc_info=True,
                    extra={"item_id": item_id}
                )
                return None
    
    async def _extract_item_data(self, page: Page, item_id: str, item_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract all relevant data from item page
        This would be customized for Savee.com's actual HTML structure
        """
        try:
            # Wait for page to fully load
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Extract basic item information
            item_data = {
                "id": item_id,
                "page_url": item_url,
            }
            
            # Extract media URLs
            media_data = await self._extract_media_data(page)
            item_data.update(media_data)
            
            # Extract Open Graph metadata
            og_data = await self._extract_og_data(page)
            item_data.update(og_data)
            
            # Extract sidebar information
            sidebar_data = await self._extract_sidebar_data(page)
            if sidebar_data:
                item_data["sidebar"] = sidebar_data
            
            # Extract source information
            source_data = await self._extract_source_data(page)
            item_data.update(source_data)
            
            # Determine media type
            item_data["media_type"] = self._determine_media_type(item_data)
            
            return item_data
            
        except Exception as e:
            logger.error(f"Failed to extract item data for {item_id}: {e}")
            return None
    
    async def _extract_media_data(self, page: Page) -> Dict[str, Any]:
        """Extract media URLs from page"""
        try:
            media_data = await page.evaluate("""
                () => {
                    const data = {};
                    
                    // Look for main image
                    const mainImage = document.querySelector('img[data-main], .main-image img, .item-image img');
                    if (mainImage && mainImage.src) {
                        data.image_url = mainImage.src;
                    }
                    
                    // Look for video
                    const video = document.querySelector('video source, video[src]');
                    if (video) {
                        data.video_url = video.src || video.getAttribute('src');
                        
                        // Look for video poster
                        const videoEl = video.closest('video');
                        if (videoEl && videoEl.poster) {
                            data.video_poster_url = videoEl.poster;
                        }
                    }
                    
                    return data;
                }
            """)
            
            return media_data or {}
            
        except Exception as e:
            logger.error(f"Failed to extract media data: {e}")
            return {}
    
    async def _extract_og_data(self, page: Page) -> Dict[str, Any]:
        """Extract Open Graph metadata"""
        try:
            og_data = await page.evaluate("""
                () => {
                    const data = {};
                    const metaTags = document.querySelectorAll('meta[property^="og:"]');
                    
                    for (const meta of metaTags) {
                        const property = meta.getAttribute('property');
                        const content = meta.getAttribute('content');
                        
                        if (property && content) {
                            switch (property) {
                                case 'og:title':
                                    data.og_title = content;
                                    break;
                                case 'og:description':
                                    data.og_description = content;
                                    break;
                                case 'og:image':
                                    data.og_image_url = content;
                                    break;
                                case 'og:url':
                                    data.og_url = content;
                                    break;
                            }
                        }
                    }
                    
                    return data;
                }
            """)
            
            return og_data or {}
            
        except Exception as e:
            logger.error(f"Failed to extract OG data: {e}")
            return {}
    
    async def _extract_sidebar_data(self, page: Page) -> Optional[Dict[str, Any]]:
        """Extract sidebar metadata (tags, stats, etc.)"""
        try:
            sidebar_data = await page.evaluate("""
                () => {
                    const data = {};
                    
                    // Look for tags
                    const tags = [];
                    const tagElements = document.querySelectorAll('.tags a, .tag, [data-tag]');
                    for (const tag of tagElements) {
                        const tagText = tag.textContent?.trim();
                        if (tagText && !tags.includes(tagText)) {
                            tags.push(tagText);
                        }
                    }
                    if (tags.length > 0) {
                        data.tags = tags;
                    }
                    
                    // Look for stats
                    const stats = {};
                    const statElements = document.querySelectorAll('[data-stat], .stat');
                    for (const stat of statElements) {
                        const statName = stat.dataset.stat || stat.className.replace('stat-', '');
                        const statValue = stat.textContent?.trim();
                        if (statName && statValue) {
                            stats[statName] = statValue;
                        }
                    }
                    if (Object.keys(stats).length > 0) {
                        data.stats = stats;
                    }
                    
                    return Object.keys(data).length > 0 ? data : null;
                }
            """)
            
            return sidebar_data
            
        except Exception as e:
            logger.error(f"Failed to extract sidebar data: {e}")
            return None
    
    async def _extract_source_data(self, page: Page) -> Dict[str, Any]:
        """Extract source/attribution information"""
        try:
            source_data = await page.evaluate("""
                () => {
                    const data = {};
                    
                    // Look for API endpoint
                    const apiLink = document.querySelector('a[href*="/api/"], [data-api-url]');
                    if (apiLink) {
                        data.source_api_url = apiLink.href || apiLink.dataset.apiUrl;
                    }
                    
                    // Look for original source
                    const sourceLink = document.querySelector('.source a, [data-source-url], .original-source a');
                    if (sourceLink) {
                        data.source_original_url = sourceLink.href || sourceLink.dataset.sourceUrl;
                    }
                    
                    return data;
                }
            """)
            
            return source_data or {}
            
        except Exception as e:
            logger.error(f"Failed to extract source data: {e}")
            return {}
    
    def _determine_media_type(self, item_data: Dict[str, Any]) -> Optional[str]:
        """Determine media type based on available URLs"""
        if item_data.get("video_url"):
            return "video"
        elif item_data.get("image_url"):
            # Check if it's a GIF
            image_url = item_data["image_url"].lower()
            if ".gif" in image_url or "gif" in image_url:
                return "gif"
            else:
                return "image"
        return None
    
    def _build_item_url(self, item_id: str, source: Optional[Source] = None) -> str:
        """Build item URL from ID"""
        # Customize this for Savee.com's URL structure
        base_url = source.base_url if source else "https://savee.it"
        
        # Example URL structure - customize for actual Savee.com format
        if not base_url.endswith("/"):
            base_url += "/"
        
        return f"{base_url}item/{item_id}"
    
    async def close(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
            self.browser = None


# Global instance
_item_scraper = ItemScraper()


async def get_item_scraper() -> ItemScraper:
    """Get global item scraper instance"""
    return _item_scraper
