"""Сетевые партии на том же сайте: шахматы, крестики-нолики, тетрис-гонка.

Vercel-серверless не держит WebSocket, поэтому комнаты хранятся в БД,
а клиенты опрашивают состояние каждые ~1.5 секунды.
"""

import json
import random
from datetime import datetime, timedelta

import chess  # python-chess
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import GameRoom, User, get_db
from web.deps import require_login, templates

router = APIRouter(tags=["online"])

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
ROOM_TTL = timedelta(hours=12)
GAME_TYPES = {"chess": "Шахматы", "xo": "Крестики-нолики", "tetris": "Тетрис"}


def _new_code(db: Session) -> str:
    while True:
        code = "".join(random.choice(CODE_ALPHABET) for _ in range(5))
        if not db.query(GameRoom).filter(GameRoom.code == code).first():
            return code


def _initial_state(game_type: str) -> dict:
    if game_type == "chess":
        return {"fen": START_FEN, "last": None, "over": False, "reason": ""}
    if game_type == "xo":
        return {"board": ".........", "moves": 0, "over": False, "winner": None}
    if game_type == "tetris":
        return {"seed": None, "target": 20, "lines": {"host": 0, "guest": 0},
                "top": {"host": False, "guest": False}, "started": False,
                "over": False, "winner": None}
    return {}


def _load(room: GameRoom) -> dict:
    try:
        return json.loads(room.state or "{}")
    except Exception:
        return {}


def _save(room: GameRoom, state: dict) -> None:
    room.state = json.dumps(state, ensure_ascii=False)


def _slot_of(room: GameRoom, user_id: int) -> str | None:
    if user_id == room.host_id:
        return "host"
    if user_id == room.guest_id:
        return "guest"
    return None


def _opp_slot(slot: str) -> str:
    return "guest" if slot == "host" else "host"


def _view(room: GameRoom, user: User, db: Session) -> dict:
    state = _load(room)
    slot = _slot_of(room, user.id)

    def us(uid):
        u = db.get(User, uid)
        return {"id": uid, "username": u.username if u else "?"}

    view = {
        "ok": True,
        "room_code": room.code,
        "game_type": room.game_type,
        "game_name": GAME_TYPES[room.game_type],
        "status": room.status,
        "my_slot": slot,
        "host": us(room.host_id),
        "guest": us(room.guest_id) if room.guest_id else None,
    }
    tpe = room.game_type
    if tpe == "chess":
        board = chess.Board(fen=state.get("fen", START_FEN))
        turn = "w" if board.turn == chess.WHITE else "b"
        my_turn = (slot == "host" and turn == "w") or (slot == "guest" and turn == "b")
        legal = []
        if slot and my_turn and not state.get("over"):
            legal = [m.uci() for m in board.legal_moves]
        view.update({
            "side": "w" if slot == "host" else "b",
            "fen": state.get("fen", START_FEN),
            "last": state.get("last"),
            "turn": turn,
            "my_turn": my_turn,
            "legal": legal,
            "over": state.get("over", False),
            "reason": state.get("reason", ""),
            "in_check": bool(board.is_check()),
        })
    elif tpe == "xo":
        moves = state.get("moves", 0)
        turn = moves % 2  # 0 → host
        my_turn = (slot == "host" and turn == 0) or (slot == "guest" and turn == 1)
        view.update({
            "board": state.get("board", "........."),
            "my_sym": "X" if slot == "host" else "O",
            "my_turn": my_turn,
            "moves": moves,
            "over": state.get("over", False),
            "winner": state.get("winner"),
            "draw": state.get("over", False) and not state.get("winner"),
        })
    else:  # tetris
        view.update({
            "seed": state.get("seed"),
            "target": state.get("target", 20),
            "lines": state.get("lines", {"host": 0, "guest": 0}),
            "top": state.get("top", {"host": False, "guest": False}),
            "started": state.get("started", False),
            "over": state.get("over", False),
            "winner": state.get("winner"),
        })
    winner = state.get("winner")
    if winner and tpe != "chess":
        view["winner_name"] = view["host"]["username"] if winner == "host" else (
            view["guest"]["username"] if view["guest"] else "?")
    if tpe == "chess" and state.get("reason"):
        view["winner_name"] = (
            view["host"]["username"] if (state["fen"].split()[1] == "b") else
            view["guest"]["username"])
    return view


def _find_room(db: Session, code: str) -> GameRoom | None:
    room = db.query(GameRoom).filter(GameRoom.code == code.upper()).first()
    if room and room.updated_at and room.updated_at < datetime.utcnow() - ROOM_TTL:
        db.delete(room)
        db.commit()
        return None
    return room


