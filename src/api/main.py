from fastapi import FastAPI
from src.api.routes.profile import router as profile_router

app = FastAPI(title="HireFlow API")

app.include_router(profile_router, prefix="/profile", tags=["profile"])

@app.get("/")
def read_root():
    return {"message": "HireFlow API is running"}
