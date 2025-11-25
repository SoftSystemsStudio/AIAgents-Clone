# Deployment Guide

## Deploy to Vercel (Recommended - Free)

### Option 1: Deploy via Vercel CLI

1. **Install Vercel CLI:**
```bash
npm install -g vercel
```

2. **Login to Vercel:**
```bash
vercel login
```

3. **Deploy:**
```bash
cd /workspaces/AIAgents
vercel --prod
```

4. **Follow prompts:**
   - Set up and deploy? **Yes**
   - Which scope? **Your account**
   - Link to existing project? **No**
   - What's your project's name? **soft-systems-studio**
   - In which directory is your code located? **./** 
   - Want to override settings? **No**

5. **Your site will be live at:**
   - `https://soft-systems-studio.vercel.app`
   - You can add custom domain in Vercel dashboard

### Option 2: Deploy via GitHub (Easier)

1. **Go to:** https://vercel.com/new

2. **Import Git Repository:**
   - Click "Import Project"
   - Connect GitHub account
   - Select `SoftSystemsStudio/AIAgents` repository
   - Click "Import"

3. **Configure Project:**
   - **Framework Preset:** Other
   - **Root Directory:** `./`
   - **Build Command:** (leave empty)
   - **Output Directory:** `./`
   - Click "Deploy"

4. **Done!** Your site is live at `https://aiagents.vercel.app`

### Add Custom Domain

1. Go to your project in Vercel dashboard
2. Click "Settings" → "Domains"
3. Add your domain (e.g., `softsystems.studio`)
4. Follow DNS configuration instructions
5. SSL certificate is automatic!

---

## Deploy API Backend to Railway (Free Tier Available)

### Option 1: Railway CLI

1. **Install Railway CLI:**
```bash
npm install -g @railway/cli
```

2. **Login:**
```bash
railway login
```

3. **Initialize:**
```bash
cd /workspaces/AIAgents
railway init
```

4. **Deploy:**
```bash
railway up
```

5. **Add environment variables:**
```bash
railway variables set ENVIRONMENT=production
railway variables set DATABASE_URL=your-db-url
```

### Option 2: Railway via GitHub

1. **Go to:** https://railway.app/new

2. **Deploy from GitHub:**
   - Click "Deploy from GitHub repo"
   - Select `SoftSystemsStudio/AIAgents`
   - Railway auto-detects Python/FastAPI

3. **Configure:**
   - Set start command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables (if needed)

4. **Done!** API is live at `https://your-app.up.railway.app`

### Update Landing Page API URL

After deploying API, update `website/landing.html`:

```javascript
// Change this line in the form submission script:
const response = await fetch('https://your-api.railway.app/api/v1/contact', {
```

---

## Alternative: Deploy to Netlify

1. **Go to:** https://app.netlify.com/

2. **Drag and drop deployment:**
   - Just drag your project folder to Netlify
   - Or connect GitHub repository

3. **Configure:**
   - Build command: (leave empty)
   - Publish directory: `./`

4. **Done!** Live at `https://your-site.netlify.app`

---

## Post-Deployment Checklist

- [ ] Test contact form on live site
- [ ] Update API URL in `website/landing.html`
- [ ] Add custom domain
- [ ] Set up Google Analytics
- [ ] Test mobile responsiveness
- [ ] Share link with friends for feedback
- [ ] Update social media links
- [ ] Add favicon
- [ ] Test all buttons and links
- [ ] Set up email notifications for leads

---

## Quick Deploy Commands

```bash
# For Vercel (landing page)
vercel --prod

# For Railway (API backend)
railway up

# Or use GitHub integration for both (recommended)
```

Your landing page will be live in under 2 minutes! 🚀
