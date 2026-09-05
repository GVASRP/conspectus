"""Контент: главная, предметы, конспекты, добавление/удаление."""

import markdown as md_lib
from datetime import date as dt_date
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import improver
from app.db import Conspect, Subject, User, get_db
from web.deps import require_login, templates

router = APIRouter(tags=["content"])


def render(request: Request, name: str, ctx: dict):
    return templates.TemplateResponse(request, name, ctx)


def _user_ctx(user: User) -> dict:
    return {"user": user}


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db), user: User = Depends(require_login)):
    subjects = db.query(Subject).order_by(Subject.name).all()
    counts = {s.id: len(s.notes) for s in subjects}
    last_notes = (
        db.query(Conspect).order_by(Conspect.created_at.desc()).limit(6).all()
    )
    total = db.query(Conspect).count()
    today_notes = db.query(Conspect).filter(func.date(Conspect.created_at) == dt_date.today()).count()
    ctx = _user_ctx(user)
    ctx.update(subjects=subjects, counts=counts, last_notes=last_notes, total=total, today_notes=today_notes)
    return render(request, "index.html", ctx)


@router.get("/subject/{subject_id}", response_class=HTMLResponse)
def subject_page(subject_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_login)):
    subject = db.get(Subject, subject_id)
    if not subject:
        return RedirectResponse("/", status_code=303)
    notes = sorted(subject.notes, key=lambda n: (n.date or "", n.created_at or ()))[::-1]
    ctx = _user_ctx(user)
    ctx.update(subject=subject, notes=notes)
    return render(request, "subject.html", ctx)


@router.get("/note/{note_id}", response_class=HTMLResponse)
def note_page(note_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_login)):
    note = db.get(Conspect, note_id)
    if not note:
        return RedirectResponse("/", status_code=303)
    rendered = md_lib.markdown(note.content or "", extensions=["extra", "sane_lists", "nl2br"])
    ctx = _user_ctx(user)
    ctx.update(note=note, html=rendered)
    return render(request, "note.html", ctx)


@router.get("/add", response_class=HTMLResponse)
def add_form(request: Request, db: Session = Depends(get_db), user: User = Depends(require_login)):
    subjects = db.query(Subject).order_by(Subject.name).all()
    ctx = _user_ctx(user)
    ctx.update(subjects=subjects)
    return render(request, "add.html", ctx)


@router.post("/add")
async def add_post(
    request: Request,
    subject_name: str = Form(""),
    subject_select: str = Form(""),
    title: str = Form(""),
    topic: str = Form(""),
    date: str = Form(""),
    content: str = Form(""),
    improve: str = Form("0"),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    def form(error: str):
        ctx = _user_ctx(user)
        ctx.update(error=error, subjects=db.query(Subject).order_by(Subject.name).all())
        return render(request, "add.html", ctx)

    name = subject_name.strip() or subject_select.strip()
    if not name:
        return form("Укажи предмет.")
    subject = db.query(Subject).filter(Subject.name == name).first()
    if not subject:
        subject = Subject(name=name)
        db.add(subject)
        db.flush()

    raw = content.strip()
    if not raw:
        return form("Пустой текст конспекта.")

    final_text = raw
    prompt_used = None
    if improve == "1":
        try:
            final_text, improved = await improver.improve(subject.name, topic, date, raw, title)
            if not improved:
                prompt_used = final_text
        except Exception as exc:  # noqa: BLE001
            return form(f"Ошибка улучшения: {exc}")

    note = Conspect(
        subject=subject,
        title=title.strip() or topic.strip() or "Без названия",
        topic=topic.strip(),
        date=date.strip(),
        content=final_text if prompt_used is None else raw,
        raw_content=raw,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    if prompt_used is not None:
        ctx = _user_ctx(user)
        ctx.update(note=note, prompt=prompt_used)
        return render(request, "prompt.html", ctx)
    return RedirectResponse(f"/note/{note.id}", status_code=303)


@router.post("/note/{note_id}/delete")
def note_delete(note_id: int, db: Session = Depends(get_db), user: User = Depends(require_login)):
    note = db.get(Conspect, note_id)
    if note:
        db.delete(note)
        db.commit()
    return RedirectResponse("/", status_code=303)