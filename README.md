# Booking API

REST API для бронирования гостиниц и номеров на Django REST Framework.

## Технологии

- Python
- Django
- Django REST Framework
- PostgreSQL
- Simple JWT
- drf-spectacular

## Установка

1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Создайте локальный файл окружения:

   ```bash
   cp .env.example .env
   ```

4. Настройте значения в `.env`, включая секретный ключ и параметры PostgreSQL.
### Запуск PostgreSQL через Docker

Убедитесь, что Docker Desktop запущен. Создайте контейнер PostgreSQL:

```bash
docker run --name booking_api_db \
  -e POSTGRES_DB=booking_api \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=booking_local_2026 \
  -p 5433:5432 \
  -d postgres:17
```

В локальном файле `.env` укажите параметры подключения:

```dotenv
DB_NAME=booking_api
DB_USER=postgres
DB_PASSWORD=booking_local_2026
DB_HOST=localhost
DB_PORT=5433
```

Убедитесь, что контейнер запущен:

```bash
docker ps
```

Если контейнер `booking_api_db` уже существует, повторно создавать его не нужно. Запустите его командой `docker start booking_api_db`, если он остановлен.
5. Примените миграции:

   ```bash
   python manage.py migrate
   ```

6. Создайте администратора:

   ```bash
   python manage.py createsuperuser
   ```

7. Запустите сервер:

   ```bash
   python manage.py runserver
   ```

## Документация API

После запуска сервера:

- Swagger: http://127.0.0.1:8000/api/docs/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/

## Запуск тестов

```bash
python manage.py test
```

## Переменные окружения

- `SECRET_KEY` — секретный ключ Django.
- `DEBUG` — режим отладки.
- `ALLOWED_HOSTS` — разрешённые хосты.
- `DB_NAME` — имя базы данных.
- `DB_USER` — пользователь PostgreSQL.
- `DB_PASSWORD` — пароль PostgreSQL.
- `DB_HOST` — адрес сервера базы данных.
- `DB_PORT` — порт PostgreSQL.
