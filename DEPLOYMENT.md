# Deployment Guide: Vercel + Render

This guide covers deploying the Multi-Agent Research Assistant with a split architecture: **Frontend on Vercel** and **Backend on Render**.

### Prerequisites

- The codebase already includes **CORS** support in `main.py` (accepts requests from any origin).
- The frontend uses a configurable **`API_BASE`** constant in `static/index.html` to route API calls to the backend.

---

## Part 1: Deploy Backend to Render

1. Create an account on [Render](https://render.com/).
2. Click **New +** → **Web Service**.
3. Select "Build and deploy from a Git repository" and connect your GitHub repo `vinod-polinati/Multi-Agent-Research-Assistant`.
4. Configure the Web Service:
   - **Name:** `multiagent-research-backend`
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `GROQ_API_KEY` — your Groq API key
   - `TAVILY_API_KEY` — your Tavily API key
6. Click **Create Web Service**.

Wait for the build to finish. Once it shows `Live`, copy the URL (e.g., `https://multiagent-research-backend.onrender.com`).

> **Note:** On Render's free tier, the app spins down after 15 minutes of inactivity. The SQLite database is ephemeral — research history will be lost on restart. For persistence, attach a Render Disk or migrate to PostgreSQL.

---

## Part 2: Connect Frontend to Backend

Update the frontend to point API calls at your Render backend URL.

1. Open `static/index.html`.
2. Find the `API_BASE` constant (around line 130):
   ```javascript
   const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
       ? '' 
       : 'https://YOUR_RENDER_URL.onrender.com'; // ⚠️ UPDATE THIS LINE
   ```
3. Replace `https://YOUR_RENDER_URL.onrender.com` with the actual URL from Part 1.
4. Commit and push:
   ```bash
   git add static/index.html
   git commit -m "chore: connect frontend to render backend"
   git push origin main
   ```

---

## Part 3: Deploy Frontend to Vercel

1. Create an account on [Vercel](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository `vinod-polinati/Multi-Agent-Research-Assistant`.
4. Configure:
   - **Framework Preset:** `Other`
   - **Root Directory:** `static`
   - **Build Command:** *(leave empty)*
   - **Output Directory:** *(leave empty)*
5. Click **Deploy**.

Vercel serves the static HTML files instantly. Once deployed, click **Visit** to open the live app.

---

## Verification

1. Open the Vercel URL in your browser.
2. Enter a research topic and click **Start Research**.
3. You should see real-time progress updates streamed from the Render backend via SSE.
4. Once complete, the structured markdown report appears in the browser and can be downloaded.

> **Tip:** If SSE events aren't arriving, check the browser console for CORS errors. Ensure the `API_BASE` URL in `index.html` exactly matches your Render service URL (no trailing slash).
