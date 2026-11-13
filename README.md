# AI E2E Testing Agent — Plateforme de test automatisé par agents IA

Plateforme full-stack qui analyse un site web à partir de sa simple URL : des agents
indépendants mesurent sa **fiabilité**, sa **sécurité**, sa **performance** et son
**accessibilité**, calculent un **score global pondéré**, produisent une **synthèse IA**
et permettent d'**exporter un rapport PDF**.

Le projet conserve l'agent historique de test End-to-End piloté par LLM (vérification
tri-couche UI · API · Base de données), désormais accessible via `/legacy`.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Agents de scan](#agents-de-scan)
- [Démarrage rapide](#démarrage-rapide)
- [Configuration](#configuration)
- [API REST](#api-rest)
- [Sécurité](#sécurité)
- [Structure du projet](#structure-du-projet)
- [Docker](#docker)
- [Limites connues](#limites-connues)

---

## Fonctionnalités

### Plateforme
- Authentification **email + mot de passe** (bcrypt, JWT), inscription et connexion.
- **Clé API** (`X-API-Key`) pour déclencher des scans depuis une pipeline CI/CD.
- Gestion multi-sites : ajout, suppression, consentement obligatoire.
- Scans **rapides** (fiabilité + sécurité) ou **complets** (4 agents + navigateur).
- Progression **temps réel** via WebSocket (logs, statut par agent).
- Historique des scans, évolution du score dans le temps.
- **Planification récurrente** par expression cron (APScheduler).
- Export de rapport **JSON**, **HTML** autonome ou **PDF**.
- Synthèse en langue naturelle via Ollama, avec **repli déterministe** si le LLM est
  indisponible (le scan n'est jamais bloqué).

### Agent E2E historique (PFE)
- Scénario en langage naturel → plan → actions Playwright → vérification tri-couche.
- Multi-Model Router local : `llama3.1:8b` (planificateur), `qwen2.5-coder:7b` (exécutant),
  `deepseek-r1:7b` (analyste).
- Interception réseau (API) et validation en base de données.

---

## Architecture

```
Utilisateur ──► Frontend Next.js 15 (App Router, Tailwind)
                    │  REST + WebSocket
                    ▼
               Backend FastAPI
        ┌───────────┼────────────────────┐
        │           │                    │
   Orchestrateur  Scheduler         Export rapports
   de scans       (APScheduler)     (HTML / PDF)
        │
        ├── Agent Fiabilité    (crawl httpx, liens morts, robots.txt)
        ├── Agent Sécurité     (TLS, en-têtes, cookies, CORS — 100 % passif)
        ├── Agent Performance  (Web Vitals via Chromium)
        ├── Agent Accessibilité(axe-core local + repli manuel)
        └── Agent Fonctionnel  (scénario E2E via Ollama)

        Persistance SQLAlchemy 2.0 ──► SQLite (défaut) ou PostgreSQL
```

**Stack** : FastAPI · SQLAlchemy 2.0 · Playwright · Pydantic v2 · APScheduler ·
Next.js 15 · React 19 · TailwindCSS 3 · Ollama.

---

## Agents de scan

| Agent | Ce qui est vérifié | Mode |
|---|---|---|
| **Fiabilité** | Statuts HTTP, erreurs 4xx/5xx, timeouts, liens morts, redirections, `robots.txt` | rapide + complet |
| **Sécurité** | HTTPS/TLS (version, expiration), en-têtes de sécurité, cookies (`Secure`/`HttpOnly`/`SameSite`), CORS, fichiers sensibles exposés, contenu mixte | rapide + complet |
| **Performance** | LCP, CLS, TTFB, nombre de requêtes, poids transféré, scripts bloquants, nœuds DOM | complet |
| **Accessibilité** | Règles WCAG 2.1 A/AA via **axe-core** (fichier local, sans CDN) | complet |
| **Fonctionnel** | Scénario E2E tri-couche (UI · API · DB) piloté par LLM | complet + scénario |

Chaque agent renvoie un **score 0–100** (pénalités par sévérité) et une liste de
**findings** (critique / élevé / moyen / faible / info) avec preuve et remédiation.

Le **score global** est une moyenne pondérée configurable :

| Dimension | Poids par défaut |
|---|---|
| Fiabilité | 30 % |
| Sécurité | 35 % |
| Performance | 20 % |
| Accessibilité | 15 % |

---

## Démarrage rapide

### Prérequis
- Python 3.11+
- Node.js 20+
- (optionnel) [Ollama](https://ollama.com) avec les modèles configurés

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows : .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env      # puis ajuster si besoin
uvicorn app.main:app --reload --port 8000 --loop app.loop:proactor_loop_factory
```

> **Windows** : `--loop app.loop:proactor_loop_factory` est indispensable avec `--reload`.
> Par défaut, uvicorn utilise une `SelectorEventLoop` qui ne supporte pas
> `asyncio.create_subprocess_exec`, ce qui fait échouer les agents
> **Performance** et **Accessibilité** (Playwright/Chromium).

- API : http://localhost:8000
- Documentation interactive : http://localhost:8000/docs
- Santé : http://localhost:8000/api/health

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

- Interface : http://localhost:3000

### 3. Démo locale (cible de test)

```bash
cd demo_target
python app.py
```

- Cible : http://localhost:8001

> ⚠️ Scanner `localhost` nécessite `ALLOW_PRIVATE_TARGETS=true` dans le `.env`
> (garde-fou anti-SSRF désactivé — **uniquement** pour la démonstration).

### 4. (Optionnel) Modèles locaux

```bash
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:7b
```

Sans Ollama, les scans fonctionnent normalement : seule la synthèse IA utilise le
repli déterministe.

---

## Configuration

Toutes les variables sont lues depuis `backend/.env` (voir `backend/.env.example`).

| Variable | Défaut | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./platform.db` | SQLAlchemy URL (Postgres : `postgresql+psycopg://...`) |
| `JWT_SECRET` | (à changer) | Secret de signature JWT — **≥ 32 caractères** en production |
| `JWT_EXPIRE_MINUTES` | `10080` | Durée de validité du token (7 jours) |
| `ALLOW_PRIVATE_TARGETS` | `false` | Autorise localhost / IP privées (démo uniquement) |
| `CORS_ORIGINS` | `http://localhost:3000` | Origines autorisées (liste séparée par virgules) |
| `SCORE_WEIGHTS` | `reliability=0.30,...` | Pondération du score global |
| `AGENT_TIMEOUT_SECONDS` | `300` | Timeout par agent |
| `MAX_CONCURRENT_SCANS` | `3` | Scans simultanés |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint Ollama |
| `MODEL_PLANNER` / `MODEL_EXECUTOR` / `MODEL_ANALYST` | `llama3.1:8b` / `qwen2.5-coder:7b` / `deepseek-r1:7b` | Modèles LLM |

> Générer un secret : `python -c "import secrets; print(secrets.token_urlsafe(48))"`

---

## API REST

Authentification : `Authorization: Bearer <jwt>` **ou** `X-API-Key: <clé>`.

### Auth
| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Création de compte (retourne un JWT) |
| `POST` | `/api/auth/login` | Connexion |
| `GET` | `/api/auth/me` | Profil courant |
| `POST` | `/api/auth/api-key` | Génère une clé API |
| `DELETE` | `/api/auth/api-key` | Révoque la clé API |

### Sites
| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/sites` | Ajoute un site (`consent: true` requis) |
| `GET` | `/api/sites` | Liste les sites + dernier scan |
| `GET` | `/api/sites/{id}` | Détail d'un site |
| `DELETE` | `/api/sites/{id}` | Supprime le site et ses scans |
| `POST` | `/api/sites/{id}/scans` | Lance un scan (`quick` / `full`) |
| `GET` | `/api/sites/{id}/history` | Historique des scores |
| `POST` | `/api/sites/{id}/schedule` | Crée / met à jour une planification cron |
| `GET` | `/api/sites/{id}/schedules` | Liste les planifications |
| `DELETE` | `/api/sites/schedules/{id}` | Supprime une planification |

### Scans
| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/scans` | Lance un scan par URL (CI/CD, JWT ou clé API) |
| `GET` | `/api/scans` | Liste les scans récents |
| `GET` | `/api/scans/{id}` | Détail complet (agents + findings) |
| `DELETE` | `/api/scans/{id}` | Supprime / annule un scan |
| `GET` | `/api/scans/{id}/report?format=json\|html\|pdf` | Export du rapport |
| `WS` | `/ws/scans/{id}?token=<jwt>` | Progression temps réel |

### Exemple CI/CD

```bash
curl -X POST http://localhost:8000/api/scans \
  -H "X-API-Key: ait_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://mon-site.tn","mode":"quick"}'
```

---

## Sécurité

- **Scans strictement passifs** : aucune tentative d'intrusion, d'injection ou de
  bruteforce. L'agent sécurité se limite à ce que le serveur expose publiquement.
- **Consentement obligatoire** : l'utilisateur certifie être autorisé à tester le site.
- **Garde-fou anti-SSRF** : blocage de `localhost`, des IP privées/réservées et des
  endpoints de métadonnées cloud. Résolution DNS vérifiée.
- **`robots.txt`** respecté par l'agent de fiabilité.
- **Mots de passe** hachés avec bcrypt (troncature sûre à 72 octets).
- **JWT signés HS256**, expiration configurable.
- **Clés API** révocables, distinctes des mots de passe.

---

## Structure du projet

```
ai-e2e-testing-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # Point d'entrée FastAPI + routes historiques
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── db.py                # Engine + sessions SQLAlchemy
│   │   ├── models.py            # User, Site, Scan, AgentResult, Finding, Schedule
│   │   ├── schemas.py           # Schémas Pydantic (API + plateforme)
│   │   ├── auth.py              # bcrypt, JWT, get_actor (JWT ou clé API)
│   │   ├── safety.py            # anti-SSRF, normalisation d'URL, robots.txt
│   │   ├── scoring.py           # pénalités, score global pondéré, notes
│   │   ├── serializers.py       # ORM → Pydantic
│   │   ├── scan_orchestrator.py # ScanHub (WS) + ScanRunner (asyncio.gather)
│   │   ├── scheduler.py         # Planification cron APScheduler
│   │   ├── agents/
│   │   │   ├── base.py          # Contrat AgentContext / AgentReport / finding
│   │   │   ├── browser.py       # Helper Playwright partagé
│   │   │   ├── reliability.py   # Crawl, liens morts, robots.txt
│   │   │   ├── security.py      # Analyse passive (TLS, en-têtes, cookies…)
│   │   │   ├── performance.py   # Web Vitals
│   │   │   ├── accessibility.py # axe-core (local) + repli manuel
│   │   │   ├── functional.py    # Scénario E2E (Ollama)
│   │   │   ├── analyst.py       # Synthèse LLM + repli déterministe
│   │   │   └── vendor/axe.min.js
│   │   ├── routers/             # auth.py · sites.py · scans.py
│   │   ├── reporting/           # web.py (HTML/PDF) · generator.py (JSON legacy)
│   │   ├── ai/ · engines/       # Agent E2E historique (multi-modèles)
│   │   └── orchestrator.py      # Orchestrateur tri-couche historique
│   ├── demo_target/             # Application bancaire de démonstration
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Tableau de bord
│   │   ├── login/ · register/   # Authentification
│   │   ├── scans/ · scans/[id]/ # Liste + détail temps réel
│   │   ├── sites/[id]/          # Détail site, scans, planification
│   │   ├── account/             # Profil + clé API
│   │   └── legacy/              # Agent E2E historique
│   ├── components/              # Navbar, ScoreGauge, FindingsTable, TrendChart…
│   └── lib/                     # api.ts, auth.tsx, labels.ts, types.ts
└── docker-compose.yml
```

---

## Docker

```bash
docker compose up --build
```

- Frontend : http://localhost:3000
- Backend : http://localhost:8000

Le `docker-compose.yml` expose toutes les variables d'environnement de la plateforme.
Ollama est supposé tourner sur l'hôte (`host.docker.internal:11434`) ; un service
commenté est fourni pour un déploiement entièrement conteneurisé. Une configuration
PostgreSQL est également disponible en commentaire.

---

## Limites connues

- Le schéma est créé via `Base.metadata.create_all` (pas d'Alembic) : les migrations
  destructives doivent être gérées manuellement.
- Les scans sont exécutés en tâches `asyncio` au sein du processus API ; pour une
  montée en charge réelle, externaliser dans une file (Celery/RQ + workers).
- Le planificateur APScheduler est en mémoire : les jobs planifiés sont rechargés au
  démarrage depuis la base, mais ne sont pas distribués entre plusieurs instances.
- L'agent fonctionnel dépend d'Ollama et d'un scénario explicite ; il est marqué
  `skipped` sinon.
- La synthèse LLM peut occasionnellement produire des imprécisions ; le repli
  déterministe garantit toujours un résumé exploitable.
