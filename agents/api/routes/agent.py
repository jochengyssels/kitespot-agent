from fastapi import APIRouter
from agents.kitespot import fetch_kitespots
from core.supabase_client import supabase

router = APIRouter()

@router.get("/run-kitespot-agent")
def run_kitespot_agent():
    spots = fetch_kitespots()

    for spot in spots:
        # insert or upsert spot data into Supabase
        supabase.table('kitespots').upsert(spot, on_conflict='name').execute()

    return {"status": "success", "inserted_spots": len(spots)}
