"""Админ-панель: заявки на регистрацию, пользователи, баны, роли."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import config
from app.db import (
    ROLE_ADMIN,
    ROLE_USER,
    STATUS_ACTIVE,
    STATUS_BANNED,
    STATUS_PENDING,
    STATUS_REJECTED,
    User,
    get_db,
)
from web.deps import require_admin, templates

router = APIRouter(prefix="/admin", tags=["admin"])


def render(request: Request, name: str, ctx: dict):
    return templates.TemplateResponse(request, name, ctx)


@router.get("", response_class=HTMLResponse)
def admin_index(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    pending = db.query(User).filter(User.status == STATUS_PENDING).order_by(User.created_at.desc()).all()
    active = db.query(User).filter(User.status == STATUS_ACTIVE).count()
    banned = db.query(User).filter(User.status == STATUS_BANNED).count()
    admins = db.query(User).filter(User.role == ROLE_ADMIN).count()
    ctx = {
        "admin": admin, "pending": pending, "active_count": active,
        "banned_count": banned, "admins_count": admins,
        "public_url": config.PUBLIC_URL,
    }
    return render(request, "admin.html", ctx)


@router.post("/request/{user_id}/approve")
def approve(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user and user.status == STATUS_PENDING:
        user.status = STATUS_ACTIVE
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/request/{user_id}/reject")
def reject(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user and user.status == STATUS_PENDING:
        user.status = STATUS_REJECTED
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/user/{user_id}/ban")
def ban(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user and user.id != admin.id and user.status != STATUS_PENDING:
        user.status = STATUS_BANNED
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/user/{user_id}/unban")
def unban(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user and user.status == STATUS_BANNED:
        user.status = STATUS_ACTIVE
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/user/{user_id}/role")
def toggle_role(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user and user.id != admin.id and user.status == STATUS_ACTIVE:
        user.role = ROLE_USER if user.role == ROLE_ADMIN else ROLE_ADMIN
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/users", response_class=HTMLResponse)
def admin_users(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return render(request, "admin_users.html", {"admin": admin, "users": users})