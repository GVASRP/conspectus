"""Сборка FastAPI-приложения: middleware, обработчики ошибок, роутеры."""

import os
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.db import SessionLocal, init_db, seed_users
from web import admin, auth, content, deps, fun
from web.deps import Forbidden, NotAuthed

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=config.APP_NAME, docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, max_age=7 * 24 * 3600)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.state.diag = {}


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    return FileResponse(
        str(BASE_DIR / "static" / "sw.js"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/__diag")
async def __diag():
    import sqlalchemy
    from app import db as app_db

    out = dict(app.state.diag or {})
    url = os.getenv("DATABASE_URL", "")
    out["has_database_url"] = bool(url)
    out["engine_url_driver"] = type(app_db.engine).__name__
    try:
        with app_db.engine.connect() as conn:
            out["connect"] = "OK"
            out["version"] = conn.exec_driver_sql("select version()").fetchone()[0][:60]
            tabs = conn.exec_driver_sql(
                "select table_name from information_schema.tables where table_schema='public' order by 1"
            ).fetchall()
            out["tables"] = [t[0] for t in tabs]
    except Exception as exc:  # noqa: BLE001
        out["connect"] = "FAIL"
        out["connect_error"] = f"{type(exc).__name__}: {exc}"
    return JSONResponse(out)


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
    try:
        init_db()
        db = SessionLocal()
        try:
            seed_users(db)
        finally:
            db.close()
        app.state.diag["startup"] = "OK"
    except Exception:  # noqa: BLE001 — не роняем приложение, показываем в /__diag
        app.state.diag["startup"] = "FAIL"
        app.state.diag["startup_error"] = traceback.format_exc()


app.include_router(auth.router)
app.include_router(content.router)
app.include_router(admin.router)
app.include_router(fun.router)