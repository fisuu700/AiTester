# Dockerfile à la racine pour déploiement Fly.io / conteneurs
FROM python:3.13-slim

WORKDIR /app

# Installation des dépendances Python et Playwright avec Chromium
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps chromium

# Copie du code backend
COPY backend/app ./app
COPY backend/.env.example .env

# Création des dossiers de stockage pour la DB et les rapports
RUN mkdir -p /app/data /app/reports

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
