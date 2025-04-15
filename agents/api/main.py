from fastapi import FastAPI
from api.routes.agent import router as agent_router
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Kitespot Agent API is running"}

# Register all routes
app.include_router(agent_router, prefix="/agent")
