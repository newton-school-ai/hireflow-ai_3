from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.profile import router as profile_router
from src.config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="HireFlow API",
    description="AI-powered job application assistant",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(profile_router)


@app.get("/")
def read_root():
    return {"message": "HireFlow API is running"}

