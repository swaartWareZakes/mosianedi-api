from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Routers
from app.routers.auth import router as auth_router
from app.routers.projects import router as projects_router
from app.routers.workflow import router as workflow_router
from app.proposal_data.router import router as proposal_data_router
from app.network_snapshot.router import router as network_snapshot_router
from app.scenarios.router import router as scenarios_router
from app.computation.router import router as computation_router
from app.ai_advisor.router import router as ai_router
from app.reports.router import router as reports_router
from app.routers.provincial_stats import router as provincial_stats_router

app = FastAPI(title="Mosianedi API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://mosianedi-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(workflow_router, prefix="/api/v1/projects", tags=["Workflow"]) # Note prefix
app.include_router(proposal_data_router, prefix="/api/v1/projects", tags=["Proposal Inputs"])
app.include_router(network_snapshot_router, prefix="/api/v1/projects", tags=["Network"])
app.include_router(scenarios_router, prefix="/api/v1/projects", tags=["Forecast"])
app.include_router(computation_router, prefix="/api/v1/projects", tags=["Simulation"])
app.include_router(ai_router, prefix="/api/v1/projects", tags=["AI"])
app.include_router(reports_router, prefix="/api/v1/projects", tags=["Reports"])
app.include_router(provincial_stats_router, prefix="/api/v1/provincial-stats", tags=["Provincial Stats"])

@app.get("/api/health")
def health_check():
    return {"status": "online", "version": "2.0.0"}