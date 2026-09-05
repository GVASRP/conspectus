"""Улучшение конспектов.

Два режима:
- AI_MODE=api: вызывает внешний OpenAI-совместимый API (OpenAI / Gemini и т.п.) и
  возвращает готовый улучшенный конспект.
- AI_MODE=prompt: возвращает готовый промт, который пользователь кидает в любую
  LLM (например, Gemini) вручную.
"""

import httpx

from . import config

# Универсальный промт, который можно отправить в любую LLM вручную.
CONSPECT_PROMPT_TEMPLATE = """Ты — опытный педагог и методист. Приведи приложенный ниже УЧЕНИЧЕСКИЙ КОНСПЕКТ к максимально качественному виду для самостоятельного изучения.

КОНТЕКСТ:
- Предмет: {subject}
- Тема: {topic}
- Дата: {date}

ЧТО СДЕЛАТЬ:
1. Исправь ошибки, опечатки, стиль. Сделай текст грамотным и связным.
2. Структурируй: заголовки, подзаголовки, списки, короткие абзацы.
3. Добавь недостающие логические связки там, где смысл потерян, НО не выдумывай новые факты, которых нет в исходнике. Вставки, добавленные от себя, помечай как «[добавлено]».
4. Выдели ключевые термины, определения, формулы.
5. В конце при необходимости добавь короткий раздел «Ключевые выводы» (3-6 пунктов) и, если есть формулы — «Формулы».
6. Не добавляй информацию, которая противоречит или полностью отсутствует в исходнике. Если в исходнике есть пробелы — честно пометь их как «[пропуск в записи]».

ФОРМАТ ОТВЕТА: верни только сам улучшенный конспект в Markdown, без вступлений и пояснений от себя.

ИСХОДНЫЙ КОНСПЕКТ:
"""
import logging

log = logging.getLogger("improver")


def build_prompt(subject: str, topic: str, date: str, raw: str, title: str = "") -> str:
    s = subject or "без предмета"
    t = topic or title or ""
    return (
        CONSPECT_PROMPT_TEMPLATE.format(subject=s, topic=t, date=date or "не указана")
        + "\n"
        + raw
        + "\n"
    )


async def improve_via_api(subject: str, topic: str, date: str, raw: str, title: str = "") -> str:
    """Улучшает конспект через OpenAI-совместимый API."""
    if not config.AI_API_KEY:
        raise RuntimeError("AI_API_KEY не задан, невозможно улучшить через API")

    prompt = build_prompt(subject, topic, date, raw, title)
    url = config.AI_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {config.AI_API_KEY}"}
    payload = {
        "model": config.AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.AI_TEMPERATURE,
        "max_tokens": config.AI_MAX_TOKENS,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        log.error("Неожиданный ответ API: %s", data)
        raise RuntimeError("Не удалось получить ответ от AI API")


async def improve(subject: str, topic: str, date: str, raw: str, title: str = "") -> tuple[str, bool]:
    """Обёртка. Возвращает (текст, improved_through_api).
    В режиме prompt возвращает сам промт."""
    if config.AI_MODE == "api":
        text = await improve_via_api(subject, topic, date, raw, title)
        return text, True
    return build_prompt(subject, topic, date, raw, title), False
