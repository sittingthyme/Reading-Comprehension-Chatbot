# Deployment Guide

This guide will help you deploy your Reading Comprehension Chatbot to production using Render (free tier).

## Prerequisites

1. A GitHub account
2. A Render account (sign up at https://render.com - free tier available)
3. An OpenAI API key (get one at https://platform.openai.com/api-keys)
4. Your code pushed to a GitHub repository

## Overview

Your application consists of:
- **Backend**: Django REST API (Python)
- **Frontend**: React + Vite (Static site)
- **Database**: PostgreSQL (provided by Render)

## Step 1: Prepare Your Repository

1. Make sure all your code is committed and pushed to GitHub:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

## Step 2: Deploy Backend (Django API)

### Option A: Using Render Dashboard (Recommended for first-time)

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `reading-chatbot-api` (or your preferred name)
   - **Region**: Choose closest to you
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `my-chatbot/backend`
   - **Environment**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
     ```
   - **Start Command**: 
     ```bash
     gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
     ```

5. Click **"Advanced"** → **"Add Environment Variable"** and add:
   - `SECRET_KEY`: Generate a secure key (you can use: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
   - `DEBUG`: `False`
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `ALLOWED_HOSTS`: Leave empty for now (we'll update after deployment)
   - `CORS_ALLOWED_ORIGINS`: Leave empty for now
   - `CSRF_TRUSTED_ORIGINS`: Leave empty for now

6. Click **"Create Web Service"**

7. **Wait for deployment** - This will take a few minutes. Note the URL (e.g., `https://reading-chatbot-api.onrender.com`)

### Option B: Using render.yaml (Automated)

1. The `render.yaml` file is already configured in your repository
2. Go to https://dashboard.render.com
3. Click **"New +"** → **"Blueprint"**
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml` and create all services
6. You'll still need to set environment variables in the dashboard

## Step 3: Create PostgreSQL Database

1. In Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `reading-chatbot-db`
   - **Database**: `reading_chatbot`
   - **User**: `reading_chatbot_user`
   - **Region**: Same as your backend
   - **Plan**: Free

3. Click **"Create Database"**
4. Copy the **Internal Database URL** (you'll need this)
5. Go back to your backend service → **Environment** tab
6. Add environment variable:
   - `DATABASE_URL`: Paste the Internal Database URL from step 4

7. **Redeploy** your backend service (click "Manual Deploy" → "Deploy latest commit")

## Step 4: Update Backend Environment Variables

After your backend is deployed, update these environment variables:

1. Go to your backend service → **Environment** tab
2. Update:
   - `ALLOWED_HOSTS`: Your backend URL (e.g., `reading-chatbot-api.onrender.com`)
   - `CORS_ALLOWED_ORIGINS`: Your frontend URL (we'll set this after deploying frontend)
   - `CSRF_TRUSTED_ORIGINS`: Your frontend URL (same as above)

## Step 5: Deploy Frontend (React App)

### Option A: Deploy as Static Site on Render

1. In Render dashboard, click **"New +"** → **"Static Site"**
2. Configure:
   - **Name**: `reading-chatbot-frontend`
   - **Repository**: Your GitHub repository
   - **Branch**: `main`
   - **Root Directory**: `my-chatbot`
   - **Build Command**: 
     ```bash
     cd my-chatbot && npm install && npm run build
     ```
   - **Publish Directory**: `my-chatbot/dist`

3. Add environment variable:
   - `VITE_API_URL`: Your backend URL (e.g., `https://reading-chatbot-api.onrender.com`)

4. Click **"Create Static Site"**

5. **Wait for deployment** - Note the URL (e.g., `https://reading-chatbot-frontend.onrender.com`)

### Option B: Deploy to Vercel (Alternative - Often Faster)

1. Go to https://vercel.com and sign in with GitHub
2. Click **"New Project"**
3. Import your repository
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `my-chatbot`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

5. Add environment variable:
   - `VITE_API_URL`: Your backend URL (e.g., `https://reading-chatbot-api.onrender.com`)

6. Click **"Deploy"**

## Step 6: Update CORS Settings

1. Go back to your backend service on Render
2. Update environment variables:
   - `CORS_ALLOWED_ORIGINS`: Your frontend URL (e.g., `https://reading-chatbot-frontend.onrender.com`)
   - `CSRF_TRUSTED_ORIGINS`: Your frontend URL (same as above)

3. **Redeploy** your backend

## Step 7: Test Your Deployment

1. Visit your frontend URL
2. Try starting a conversation
3. Check that messages are being saved and responses are working

## Troubleshooting

### Backend Issues

- **500 Error**: Check the logs in Render dashboard. Common issues:
  - Missing environment variables (especially `OPENAI_API_KEY`)
  - Database connection issues (check `DATABASE_URL`)
  - Static files not collected (check build logs)

- **CORS Errors**: Make sure `CORS_ALLOWED_ORIGINS` includes your frontend URL

- **Database Migration Errors**: 
  ```bash
  # SSH into your Render service (if available) or use shell
  python manage.py migrate
  ```

### Frontend Issues

- **API Connection Errors**: 
  - Verify `VITE_API_URL` is set correctly
  - Check browser console for CORS errors
  - Ensure backend is running and accessible

- **Build Errors**: 
  - Check that all dependencies are in `package.json`
  - Verify Node.js version compatibility

## Environment Variables Summary

### Backend (Django)
- `SECRET_KEY`: Django secret key (auto-generated or custom)
- `DEBUG`: `False` (for production)
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: PostgreSQL connection string (from Render)
- `ALLOWED_HOSTS`: Your backend domain
- `CORS_ALLOWED_ORIGINS`: Your frontend URL
- `CSRF_TRUSTED_ORIGINS`: Your frontend URL

### Frontend (React/Vite)
- `VITE_API_URL`: Your backend API URL (e.g., `https://reading-chatbot-api.onrender.com`)

## Cost

- **Render Free Tier**: 
  - Web services: Free (spins down after 15 min inactivity)
  - PostgreSQL: Free (limited to 90 days, then requires upgrade)
  - Static sites: Free (always on)

- **OpenAI API**: Pay-as-you-go (very affordable for small projects)

## Next Steps

1. Set up a custom domain (optional)
2. Configure automatic deployments from GitHub
3. Set up monitoring and error tracking
4. Consider upgrading to paid plans for better performance

## Alternative Deployment Options

### Railway
- Similar to Render, good free tier
- Visit https://railway.app

### Fly.io
- Good for global distribution
- Visit https://fly.io

### Heroku
- Traditional option, now requires paid plans
- Visit https://heroku.com

## Support

If you encounter issues:
1. Check Render service logs
2. Verify all environment variables are set
3. Ensure database migrations ran successfully
4. Check that your OpenAI API key is valid and has credits
