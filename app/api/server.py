"""FastAPI app factory. Run: uvicorn app.api.server:app --reload"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="RFP Intelligence Platform",
        description="RAG search engine + multi-agent extraction/Q&A over bid documents.",
        version="0.1.0",
    )
    # Allow the React dev server (and any local origin) to call the API from the browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/")
    def root() -> dict:
        return {
            "service": "RFP Intelligence Platform",
            "docs": "/docs",
            "endpoints": ["/upload", "/index", "/search", "/ask", "/extract", "/health"],
            "note": "Web UI runs separately at http://localhost:5173 (npm run dev).",
        }

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
