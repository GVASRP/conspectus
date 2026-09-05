"""Аутентификация: вход и выход с обязательной 2FA, регистрация по заявке,
восстановление пароля по коду из Telegram, смена пароля в настройках.
"""

import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import config, security
from app.db import (
    STATUS_ACTIVE,
    STATUS_BANNED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ROLE_ADMIN,
    User,
    check_reset_code,
    get_db,
    hash_password,
    issue_reset_code,
    verify_password,
)
from app.notify import notify_admin, send_tg
from web.deps import Forbidden, NotAuthed, require_login, templates

router = APIRouter(tags=["auth"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]{3,32}$")


def _render(request: Request, name: str, ctx: dict):
    return templates.TemplateResponse(request, name, ctx)


# ---------------------------------------------------------------- login
@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return _render(request, "login.html", {"flash": request.session.pop("flash", "")})


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or not verify_password(password, user.password_hash):
        return _render(request, "login.html", {"error": "Неверный логин или пароль"})
    if user.status == STATUS_BANNED:
        return _render(request, "login.html", {"error": "Аккаунт заблокирован администратором."})
    if user.status == STATUS_REJECTED:
        return _render(request, "login.html", {"error": "Заявка на регистрацию отклонена."})
    if user.status == STATUS_PENDING:
        return _render(request, "login.html", {"error": "Заявка ещё ожидает одобрения. Зайди позже."})
    request.session["login_uid"] = user.id
    request.session["login_name"] = user.username
    if not user.totp_confirmed:
        return RedirectResponse("/login/enroll", status_code=303)
    return RedirectResponse("/login/totp", status_code=303)


@router.get("/login/totp", response_class=HTMLResponse)
def login_totp_form(request: Request):
    if not request.session.get("login_uid"):
        return RedirectResponse("/login", status_code=303)
    return _render(request, "login_totp.html", {"name": request.session.get("login_name", "")})


@router.post("/login/totp")
def login_totp_post(
    request: Request,
    code: str = Form(""),
    db: Session = Depends(get_db),
):
    uid = request.session.get("login_uid")
    if not uid:
        return RedirectResponse("/login", status_code=303)
    user = db.get(User, uid)
    if not user or not security.verify(code, user.totp_secret):
        return _render(request, "login_totp.html", {"name": user.username if user else "", "error": "Неверный код"})
    request.session["user_id"] = user.id
    request.session.pop("login_uid", None)
    request.session.pop("login_name", None)
    return RedirectResponse("/", status_code=303)


@router.get("/login/enroll", response_class=HTMLResponse)
def login_enroll_form(request: Request, db: Session = Depends(get_db)):
    uid = request.session.get("login_uid")
    if not uid:
        return RedirectResponse("/login", status_code=303)
    user = db.get(User, uid)
    if not user:
        return RedirectResponse("/login", status_code=303)
    secret = user.totp_secret or security.new_secret()
    qr = security.qr_svg(secret, user.username)
    return _render(request, "login_enroll.html", {"qr": qr, "secret": secret, "name": user.username})


@router.post("/login/enroll")
def login_enroll_post(
    request: Request,
    code: str = Form(""),
    db: Session = Depends(get_db),
):
    uid = request.session.get("login_uid")
    if not uid:
        return RedirectResponse("/login", status_code=303)
    user = db.get(User, uid)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not security.verify(code, user.totp_secret):
        qr = security.qr_svg(user.totp_secret, user.username)
        return _render(request, "login_enroll.html",
                       {"qr": qr, "secret": user.totp_secret, "name": user.username, "error": "Неверный код"})
    user.totp_confirmed = True
    db.commit()
    request.session["user_id"] = user.id
    request.session.pop("login_uid", None)
    request.session.pop("login_name", None)
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------- register
@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return _render(request, "register.html", {"config": config})


@router.post("/register")
def register_post(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    password2: str = Form(""),
    tg_id: str = Form(""),
    db: Session = Depends(get_db),
):
    username = username.strip()
    if not USERNAME_RE.match(username):
        return _render(request, "register.html", {"error": "Логин: 3–32 символа, буквы/цифры/_-.", "config": config})
    if len(password) < 8:
        return _render(request, "register.html", {"error": "Пароль: минимум 8 символов.", "config": config})
    if password != password2:
        return _render(request, "register.html", {"error": "Пароли не совпадают.", "config": config})
    if db.query(User).filter(User.username == username).first():
        return _render(request, "register.html", {"error": "Такой логин уже занят.", "config": config})
    user = User(
        username=username,
        password_hash=hash_password(password),
        totp_secret=security.new_secret(),
        tg_id=tg_id.strip(),
        status=STATUS_PENDING,
    )
    db.add(user)
    db.commit()
    request.session["reg_uid"] = user.id
    return RedirectResponse("/register/totp", status_code=303)


@router.get("/register/totp", response_class=HTMLResponse)
def register_totp_form(request: Request, db: Session = Depends(get_db)):
    rid = request.session.get("reg_uid")
    if not rid:
        return RedirectResponse("/register", status_code=303)
    user = db.get(User, rid)
    if not user:
        return RedirectResponse("/register", status_code=303)
    qr = security.qr_svg(user.totp_secret, user.username)
    return _render(request, "register_totp.html", {"qr": qr, "secret": user.totp_secret, "name": user.username})


@router.post("/register/totp")
async def register_totp_post(
    request: Request,
    code: str = Form(""),
    db: Session = Depends(get_db),
):
    rid = request.session.get("reg_uid")
    if not rid:
        return RedirectResponse("/register", status_code=303)
    user = db.get(User, rid)
    if not user:
        return RedirectResponse("/register", status_code=303)
    if not security.verify(code, user.totp_secret):
        qr = security.qr_svg(user.totp_secret, user.username)
        return _render(request, "register_totp.html",
                       {"qr": qr, "secret": user.totp_secret, "name": user.username, "error": "Неверный код"})
    user.totp_confirmed = True
    db.commit()
    request.session.pop("reg_uid", None)
    await notify_admin(
        f"🎓 На сервере {config.APP_NAME} новая заявка на регистрацию:\n"
        f"ник: @{user.username}\n"
        f"telegram: {user.tg_id or 'не указан'}\n"
        "Одобрить или отклонить: зайди на сайт в админ-панель."
    )
    return _render(request, "register_done.html", {})


# ---------------------------------------------------------------- forgot password
@router.get("/forgot", response_class=HTMLResponse)
def forgot_form(request: Request):
    return _render(request, "forgot.html", {})


@router.post("/forgot")
async def forgot_post(
    request: Request,
    username: str = Form(""),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username.strip()).first()
    generic = _render(request, "forgot.html",
                      {"error": "Если такой аккаунт есть и к нему привязан Telegram — код уже отправлен."})
    if not user or user.status != STATUS_ACTIVE:
        return generic
    if not user.totp_confirmed:
        return _render(request, "forgot.html", {"error": "2FA для этого аккаунта не настроена. Обратись к администратору."})
    if not user.tg_id:
        return _render(request, "forgot.html", {"error": "К аккаунту не привязан Telegram. Обратись к администратору."})
    code = issue_reset_code(db, user)
    ok = await send_tg(user.tg_id, f"🔐 {config.APP_NAME}: код для сброса пароля — {code}. Действует 10 минут.")
    if not ok:
        return _render(request, "forgot.html", {"error": "Не удалось отправить код в Telegram. Проверь, что ты написал(а) боту."})
    request.session["forgot_uid"] = user.id
    request.session["forgot_name"] = user.username
    return RedirectResponse("/forgot/verify", status_code=303)


@router.get("/forgot/verify", response_class=HTMLResponse)
def forgot_verify_form(request: Request):
    if not request.session.get("forgot_uid"):
        return RedirectResponse("/forgot", status_code=303)
    return _render(request, "forgot_verify.html", {"name": request.session.get("forgot_name", "")})


@router.post("/forgot/verify")
def forgot_verify_post(
    request: Request,
    code: str = Form(""),
    password: str = Form(""),
    password2: str = Form(""),
    totp: str = Form(""),
    db: Session = Depends(get_db),
):
    uid = request.session.get("forgot_uid")
    if not uid:
        return RedirectResponse("/forgot", status_code=303)
    user = db.get(User, uid)
    if not user:
        return RedirectResponse("/forgot", status_code=303)
    if not check_reset_code(db, user, code):
        return _render(request, "forgot_verify.html",
                       {"name": user.username, "error": "Неверный или просроченный код."})
    if len(password) < 8:
        return _render(request, "forgot_verify.html", {"name": user.username, "error": "Пароль: минимум 8 символов."})
    if password != password2:
        return _render(request, "forgot_verify.html", {"name": user.username, "error": "Пароли не совпадают."})
    if not security.verify(totp, user.totp_secret):
        return _render(request, "forgot_verify.html", {"name": user.username, "error": "Неверный код 2FA."})
    user.password_hash = hash_password(password)
    db.commit()
    request.session.clear()
    request.session["flash"] = "Пароль изменён. Войди с новым паролем и кодом 2FA."
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------- settings
@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user: User = Depends(require_login)):
    return _render(request, "settings.html", {"u": user, "ok": request.session.pop("ok", "")})


@router.post("/settings/tg")
def settings_tg_post(
    request: Request,
    tg_id: str = Form(""),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    tg_id = tg_id.strip()
    if tg_id and not tg_id.lstrip("-").isdigit():
        return _render(request, "settings.html", {"u": user, "error": "Telegram ID — это число (узнать: @userinfobot)."})
    user.tg_id = tg_id
    db.commit()
    request.session["ok"] = "Telegram привязан."
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/password")
def settings_password_post(
    request: Request,
    current: str = Form(""),
    totp: str = Form(""),
    password: str = Form(""),
    password2: str = Form(""),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    err = None
    if not verify_password(current, user.password_hash):
        err = "Текущий пароль неверный."
    elif not security.verify(totp, user.totp_secret):
        err = "Неверный код 2FA."
    elif len(password) < 8:
        err = "Новый пароль: минимум 8 символов."
    elif password != password2:
        err = "Пароли не совпадают."
    if err:
        return _render(request, "settings.html", {"u": user, "error": err})
    user.password_hash = hash_password(password)
    db.commit()
    request.session["ok"] = "Пароль обновлён."
    return RedirectResponse("/settings", status_code=303)