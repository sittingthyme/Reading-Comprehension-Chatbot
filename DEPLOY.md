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
| `DATABASE_SSL_REQUIRE` | Set `true` for Render / most managed Postgres (see `render.yaml` example). |
| `CORS_TRUST_ONRENDER` | On Render, defaults to allowing `https://*.onrender.com` when `RENDER` is set, so the SPA and API on different `*.onrender.com` hostnames can talk without hand-copying URLs. Set `false` if you use only explicit `CORS_ALLOWED_ORIGINS`. |
| `FRONTEND_ORIGIN` | Optional: exact `https://` origin of the static app for `CSRF_TRUSTED_ORIGINS` (Django has no CORS-style regex for CSRF). |
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

A sample blueprint lives at [`my-chatbot/render.yaml`](my-chatbot/render.yaml). Service **`rootDir`** is relative to the repository root (e.g. `my-chatbot` for the frontend). With a `rootDir` set, Render’s [monorepo docs](https://render.com/docs/monorepo-support) require **`staticPublishPath` (publish directory) to be relative to that same `rootDir`**—for this Vite app use `dist`, not `my-chatbot/dist`. In the Render dashboard, leave **Root Directory** empty at the repo level unless you overrode it—if you set Root Directory to `my-chatbot`, change the blueprint `rootDir` entries to `.` and `backend` accordingly.

The blueprint:

- Wires `DATABASE_URL` to the managed Postgres and sets `DATABASE_SSL_REQUIRE=true`.
- Runs **`migrate` before `collectstatic`** so the app uses the linked database from the first build.
- Sets **`VITE_API_URL` from the API service** (`fromService` → `RENDER_EXTERNAL_URL`) so the static build actually calls your deployed API (this is what makes rows appear in Render Postgres instead of a local `db.sqlite3`).

Django is configured so that, on Render (`RENDER=1`):

- `ALLOWED_HOSTS` is derived from the API’s `RENDER_EXTERNAL_URL` as well as any explicit `ALLOWED_HOSTS`.
- CORS can allow the static site using the `*.onrender.com` regex (see `CORS_TRUST_ONRENDER` in settings).

**Custom domains:** add your real `https://` origins to `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` in the API service and rebuild the frontend with `VITE_API_URL` pointing at the API. If you disable the regex, set `CORS_TRUST_ONRENDER=false` and use explicit lists only.

## 4. Single VPS (optional)

Use a reverse proxy (e.g. nginx): serve `dist/` as static files for `/`, and proxy `/api/` and `/admin/` to Gunicorn on a Unix socket or TCP port.
