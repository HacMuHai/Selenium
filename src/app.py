from fastapi import FastAPI
from api.comments import router as router_comments

app = FastAPI()
app.include_router(router_comments)


@app.get("/")
def root():
    return {"status": "ook"}

# Chạy: uvicorn src.app:app --reload
