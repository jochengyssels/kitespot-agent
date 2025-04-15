from fastapi import APIRouter
import logging
import asyncio

from agents.kitespot_agent import KitespotDiscoveryCrawler
from agents.kitespot_image_enrichment import KitespotImageEnrichmentAgent

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/kitespot-agent")
async def run_kitespot_agent():
    logger.info("Triggered Kitespot Discovery Agent")

    crawler = KitespotDiscoveryCrawler()

    # Set test_mode=False for production
    new_spots_count = await crawler.discover_kitespots(test_mode=False)

    logger.info(f"Kitespot Discovery Agent finished - {new_spots_count} new spots inserted")

    return {
        "status": "success",
        "new_spots_added": new_spots_count
    }



@router.get("/kitespot-image-enrichment")
async def run_kitespot_image_enrichment():
    logger.info("Triggered Kitespot Image Enrichment Agent")

    agent = KitespotImageEnrichmentAgent()
    agent.enrich_kitespot_images()

    logger.info("Kitespot Image Enrichment Agent finished")

    return {
        "status": "success",
        "message": "Image enrichment completed"
    }
    