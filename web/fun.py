"""Развлечения: комната отдыха — игры, погода, мини-приколы."""

import random
import re

import chess  # python-chess
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import Conspect, Subject, User, get_db
from web.deps import require_login, templates

router = APIRouter(tags=["fun"])

GAMES = {
    "2048": "2048",
    "snake": "Змейка",
    "memory": "Память",
    "tetris": "Тетрис",
    "minesweeper": "Сапёр",
    "fifteen": "Пятнашки",
    "chess": "Шахматы с ботом",
    "xo": "Крестики-нолики с ботом",
    "quiz": "Квиз по конспектам",
    "weather": "Погода",
}

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# ---------------------------------------------------------------- шахматный бот
_PIECE_VAL = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900}


def _chess_eval(board: chess.Board) -> int:
    """Материал + лёгкие бонусы (продвинутые пешки, центр, безопасность короля)."""
    score = 0
    for sq in chess.SQUARES:
        pc = board.piece_at(sq)
        if not pc:
            continue
        sign = 1 if pc.color == chess.WHITE else -1
        v = _PIECE_VAL.get(pc.symbol().lower(), 0)
        fi, rn = chess.square_file(sq), chess.square_rank(sq)
        if pc.piece_type == chess.PAWN:
            adv = rn if pc.color == chess.WHITE else 7 - rn
            v += adv * 12
        elif pc.piece_type in (chess.KNIGHT, chess.BISHOP):
            v += int((3.5 - abs(fi - 3.5) - abs(rn - 3.5)) * 10)
        elif pc.piece_type == chess.KING:
            if rn in (0, 7) and 2 <= fi <= 5:
                v += 15 if pc.color == chess.WHITE else -15
        score += sign * v
    # небольшой штраф за висячего/тупикового ферзя — отсекаем грубые зевки
    return score


def _chess_search(board: chess.Board, depth: int, alpha: int, beta: int) -> int:
    if board.is_game_over():
        if board.is_checkmate():
            return -100000 + board.fullmove_number
        return 0
    if depth == 0:
        return _chess_eval(board)
    moves = list(board.legal_moves)
    moves.sort(key=lambda m: board.is_capture(m), reverse=True)
    best = -10 ** 9
    for m in moves:
        board.push(m)
        s = -_chess_search(board, depth - 1, -beta, -alpha)
        board.pop()
        if s > best:
            best = s
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best


def _chess_bot_move(board: chess.Board, depth: int):
    moves = list(board.legal_moves)
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]
    moves.sort(key=lambda m: (board.is_capture(m), board.is_check()), reverse=True)
    best_move, best_score = moves[0], -10 ** 9
    for m in moves:
        board.push(m)
        s = -_chess_search(board, depth - 1, -10 ** 9, 10 ** 9)
        board.pop()
        if s > best_score:
            best_score, best_move = s, m
    return best_move


def _chess_over_reason(board: chess.Board) -> str:
    if board.is_checkmate():
        return "Мат"
    if board.is_stalemate():
        return "Пат"
    if board.is_insufficient_material():
        return "Ничья: недостаточно материала"
    if board.is_fifty_moves():
        return "Ничья: правило 50 ходов"
    if board.is_repetition():
        return "Ничья: троекратное повторение"
    return "Игра окончена"


# ---------------------------------------------------------------- ХО-бот
_XO_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def _xo_winner(board: str):
    for a, b, c in _XO_LINES:
        if board[a] == board[b] == board[c] != ".":
            return board[a]
    if "." not in board:
        return "draw"
    return None


def _xo_minimax(board: str, sym: str) -> int:
    """Оценка с точки зрения X (X максимизирует, O минимизирует)."""
    w = _xo_winner(board)
    if w == "X":
        return 1
    if w == "O":
        return -1
    if w == "draw":
        return 0
    sym2 = "O" if sym == "X" else "X"
    if sym == "X":
        return max(_xo_minimax(board[:i] + sym + board[i + 1:], sym2)
                   for i, v in enumerate(board) if v == ".")
    return min(_xo_minimax(board[:i] + sym + board[i + 1:], sym2)
               for i, v in enumerate(board) if v == ".")


def _xo_bot_move(board: str, bot_sym: str) -> int:
    empty = [i for i, v in enumerate(board) if v == "."]
    if not empty:
        return -1
    # иногда ошибаемся, чтобы человек мог выиграть
    if random.random() < 0.14:
        return random.choice(empty)
    best, best_score = empty[0], None
    for i in empty:
        nb = board[:i] + bot_sym + board[i + 1:]
        s = _xo_minimax(nb, "O" if bot_sym == "X" else "X")
        if bot_sym == "O":
            s = -s  # играем от лица бота
        if best_score is None or s > best_score:
            best_score, best = s, i
    return best


