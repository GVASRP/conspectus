"""Аутентификация: вход и выход с 2FA по почте, регистрация по заявке,
восстановление пароля по коду на почту, смена пароля в настройках.
"""

import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import config, security
from app.db import (
    STATUS_ACTIVE,
    STATUS_BANNED,
    STATUS_PENDING,
    STATUS_REJECTED,
    User,
    check_email_code,
    check_reset_code,
    get_db,
    hash_password,
    issue_email_code,
    issue_reset_code,
    verify_password,
)
from app.mail import send_email
from app.notify import notify_admin
from web.deps import require_login, templates

router = APIRouter(tags=["auth"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _render(request: Request, name: str, ctx: dict):
    return templates.TemplateResponse(request, name, ctx)


async def _start_2fa(db: Session, request: Request, user: User) -> bool:
    """Генерирует код 2FA и отправляет его на почту пользователя."""
    code = issue_email_code(db, user)
    return await send_email(
        user.email,
        f"Код для входа · {config.APP_NAME}",
        f"{config.APP_NAME}: твой код для входа — {code}.\nДействует 10 минут.",
    )


# ---------------------------------------------------------------- login
@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return _render(request, "login.html", {"flash": request.session.pop("flash", "")})


@router.post("/login")
async def login_post(
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
    if not user.email:
        return RedirectResponse("/login/email", status_code=303)
    ok = await _start_2fa(db, request, user)
    if not ok:
        return _render(request, "login.html", {"error": "Не удалось отправить код: почта не настроена. Сообщи администратору."})
    request.session["2fa_to"] = user.email
    return RedirectResponse("/login/2fa", status_code=303)


@router.get("/login/email", response_class=HTMLResponse)
def login_email_form(request: Request):
    if not request.session.get("login_uid"):
        return RedirectResponse("/login", status_code=303)
    return _render(request, "login_email.html", {"name": request.session.get("login_name", "")})


@router.post("/login/email")
async def login_email_post(
    request: Request,
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    uid = request.session.get("login_uid")
    if not uid:
        return RedirectResponse("/login", status_code=303)
    user = db.get(User, uid)
    if not user:
        return RedirectResponse("/login", status_code=303)
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return _render(request, "login_email.html", {"name": user.username, "error": "Некорректный email."})
    taken = db.query(User).filter(User.email == email, User.id != user.id).first()
    if taken:
        return _render(request, "login_email.html", {"name": user.username, "error": "Этот email уже привязан к другой учётке."})
    user.email = email
    db.commit()
    ok = await _start_2fa(db, request, user)
    if not ok:
        return _render(request, "login_email.html", {"name": user.username, "error": "Не удалось отправить код: почта не настроена."})
    request.session["2fa_to"] = email
    return RedirectResponse("/login/2fa", status_code=303)


@router.get("/login/2fa", response_class=HTMLResponse)
def login_2fa_form(request: Request):
    if not request.session.get("login_uid"):
        return RedirectResponse("/login", status_code=303)
    return _render(request, "login_2fa.html", {
        "name": request.session.get("login_name", ""),
        "to": request.session.get("2fa_to", ""),
    })


@router.post("/login/2fa")
def login_2fa_post(
    request: Request,
    code: str = Form(""),
    db: Session = Depends(get_db),
):
    uid = request.session.get("login_uid")
    if not uid:
        return RedirectResponse("/login", status_code=303)
    user = db.get(User, uid)
    if not user or not check_email_code(db, user, code):
        return _render(request, "login_2fa.html", {
            "name": user.username if user else "",
            "to": request.session.get("2fa_to", ""),
            "error": "Неверный или просроченный код.",
        })
    request.session["user_id"] = user.id
    request.session.pop("login_uid", None)
    request.session.pop("login_name", None)
    request.session.pop("2fa_to", None)
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
async def register_post(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    password2: str = Form(""),
    email: str = Form(""),
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
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return _render(request, "register.html", {"error": "Укажи корректный email — на него приходят коды входа.", "config": config})
    if db.query(User).filter(User.username == username).first():
        return _render(request, "register.html", {"error": "Такой логин уже занят.", "config": config})
    if db.query(User).filter(User.email == email).first():
        return _render(request, "register.html", {"error": "Этот email уже зарегистрирован.", "config": config})
    user = User(
        username=username,
        password_hash=hash_password(password),
        email=email,
        totp_secret=security.new_secret(),
        tg_id=tg_id.strip(),
        status=STATUS_PENDING,
    )
    db.add(user)
    db.commit()
    await notify_admin(
        f"🎓 На сервере {config.APP_NAME} новая заявка на регистрацию:\n"
        f"ник: @{user.username}\n"
        f"email: {user.email}\n"
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
                      {"error": "Если такой аккаунт есть и к нему привязана почта — код уже отправлен."})
    if not user or user.status != STATUS_ACTIVE:
        return generic
    if not user.email:
        return _render(request, "forgot.html", {"error": "К аккаунту не привязана почта. Обратись к администратору."})
    code = issue_reset_code(db, user)
    ok = await send_email(
        user.email,
        f"Восстановление пароля · {config.APP_NAME}",
        f"{config.APP_NAME}: код для сброса пароля — {code}. Действует 10 минут.",
    )
    if not ok:
        return _render(request, "forgot.html", {"error": "Не удалось отправить код — почта временно недоступна."})
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
    user.password_hash = hash_password(password)
    db.commit()
    request.session.clear()
    request.session["flash"] = "Пароль изменён. Войди с новым паролем и кодом из почты."
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


@router.post("/settings/email")
def settings_email_post(
    request: Request,
    email: str = Form(""),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return _render(request, "settings.html", {"u": user, "error": "Некорректный email."})
    taken = db.query(User).filter(User.email == email, User.id != user.id).first()
    if taken:
        return _render(request, "settings.html", {"u": user, "error": "Этот email уже привязан к другой учётке."})
    user.email = email
    db.commit()
    request.session["ok"] = "Email для 2FA сохранён."
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/password")
def settings_password_post(
    request: Request,
    current: str = Form(""),
    password: str = Form(""),
    password2: str = Form(""),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    err = None
    if not verify_password(current, user.password_hash):
        err = "Текущий пароль неверный."
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