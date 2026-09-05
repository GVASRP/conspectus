"""Telegram-бот для добавления, улучшения и просмотра конспектов.
Доступ строго ограничен списком BOT_ALLOWED_IDS (см. .env).
"""

import logging

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from app import config
from app import improver
from app.db import Conspect, SessionLocal, Subject

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

router = Router()

AUTH_IDS = set(int(x) for x in config.BOT_ALLOWED_IDS.split(",") if x.strip()) if config.BOT_ALLOWED_IDS.strip() else set()


def is_allowed(user_id) -> bool:
    if not AUTH_IDS:
        return True
    return user_id in AUTH_IDS


class AuthMiddleware(BaseMiddleware):
    """Отсекает всё, что приходит от неавторизованных пользователей."""

    async def __call__(self, handler, event, data: dict):
        # на dp.message/dp.callback_query событие — само сообщение/колбек,
        # на dp.update — обёртка Update
        inner = event.event if isinstance(event, Update) else event
        user = getattr(inner, "from_user", None)
        uid = user.id if user is not None else None
        if is_allowed(uid):
            return await handler(event, data)
        if isinstance(inner, Message):
            try:
                await inner.answer("⛔ Доступ запрещён. Этот бот — только для приглашённых.")
            except Exception:  # noqa: BLE001
                pass
        return None


class AddFlow(StatesGroup):
    subject = State()
    title = State()
    topic = State()
    date = State()
    content = State()


async def ensure_allowed(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Доступ запрещён.")
        return False
    return True


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if not await ensure_allowed(message):
        return
    await state.clear()
    await message.answer(
        "Привет! Это база конспектов.\n\n"
        "Команды:\n"
        "/add — добавить конспект (пошагово)\n"
        "/list — список предметов\n"
        "/subjects — то же\n"
        "/help — справка\n\n"
        "Можно также просто прислать текст — сохраню в последний предмет."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    if not await ensure_allowed(message):
        return
    await message.answer(
        "Команды:\n"
        "/add — добавить конспект\n"
        "/list — список предметов (с id конспектов)\n"
        "/improve <id> — улучшить конспект через ИИ\n"
        "/cancel — отменить текущий ввод\n"
        "/help — справка"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if not await ensure_allowed(message):
        return
    if await state.get_state() is None:
        await message.answer("Сейчас ничего не набираем — отменять нечего.")
        return
    await state.clear()
    await message.answer("Отменено. Что дальше? /add, /list или /help")


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    if not await ensure_allowed(message):
        return
    db = SessionLocal()
    subjects = db.query(Subject).order_by(Subject.name).all()
    db.close()
    if not subjects:
        await state.set_state(AddFlow.subject)
        await message.answer("Какой предмет? Напиши название (например: Алгебра).")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s.name, callback_data=f"subject:{s.id}")] for s in subjects
        ]
        + [[InlineKeyboardButton(text="✍️ Новый предмет", callback_data="subject:new")]]
    )
    await state.set_state(AddFlow.subject)
    await message.answer("Выбери предмет или создай новый:", reply_markup=kb)


@router.callback_query(F.data.startswith("subject:"))
async def cb_subject(call: CallbackQuery, state: FSMContext):
    if not is_allowed(call.from_user.id):
        return
    data = call.data.split(":", 1)[1]
    if data == "new":
        await call.message.answer("Напиши название нового предмета:")
        await state.set_state(AddFlow.subject)
        await call.answer()
        return
    await state.update_data(subject_id=int(data))
    await call.message.answer("Тема / название конспекта (или '-' чтобы пропустить):")
    await state.set_state(AddFlow.title)
    await call.answer()


@router.message(AddFlow.subject)
async def on_subject(message: Message, state: FSMContext):
    db = SessionLocal()
    name = message.text.strip()
    subj = db.query(Subject).filter(Subject.name == name).first()
    if not subj:
        subj = Subject(name=name)
        db.add(subj)
        db.flush()
    db.commit()
    await state.update_data(subject_id=subj.id)
    db.close()
    await message.answer("Тема / название конспекта (или '-' чтобы пропустить):")
    await state.set_state(AddFlow.title)


@router.message(AddFlow.title)
async def on_title(message: Message, state: FSMContext):
    t = message.text.strip()
    if t == "-":
        t = ""
    await state.update_data(title=t)
    await message.answer("Тема (кратко, например 'Квадратичная функция') или '-' пропустить:")
    await state.set_state(AddFlow.topic)


@router.message(AddFlow.topic)
async def on_topic(message: Message, state: FSMContext):
    t = message.text.strip()
    if t == "-":
        t = ""
    await state.update_data(topic=t)
    await message.answer("Дата (например 2026-09-05 или '-' пропустить):")
    await state.set_state(AddFlow.date)


