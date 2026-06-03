# PlantCare

PlantCare — итоговый проект по требованиям из `Требования к проекту.pdf`: сервис
ухода за домашними и балконными растениями. Пользователь ведет личный список
растений, планирует задачи ухода, отмечает выполненный полив, собирает растения
в коллекции и получает погодную подсказку Open-Meteo: температуру, влажность,
осадки сегодня/завтра и текстовый вывод вроде «скоро дождь» или «дождя не
будет».

## Стек

- Frontend: React, TypeScript, Vite, Material UI, React Hook Form.
- Backend: Python, Django, Django REST Framework, Simple JWT, drf-spectacular.
- Авторизация: JWT в `HttpOnly` cookies (`SameSite=Lax`), без хранения токенов в `localStorage`.
- База данных: PostgreSQL в Docker, SQLite для локальной разработки без Docker.
- Интеграции: Open-Meteo API.
- Тесты: pytest, pytest-django, coverage; нагрузочные сценарии Locust.
- Запуск: Docker и Docker Compose.

## Быстрый запуск через Docker

```bash
docker compose up --build
```

После старта:

- frontend: http://localhost:5173
- backend API: http://localhost:8000/api/
- Swagger/OpenAPI: http://localhost:8000/api/docs/

Backend при старте применяет миграции и добавляет демо-виды растений.

## Локальный запуск без Docker

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Проверки

Backend-тесты и покрытие:

```bash
source .venv/bin/activate
cd backend
coverage run -m pytest
coverage report
```

Frontend-сборка:

```bash
cd frontend
npm run build
```

Нагрузочное тестирование:

```bash
source .venv/bin/activate
locust -f locustfile.py --host http://localhost:8000
```

## CSV-импорт

Файл для массовой загрузки растений должен содержать заголовки:

```csv
species_name,nickname,location_type,watering_interval_days,notes
Базилик,Кухня,balcony,2,Любит солнце
```

`location_type` принимает значения `indoor` или `balcony`.

## Безопасность авторизации

После входа backend устанавливает два cookie:

- `plantcare_access` — короткоживущий JWT access token.
- `plantcare_refresh` — refresh token, ограниченный путем `/api/auth/token/refresh/`.

Оба cookie имеют флаг `HttpOnly`, поэтому frontend JavaScript не может прочитать
или украсть токены напрямую. `SameSite=Lax` снижает риск CSRF для cross-site
POST-запросов. В продакшене при HTTPS нужно поставить `JWT_COOKIE_SECURE=1`,
чтобы cookies передавались только по защищенному соединению.

## Основные страницы

- Каталог растений.
- Мои растения.
- Карточка растения.
- Календарь ухода.
- Профиль и настройки.
- Авторизация.
