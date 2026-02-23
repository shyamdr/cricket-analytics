"""FastAPI application — serves the cricket analytics gold layer."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.database import close_conn, get_conn
from src.api.routers import batting, bowling, matches, players, teams


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DuckDB connection lifecycle."""
    get_conn()  # open on startup
    yield
    close_conn()  # close on shutdown


app = FastAPI(
    title="Cricket Analytics API",
    description="IPL cricket analytics powered by DuckDB. Query player stats, team records, match data, and more.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(players.router)
app.include_router(teams.router)
app.include_router(matches.router)
app.include_router(batting.router)
app.include_router(bowling.router)


@app.get("/", tags=["health"])
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "cricket-analytics-api"}
