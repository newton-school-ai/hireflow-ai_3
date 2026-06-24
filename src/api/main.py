from fastapi import FastAPI

app = FastAPI(title="HireFlow API")

@app.get("/")
def read_root():
    return {"message": "HireFlow API is running"}
