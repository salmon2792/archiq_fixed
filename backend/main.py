"""
ArchIQ Backend - Architecture-Aware Career Intelligence Platform
FastAPI backend with job scraping, AI reasoning, and skill matching
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

from api.routes import router as api_router
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="ArchIQ API",
    description="Architecture-Aware Career Intelligence Platform for Hardware Engineers",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow_credentials must be False when allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ArchIQ API", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "service": "ArchIQ API",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1"
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
