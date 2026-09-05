"""Общие зависимости веб-приложения: проверка входа и прав."""

from pathlib import Path

from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from fastapi import Depends, Request

from app.db import STATUS_ACTIVE, User, get_db
from app.config import APP_NAME

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
templates.env.globals["APP_NAME"] = APP_NAME


class NotAuthed(Exception):
    """Пустой пользователь/нет сессии — редирект на /login."""


class Forbidden(Exception):
    """Нет прав (например, админ-панель для не-админа)."""


def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    uid = request.session.get("user_id")
    if not uid:
        raise NotAuthed()
    user = db.get(User, uid)
    if not user or user.status != STATUS_ACTIVE:
        request.session.clear()
        raise NotAuthed()
    return user


def require_admin(user: User = Depends(require_login)) -> User:
    if user.role != "admin":
        raise Forbidden()
    return user