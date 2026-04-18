"""FastAPI application — serves the cricket analytics gold layer."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.database import close_conn, get_conn
from src.api.routers import batting, bowling, images, matches, news, players, standings, teams


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DuckDB connection lifecycle."""
    get_conn()  # open on startup
    yield
    close_conn()  # close on shutdown


app = FastAPI(
    title="InsideEdge API",
    description="Cricket analytics powered by DuckDB. Query player stats, team records, match data, and more.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend (dev + production) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://insideedge(-[a-z0-9]+)?\.vercel\.app|http://localhost:3000",
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(players.router)
app.include_router(teams.router)
app.include_router(matches.router)
app.include_router(batting.router)
app.include_router(bowling.router)
app.include_router(images.router)
app.include_router(news.router)
app.include_router(standings.router)


@app.get("/", tags=["health"])
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "insideedge-api"}
