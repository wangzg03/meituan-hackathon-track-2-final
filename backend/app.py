from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.evaluation import router as evaluation_router
from routes.scenarios import router as scenarios_router

app = FastAPI(title="美团评测系统 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluation_router, prefix="/api/evaluation", tags=["评测"])
app.include_router(scenarios_router, prefix="/api/scenarios", tags=["场景"])

@app.get("/")
def root():
    return {"message": "美团评测系统 API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}