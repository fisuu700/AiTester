# Image officielle Playwright basée sur Ubuntu (contient Node.js, Python et tous les prérequis Chromium)
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

# Installation des dépendances Python du projet
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install chromium

# Copie du code backend
COPY backend/app ./app
COPY backend/.env.example .env

# Création des dossiers de stockage pour la DB et les rapports
RUN mkdir -p /app/data /app/reports

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
