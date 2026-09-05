"""Развлечения: комната отдыха — игры, погода, мини-приколы."""

import random
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import Conspect, Subject, User, get_db
from web.deps import require_login, templates

router = APIRouter(tags=["fun"])

GAMES = {
    "2048": "2048",
    "snake": "Змейка",
    "memory": "Память",
    "quiz": "Квиз по конспектам",
    "weather": "Погода",
}

_WD = re.compile(r"[#*_`\[\]()<>!~|]")
_WS = re.compile(r"\s+")


def _strip_md(text: str) -> str:
    text = _WS.sub(" ", _WD.sub(" ", text or "")).strip()
    return text


@router.get("/fun", response_class=HTMLResponse)
def fun_hub(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(request, "fun.html", {"user": user, "active": "fun", "games": GAMES})


@router.get("/fun/play/{game}", response_class=HTMLResponse)
def fun_game(game: str, request: Request, user: User = Depends(require_login)):
    name = GAMES.get(game)
    if not name:
        return templates.TemplateResponse(request, "404.html", {}, status_code=404)
    return templates.TemplateResponse(
        request, "games/game.html",
        {"user": user, "active": "fun", "game": game, "game_name": name},
    )


@router.get("/api/fun/quiz")
def quiz_question(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    subjects = db.query(Subject).all()
    if len(subjects) < 2:
        return JSONResponse({"ok": False, "error": "Нужно минимум два предмета с конспектами."})
    notes = db.query(Conspect).all()
    if not notes:
        return JSONResponse({"ok": False, "error": "Конспектов пока нет — добавь что-нибудь, чтобы играть."})
    note = random.choice(notes)
    correct = note.subject
    distractors = random.sample([s for s in subjects if s.id != correct.id], min(3, len(subjects) - 1))
    options = distractors + [correct]
    random.shuffle(options)
    snippet = _strip_md(note.content or note.raw_content or "")
    if len(snippet) > 170:
        snippet = snippet[:170] + "…"
    if not snippet:
        snippet = "Конспект без текста. Угадай предмет по заголовку."
    return JSONResponse({"ok": True, "question": {
        "id": note.id,
        "title": note.title or note.topic or "Конспект",
        "snippet": snippet,
        "options": [{"id": s.id, "name": s.name} for s in options],
        "answer_id": correct.id,
        "answer_name": correct.name,
    }})