from fastapi import FastAPI
from api.routes.agent import router as agent_router

app = FastAPI()

app.include_router(agent_router, prefix="/agent")

@app.get("/")
def root():
    return {"status": "Kitespot Agent API ready"}
