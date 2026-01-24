# app/main.py

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# -------------------------------------------------------------------
# 1. Load .env
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# -------------------------------------------------------------------
# 2. Router Imports
# -------------------------------------------------------------------
# Core Project & User context
from app.routers.projects import router as projects_router
from app.proposal_data.router import router as proposal_data_router

# Provincial data inputs (province-by-province)
from app.routers.provincial_stats import router as provincial_stats_router
# from app.routers.master_data import router as master_data_router

# The 3 Pillars of the App
from app.network_snapshot.router import router as network_snapshot_router
from app.scenarios.router import router as scenarios_router
from app.computation.router import router as computation_router

# Treasury Extensions
from app.ai_advisor.router import router as ai_router
from app.reports.router import router as reports_router

# -------------------------------------------------------------------
# 3. App Config
# -------------------------------------------------------------------
app = FastAPI(
    title="Mosianedi Investment API",
    description="API Gateway for Provincial Road Budget Proposals & Forecasting.",
    version="1.0.0",
)

# -------------------------------------------------------------------
# 4. CORS Middleware
# -------------------------------------------------------------------
origins = [
    "http://localhost:3000",                       # Local Development
    "http://localhost:3001",                       # Optional alt dev port
    "https://mosianedi-frontend.vercel.app",       # Production Frontend
    # "https://mosianedi-frontend-git-main.vercel.app",  # Preview deployments
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# 5. Register Routes
# -------------------------------------------------------------------
# Everything stays under /api/v1/projects to keep project context consistent.

# Projects + Proposal Inputs
app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(proposal_data_router, prefix="/api/v1/projects", tags=["Proposal Inputs"])

# Province-specific uploads/inputs
app.include_router(provincial_stats_router, prefix="/api/v1/projects", tags=["Provincial Stats"])
# app.include_router(master_data_router, prefix="/api/v1/projects", tags=["Master Data"])

# Core Pillars
app.include_router(network_snapshot_router, prefix="/api/v1/projects", tags=["Network Snapshot"])
app.include_router(scenarios_router, prefix="/api/v1/projects", tags=["Forecast & Strategy"])
app.include_router(computation_router, prefix="/api/v1/projects", tags=["Computation Engine"])

# AI & Reports
app.include_router(ai_router, prefix="/api/v1/projects", tags=["AI Advisor"])
app.include_router(reports_router, prefix="/api/v1/projects", tags=["Reports"])

# -------------------------------------------------------------------
# 6. Health Check
# -------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    return {"status": "online", "version": "1.0.0"}


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Mosianedi Investment API",
        "version": "1.0.0",
    }