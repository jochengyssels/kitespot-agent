from fastapi import APIRouter
from agents.kiteschool_agent import KiteschoolAgent
import logging

logger = logging.getLogger("api.routes.kiteschool_agent")

router = APIRouter()

@router.get("/agent/kiteschool-agent")
async def run_kiteschool_agent():
    logger.info("Triggered Kiteschool Agent")
    agent = KiteschoolAgent()
    agent.enrich_kiteschools()
    logger.info("Kiteschool Agent finished")
    return {"status": "success"}
