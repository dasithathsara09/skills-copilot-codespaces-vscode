# Analytics & Data Management Platform

A modern full-stack data analytics and management web app with a React + Tailwind frontend and FastAPI + SQLite backend.

## Tech Stack

- **Frontend**: React (Vite), Tailwind CSS, Lucide Icons, Recharts
- **Backend**: FastAPI, SQLAlchemy ORM, SQLite, JWT auth
- **DevOps**: Docker, Docker Compose

## Features

- Interactive dashboard with KPI cards and trend/distribution charts
- JWT-secured API with Swagger docs at `/docs`
- Full CRUD for records with search and category filtering
- CSV import/export for records
- Automated report generation endpoint (`/reports/summary`)

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── tests/
│   │   └── test_api.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── Dockerfile
│   └── package.json
├── Dockerfile
└── docker-compose.yml
```

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.
Swagger docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

## Docker Setup

```bash
docker compose up --build
```

## Useful Scripts

- Backend tests: `cd backend && pytest`
- Frontend build: `cd frontend && npm run build`