def _xo_my_turn(board: str, my_sym: str) -> bool:
    placed = sum(1 for c in board if c != ".")
    return ("X" if placed % 2 == 0 else "O") == my_sym

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
    notes = db.query(Conspect).filter(Conspect.subject_id.isnot(None)).all()
    if not notes:
        return JSONResponse({"ok": False, "error": "Конспектов пока нет — добавь что-нибудь, чтобы играть."})
    subjects = db.query(Subject).filter(Subject.id.in_([n.subject_id for n in notes])).all()
    if len(subjects) < 2:
        return JSONResponse({"ok": False, "error": "Нужно минимум два предмета с конспектами, а пока один."})
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


# ---------------------------------------------------------------- партии с ботом
@router.post("/api/bot/chess/move")
def bot_chess_move(request: Request, user: User = Depends(require_login),
                   fen: str = Form(START_FEN), uci: str = Form(""), color: str = Form("w")):
    """Stateless: клиент шлёт свою позицию и ход, сервер отвечает ходом бота."""
    color = "w" if color != "b" else "b"
    try:
        board = chess.Board(fen=fen or START_FEN)
    except Exception:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": "Некорректная позиция."})
    mvn = (uci or "").strip().lower()
    last_uci = ""
    if mvn:
        try:
            move = chess.Move.from_uci(mvn)
        except ValueError:
            return JSONResponse({"ok": False, "error": "Некорректный ход."})
        if move not in board.legal_moves:
            return JSONResponse({"ok": False, "error": "Так ходить нельзя."})
        board.push(move)
        last_uci = mvn
    if not board.is_game_over():
        turn = "w" if board.turn == chess.WHITE else "b"
        if turn != color:
            bot_move = _chess_bot_move(board, 3)
            if bot_move:
                board.push(bot_move)
                last_uci = bot_move.uci()
    turn = "w" if board.turn == chess.WHITE else "b"
    over = board.is_game_over()
    my_turn = not over and turn == color
    legal = [m.uci() for m in board.legal_moves] if my_turn else []
    winner = None
    if board.is_checkmate():
        winner = "bot" if turn == color else "me"  # тот, кто под матом, — проиграл
    return JSONResponse({
        "ok": True,
        "fen": board.fen(),
        "turn": turn,
        "my_turn": my_turn,
        "legal": legal,
        "last": last_uci or None,
        "in_check": bool(board.is_check()),
        "over": over,
        "reason": _chess_over_reason(board) if over else "",
        "winner": winner,
        "player_color": color,
    })


@router.post("/api/bot/xo/move")
def bot_xo_move(request: Request, user: User = Depends(require_login),
                board: str = Form("........."), cell: str = Form("-1"), my_sym: str = Form("X")):
    """Stateless крестики-нолики против бота. cell=-1 — бот ходит первым."""
    my_sym = "X" if my_sym != "O" else "O"
    b = "".join((c if c in "XO" else ".") for c in (board or ""))
    if len(b) != 9:
        b = "........."
    if (cell or "").strip() != "-1":
        if not _xo_my_turn(b, my_sym):
            return JSONResponse({"ok": False, "error": "Сейчас не ваш ход."})
        try:
            idx = int(cell)
        except ValueError:
            return JSONResponse({"ok": False, "error": "Некорректная клетка."})
        if not (0 <= idx < 9) or b[idx] != ".":
            return JSONResponse({"ok": False, "error": "Клетка недоступна."})
        b = b[:idx] + my_sym + b[idx + 1:]
    over = _xo_winner(b)
    if not over and not _xo_my_turn(b, my_sym):
        bot_sym = "O" if my_sym == "X" else "X"
        i = _xo_bot_move(b, bot_sym)
        if i >= 0:
            b = b[:i] + bot_sym + b[i + 1:]
    over = _xo_winner(b)
    win_char = over if over in ("X", "O") else None
    winner = None
    if win_char:
        winner = "me" if win_char == my_sym else "bot"
    return JSONResponse({
        "ok": True,
        "board": b,
        "my_sym": my_sym,
        "my_turn": not over and _xo_my_turn(b, my_sym),
        "over": bool(over),
        "winner": winner,
        "draw": over == "draw",
        "moves": sum(1 for c in b if c != "."),
    })