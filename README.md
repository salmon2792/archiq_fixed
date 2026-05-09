# ArchIQ — Architecture-Aware Career Intelligence Platform

> Not keyword matching. Real domain reasoning for hardware, embedded, and silicon engineers.

## What it does

- **Direct internet job scraping** — LinkedIn, Indeed, Wellfound, + 10 company career pages (NVIDIA, ARM, Intel, Qualcomm, Tenstorrent, Bosch, NXP, etc.)
- **Architecture-aware skill extraction** — 50+ hardware/embedded skills detected with depth estimation (awareness → arch reasoning → production exposure)
- **Role fit scoring** — maps your profile to 7 target roles: arch validation, performance engineer, SoC engineer, AI accelerator engineer, benchmarking engineer, HW/SW co-design, embedded systems
- **Intelligent job matching** — semantic skill overlap + architecture domain alignment scoring
- **Gap analysis** — prioritized list of missing skills ranked by impact on your target roles
- **AI mentor chatbot** — career reasoning, project suggestions, company comparisons
- **PWA** — installable on any device (iOS, Android, desktop) from browser, works offline

---

## Stack

| Layer | Tech | Why |
|-------|------|-----|
| Frontend | Vanilla JS PWA | Zero deps, works everywhere, installable |
| Backend | Python FastAPI | Async, fast, easy deploy |
| Database | SQLite (aiosqlite) | Zero config, upgradeable to Postgres |
| Scraping | httpx + BeautifulSoup | No paid APIs, direct internet |
| AI | HuggingFace free API + rule-based | No API keys needed |
| Hosting | Railway (backend) + Vercel (frontend) | Free tier, persistent |

---

## Quick Start — Local

```bash
# 1. Clone / download the project
cd archiq

# 2. One command setup & start
chmod +x start.sh && ./start.sh

# 3. Open browser
# http://localhost:3000
```

**Requirements:** Python 3.9+, pip — that's it.

---

## Publish to GitHub

1. Initialize the repository if needed:

```bash
git init
git branch -M main
git add .
git commit -m "Initial commit"
```

2. Create a GitHub repo and add a remote:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

3. Automatic frontend site deployment is enabled via GitHub Actions.
   - The static frontend is published from `frontend/` to the `gh-pages` branch.
   - After first push, enable GitHub Pages in repository Settings if needed.

4. Use Railway for the backend:
   - Connect the repo to Railway and deploy the `backend/` service.
   - Railway will use `backend/requirements.txt` and `backend/railway.toml`.

---

## Deploy to Web (Free, Permanent URL)

### Step 1 — Deploy Backend to Railway

1. Go to **https://railway.app** → Sign up free
2. Click **New Project → Deploy from GitHub**
3. Upload/push the `backend/` folder to a GitHub repo
4. Railway auto-detects Python and deploys
5. Go to **Settings → Generate Domain** → copy your URL (e.g. `https://archiq-backend.railway.app`)

### Step 2 — Deploy Frontend to Vercel

1. Go to **https://vercel.com** → Sign up free
2. Click **New Project → Upload** the `frontend/` folder
3. Open `deploy/vercel.json` → replace `YOUR-RAILWAY-BACKEND-URL` with your Railway URL
4. Deploy → Vercel gives you a permanent URL (e.g. `https://archiq.vercel.app`)

> If you use this Vercel proxy route, the frontend can keep using `/api/v1` and you do not need to edit `frontend/index.html`.

### Step 3 — Optional: Direct Backend API URL

If you are not using the Vercel proxy route, open `frontend/index.html` and find:
```js
const API = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api/v1'
  : '/api/v1';
```
Change `/api/v1` to your Railway backend URL:
```js
  : 'https://archiq-backend.railway.app/api/v1';
```

Then redeploy the frontend. Done — your app is live!

---

## Install as Mobile App (PWA)

### iPhone / iPad
1. Open your Vercel URL in **Safari**
2. Tap the **Share** button (box with arrow)
3. Tap **"Add to Home Screen"**
4. Tap **Add** — ArchIQ icon appears on your home screen

