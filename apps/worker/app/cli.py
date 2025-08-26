"""
CLI entrypoint to run a single scrape cycle without a long-running service.

Use cases:
- Local/manual run: python -m app.cli --max-items 50
- GitHub Actions scheduled run: calls the same entry

Behavior:
- Reads enabled sources from the database
- Scrapes each source (home/trending/listing) via SaveeScraper
- Uploads media to R2 (image/video + optional poster)
- Upserts into core.blocks with ON CONFLICT DO UPDATE
- Records a run in public.runs with counters
"""
import argparse
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from .config import settings
from .logging_config import setup_logging
from .models import Source, Run, Block
from .scraper.savee import SaveeScraper
from .storage.r2 import R2Storage


logger = setup_logging(__name__)


def _detect_source_kind(url: str, declared_type: Optional[str]) -> str:
    """Return one of: 'home' | 'trending' | 'listing'.

    - Prefer URL-based detection
    - Fallback to declared_type if helpful
    - Default to 'listing'
    """
    if not url:
        return 'listing'

    u = url.lower().strip()
    if u in {"https://savee.com", "https://savee.com/", "savee.com", "http://savee.com", "http://savee.com/"}:
        return 'home'
    if "savee.com/pop" in u or "savee.com/trending" in u or "savee.com/popular" in u:
        return 'trending'

    if declared_type in {"home", "trending"}:
        return declared_type
    return 'listing'


async def _upsert_block(
    session: AsyncSession,
    source_id,
    item,
    media_key: str,
    video_poster_key: Optional[str],
):
    """Upsert a block using ON CONFLICT DO UPDATE.

    Maps from ScrapedItem -> core.blocks schema.
    """
    upsert_data = {
        'source_id': source_id,
        'external_id': item.external_id,
        'title_raw': item.title,
        'description_raw': item.description,
        'tags_raw': item.tags or [],
        'media_key': media_key,
        'media_type': item.media_type,
        'video_poster_key': video_poster_key,
        'url': item.source_url,
        'source_api_url': None,
        'source_original_url': item.media_url,
        'sidebar_info': {},
        'og_title': None,
        'og_description': None,
        'og_image_url': None,
        'og_url': None,
        'updated_at': func.current_timestamp(),
    }

    stmt = insert(Block).values(**upsert_data)
    stmt = stmt.on_conflict_do_update(
        constraint='uq_core_blocks_source_external',
        set_={
            'title_raw': stmt.excluded.title_raw,
            'description_raw': stmt.excluded.description_raw,
            'tags_raw': stmt.excluded.tags_raw,
            'media_key': stmt.excluded.media_key,
            'media_type': stmt.excluded.media_type,
            'video_poster_key': stmt.excluded.video_poster_key,
            'url': stmt.excluded.url,
            'source_api_url': stmt.excluded.source_api_url,
            'source_original_url': stmt.excluded.source_original_url,
            'sidebar_info': stmt.excluded.sidebar_info,
            'og_title': stmt.excluded.og_title,
            'og_description': stmt.excluded.og_description,
            'og_image_url': stmt.excluded.og_image_url,
            'og_url': stmt.excluded.og_url,
            'updated_at': stmt.excluded.updated_at,
        }
    )

    await session.execute(stmt)


