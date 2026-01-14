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
from app.routers.projects import router as projects_router
from app.proposal_data.router import router as proposal_data_router
from app.network_snapshot.router import router as network_snapshot_router
from app.scenarios.router import router as scenarios_router
from app.computation.router import router as computation_router
from app.ai_advisor import router as ai_router

# -------------------------------------------------------------------
# 3. App Config
# -------------------------------------------------------------------
app = FastAPI(
    title="Mosianedi Investment API",
    description="API Gateway for Provincial Road Budget Proposals & Forecasting.",
    version="1.0.0",
)

# -------------------------------------------------------------------
# 4. CORS Middleware (The Fix)
# -------------------------------------------------------------------
# You MUST list the specific domains. Wildcard "*" fails with credentials.
origins = [
    "http://localhost:3000",                      # Local Development
    "https://mosianedi-frontend.vercel.app",      # Production Frontend
    # Add any other preview URLs here if needed, e.g.:
    # "https://mosianedi-frontend-git-main.vercel.app" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # 👈 Specific origins, not ["*"]
    allow_credentials=True,       # Required for Supabase Auth headers
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# 5. Register Routes
# -------------------------------------------------------------------
app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(proposal_data_router, prefix="/api/v1/projects", tags=["Proposal Inputs"])
app.include_router(network_snapshot_router, prefix="/api/v1/projects", tags=["Network Snapshot"])
app.include_router(scenarios_router, prefix="/api/v1/projects", tags=["Forecast & Strategy"])
app.include_router(computation_router, prefix="/api/v1/projects", tags=["Computation Engine"])
app.include_router(ai_router.router, prefix="/api/v1/projects", tags=["AI Advisor"])

# -------------------------------------------------------------------
# 6. Health Check
# -------------------------------------------------------------------
@app.get("/api/health") # Renamed for clarity, often useful to have under /api
def health_check():
    return {"status": "online", "version": "1.0.0"}

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Mosianedi Investment API",
        "version": "1.0.0"
    }