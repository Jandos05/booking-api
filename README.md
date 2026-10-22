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
5. Создайте базу данных PostgreSQL с именем, указанным в `DB_NAME`.
6. Примените миграции:

   ```bash
   python manage.py migrate
   ```

7. Создайте администратора:

   ```bash
   python manage.py createsuperuser
   ```

8. Запустите сервер:

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
