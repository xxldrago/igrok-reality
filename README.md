# Игрок.Реальность

Telegram-платформа для 90-дневного квеста с ежедневным контентом, оплатой, реферальной системой и админ-панелью.

## Архитектура

**Модульный монолит** — 4 процесса, общее ядро:

| Процесс | Стек | Описание |
|---------|------|----------|
| **Bot** | aiogram 3.31 | Telegram-бот для пользователей |
| **API** | FastAPI | REST API для вебхуков и админки |
| **Worker** | ARQ | Фоновые задачи (доставка сообщений) |
| **Scheduler** | APScheduler | Cron-триггеры (ежедневная доставка) |

**Инфраструктура:** PostgreSQL 15+, Redis, Docker Compose

## Полная функциональность

### 1. Регистрация и онбординг

- **Команда `/start`** — точка входа с deep-link для рефералов
- **FSM-машина состояний** — 7 шагов регистрации:
  1. Приветствие и介绍
  2. Пользовательское соглашение (152-ФЗ)
  3. Конфиденциальность
  4. Вопрос 1: Стиль жизни
  5. Вопрос 2: Цели
  6. Вопрос 3: Предпочтения
  7. Вопрос 4: Мотивация
- **Архетипы** — 4 типа игроков (Воин, Маг, Стратег, Исследователь) на основе ответов
- **Реферальная ссылка** — генерируется автоматически, формат: `https://t.me/BOT?start=CODE`

### 2. Квест-движок (90 дней)

- **Свитки (Scrolls)** — ежедневные задания, 360 штук (4 архетипа × 90 дней)
- **Доставка** — автоматическая в 08:00 по МСК через APScheduler + ARQ
- **Отметка выполнения** — inline-кнопка "Выполнил" с callback
- **Сид данных** — скрипт заполнения БД из JSON-файла

### 3. Прогресс и геймификация

- **Опыт (XP)** — начисляется за выполнение свитков
- **Стрики** — отслеживание серий дней подряд с учётом таймзоны пользователя
- **Лидерборд** — рейтинг игроков в Redis (sorted set)
- **Команды:**
  - `/progress` — текущий прогресс (уровень, XP, стрик)
  - `/leaderboard` — топ игроков

### 4. Платежи (Platega.io)

- **Методы оплаты:** СБП, ЕРИП, банковские карты
- **Команда `/pay`** — инициация платежа с inline-кнопкой
- **Вебхук** — обработка статусов: `CONFIRMED`, `CANCELED`, `CHARGEBACKED`, `REFUNDED`
- **Идемпотентность** — защита от дублирования через `idempotency_key`
- **Доступ к каналу** — автоматическая выдача инвайт-ссылки после оплаты, отзыв при отмене

### 5. Реферальная система и комиссия

- **Команда `/referral`** — показ реферальной ссылки с кнопкой копирования
- **Трекинг** — запись реферала при регистрации через deep-link
- **Комиссия** — 10% от первой оплаты реферала (разовая)
- **Баланс наставника** — отслеживание заработанных/выплаченных средств
- **Ручные выплаты** — админ может провести выплату через API

### 6. Админ-панель (React + Ant Design)

**Вход:** JWT-аутентификация с ролями (master, leader, curator)

| Раздел | Описание | Роли |
|--------|----------|------|
| **Пользователи** | Список с поиском/фильтрами, детальный профиль | master, leader, curator |
| **Свитки** | CRUD: создание, редактирование, удаление | master, leader |
| **Платежи** | Список транзакций с фильтрами по статусу | master, leader |
| **Настройки** | Конфигурация платформы (ключ-значение) | master |
| **Аудит** | Журнал всех действий администраторов | master, leader |

**Компоненты:**
- `RoleGuard` — управление видимостью по ролям
- `AdminLayout` — боковое меню с ролевым ограничением
- Ant Design Table с серверной пагинацией

### 7. Безопасность

- **152-ФЗ** — согласие на обработку ПДн, серверы в России
- **Вебхуки Platega** — верификация заголовков `X-MerchantId` + `X-Secret`
- **Rate limiting** — очередь исходящих сообщений (Telegram: 20-25 msg/sec)
- **RBAC** — ролевая модель: master > leader > curator

## Технические решения

| Компонент | Выбор | Обоснование |
|-----------|-------|-------------|
| Telegram | aiogram 3.31 | Async, FSM, router pattern |
| API | FastAPI | Автоматическая OpenAPI-документация |
| ORM | SQLAlchemy 2.0 async | Type hints, async/await |
| Миграции | Alembic | Контроль версий схемы |
| Очередь | ARQ + Redis | Async, lightweight |
| Планировщик | APScheduler | Cron-триггеры |
| Платежи | Platega.io | СБП, ЕРИП, карты, крипто |
| Админка | React + Ant Design | Material-like, rich components |
| БД | PostgreSQL 15+ | JSONB, CTE, window functions |
| Кэш | Redis | Leaderboard (sorted sets), брокер |

## Запуск

```bash
# Клонировать
git clone https://github.com/xxldrago/igrok-reality.git
cd igrok-reality

# Настроить окружение
cp .env.example .env
# Заполнить переменные в .env

# Запустить все сервисы
docker compose up -d

# Сид данных
docker compose exec bot python -m app.shared.seed
```

## Переменные окружения

```bash
# Telegram
BOT_TOKEN=
MASTER_CHANNEL_ID=
QUEST_CHANNEL_ID=
PAYMENT_CHANNEL_ID=

# База данных
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/igrok

# Redis
REDIS_URL=redis://localhost:6379/0

# Platega.io
PLATEGA_MERCHANT_ID=
PLATEGA_SECRET=
PLATEGA_WEBHOOK_URL=

# Админка
ADMIN_USERNAME=
ADMIN_PASSWORD=
JWT_SECRET=

# Приложение
ENVIRONMENT=development
LOG_LEVEL=INFO
TZ=Europe/Moscow
```

## Структура проекта

```
src/
├── app/
│   ├── shared/           # Общее ядро
│   │   ├── models/       # SQLAlchemy модели (7 таблиц)
│   │   ├── config.py     # Настройки (pydantic-settings)
│   │   └── database.py   # Async сессии PostgreSQL
│   ├── bot/              # Telegram-бот
│   │   ├── handlers/     # Роутеры (registration, quest, progress, referral)
│   │   ├── services/     # Бизнес-логика (user, scroll, progress, payment, commission)
│   │   └── main.py       # Точка входа бота
│   └── api/              # FastAPI
│       ├── routes/       # Эндпоинты (health, admin, webhooks)
│       ├── auth.py       # JWT-аутентификация
│       └── main.py       # Точка входа API
├── admin/                # React-админка
│   ├── src/
│   │   ├── pages/        # Users, Scrolls, Payments, Settings, AuditLog
│   │   ├── components/   # RoleGuard
│   │   ├── services/     # API-клиент
│   │   └── layouts/      # AdminLayout
│   └── package.json
├── tests/                # Unit-тесты (81 тест)
└── alembic/              # Миграции БД
```

## Тесты

```bash
# Все тесты
pytest tests/ -v

# Только unit-тесты
pytest tests/unit/ -v
```

**Покрытие:** 81 тест, все проходят.

## Лицензия

Proprietary — All rights reserved.
