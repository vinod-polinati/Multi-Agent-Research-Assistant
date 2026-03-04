# 🚀 Deployment Guide: Vercel + Render

Deploying a split architecture (Frontend on Vercel, Backend on Render) allows for great scale and separation of concerns.

I have updated the codebase to support this:
1. **CORS is enabled** in `main.py` so the backend can accept requests from the Vercel frontend.
2. An **`API_BASE` constant** was added to `static/index.html` so the frontend knows how to communicate with Render.

Follow these steps exactly:

---

## Part 1: Deploy Backend to Render

1. Create an account on [Render](https://render.com/).
2. Click **New +** and select **Web Service**.
3. Select "Build and deploy from a Git repository" and connect your GitHub repo `vinod-polinati/AI-Research-Agent`.
4. Configure the Web Service:
   - **Name:** `multiagent-research-backend`
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Scroll down to **Environment Variables** and add:
   - `GROQ_API_KEY`: *(paste your real Groq key here)*
   - `TAVILY_API_KEY`: *(paste your real Tavily key here)*
6. Click **Create Web Service**. 

Wait for the build to finish. Once it says `Live`, copy the URL provided (e.g., `https://multiagent-research-backend.onrender.com`).

*(Note: On the free tier, Render will spin down your app after 15 minutes of inactivity. When it spins down, the SQLite database will be cleared since the disk is ephemeral. To persist research history permanently, you would need to attach a Render Disk or upgrade to a Postgres database).*

---

## Part 2: Connect Frontend to Backend

Now you need to tell your Vercel frontend where your Render backend is.

1. Open `static/index.html` in your editor.
2. Find line 128:
   ```javascript
   const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
       ? '' 
       : 'https://YOUR_RENDER_URL.onrender.com'; // ⚠️ UPDATE THIS LINE
   ```
3. Replace `https://YOUR_RENDER_URL.onrender.com` with the actual URL you copied from Render in step 1.
4. **Commit and push** this change to GitHub:
   ```bash
   git add static/index.html
   git commit -m "chore: connect frontend to render backend"
   git push origin main
   ```

---

## Part 3: Deploy Frontend to Vercel

1. Create an account on [Vercel](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository `vinod-polinati/AI-Research-Agent`.
4. Configure the Project:
   - **Framework Preset:** `Other`
   - **Root Directory:** Edit this and type `static`
   - **Build Command:** *(leave empty)*
   - **Output Directory:** *(leave empty)*
5. Click **Deploy**.

Because Vercel is serving static HTML elements out of the `static` directory, it takes literally 3 seconds. Once finished, click **Visit** to see your live application.

🎉 **You are live!** 
The Vercel frontend will now seamlessly call the Render backend using the `API_BASE` URL, and results will stream live to the browser.
