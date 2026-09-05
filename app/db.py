import hashlib
import os
import secrets
import ssl as _ssl
from base64 import b64decode, b64encode
from datetime import datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "conspectus.db"))

# --- статусы пользователя ---
STATUS_PENDING = "pending"     # заявка на регистрацию ждёт одобрения
STATUS_ACTIVE = "active"       # допущен
STATUS_REJECTED = "rejected"   # отклонён
STATUS_BANNED = "banned"       # забанен

ROLE_USER = "user"
ROLE_ADMIN = "admin"

RESET_CODE_TTL = timedelta(minutes=10)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False, index=True)

    notes = relationship("Conspect", back_populates="subject", cascade="all, delete-orphan")


class Conspect(Base):
    __tablename__ = "conspects"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    topic = Column(String(200), default="", nullable=False)
    date = Column(String(20), default="", nullable=False)  # ГГГГ-ММ-ДД или свободный текст
    content = Column(Text, nullable=False, default="")
    raw_content = Column(Text, nullable=True)  # исходник до улучшения
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subject = relationship("Subject", back_populates="notes")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(200), default="", nullable=False)  # для 2FA-кодов
    totp_secret = Column(String(64), default="", nullable=False)  # устарело, оставлено для совместимости
    totp_confirmed = Column(Boolean, default=False, nullable=False)
    tg_id = Column(String(32), default="", nullable=False)  # для сброса пароля через Telegram
    role = Column(String(20), default=ROLE_USER, nullable=False)
    status = Column(String(20), default=STATUS_PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reset_codes = relationship("ResetCode", back_populates="user", cascade="all, delete-orphan")
    email_codes = relationship("EmailCode", back_populates="user", cascade="all, delete-orphan")


class ResetCode(Base):
    __tablename__ = "reset_codes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reset_codes")


class EmailCode(Base):
    __tablename__ = "email_codes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="email_codes")


_PBKDF2_ITER = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITER)
    return f"pbkdf2${_PBKDF2_ITER}${b64encode(salt).decode()}${b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt_b64, hash_b64 = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), b64decode(salt_b64), int(iters))
        return secrets.compare_digest(dk, b64decode(hash_b64))
    except Exception:
        return False


def seed_users(db) -> None:
    """Создаёт админа и (опционально) заранее допущенных пользователей из .env.
    Админ создаётся со статусом active; пароль и права обновляются при изменении в .env."""
    from . import config
    from .security import new_secret

    if config.WEB_ADMIN_USERNAME and config.WEB_ADMIN_PASSWORD:
        user = db.query(User).filter(User.username == config.WEB_ADMIN_USERNAME).first()
        if user is None:
            db.add(User(
                username=config.WEB_ADMIN_USERNAME,
                password_hash=hash_password(config.WEB_ADMIN_PASSWORD),
                totp_secret=new_secret(),
                role=ROLE_ADMIN,
                status=STATUS_ACTIVE,
            ))
        else:
            user.password_hash = hash_password(config.WEB_ADMIN_PASSWORD)
            user.role = ROLE_ADMIN
            user.status = STATUS_ACTIVE
    for chunk in (config.WEB_EXTRA_USERS or "").replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        u, p = (x.strip() for x in chunk.split(":", 1))
        if u and p and not db.query(User).filter(User.username == u).first():
            db.add(User(
                username=u,
                password_hash=hash_password(p),
                totp_secret=new_secret(),
                role=ROLE_USER,
                status=STATUS_ACTIVE,
            ))
    db.commit()


def issue_reset_code(db, user: User) -> str:
    """Генерирует 6-значный код для сброса пароля и сохраняет его хеш."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.query(ResetCode).filter(ResetCode.user_id == user.id, ResetCode.used.is_(False)).update(
        {ResetCode.used: True}, synchronize_session=False
    )
    db.add(ResetCode(
        user_id=user.id,
        code_hash=hashlib.sha256(code.encode()).hexdigest(),
        expires_at=datetime.utcnow() + RESET_CODE_TTL,
    ))
    db.commit()
    return code


def check_reset_code(db, user: User, code: str) -> bool:
    row = (
        db.query(ResetCode)
        .filter(
            ResetCode.user_id == user.id,
            ResetCode.used.is_(False),
            ResetCode.expires_at > datetime.utcnow(),
        )
        .order_by(ResetCode.id.desc())
        .first()
    )
    if not row:
        return False
    ok = secrets.compare_digest(row.code_hash, hashlib.sha256(code.strip().encode()).hexdigest())
    if ok:
        row.used = True
        db.commit()
    return ok


def issue_email_code(db, user: User) -> str:
    """6-значный код 2FA для входа по почте."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.query(EmailCode).filter(EmailCode.user_id == user.id, EmailCode.used.is_(False)).update(
        {EmailCode.used: True}, synchronize_session=False
    )
    db.add(EmailCode(
        user_id=user.id,
        code_hash=hashlib.sha256(code.encode()).hexdigest(),
        expires_at=datetime.utcnow() + RESET_CODE_TTL,
    ))
    db.commit()
    return code


def check_email_code(db, user: User, code: str) -> bool:
    row = (
        db.query(EmailCode)
        .filter(
            EmailCode.user_id == user.id,
            EmailCode.used.is_(False),
            EmailCode.expires_at > datetime.utcnow(),
        )
        .order_by(EmailCode.id.desc())
        .first()
    )
    if not row:
        return False
    ok = secrets.compare_digest(row.code_hash, hashlib.sha256(code.strip().encode()).hexdigest())
    if ok:
        row.used = True
        db.commit()
    return ok


DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    _url = DATABASE_URL
    if _url.startswith("postgres://"):
        _url = "postgresql" + _url[len("postgres"):]
    # лёгкий чистый драйвер без нативных бинарников (устойчив на serverless)
    if _url.startswith("postgresql://") and "+" not in _url.split("://")[0]:
        _url = "postgresql+pg8000://" + _url.split("postgresql://", 1)[1]
    # Supabase pooler требует TLS, но у многоклиентского пулера (Supavisor)
    # в цепочке свой self-signed root, который не проходит проверку штатными CA.
    # Оставляем шифрование канала, верификацию цепочки отключаем (аналог sslmode=require).
    _tls = _ssl.create_default_context()
    _tls.check_hostname = False
    _tls.verify_mode = _ssl.CERT_NONE
    engine = create_engine(_url, pool_pre_ping=True, connect_args={"ssl_context": _tls})
else:
    # Без DATABASE_URL — in-memory sqlite (Vercel: файловая система read-only,
    # файла на диске создать нельзя). Данные живут до конца процесса.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()