async def _process_source(
    session: AsyncSession,
    storage: R2Storage,
    scraper: SaveeScraper,
    source_id,
    source_url: str,
    source_type: str,
    max_items: int,
) -> Dict[str, int]:
    """Scrape and upsert items for a single source; return counters."""
    counters = {
        'items_found': 0,
        'items_uploaded': 0,
        'items_upserted': 0,
        'errors': 0,
    }

    # Create run record
    run = Run(
        source_id=source_id,
        kind='manual',
        status='running',
        counters=None,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    try:
        kind = _detect_source_kind(source_url, source_type)
        if kind == 'home':
            items = await scraper.scrape_home(max_items=max_items)
        elif kind == 'trending':
            items = await scraper.scrape_trending(max_items=max_items)
        else:
            items = await scraper.scrape_listing(source_url, max_items=max_items)

        counters['items_found'] = len(items)

        for item in items:
            try:
                media_key = None
                video_poster_key = None
                base_key = f"blocks/{item.external_id}"

                if item.media_type == 'image':
                    media_key = await storage.upload_image(item.media_url, base_key)
                elif item.media_type == 'video':
                    media_key = await storage.upload_video(item.media_url, base_key)
                    if getattr(item, 'thumbnail_url', None):
                        try:
                            video_poster_key = await storage.upload_image(item.thumbnail_url, base_key)
                        except Exception:
                            video_poster_key = None
                else:
                    # Skip unsupported media types
                    continue

                counters['items_uploaded'] += 1

                await _upsert_block(
                    session=session,
                    source_id=source_id,
                    item=item,
                    media_key=media_key or '',
                    video_poster_key=video_poster_key,
                )
                await session.commit()
                counters['items_upserted'] += 1
            except Exception as e:
                logger.error(f"Failed to process item {getattr(item, 'external_id', 'unknown')}: {e}")
                counters['errors'] += 1

        run.status = 'success'
        run.finished_at = datetime.now(timezone.utc)
        run.counters = counters
        session.add(run)
        await session.commit()
        return counters
    except Exception as e:
        logger.error(f"Source run failed for {source_id}: {e}")
        run.status = 'error'
        run.finished_at = datetime.now(timezone.utc)
        run.error = str(e)
        run.counters = counters
        session.add(run)
        await session.commit()
        return counters


async def run_once(max_items: int = 50, only_enabled: bool = True, limit_sources: Optional[int] = None) -> Dict[str, Dict[str, int]]:
    """Run one scrape cycle across sources; return per-source counters."""
    engine = create_async_engine(settings.async_database_url)
    Session = async_sessionmaker(engine)

    async with Session() as session:
        # Load sources
        stmt = select(Source)
        if only_enabled:
            stmt = stmt.where(Source.enabled == True)  # noqa: E712
        if limit_sources:
            stmt = stmt.limit(limit_sources)

        result = await session.execute(stmt)
        sources: List[Source] = list(result.scalars().all())

        if not sources:
            logger.info("No sources found (or enabled). Nothing to do.")
            await engine.dispose()
            return {}

        # Extract all source attributes upfront to avoid SQLAlchemy session issues
        source_data = []
        for src in sources:
            source_data.append({
                'id': src.id,
                'name': src.name,
                'type': src.type,
                'url': src.url,
            })

        out: Dict[str, Dict[str, int]] = {}
        scraper = SaveeScraper()
        async with R2Storage() as storage:
            for src_data in source_data:
                src_id = str(src_data['id'])
                src_name = src_data['name']
                src_type = src_data['type']
                src_url = src_data['url']
                logger.info(f"Processing source {src_id} - {src_name} [{src_type}] {src_url}")
                counters = await _process_source(
                    session, storage, scraper, 
                    src_data['id'], src_data['url'], src_data['type'], 
                    max_items
                )
                out[src_id] = counters

    await engine.dispose()
    return out


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one scrape cycle")
    parser.add_argument("--max-items", type=int, default=50, help="Max items per source")
    parser.add_argument("--all", action="store_true", help="Include disabled sources as well")
    parser.add_argument("--limit-sources", type=int, default=None, help="Process only first N sources")
    return parser.parse_args()


def main():
    args = _parse_args()
    out = asyncio.run(run_once(max_items=args.max_items, only_enabled=(not args.all), limit_sources=args.limit_sources))
    # Minimal stdout for CI visibility
    for source_id, counters in out.items():
        logger.info(f"Source {source_id} -> {counters}")


if __name__ == "__main__":
    main()


