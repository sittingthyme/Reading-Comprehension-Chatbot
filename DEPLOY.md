# Deploying Reading-Comprehension-Chatbot

The app has two parts: a **Vite/React** frontend in [`my-chatbot/`](my-chatbot/) and a **Django** API in [`my-chatbot/backend/`](my-chatbot/backend/). The browser loads the SPA from a static host and calls the API over HTTPS.

## 1. Backend (Django + Gunicorn)

**Service root:** [`my-chatbot/backend/`](my-chatbot/backend/) (where `manage.py`, `requirements.txt`, and [`Procfile`](my-chatbot/backend/Procfile) live).

**Install:** `pip install -r requirements.txt`

**Every deploy:**

1. `python manage.py migrate --noinput`
2. `python manage.py collectstatic --noinput` (WhiteNoise serves `STATIC_ROOT`)
3. Start the web process: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

On **Heroku**, the [`Procfile`](my-chatbot/backend/Procfile) `release:` line runs migrate and collectstatic automatically before the new `web` dyno starts.

**Environment variables** (see also [`my-chatbot/backend/.env.example`](my-chatbot/backend/.env.example)):

| Variable | Production notes |
|----------|------------------|
| `SECRET_KEY` | Long random string; never commit it. |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | Comma-separated API hostname(s), e.g. `api.example.com` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated **frontend** origins, e.g. `https://app.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Same as frontend origins, with scheme (needed for trusted cross-origin CSRF). |
| `DATABASE_URL` | Optional locally; use managed **PostgreSQL** in production. Supports `postgres://` and `postgresql://` (via `dj-database-url`). |
| `DATABASE_SSL_REQUIRE` | Set `true` if your DB requires SSL (common on managed Postgres). |
| `OPENAI_API_KEY` | Required for chat. |
| `STUDY_*` | Enrollment codes, dates, timezone, PIN length, etc. |

With `DEBUG=False`, session/CSRF cookies use the `Secure` flag; serve the site over HTTPS. Set `SECURE_SSL_REDIRECT=true` if appropriate for your reverse proxy.

## 2. Frontend (static build)

**Build** (from [`my-chatbot/`](my-chatbot/)):

```bash
VITE_API_URL=https://your-api-host.example.com npm run build
```

`VITE_API_URL` must be the **public base URL** of the Django API (no trailing slash). It is embedded at build time; rebuild when the API URL changes.

**Publish** the contents of `my-chatbot/dist/` to any static host (Netlify, Vercel, Cloudflare Pages, S3+CDN, etc.).

Optional env vars: [`my-chatbot/.env.example`](my-chatbot/.env.example).

**Note:** Local dev uses the Vite dev proxy in [`vite.config.js`](my-chatbot/vite.config.js) for `/api`. That proxy does not exist in production—clients must reach the real API via `VITE_API_URL`.

## 3. Render (example)

A sample blueprint lives at [`my-chatbot/render.yaml`](my-chatbot/render.yaml). **`rootDir` values are relative to the Git repository root** (`Reading-Comprehension-Chatbot`), e.g. `my-chatbot` for the frontend and `my-chatbot/backend` for the API. **`staticPublishPath`** is also from the repo root (`my-chatbot/dist`), not from `rootDir`. In the Render dashboard, leave **Root Directory** empty (repo root) unless you know you overrode it—if you set Root Directory to `my-chatbot`, change the blueprint `rootDir` entries to `.` and `backend` and set `staticPublishPath` to `./dist`.

After the first deploy, set `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and `VITE_API_URL` to your real frontend and backend URLs, then redeploy the frontend so it picks up `VITE_API_URL`.

## 4. Single VPS (optional)

Use a reverse proxy (e.g. nginx): serve `dist/` as static files for `/`, and proxy `/api/` and `/admin/` to Gunicorn on a Unix socket or TCP port.
