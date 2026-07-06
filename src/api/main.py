from fastapi import FastAPI

from src.api.routes.profile import router as profile_router

app = FastAPI(title="HireFlow API")
app.include_router(profile_router)


@app.get("/")
def read_root():
    return {"message": "HireFlow API is running"}
