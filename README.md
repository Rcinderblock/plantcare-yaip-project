# PlantCare

PlantCare — итоговый проект по требованиям из `Требования к проекту.pdf`: сервис
ухода за домашними и балконными растениями. Пользователь ведет личный список
растений, планирует задачи ухода, отмечает выполненный полив, собирает растения
в коллекции и получает подсказку по поливу с учетом прогноза Open-Meteo.

## Стек

- Frontend: React, TypeScript, Vite, Material UI, React Hook Form.
- Backend: Python, Django, Django REST Framework, Simple JWT, drf-spectacular.
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

## Основные страницы

- Каталог растений.
- Мои растения.
- Карточка растения.
- Календарь ухода.
- Профиль и настройки.
- Авторизация.
