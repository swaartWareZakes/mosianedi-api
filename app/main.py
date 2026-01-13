# app/main.py

from pathlib import Path
from dotenv import load_dotenv

# -------------------------------------------------------------------
# 1. Load .env BEFORE importing anything else
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# -------------------------------------------------------------------
# 2. FastAPI + CORS
# -------------------------------------------------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# -------------------------------------------------------------------
# 3. Router Imports
# -------------------------------------------------------------------
# Core Project & Proposal Logic
from app.routers.projects import router as projects_router
from app.proposal_data.router import router as proposal_data_router

# Analysis & Forecasting
from app.network_snapshot.router import router as network_snapshot_router
from app.scenarios.router import router as scenarios_router
from app.computation.router import router as computation_router

# Dashboards (Uncomment when ready)
# from app.dashboards.router import router as dashboards_router 

# NOTE: 'provincial_stats' has been removed as it is replaced by 'proposal_data'.

# -------------------------------------------------------------------
# 4. App Config
# -------------------------------------------------------------------
app = FastAPI(
    title="Mosianedi Investment API",
    description="API Gateway for Provincial Road Budget Proposals & Forecasting.",
    version="1.0.0",
)

# -------------------------------------------------------------------
# 5. Middleware
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# 6. Register Routes
# -------------------------------------------------------------------

# A. Projects (The Proposal Container)
app.include_router(
    projects_router,
    prefix="/api/v1/projects",
    tags=["Projects"],
)

# B. Proposal Inputs (The Green Blocks)
app.include_router(
    proposal_data_router,
    prefix="/api/v1/projects",
    tags=["Proposal Inputs"],
)

# C. Network Snapshot (The Current State Visuals)
app.include_router(
    network_snapshot_router, 
    prefix="/api/v1/projects", 
    tags=["Network Snapshot"]
)

# D. Forecasts (The Future Variables - Inflation, Deterioration)
app.include_router(
    scenarios_router, 
    prefix="/api/v1/projects", 
    tags=["Forecast & Strategy"]
)

# E. Computation (The Math Engine)
app.include_router(
    computation_router,
    prefix="/api/v1/projects",
    tags=["Computation Engine"]
)

# F. Dashboards (Future)
# app.include_router(
#     dashboards_router, 
#     prefix="/api/v1/projects", 
#     tags=["Dashboards"]
# )

# -------------------------------------------------------------------
# 7. Health Check
# -------------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Mosianedi Investment API",
        "version": "1.0.0"
    }