### Android
1. Open your Vercel URL in **Chrome**
2. Tap the **3-dot menu**
3. Tap **"Add to Home Screen"** or **"Install App"**
4. Tap **Install**

### Desktop (Chrome/Edge)
1. Open your Vercel URL
2. Click the **install icon** in the address bar (right side)
3. Click **Install**

---

## Project Structure

```
archiq/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile               # Container build
│   ├── railway.toml             # Railway deploy config
│   ├── Procfile                 # Process definition
│   ├── api/
│   │   └── routes.py            # All API endpoints
│   ├── ai_engine/
│   │   ├── engine.py            # Skill extraction, matching, gaps, mentor
│   │   └── ontology.py          # Domain knowledge graph (the brain)
│   ├── scraper/
│   │   └── scraper.py           # Multi-source job scraper
│   └── db/
│       └── database.py          # SQLite schema + init
├── frontend/
│   ├── index.html               # Complete PWA app (single file)
│   ├── manifest.json            # PWA install config
│   └── sw.js                    # Service worker (offline support)
├── deploy/
│   ├── vercel.json              # Vercel frontend config
│   └── nginx.conf               # Docker nginx config
├── docker-compose.yml           # Local Docker full-stack
├── start.sh                     # One-command local start
├── stop.sh                      # Stop all services
└── README.md
```

---

## API Endpoints

| Method | Endpoint | What it does |
|--------|----------|--------------|
| POST | `/api/v1/users` | Create user account |
| POST | `/api/v1/profile/upload` | Upload PDF resume |
| POST | `/api/v1/profile/text` | Paste profile text |
| GET | `/api/v1/skills/{user_id}` | Get extracted skills |
| GET | `/api/v1/role-fit/{user_id}` | Role fit scores |
| GET | `/api/v1/gap-analysis/{user_id}` | Gap analysis |
| POST | `/api/v1/jobs/scrape` | Trigger internet job scrape |
| GET | `/api/v1/scrape/status` | Scrape progress |
| GET | `/api/v1/jobs` | List jobs (with match scores) |
| POST | `/api/v1/jobs/match/{user_id}` | Compute match scores |
| GET | `/api/v1/jobs/{id}/explain/{uid}` | AI match explanation |
| POST | `/api/v1/mentor/chat` | Chat with AI mentor |
| GET | `/api/v1/dashboard/{user_id}` | Full dashboard data |

Interactive API docs at: `http://localhost:8000/docs`

---

## How Skill Depth Works

The engine estimates depth from the **context** of how you mention a skill — not just that you mention it.

| Level | What it means | Example |
|-------|---------------|---------|
| Awareness | Heard of it, studied it | "familiar with PMU" |
| Implementation | Wrote code using it | "implemented BIST controller" |
| Optimization | Tuned it for performance | "optimized cache hit rate by 23%" |
| Arch Reasoning | Designed around tradeoffs | "designed APB bus topology for SoC" |
| Production Exposure | Silicon / deployed level | "validated on post-silicon bring-up" |

---

## Scraping Sources

- **LinkedIn Jobs** — public search, no login
- **Indeed** — direct scraping
- **Wellfound** — startup jobs
- **NVIDIA** careers
- **AMD** careers
- **Intel** jobs
- **ARM** careers
- **Qualcomm** careers
- **Tenstorrent** jobs
- **Bosch** careers
- **NXP** careers

---

## Upgrade Path

When you need more scale:

1. **Database**: Change `DATABASE_URL` to a PostgreSQL URL → aiosqlite → asyncpg, same schema
2. **AI**: Add `ANTHROPIC_API_KEY` env var → upgrade mentor to Claude for much better responses
3. **Scraping**: Add Playwright for JS-rendered career pages
4. **Embeddings**: Add pgvector + sentence-transformers for semantic job search
5. **Auth**: Add JWT tokens in the `/users` endpoint

---

## License

MIT — use freely, build on top of it.
