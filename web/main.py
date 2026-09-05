"""Сборка FastAPI-приложения: middleware, обработчики ошибок, роутеры."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import os
from pathlib import Path

from app import config
from app.db import SessionLocal, init_db, seed_users
from web import admin, auth, content, deps
from web.deps import Forbidden, NotAuthed

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=config.APP_NAME, docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, max_age=7 * 24 * 3600)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.exception_handler(NotAuthed)
async def not_authed(request: Request, exc: NotAuthed):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(Forbidden)
async def forbidden(request: Request, exc: Forbidden):
    return deps.templates.TemplateResponse(request, "403.html", {}, status_code=403)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return deps.templates.TemplateResponse(request, "404.html", {}, status_code=404)


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(content.router)
app.include_router(admin.router)