@router.message(AddFlow.date)
async def on_date(message: Message, state: FSMContext):
    d = message.text.strip()
    if d == "-":
        d = ""
    await state.update_data(date=d)
    await message.answer(
        "Теперь пришли текст конспекта (или файл .txt). "
        "После этого я сохраню. Отвечать на 'импрувнуть?' не нужно."
    )
    await state.set_state(AddFlow.content)


@router.message(AddFlow.content)
async def on_content(message: Message, state: FSMContext):
    if message.text:
        raw = message.text.strip()
    elif message.document:
        raw = (await message.bot.download(message.document)).read().decode("utf-8", errors="replace").strip()
    else:
        await message.answer("Пришли текст или .txt файл.")
        return
    if not raw:
        await message.answer("Пустой текст, попробуй ещё раз.")
        return

    data = await state.get_data()
    db = SessionLocal()
    subj = db.get(Subject, data["subject_id"])
    if not subj:
        db.close()
        await state.clear()
        await message.answer("Ошибка: предмет не найден. Начни заново /add")
        return

    title = data.get("title") or data.get("topic") or "Без названия"
    note = Conspect(
        subject=subj,
        title=title,
        topic=data.get("topic", ""),
        date=data.get("date", ""),
        content=raw,
        raw_content=raw,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    db.close()

    await state.clear()
    await message.answer(
        f"✅ Сохранено в «{subj.name}»:\n"
        f"Название: {note.title}\n"
        f"Тема: {note.topic or '—'}\n"
        f"Дата: {note.date or '—'}\n\n"
        f"Хочешь улучшить текст через ИИ? Отправь /improve {note.id}"
    )


@router.message(Command("list"))
@router.message(Command("subjects"))
async def cmd_list(message: Message):
    if not await ensure_allowed(message):
        return
    db = SessionLocal()
    subjects = db.query(Subject).order_by(Subject.name).all()
    recent = db.query(Conspect).order_by(Conspect.id.desc()).limit(10).all()
    db.close()
    lines = [f"📘 <b>{s.name}</b> — {len(s.notes)} консп." for s in subjects]
    if recent:
        lines.append("")
        lines.append("Последние конспекты (id нужен для /improve):")
        for n in recent:
            suffix = f" • {n.date}" if n.date else ""
            lines.append(f"#{n.id} <b>{n.title}</b> — {n.subject.name}{suffix}")
    text = "\n".join(lines) if lines else "Пока пусто. Добавь /add"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("improve"))
async def cmd_improve(message: Message):
    if not await ensure_allowed(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /improve <id конспекта>\nСписок: /list (нет id — скоро добавлю)")
        return
    note_id = int(parts[1]) if parts[1].isdigit() else None
    if not note_id:
        await message.answer("Некорректный id.")
        return
    db = SessionLocal()
    note = db.get(Conspect, note_id)
    db.close()
    if not note:
        await message.answer("Конспект не найден.")
        return
    try:
        result, improved = await improver.improve(note.subject.name, note.topic, note.date, note.raw_content or note.content, note.title)
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка улучшения: {exc}")
        return
    db = SessionLocal()
    note = db.get(Conspect, note_id)
    if improved:
        note.content = result
        note.raw_content = note.raw_content or result
        db.commit()
        await message.answer(f"✅ Конспект #{note_id} улучшен и сохранён.")
    else:
        db.commit()
        await message.answer("Вот промт — скопируй и вставь в Gemini/другую LM:\n\n" + result[:3900])
    db.close()


def setup(dp: Dispatcher):
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.include_router(router)


def main():
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    setup(dp)
    command_enabled = [
        BotCommand(command="start", description="Старт и справка"),
        BotCommand(command="add", description="Добавить конспект"),
        BotCommand(command="list", description="Список предметов и конспектов"),
        BotCommand(command="improve", description="Улучшить конспект через ИИ (id)"),
        BotCommand(command="cancel", description="Отменить текущий ввод"),
        BotCommand(command="help", description="Справка"),
    ]

    async def run():
        try:
            await bot.set_my_commands(command_enabled)
        except Exception:  # noqa: BLE001 — сеть может быть недоступна при старте
            log.warning("Не удалось установить меню команд, продолжаем без него")
        if config.ADMIN_TG_ID:
            try:
                await bot.send_message(int(config.ADMIN_TG_ID), "✅ Конспекты: бот запущен")
            except Exception:  # noqa: BLE001
                log.warning("Не удалось отправить стартовое сообщение админу")
        try:
            await dp.run_polling(bot)
        finally:
            await bot.session.close()

    import asyncio

    asyncio.run(run())


if __name__ == "__main__":
    main()
