# Игрок.Реальность (ОРЪ)

Telegram-платформа 90-дневного квеста «Игра ОРЪ»: входной тест на архетип, ежедневные свитки с XP, стрик, оплата через Platega.io, реферальная система и две админ-панели (веб + Telegram Mini App).

## Архитектура

**Модульный монолит** — 4 процесса + фронты:

| Процесс | Стек | Описание |
|---------|------|----------|
| **Bot** | aiogram 3.x | Telegram-бот: регистрация, квиз, команды, оплата |
| **API** | FastAPI | REST API, вебхук Platega, раздача фронтов и медиа |
| **Worker** | ARQ | Фон: рассылка свитков, очередь уведомлений |
| **Scheduler** | APScheduler | Cron: слоты доставки, напоминания, прокачка очереди |

**Инфраструктура:** PostgreSQL 15+, Redis, Docker Compose. Фронты собираются внутри Dockerfile (multi-stage + Node).

## Путь игрока

1. `/start` → приветствие ОРЪ (режется на чанки по 4096) → согласие 152-ФЗ
2. **Входной тест** — 4 вопроса (Тело / Тропа / Компас / Отклик), варианты A–D
3. **Архетип** — большинство из 4 побеждает (3–4), сплит решает ответ на вопрос 1. Маппинг: A→Голова, B→Панцирь, C→Вихрь, D→Призрак + персональный результат с девизом и практикой
4. **Оплата** — промпт сразу после регистрации: кнопка на Platega (4900₽ из настроек) или «Тестовая оплата» при выключенном приёме. После оплаты: `paid_at`, часы квеста стартуют, доступ продолжается **внутри бота**
5. **Свитки** — ежедневно по слотам (05:00, 08:00, 12:00, 14:00, 16:00, 21:00), кнопка «✅ Выполнить» → отчёт/skip
6. Типы дней: обычные (8 свитков, 31 XP) • медитация 1, 8, 15… (+Корни, 36 XP) • дыхание 7, 14, 21… (Ветер ×3 + Зря + Отчёт, 20 XP) • осознание 6, 13, 20… (Зря + Отчёт, 8 XP)
7. Ночной зачёт 00:00–05:00 относит команды на прошлый день; повторы блокируются; опечатки получают подсказку со списком команд дня

### Команды бота

`/start` `/pay` `/today` `/report` `/wakeup` `/cold` `/scan` `/scanreport` `/breath` `/micro` `/focus` `/food` `/sleep` `/profile` `/progress` `/leaderboard` `/referral` `/admin` (роли master/leader/curator → TMA-панель)

## Платежи (Platega.io)

- Создание платежа в `/pay`, колбэк вебхука `CONFIRMED/CANCELED/CHARGEBACKED/REFUNDED`, идемпотентность по `idempotency_key`
- Общий финализатор успеха: `users.paid_at`, старт часов, доступ в квест-канал (инвайт), уведомление, пост в payment-канал, комиссия наставнику (10% с первой оплаты)
- Возврат/чарджбэк: бан в канале + сброс `paid_at`
- Тестовый режим: `payments_enabled=false` → кнопка «Тестовая оплата» идёт тем же путём без Platega

## Админ-панели

Веб (`/admin/`, JWT) и TMA (`/app/`, вход по Telegram initData, вне Telegram — пароль). Роли: master > leader > curator (+ specialist, player).

| Раздел | Возможности |
|--------|-------------|
| Дашборд | KPI, удержание, активность |
| Пользователи | Поиск/фильтры, карточка: профиль, прогресс-теплокарта 90 дней, платежи, **редактирование и создание** |
| Свитки | Контент 90×N с фильтром по дню, **вложения** (фото/видео/файлы), баннер покрытия 625, редактор типов (XP, часы) |
| Рассылка | Текст + **вложения** + parse_mode, фильтр по архетипу, **отложенная отправка** с календарём, очередь и отмена |
| Входной тест | Вступление, 4 вопроса, скоринг A–D, тексты результатов |
| Платежи / Финансы | Транзакции, комиссии, призовые фонды, CSV-экспорт |
| Настройки | Группы: Telegram, Platega, оплата (цена, вкл/выкл), механики, медиа, контент |
| Профиль | Логин, @telegram, смена пароля |
| Модерация / Аудит | Жалобы, журнал действий |

## Настройки из панели (без рестарта, если не сказано иначе)

Цена и вкл/выкл оплаты, токены и ID каналов, Platega, XP-веса, стрик-бонусы, grace-часы, размер лидерборда, время напоминания, слоты доставки и предупреждение о стрике (**рестарт scheduler**), тексты приветствия/согласия/квиза, `media_base_url`. Инфра (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`) — только через `.env`.

## Запуск и обновление (VPS)

```bash
cd /home/igrok/igrok
git pull
# одноразово, если alembic_version ещё VARCHAR(32):
docker compose run --rm api python -c "
import asyncio, asyncpg, urllib.parse as up
from app.shared.config import settings
async def f():
    d=settings.DATABASE_URL.replace('postgresql+asyncpg://','postgresql://'); p=up.urlparse(d)
    c=await asyncpg.connect(host=p.hostname,port=p.port,user=p.username,password=p.password,database=p.path.lstrip('/'))
    await c.execute('ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(128)')
    await c.close(); print('widened')
asyncio.run(f())
"
docker compose run --rm api alembic -c src/alembic.ini upgrade head
docker compose build
# Сиды (upsert; затрут ручные правки квиза/приветствия из панели!):
docker compose run --rm bot python -m scripts.seed_daily_scrolls --rebuild
docker compose run --rm bot python -m scripts.insert_welcome_message
docker compose run --rm bot python -m scripts.seed_quiz_config
docker compose up -d
# Проверка:
docker compose run --rm api alembic -c src/alembic.ini current  # head
docker compose ps
```

Первый вход в веб-панель — логин/пароль из `.env` (`ADMIN_USERNAME`/`ADMIN_PASSWORD`); вход в TMA — командой `/admin` в боте (роль master/leader/curator).

## Структура проекта

```
src/
├── app/
│   ├── shared/      # config, database, models (users, scrolls, payments, ...)
│   ├── bot/         # handlers (registration, daily, payment, scroll, ...), services, keyboards
│   ├── api/         # routes (admin, media, webhooks, auth), main.py (+раздача /admin /app /media)
│   ├── worker/      # ARQ-задачи (scroll_slot, notifications)
│   └── scheduler/   # APScheduler (слоты, напоминания, прокачка очереди)
├── admin/           # React (веб-панель)
├── tma/             # React (Telegram Mini App)
├── alembic.ini      # запуск: alembic -c src/alembic.ini ...
└── alembic/versions # миграции
scripts/             # seed_daily_scrolls, seed_quiz_config, insert_welcome_message, init_db
tests/unit/          # юнит-тесты
docs/                # DEPLOY.md, ROLE_MECHANICS.md
```

## Тесты

```bash
.venv/bin/python -m pytest tests/ -q
```

227 passed (1 сетевой `test_login_success` требует DNS — не код). Фронты: `npx tsc --noEmit` + `npm run build` в `src/admin` и `src/tma`.

## Лицензия

Proprietary — All rights reserved.