# ---------------------------------------------------------------- страницы
@router.get("/fun/online", response_class=HTMLResponse)
def online_lobby(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    open_rooms = (db.query(GameRoom)
                  .filter(GameRoom.status == "waiting")
                  .order_by(GameRoom.created_at.desc()).limit(12).all())
    mine = (db.query(GameRoom)
            .filter((GameRoom.host_id == user.id) | (GameRoom.guest_id == user.id),
                    GameRoom.status != "waiting")
            .order_by(GameRoom.updated_at.desc()).limit(12).all())
    return templates.TemplateResponse(request, "fun_online.html", {
        "user": user, "active": "fun",
        "types": GAME_TYPES,
        "open_rooms": [{
            "code": r.code, "game_type": r.game_type, "game_name": GAME_TYPES.get(r.game_type, "?"),
            "host": (db.get(User, r.host_id).username if r.host_id else "?"),
            "created": r.created_at,
        } for r in open_rooms],
        "mine": [{
            "code": r.code, "game_type": r.game_type, "game_name": GAME_TYPES.get(r.game_type, "?"),
            "status_label": "идёт" if r.status == "active" else "завершена",
        } for r in mine],
    })


@router.get("/fun/online/game", response_class=HTMLResponse)
def online_game(request: Request, user: User = Depends(require_login), code: str = "", game_type: str = ""):
    game_type = game_type if game_type in GAME_TYPES else ""
    return templates.TemplateResponse(request, "fun_online_game.html", {
        "user": user, "active": "fun", "room_code": code.upper(), "game_type": game_type,
    })


# ---------------------------------------------------------------- API
@router.post("/api/games/create")
def create_game(request: Request, user: User = Depends(require_login),
                db: Session = Depends(get_db), game_type: str = Form("")):
    if game_type not in GAME_TYPES:
        return JSONResponse({"ok": False, "error": "Неизвестная игра."})
    room = GameRoom(
        code=_new_code(db), game_type=game_type, host_id=user.id,
        status="waiting", state=json.dumps(_initial_state(game_type), ensure_ascii=False),
    )
    db.add(room)
    db.commit()
    return JSONResponse({"ok": True, "code": room.code, "game_type": game_type})


@router.post("/api/games/join")
def join_game(request: Request, user: User = Depends(require_login),
              db: Session = Depends(get_db), code: str = Form("")):
    room = _find_room(db, code)
    if not room:
        return JSONResponse({"ok": False, "error": "Комната не найдена или уже закрыта."})
    if room.status == "finished":
        return JSONResponse({"ok": False, "error": "Партия уже завершена."})
    slot = _slot_of(room, user.id)
    if slot:
        return JSONResponse({"ok": True, "code": room.code, "game_type": room.game_type})
    if room.guest_id is not None and room.guest_id != user.id:
        return JSONResponse({"ok": False, "error": "Комната занята. Нужен другой код."})
    room.guest_id = user.id
    room.status = "active"
    db.commit()
    return JSONResponse({"ok": True, "code": room.code, "game_type": room.game_type})


@router.get("/api/games/{code}")
def get_game(code: str, request: Request, user: User = Depends(require_login),
             db: Session = Depends(get_db)):
    room = _find_room(db, code)
    if not room:
        return JSONResponse({"ok": False, "error": "Комната закрыта."})
    return JSONResponse(_view(room, user, db))


@router.post("/api/games/{code}/move")
def make_move(code: str, request: Request, user: User = Depends(require_login),
              db: Session = Depends(get_db),
              uci: str = Form(""), cell: str = Form("-1")):
    room = _find_room(db, code)
    if not room:
        return JSONResponse({"ok": False, "error": "Комната закрыта."})
    if room.status != "active":
        return JSONResponse({"ok": False, "error": "Партия не идёт."})
    state = _load(room)
    if state.get("over"):
        return JSONResponse({"ok": False, "error": "Партия уже завершена."})
    slot = _slot_of(room, user.id)
    if not slot:
        return JSONResponse({"ok": False, "error": "Вы не участник этой партии."})

    if room.game_type == "chess":
        board = chess.Board(fen=state.get("fen", START_FEN))
        turn_is_host = board.turn == chess.WHITE
        if (slot == "host") != turn_is_host:
            return JSONResponse({"ok": False, "error": "Сейчас не ваш ход."})
        uci = (uci or "").strip().lower()
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return JSONResponse({"ok": False, "error": "Некорректный ход."})
        if move not in board.legal_moves:
            return JSONResponse({"ok": False, "error": "Так ходить нельзя."})
        board.push(move)
        state["fen"] = board.fen()
        state["last"] = uci
        if board.is_checkmate():
            state["over"] = True
            state["reason"] = "Мат"
            room.status = "finished"
            room.winner_id = room.host_id if board.turn == chess.BLACK else room.guest_id
        elif board.is_game_over():
            state["over"] = True
            state["reason"] = "Ничья"
            room.status = "finished"
        _save(room, state)
        db.commit()
        return JSONResponse(_view(room, user, db))

    if room.game_type == "xo":
        try:
            cell_i = int(cell)
        except ValueError:
            return JSONResponse({"ok": False, "error": "Некорректная клетка."})
        moves = state.get("moves", 0)
        turn_host = moves % 2 == 0
        if (slot == "host") != turn_host:
            return JSONResponse({"ok": False, "error": "Сейчас не ваш ход."})
        if not (0 <= cell_i < 9):
            return JSONResponse({"ok": False, "error": "Некорректная клетка."})
        board = list(state.get("board", "........."))
        if board[cell_i] != ".":
            return JSONResponse({"ok": False, "error": "Клетка уже занята."})
        board[cell_i] = "X" if slot == "host" else "O"
        moves += 1
        state["board"] = "".join(board)
        state["moves"] = moves
        lines = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
        winner = None
        for a, b, c in lines:
            if board[a] == board[b] == board[c] != ".":
                winner = "host" if board[a] == "X" else "guest"
        if winner:
            state["over"] = True
            state["winner"] = winner
            room.status = "finished"
            room.winner_id = room.host_id if winner == "host" else room.guest_id
        elif moves == 9:
            state["over"] = True
            state["winner"] = None
            room.status = "finished"
        _save(room, state)
        db.commit()
        return JSONResponse(_view(room, user, db))

    return JSONResponse({"ok": False, "error": "Для этой игры такой запрос не нужен."})


@router.post("/api/games/{code}/event")
def game_event(code: str, request: Request, user: User = Depends(require_login),
               db: Session = Depends(get_db), event: str = Form(""), value: str = Form("")):
    room = _find_room(db, code)
    if not room:
        return JSONResponse({"ok": False, "error": "Комната закрыта."})
    if room.game_type != "tetris":
        return JSONResponse({"ok": False, "error": "Нет события для этой игры."})
    slot = _slot_of(room, user.id)
    if not slot:
        return JSONResponse({"ok": False, "error": "Вы не участник этой комнаты."})
    state = _load(room)
    if event == "start":
        if slot != "host":
            return JSONResponse({"ok": False, "error": "Стартовать может только создатель."})
        if not room.guest_id:
            return JSONResponse({"ok": False, "error": "Ждём второго игрока."})
        state["seed"] = random.randrange(1, 2 ** 31 - 1)
        state["lines"] = {"host": 0, "guest": 0}
        state["top"] = {"host": False, "guest": False}
        state["started"] = True
        state["over"] = False
        state["winner"] = None
        room.status = "active"
        room.winner_id = None
    elif event == "lines":
        try:
            val = max(0, int(value))
        except ValueError:
            return JSONResponse({"ok": False, "error": "Некорректное значение."})
        state["lines"][slot] = max(state["lines"].get(slot, 0), val)
    elif event in ("topout", "giveup"):
        state["top"][slot] = True
    else:
        return JSONResponse({"ok": False, "error": "Неизвестное событие."})

    if not state.get("over"):
        lines = state["lines"]
        top = state["top"]
        target = state.get("target", 20)
        if lines.get(slot, 0) >= target:
            state["over"] = True
            state["winner"] = slot
            room.winner_id = room.host_id if slot == "host" else room.guest_id
            room.status = "finished"
        elif top.get(slot) and top.get("host") and top.get("guest"):
            state["over"] = True
            state["winner"] = None          # оба вылетели — ничья
            room.winner_id = None
            room.status = "finished"

    _save(room, state)
    db.commit()
    return JSONResponse(_view(room, user, db))


@router.post("/api/games/{code}/rematch")
def rematch(code: str, request: Request, user: User = Depends(require_login),
            db: Session = Depends(get_db)):
    room = _find_room(db, code)
    if not room:
        return JSONResponse({"ok": False, "error": "Комната закрыта."})
    if room.status != "finished":
        return JSONResponse({"ok": False, "error": "Реванш доступен после завершения партии."})
    if not _slot_of(room, user.id):
        return JSONResponse({"ok": False, "error": "Вы не участник этой комнаты."})
    state = _initial_state(room.game_type)
    room.state = json.dumps(state, ensure_ascii=False)
    room.status = "waiting" if room.guest_id is None else "active"
    room.winner_id = None
    db.commit()
    return JSONResponse({"ok": True, "code": room.code, "game_type": room.game_type})


@router.post("/api/games/{code}/leave")
def leave(code: str, request: Request, user: User = Depends(require_login),
          db: Session = Depends(get_db)):
    room = _find_room(db, code)
    if not room:
        return JSONResponse({"ok": True})
    if user.id == room.host_id:
        db.delete(room)
        db.commit()
        return JSONResponse({"ok": True})
    if user.id == room.guest_id:
        room.guest_id = None
        room.status = "waiting"
        room.state = json.dumps(_initial_state(room.game_type), ensure_ascii=False)
        room.winner_id = None
        db.commit()
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Вы не участник этой комнаты."})