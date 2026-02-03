# Quick Deployment Checklist

## Before You Start
- [ ] Code is pushed to GitHub
- [ ] You have a Render account (free tier works)
- [ ] You have an OpenAI API key

## Deployment Steps

### 1. Deploy Backend (5 minutes)
1. Go to https://dashboard.render.com → **New +** → **Web Service**
2. Connect GitHub repo
3. Settings:
   - Root Directory: `my-chatbot/backend`
   - Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput`
   - Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
4. Add env vars:
   - `SECRET_KEY` (generate one)
   - `DEBUG` = `False`
   - `OPENAI_API_KEY` = (your key)
5. **Save** → Note the URL (e.g., `https://your-api.onrender.com`)

### 2. Create Database (2 minutes)
1. **New +** → **PostgreSQL**
2. Name: `reading-chatbot-db`
3. Copy the **Internal Database URL**
4. Go back to backend → Environment → Add `DATABASE_URL` = (paste URL)
5. **Redeploy** backend

### 3. Deploy Frontend (3 minutes)
1. **New +** → **Static Site**
2. Root Directory: `my-chatbot`
3. Build: `cd my-chatbot && npm install && npm run build`
4. Publish: `my-chatbot/dist`
5. Add env var: `VITE_API_URL` = (your backend URL from step 1)
6. **Save** → Note the URL (e.g., `https://your-frontend.onrender.com`)

### 4. Update CORS (1 minute)
1. Backend → Environment
2. Add/Update:
   - `CORS_ALLOWED_ORIGINS` = (your frontend URL)
   - `CSRF_TRUSTED_ORIGINS` = (your frontend URL)
   - `ALLOWED_HOSTS` = (your backend domain, e.g., `your-api.onrender.com`)
3. **Redeploy** backend

### 5. Test
Visit your frontend URL and start chatting!

## Common Issues

**CORS Error?** → Make sure `CORS_ALLOWED_ORIGINS` matches your frontend URL exactly

**500 Error?** → Check logs, verify `OPENAI_API_KEY` is set

**Database Error?** → Make sure `DATABASE_URL` is set and backend was redeployed

## Need Help?
See `DEPLOYMENT.md` for detailed instructions.
