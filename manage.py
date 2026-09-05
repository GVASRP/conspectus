"""CLI-инструменты: создание пользователей, сброс 2FA, бан и т.п.

Примеры:
  python manage.py users
  python manage.py create-user --username vasya --password secretpass
  python manage.py create-user --username vasya --password secretpass --admin
  python manage.py reset-totp --username vasya
  python manage.py ban --username vasya
  python manage.py unban --username vasya
"""

import argparse
import secrets
import sys

from app import security
from app.db import (
    ROLE_ADMIN,
    ROLE_USER,
    STATUS_ACTIVE,
    STATUS_BANNED,
    STATUS_PENDING,
    STATUS_REJECTED,
    SessionLocal,
    User,
    hash_password,
    init_db,
    seed_users,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Conspectus CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("users", help="список пользователей")

    p = sub.add_parser("create-user", help="создать пользователя")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--admin", action="store_true", help="сделать администратором")
    p.add_argument("--approve", action="store_true", help="сразу допустить (active)")

    p = sub.add_parser("reset-totp", help="сбросить 2FA (пригодится, если потерял телефон)")
    p.add_argument("--username", required=True)

    p = sub.add_parser("ban", help="забанить")
    p.add_argument("--username", required=True)

    p = sub.add_parser("unban", help="разбанить")
    p.add_argument("--username", required=True)

    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
        if args.cmd == "users":
            for u in db.query(User).order_by(User.id).all():
                role = "admin" if u.role == ROLE_ADMIN else "user"
                print(f"#{u.id:>3}  @{u.username:<22} {role:<6} {u.status:<9} 2fa={'YES' if u.totp_confirmed else 'no '}"
                      f" tg={u.tg_id or '-'}")
            return 0

        if args.cmd == "create-user":
            username = args.username.strip()
            if db.query(User).filter(User.username == username).first():
                print(f"Ошибка: @{username} уже существует", file=sys.stderr)
                return 1
            user = User(
                username=username,
                password_hash=hash_password(args.password),
                totp_secret=security.new_secret(),
                role=ROLE_ADMIN if args.admin else ROLE_USER,
                status=STATUS_ACTIVE if args.approve or args.admin else STATUS_PENDING,
            )
            db.add(user)
            db.commit()
            print(f"Создан @{username} (роль={user.role}, статус={user.status}). 2FA будет предложена при первом входе.")
            return 0

        if args.cmd == "reset-totp":
            user = db.query(User).filter(User.username == args.username.strip()).first()
            if not user:
                print(f"Ошибка: @{args.username} не найден", file=sys.stderr)
                return 1
            user.totp_secret = security.new_secret()
            user.totp_confirmed = False
            db.commit()
            print(f"2FA для @{user.username} сброшена. При следующем входе покажется QR — отсканируй заново.")
            return 0

        if args.cmd in ("ban", "unban"):
            user = db.query(User).filter(User.username == args.username.strip()).first()
            if not user:
                print(f"Ошибка: @{args.username} не найден", file=sys.stderr)
                return 1
            user.status = STATUS_BANNED if args.cmd == "ban" else STATUS_ACTIVE
            db.commit()
            print(f"@{user.username}: {user.status}")
            return 0

    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())