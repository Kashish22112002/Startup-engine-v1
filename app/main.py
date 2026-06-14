import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app import database
from app import analyzer

# Initialize FastAPI App
app = FastAPI(
    title="Reddit Pain-Point Miner & Startup Idea Validator",
    description="An automated co-pilot to discover customer frustrations and validate market demand.",
    version="1.0.0"
)

# Request schemas
class MineRequest(BaseModel):
    subreddit: str = Field(..., description="Name of the subreddit, e.g., 'smallbusiness' or 'freelance'")
    lookback_days: int = Field(30, description="Lookback window in days", ge=1, le=90)

class ValidateRequest(BaseModel):
    idea_name: str = Field(..., description="A short name for the startup idea")
    idea_text: str = Field(..., description="1-3 sentences describing the value proposition and core features")
    target_niche: str = Field(..., description="The main target audience, e.g., 'freelance accountants'")

# DB Initialization on Startup
@app.on_event("startup")
def startup_event():
    database.init_db()
    print("Database initialized successfully.")

# API Endpoints
@app.post("/api/mine")
def mine_niche(request: MineRequest):
    sub_clean = request.subreddit.lower().replace("r/", "").strip()
    if not sub_clean:
        raise HTTPException(status_code=400, detail="Subreddit name cannot be empty.")
    
    try:
        clusters = analyzer.mine_subreddit(sub_clean, request.lookback_days)
        return {
            "success": True,
            "subreddit": sub_clean,
            "clusters_count": len(clusters),
            "clusters": clusters
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to mine subreddit: {str(e)}")

@app.post("/api/validate")
def validate_idea_endpoint(request: ValidateRequest):
    if not request.idea_name.strip() or not request.idea_text.strip():
        raise HTTPException(status_code=400, detail="Idea name and description cannot be empty.")
    
    try:
        report = analyzer.validate_idea(
            request.idea_name,
            request.idea_text,
            request.target_niche
        )
        return report
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to validate idea: {str(e)}")

@app.get("/api/history/mining")
def get_mining_history():
    try:
        subreddits = database.get_tracked_subreddits()
        history = []
        for sub in subreddits:
            clusters = database.get_pain_point_clusters(sub["name"])
            history.append({
                "subreddit": sub["name"],
                "last_scraped_at": sub["last_scraped_at"],
                "tracked": bool(sub["tracked"]),
                "clusters": clusters
            })
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load mining history: {str(e)}")

@app.get("/api/history/validations")
def get_validations_history():
    try:
        validations = database.get_idea_validations()
        return validations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load validation history: {str(e)}")

@app.get("/api/status")
def get_status():
    from app import llm_client
    provider, _ = llm_client.get_llm_provider()
    return {"live": provider is not None}


# Serve Static Files (Frontend SPA)
# Make sure the static directory exists
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static files router
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Catch-all endpoint to serve index.html for the client-side router
@app.get("/")
def read_root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Welcome to the Reddit Pain-Point Miner API. Frontend files missing."}
