# Деплой Игрок.Реальность на Ubuntu VPS

## Содержание

1. [Требования](#1-требования)
2. [Подготовка сервера](#2-подготовка-сервера)
3. [DNS записи](#3-dns-записи)
4. [Клонирование и настройка](#4-клонирование-и-настройка)
5. [Telegram Bot](#5-telegram-bot)
6. [Docker и деплой](#6-docker-и-деплой)
7. [SSL сертификаты](#7-ssl-сертификаты)
8. [Nginx](#8-nginx)
9. [Миграции и seed](#9-миграции-и-seed)
10. [Первый запуск](#10-первый-запуск)
11. [Проверка](#11-проверка)
12. [Обновление](#12-обновление)

---

## 1. Требования

| Ресурс | Минимум | Рекомендация |
|--------|---------|--------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB |
| Диск | 20 GB SSD | 40 GB SSD |
| ОС | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Домен | 2 поддомена | — |

**Нужные домены:**
- `панель.оръ.рф` — админ-панель (веб)
- `api.оръ.рф` — API + TMA (Telegram Mini App)

---

## 2. Подготовка сервера

### Подключение к серверу

```bash
ssh root@<IP_СЕРВЕРА>
```

### Обновление системы

```bash
apt update && apt upgrade -y
```

### Установка Docker

```bash
# Docker
curl -fsSL https://get.docker.com | sh

# Docker Compose (plugin)
apt install -y docker-compose-plugin

# Проверка
docker --version
docker compose version
```

### Установка Nginx

```bash
apt install -y nginx
systemctl enable nginx
systemctl start nginx
```

### Установка Certbot (для SSL)

```bash
apt install -y certbot python3-certbot-nginx
```

### Настройка файрвола

```bash
# UFW
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

### Создание директории проекта

```bash
mkdir -p /opt/igrok
```

---

## 3. DNS записи

Настройте DNS у вашего регистратора:

| Тип | Имя | Значение | TTL |
|-----|-----|----------|-----|
| A | `api` | `<IP_СЕРВЕРА>` | 300 |
| A | `панель` | `<IP_СЕРВЕРА>` | 300 |

> **Примечание:** `.оръ.рф` — кириллический домен. Убедитесь, что ваш регистратор поддерживает IDN (Internationalized Domain Names) и настройте IDN-кодировку (Punycode) если нужно.

Проверьте DNS:

```bash
dig api.оръ.рф +short
dig панель.оръ.рф +short
```

---

## 4. Клонирование и настройка

### Клонирование репозитория

```bash
cd /opt/igrok
git clone <URL_РЕПОЗИТОРИЯ> .
```

### Создание .env файла

```bash
cp .env.example .env
nano .env
```

Заполните все переменные:

```bash
# === Telegram Bot ===
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
BOT_USERNAME=igrok_reality_bot
MASTER_CHANNEL_ID=-1001234567890
QUEST_CHANNEL_ID=-1001234567891
PAYMENT_CHANNEL_ID=-1001234567892

# === Database ===
DATABASE_URL=postgresql+asyncpg://igrok:igrok@postgres:5432/igrok

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === Platega.io Payments ===
PLATEGA_MERCHANT_ID=your_merchant_id
PLATEGA_SECRET=your_secret
PLATEGA_WEBHOOK_URL=https://api.оръ.рф/webhook/platega

# === JWT Auth (измените в продакшене!) ===
JWT_SECRET=your-super-secret-key-change-this
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-password

# === TMA ===
TMA_WEBAPP_URL=https://api.оръ.рф

# === Application ===
ENVIRONMENT=production
LOG_LEVEL=INFO
TZ=Asia/Krasnoyarsk
```

**Важно:** Замените все значения на реальные. Особенно:
- `BOT_TOKEN` — от BotFather
- `MASTER_CHANNEL_ID`, `QUEST_CHANNEL_ID`, `PAYMENT_CHANNEL_ID` — ID каналов
- `JWT_SECRET` — генерируйте длинную строку: `openssl rand -hex 32`
- `ADMIN_PASSWORD` — надёжный пароль

---

## 5. Telegram Bot

### Создание бота

1. Найдите `@BotFather` в Telegram
2. Отправьте `/newbot`
3. Имя: `Игрок.Реальность`
4. Username: `igrok_reality_bot` (или другой)
5. Сохраните токен → вставьте в `BOT_TOKEN`

### Настройка бота

```bash
# Установите описание
# В BotFather: /setdescription
# Вставьте текст описания бота

# Установите команды
# В BotFather: /setcommands
# Вставьте:
start - Начать игру
progress - Мой прогресс
profile - Мой профиль
leaderboard - Рейтинг
pay - Оплатить доступ
referral - Моя реферальная ссылка
clan - Мой клан
today - Сегодняшние задания
help - Помощь
```

### Создание каналов

Создайте 3 канала в Telegram:

1. **Master Channel** — приватный канал для мастера
   - Создайте канал → Сделайте приватным
   - Добавьте бота администратором
   - Перешлите любое сообщение в `@userinfobot` или `@getidsbot` → получите ID канала
   - Запишите в `MASTER_CHANNEL_ID` (с префиксом `-100`)

2. **Quest Channel** — канал с контентом квеста
   - Создайте канал → Сделайте приватным
   - Добавьте бота администратором
   - Получите ID → `QUEST_CHANNEL_ID`

3. **Payment Channel** — канал для платных уведомлений
   - Создайте канал → Сделайте приватным
   - Добавьте бота администратором
   - Получите ID → `PAYMENT_CHANNEL_ID`

### Настройка Webhook (Platega.io)

В личном кабинете Platega.io:
- Webhook URL: `https://api.оръ.рф/webhook/platega`
- Метод: POST
- Заголовки: `X-MerchantId`, `X-Secret`

---

## 6. Docker и деплой

### Сборка образов

```bash
cd /opt/igrok

# Сборка всех сервисов
docker compose build --no-cache
```

### Первый запуск

```bash
# Запустить все сервисы
docker compose up -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f
```

### Проверка健康的 сервисов

```bash
# Все сервисы должны быть running
docker compose ps

# Проверка логов каждого сервиса
docker compose logs bot
docker compose logs api
docker compose logs worker
docker compose logs scheduler
docker compose logs postgres
docker compose logs redis
```

---

## 7. SSL сертификаты

### Получение сертификатов

```bash
# Для api.оръ.рф
certbot --nginx -d api.оръ.рф --non-interactive --agree-tos -m your@email.com

# Для панель.оръ.рф
certbot --nginx -d панель.оръ.рф --non-interactive --agree-tos -m your@email.com
```

### Автообновление

```bash
# Проверьте таймер
systemctl status certbot.timer

# Тест обновления
certbot renew --dry-run
```

---

## 8. Nginx

### Создание конфигурации API

```bash
nano /etc/nginx/sites-available/api.igrok
```

```nginx
server {
    listen 80;
    server_name api.оръ.рф;

    # Редирект на HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.оръ.рф;

    ssl_certificate /etc/letsencrypt/live/api.оръ.рф/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.оръ.рф/privkey.pem;

    # SSL параметры
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Заголовки
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Прокси на API
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Статика TMA
    location /app/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Статика TMA assets
    location /app/assets/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # WebSocket (если нужно)
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Создание конфигурации Admin Panel

```bash
nano /etc/nginx/sites-available/panel.igrok
```

```nginx
server {
    listen 80;
    server_name панель.оръ.рф;

    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name панель.оръ.рф;

    ssl_certificate /etc/letsencrypt/live/панель.оръ.рф/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/панель.оръ.рф/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Прокси на API (админка — это SPA, отдаётся API)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Статика админки
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    location /admin/assets/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Активация конфигураций

```bash
# Симлинки
ln -sf /etc/nginx/sites-available/api.igrok /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/panel.igrok /etc/nginx/sites-enabled/

# Удаление дефолтного сайта (опционально)
rm -f /etc/nginx/sites-enabled/default

# Проверка конфигурации
nginx -t

# Перезапуск
systemctl reload nginx
```

---

## 9. Миграции и seed

### Применение миграций

```bash
cd /opt/igrok

# Запустить контейнер с Python
docker compose run --rm bot bash

# Внутри контейнера:
cd /app/src
alembic upgrade head

# Выйти
exit
```

### Заполнение базы данных

```bash
# Seed scroll types (9 типов свитков)
docker compose run --rm bot python -m scripts.seed_scroll_types

# Seed daily scrolls (90 дней × типы)
docker compose run --rm bot python -m scripts.seed_daily_scrolls

# Вставка приветственного сообщения
docker compose run --rm bot python -m scripts.insert_welcome_message
```

### Создание первого admin-пользователя

После первого запуска API, создайте master-пользователя вручную:

```bash
# Подключиться к PostgreSQL
docker compose exec postgres psql -U igrok -d igrok

# Создать пользователя
INSERT INTO users (id, telegram_id, username, role, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    123456789,  -- ваш Telegram ID
    'admin',
    'master',
    NOW(),
    NOW()
);

# Выйти
\q
```

**Как узнать свой Telegram ID:**
1. Напишите боту `@userinfobot`
2. Он покажет ваш ID

---

## 10. Первый запуск

### Полная перезагрузка

```bash
cd /opt/igrok

# Остановить все
docker compose down

# Запустить все
docker compose up -d

# Проверить
docker compose ps
```

### Проверка работоспособности

```bash
# API health check
curl https://api.оръ.рф/health

# Должен вернуть: {"status": "ok"}

# Админка (должна отдать HTML)
curl -I https://панель.оръ.рф/

# Telegram бот (проверка логов)
docker compose logs bot | tail -20
```

### Вход в админ-панель

1. Откройте `https://панель.оръ.рф`
2. Введите логин/пароль из `.env`
3. Вы должны увидеть дашборд

### Тест бота

1. Найдите бота в Telegram
2. Отправьте `/start`
3. Пройдите квиз на определение архетипа
4. Проверьте `/progress`

---

## 11. Проверка

### Чек-лист

| Проверка | Команда | Ожидаемый результат |
|----------|---------|---------------------|
| API работает | `curl https://api.оръ.рф/health` | `{"status":"ok"}` |
| Admin panel открывается | Открыть `https://панель.оръ.рф` | Страница входа |
| TMA работает | Открыть бота → Menu → Mini App | Приложение открывается |
| SSL работает | Проверить в браузере | Зелёный замок |
| Бот отвечает | `/start` в Telegram | Приветствие + квиз |
| Платежи настроены | Platega webhook | Статус `CONFIRMED` при оплате |
| Worker работает | `docker compose logs worker` | Нет ошибок |
| Scheduler работает | `docker compose logs scheduler` | Cron jobs зарегистрированы |

### Логи

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f bot
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f scheduler

# PostgreSQL
docker compose logs -f postgres

# Ошибки
docker compose logs --since 1h | grep -i error
```

---

## 12. Обновление

### Обновление кода

```bash
cd /opt/igrok

# Остановить сервисы
docker compose down

# Получить обновления
git pull origin main

# Пересобрать образы
docker compose build --no-cache

# Запустить
docker compose up -d

# Применить миграции (если есть)
docker compose run --rm alembic upgrade head
```

### Обновление SSL

```bash
certbot renew
systemctl reload nginx
```

### Бэкап базы данных

```bash
# Бэкап
docker compose exec postgres pg_dump -U igrok igrok > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление
cat backup.sql | docker compose exec -T postgres psql -U igrok -d igrok
```

### Автоматический бэкап (crontab)

```bash
# Добавить в crontab
crontab -e

# Бэкап каждый день в 3:00
0 3 * * * cd /opt/igrok && docker compose exec -T postgres pg_dump -U igrok igrok | gzip > /backups/igrok_$(date +\%Y\%m\%d).sql.gz
```

---

## Полезные команды

```bash
# Статус
docker compose ps

# Логи
docker compose logs -f [сервис]

# Перезапуск
docker compose restart [сервис]

# Остановка
docker compose down

# Запуск
docker compose up -d

# Вход в контейнер
docker compose exec bot bash
docker compose exec api bash
docker compose exec postgres psql -U igrok -d igrok

# Миграции
docker compose run --rm alembic upgrade head
docker compose run --rm alembic downgrade -1

# Seed
docker compose run --rm bot python -m scripts.seed_scroll_types
docker compose run --rm bot python -m scripts.seed_daily_scrolls
docker compose run --rm bot python -m scripts.insert_welcome_message
```

---

## Устранение неполадок

| Проблема | Решение |
|----------|---------|
| Бот не отвечает | `docker compose logs bot` — проверить токен |
| API 502 | `docker compose ps` — проверить что api запущен |
| Admin не открывается | Проверить DNS, SSL, nginx |
| Миграции не применяются | `docker compose run --rm alembic upgrade head` |
| Worker не отправляет уведомления | `docker compose logs worker` — проверить Redis |
| Платежи не проходят | Проверить Platega webhook URL и `.env` |
| SSL не работает | `certbot renew --force-renewal` |
