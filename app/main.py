# app/main.py (FINAL UPDATED VERSION)

from pathlib import Path
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Load .env BEFORE importing anything that relies on environment vars
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# -------------------------------------------------------------------
# FastAPI + CORS
# -------------------------------------------------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
# NOTE: Ensure each module's __init__.py exposes 'router' 
# or change imports to: from app.master_data.router import router as ...
from app.routers import projects
from app.master_data import router as master_data_router
from app.network_snapshot import router as network_snapshot_router
from app.scenarios import router as scenarios_router
# Only include this if the dashboards module exists to avoid startup errors
# from app.dashboards import router as dashboards_router 

# -------------------------------------------------------------------
# FastAPI APP CONFIG
# -------------------------------------------------------------------
app = FastAPI(
    title="Mosianedi Investment API",
    description="API Gateway for RONET computation and scenario management.",
)


# -------------------------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all — adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------
app.include_router(
    projects.router,
    prefix="/api/v1/projects",
    tags=["Projects"],
)

app.include_router(
    master_data_router,
    prefix="/api/v1/projects",
    tags=["Master Data"],
)

app.include_router(
    network_snapshot_router, 
    prefix="/api/v1/projects", 
    tags=["Network"]
)

app.include_router(
    scenarios_router, 
    prefix="/api/v1/projects", 
    tags=["Scenarios"]
)

# Uncomment when the dashboards module is ready
# app.include_router(
#     dashboards_router, 
#     prefix="/api/v1/projects", 
#     tags=["Dashboards"]
# )

# -------------------------------------------------------------------
# ROOT PING / HEALTHCHECK
# -------------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "status": "ok",
        "service": "Mosianedi Investment API"
    }