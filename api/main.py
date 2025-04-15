from fastapi import FastAPI, Request, Depends, HTTPException
import os
from api.routes import kitespot_agent, kiteschool_agent

API_KEY = os.getenv("AGENT_API_KEY")

app = FastAPI()


def verify_api_key(request: Request):
    if request.headers.get("x-api-key") != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")


# Include Routes
app.include_router(
    kitespot_agent.router,
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    kiteschool_agent.router,
    dependencies=[Depends(verify_api_key)]
)
