"""Отправка кодов 2FA и восстановления через Supabase Auth (email от supabase.co).

Поток:
  send_code(email)    — гарантирует создание пользователя (signUp) и шлёт код (otp)
  verify_code(email, code) — проверяет email-OTP
Нужные настройки в дашборде Supabase:
  Auth → Sign In / Providers → Email включён, «Confirm email» ВЫКЛЮЧЕН
  Auth → Email Templates → Email OTP включён
"""

import asyncio
import json
import logging
import secrets
import urllib.error
import urllib.request

from . import config

log = logging.getLogger("mail")

SIGNUP_EP = "/auth/v1/signup"
OTP_EP = "/auth/v1/otp"
VERIFY_EP = "/auth/v1/verify"


def _headers() -> dict:
    anon = config.SUPABASE_ANON_KEY
    return {
        "apikey": anon,
        "Authorization": "Bearer " + anon,
        "Content-Type": "application/json",
        "User-Agent": "conspectus-app",
        "Accept": "application/json",
    }


def _post(path: str, payload: dict) -> bool:
    req = urllib.request.Request(
        config.SUPABASE_URL.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        log.info("supabase %s -> %s %s", path, e.code, e.read(200).decode("utf-8", "ignore"))
        return False


def send_code_sync(email: str) -> bool:
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        log.warning("Supabase Email не настроен (SUPABASE_URL/SUPABASE_ANON_KEY)")
        return False
    # обеспечиваем существование пользователя в Supabase Auth
    _post(SIGNUP_EP, {"email": email, "password": secrets.token_urlsafe(24)})
    return _post(OTP_EP, {"email": email})


def verify_code_sync(email: str, code: str) -> bool:
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        return False
    return _post(VERIFY_EP, {"type": "email", "email": email, "token": code.strip()})


async def send_code(email: str) -> bool:
    return await asyncio.to_thread(send_code_sync, email)


async def verify_code(email: str, code: str) -> bool:
    return await asyncio.to_thread(verify_code_sync, email)