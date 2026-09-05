# Conspectus 🎓

Личная база конспектов для 10 класса. Записи и «простыни» текста превращаются в
нормальные структурированные конспекты, которые хранятся по предметам, темам и датам.

- **Веб-сайт** — красивый дашборд с предметами, конспектами и поиском.
- **Telegram-бот** — добавлять конспекты, улучшать через ИИ.
- **Улучшение текста** — через API (OpenAI-совместимый, в т.ч. Gemini) или ручным промтом.

## 🛡 Безопасность из коробки

- **Обязательная 2FA (TOTP)** — на входе, на регистрации, при смене пароля
  (в настройках) и при восстановлении пароля. Секреты — PBKDF2, сессии — подписанные cookie.
- **Вход только для приглашённых.** Регистрация создаёт *заявку* — её одобряет админ
  в админ-панели. Отклонённые и забаненные не могут войти.
- **Админ-панель `/admin`** — одобрение/отклонение заявок, баны, выдача ролей.
  О новых заявках админу приходит уведомление в Telegram (`ADMIN_TG_ID`).
- **Телеграм-бот** — только для Telegram ID из `BOT_ALLOWED_IDS` (посторонние отсекаются
  middleware до любых команд).
- **Восстановление пароля** — 6-значный код приходит в **Telegram** (нужен привязанный
  `tg_id`), плюс подтверждение TOTP.

## Как это работает

1. Ты диктуешь/переписываешь записи учителя → текст.
2. Текст улучшается промтом → структурированный конспект.
3. Конспект сохраняется в SQLite и публикуется на сайте и в боте.

Два режима улучшения (переменная `AI_MODE`):

| Режим | Что делает |
|---|---|
| `prompt` | Возвращает готовый промт. Вставляешь его в Gemini/другую LLM, получаешь улучшенный текст. 100% бесплатно. |
| `api` | Автоматически вызывает API нейросети (OpenAI, Gemini и др. — всё, что поддерживает OpenAI-формат). Нужен ключ. |

## Установка (локально / на VPS)

Python 3.10+.

```bash
python -m venv .venv
# Linux:  source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # заполни BOT_TOKEN, WEB_ADMIN_*, SECRET_KEY и др.
```

### Запуск сайта

```bash
python run_web.py
# → http://localhost:8000
```

### Запуск бота

```bash
python run_bot.py
```

## Настройка `.env`

```ini
BOT_TOKEN=                # от @BotFather
BOT_ALLOWED_IDS=          # твой Telegram ID (через запятую). Пусто = бот открыт всем! НЕ ставь пустым.
ADMIN_TG_ID=              # твой Telegram ID — уведомления о заявках
PUBLIC_URL=http://1.2.3.4:8000   # публичный адрес сайта

# --- обязательно! ---
WEB_ADMIN_USERNAME=admin
WEB_ADMIN_PASSWORD=       # придумай надёжный пароль
SECRET_KEY=               # python -c "import secrets; print(secrets.token_hex(32))"

AI_MODE=prompt            # prompt | api
AI_API_KEY=               # ключ API (для mode=api)
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
WEB_HOST=0.0.0.0
WEB_PORT=8000
```

> При первом запуске создастся учётка `WEB_ADMIN_USERNAME`. При первом входе система
> предложит настроить 2FA (отсканировать QR). Без `WEB_ADMIN_PASSWORD` в `.env` войти
> не сможет никто.

Для Gemini с `AI_MODE=api`:

```ini
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
AI_MODEL=gemini-2.0-flash
AI_API_KEY=<ключ от Google AI Studio>
```

## Регистрация и администрирование

1. Нужный человек открывает `PUBLIC_URL/register`, создаёт аккаунт, сразу настраивает 2FA.
2. В админ-панели (`/admin`) появляется заявка (+ уведомление в Telegram).
3. Ты жмёшь **Одобрить** — человек может входить.
4. В `/admin/users`: бан/разбан, выдача ролей (нельзя снять/выдать себе).

## CLI (`manage.py`)

Полезно, если потерял телефон, забыл пароль админа или хочешь выдать доступ из терминала:

```bash
python manage.py users                      # список
python manage.py create-user --username vasya --password s3cret --admin --approve
python manage.py reset-totp --username vasya   # сброс 2FA (покажет QR при входе)
python manage.py ban --username vasya
python manage.py unban --username vasya
```

## Деплой на VPS (1ГБ/1 ядро — этого хватает)

Два процесса: `python run_web.py` и `python run_bot.py`. Поддерживаются через `systemd`.

```bash
cd /opt/conspectus
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env
```

`/etc/systemd/system/conspectus-web.service`:

```ini
[Unit]
Description=Conspectus Web
After=network.target

[Service]
WorkingDirectory=/opt/conspectus
ExecStart=/opt/conspectus/.venv/bin/python run_web.py
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/conspectus-bot.service` — то же, но `ExecStart=... run_bot.py`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now conspectus-web conspectus-bot
```

> Старый бот перед этим удаляется: `sudo systemctl disable --now <старый сервис>` и
> останови его процесс, если он запущен через `nohup`/`screen`.

## Как улучшить текст вручную (режим prompt, бесплатно)

Бот (`/improve <id>`) или сайт (галочка «Улучшить») вернёт текст-промт. Вставь его в
[Gemini](https://gemini.google.com) и получи улучшенный конспект. Сохранить его можно
повторно через бота или сайт.

## Команды бота

```
/start  — приветствие
/add    — добавить конспект (пошагово)
/list   — список предметов
/improve <id> — улучшить конспект через ИИ
/help   — справка
```