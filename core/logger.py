import logging
import uuid
from datetime import datetime
from core.supabase_client import supabase

logger = logging.getLogger("agent")


def log_agent_action(agent_name: str, status: str, metadata: dict = None):
    """
    Store a structured log entry in the Supabase agent_logs table

    Args:
        agent_name (str): Name of the agent (example: 'kitespot_image_enrichment')
        status (str): Status of the action (example: 'started', 'finished', 'error')
        metadata (dict): Optional additional data to store
    """
    try:
        payload = {
            "id": str(uuid.uuid4()),
            "agent_name": agent_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        logger.info(f"[{agent_name}] {status} — {metadata}")
        supabase.table("agent_logs").insert(payload).execute()
    except Exception as e:
        logger.error(f"Failed to log agent action: {e}")
