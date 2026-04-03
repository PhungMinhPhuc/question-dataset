import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import Depends
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Thêm engine parser vào path
ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "src", "engine")
if ENGINE_PATH not in sys.path:
    sys.path.insert(0, ENGINE_PATH)

from routers import auth, questions, upload, classes, contests
from auth import get_current_user

app = FastAPI(
    title="Hệ thống CSDL",
    description="API cho hệ thống CSDL",
    version="1.0.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (ảnh câu hỏi) ───────────────────────────────────────────────
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response

IMG_STORAGE_PATH = os.getenv("IMG_STORAGE_PATH", "./storage")
os.makedirs(IMG_STORAGE_PATH, exist_ok=True)
app.mount("/static/images", NoCacheStaticFiles(directory=IMG_STORAGE_PATH), name="images")

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(questions.router)
app.include_router(upload.router)
app.include_router(classes.router)
app.include_router(contests.router)


@app.get("/")
def root():
    return {"message": "API đang chạy. Truy cập /docs để xem tài liệu."}


@app.get("/health")
def health():
    from db import get_connection
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
