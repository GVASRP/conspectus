import os

from dotenv import load_dotenv

load_dotenv()


def get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Провайдер улучшения конспектов (OpenAI-совместимый API)
# Подходит для OpenAI, Google Gemini (нужен ключ + base_url на Google endpoint),
# любых OpenAI-совместимых сервисов.
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.4"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4000"))

# Горизонтальный масштаб улучшения: "api" (автоматически через API)
# или "prompt" (выдаём промт, пользователь улучшает вручную/через Gemini).
AI_MODE = os.getenv("AI_MODE", "prompt")

# Разрешённые Telegram ID (через запятую). Пусто = все.
BOT_ALLOWED_IDS = os.getenv("BOT_ALLOWED_IDS", "")

# Веб-интерфейс: авторизация
# Администратор (единственный, пароль меняется через upsert_user)
WEB_ADMIN_USERNAME = os.getenv("WEB_ADMIN_USERNAME", "admin")
WEB_ADMIN_PASSWORD = os.getenv("WEB_ADMIN_PASSWORD", "")
# Дополнительные пользователи: user1:pass1,user2:pass2
WEB_EXTRA_USERS = os.getenv("WEB_EXTRA_USERS", "")
# Telegram ID админа — для уведомлений о новых заявках (пусто = не слать)
ADMIN_TG_ID = os.getenv("ADMIN_TG_ID", "")

# Отправка 2FA-кодов через Supabase Auth (email от @supabase.co)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
# Вход только логин+пароль без почтового кода. Вернуть 2FA: WEB_REQUIRE_2FA=true
WEB_REQUIRE_2FA = get_bool("WEB_REQUIRE_2FA", False)
# Публичный адрес сайта (для ссылок в админке), напр. http://1.2.3.4:8000
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
# Название проекта / issuer для TOTP
APP_NAME = os.getenv("APP_NAME", "Conspectus")
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
