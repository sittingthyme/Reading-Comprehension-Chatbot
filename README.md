# Reading-Comprehension-Chatbot

## Local development

1. Install Python 3 and Node.js.
2. Open the `my-chatbot` folder in a terminal.
3. Frontend: `npm install` then `npm run dev` (Vite; default port 5173).
4. Backend (new terminal): `cd backend`, create a venv (`python3 -m venv venv`), activate it, `pip install -r requirements.txt`, then `python manage.py migrate` and `python manage.py runserver`.
5. Open the URL Vite prints (e.g. http://localhost:5173). API requests go to Django via the Vite proxy.

Copy [`my-chatbot/backend/.env.example`](my-chatbot/backend/.env.example) to `my-chatbot/backend/.env` and adjust if needed. Optional: [`my-chatbot/.env.example`](my-chatbot/.env.example) for the frontend.

Django admin (local): http://127.0.0.1:8000/admin/

## Deployment

See **[DEPLOY.md](DEPLOY.md)** for production hosting (split static frontend + Django API), environment variables, migrate/collectstatic, and the sample [`render.yaml`](render.yaml) at the repo root for Render.