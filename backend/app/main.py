"""
main.py — FastAPI application entry point (SPEC §13, ARCHITECTURE §2).

Mounts:
  /api/...        all API routers
  /api/photos/    static photo files from data/photos/
  /               the built React PWA from app/static/ (fallback to index.html)

CORS is open in dev; in production a single origin is used (ARCHITECTURE §2).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import create_db_and_tables
from app.routers import auth as auth_router_mod
from app.routers import findings, inspections, properties, runs, tenancies

app = FastAPI(title="Deposit Rakshak API", version="0.1.0")

# ---------------------------------------------------------------------------
# CORS (dev: allow all; demo: same-origin via tunnel so this is fine)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------

app.include_router(auth_router_mod.router)        # /api/auth/...
app.include_router(auth_router_mod.me_router)     # /api/me
app.include_router(properties.router)             # /api/properties/...
app.include_router(tenancies.router)              # /api/tenancies/...
app.include_router(inspections.router)            # /api/inspections/...
app.include_router(findings.router)               # /api/findings/..., /api/rate-card
app.include_router(runs.router)                   # /api/runs/..., /api/tenancies/{id}/report

# ---------------------------------------------------------------------------
# Static: photos served at /api/photos/<sha256>
# ---------------------------------------------------------------------------

PHOTOS_DIR = Path("data/photos")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")

# ---------------------------------------------------------------------------
# Static: built PWA at / (must come last)
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")
