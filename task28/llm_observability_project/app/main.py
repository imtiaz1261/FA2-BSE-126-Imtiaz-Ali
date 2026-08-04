from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import chat, metrics, benchmark
from app.models.database import init_db
import traceback

app = FastAPI(title="LLM Observability, Cost Tracking & Optimization System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit default port
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(chat.router)
app.include_router(metrics.router)
app.include_router(benchmark.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces or internals to the client.
    # Log the exception details to the server console for debugging.
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
