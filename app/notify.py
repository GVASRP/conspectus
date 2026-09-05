"""Уведомления в Telegram (для кодов сброса пароля и оповещений админа)."""

import logging

import httpx

from . import config

log = logging.getLogger("notify")


async def send_tg(chat_id, text: str) -> bool:
    """Отправляет сообщение пользователю Telegram (ботом из BOT_TOKEN)."""
    if not config.BOT_TOKEN:
        return False
    if not chat_id:
        return False
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": int(str(chat_id).strip()),
                    "text": text,
                    "disable_web_page_preview": True,
                },
            )
            return resp.status_code == 200
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram notify failed: %s", exc)
        return False


async def notify_admin(text: str) -> bool:
    """Шлёт сообщение админу если задан ADMIN_TG_ID."""
    return await send_tg(config.ADMIN_TG_ID, text)