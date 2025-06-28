# Telegram Rent Bot: AI-Гид по Калининграду

Этот проект представляет собой многофункционального Telegram-бота, предназначенного для аренды жилья в Калининградской области. На текущем этапе реализован MVP для владельцев недвижимости, в активной разработке находится функционал для клиентов.

Глобальная цель проекта — создание комплексного AI-помощника для туристов.

## Технологический стек

- **Бэкенд:** Python 3.11
- **Telegram Bot API:** `aiogram` 3.x
- **Веб-сервер:** `aiohttp` (для Telegram Web Apps)
- **База данных:** `PostgreSQL`
- **ORM и Миграции:** `SQLAlchemy` 2.0, `Alembic`
- **Кэш / FSM:** `Redis`
- **Окружение:** `Docker`, `Docker Compose`

---

## Быстрый старт (Локальная разработка)

### 1. Предварительные требования

- Установленный [Docker](https://www.docker.com/get-started/) и Docker Compose.
- Git.

### 2. Настройка окружения

1.  **Клонируйте репозиторий:**
    ```bash
    git clone https://github.com/Zaebanec/telegram-rent-bot.git
    cd telegram-rent-bot
    ```

2.  **Создайте файл с переменными окружения:**
    Скопируйте файл `.env.example` в `.env` и заполните его вашими данными.
    ```bash
    cp .env.example .env
    ```
    Обязательно укажите ваш `BOT_TOKEN`.

### 3. Запуск проекта

1.  **Сборка и запуск контейнеров:**
    Эта команда запустит бота, базу данных и Redis в фоновом режиме.
    ```bash
    docker-compose up --build -d
    ```

2.  **Применение миграций базы данных (ВАЖНО!)**
    При первом запуске или после внесения изменений в модели данных (`app/models/models.py`), необходимо применить миграции. **Эта команда выполняется отдельно.**
    ```bash
    docker-compose run --rm bot alembic upgrade head
    ```

### 4. Остановка проекта

Чтобы остановить все сервисы, выполните:
```bash
docker-compose down

Управление миграциями Alembic
Создание новой миграции (после изменения моделей):
Generated bash
docker-compose run --rm bot alembic revision --autogenerate -m "Краткое описание изменений"
Use code with caution.
Bash
Применение последней миграции:
Generated bash
docker-compose run --rm bot alembic upgrade head
Use code with caution.
Bash
Откат последней миграции:
Generated bash
docker-compose run --rm bot alembic downgrade -1