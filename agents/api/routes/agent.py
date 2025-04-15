from fastapi import APIRouter, HTTPException
from agents.kitespot import fetch_kitespots
from core.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/run-kitespot-agent")
def run_kitespot_agent():
    logger.info("Kitespot agent started.")

    spots = fetch_kitespots()

    if not spots:
        logger.warning("No kitespots found or fetched.")
        raise HTTPException(status_code=404, detail="No kitespots found")

    for spot in spots:
        try:
            supabase.table('kitespots').upsert(
                spot,
                on_conflict='name'  # Adjust depending on your uniqueness constraints
            ).execute()
            logger.info(f"Upserted spot: {spot['name']}")
        except Exception as e:
            logger.error(f"Failed to upsert spot {spot['name']}: {e}")

    logger.info(f"Agent finished. {len(spots)} spots processed.")

    return {
        "status": "success",
        "total_spots_processed": len(spots)
    }
