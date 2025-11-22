# 🚀 Quick Deploy Guide - Get Your Site Live in 2 Minutes!

## Easiest Method: Deploy via Vercel Website (No CLI needed)

### Step 1: Go to Vercel
1. Visit: **https://vercel.com/new**
2. Sign up/login with GitHub

### Step 2: Import Your Repository
1. Click **"Import Git Repository"**
2. Find and select: **`SoftSystemsStudio/AIAgents`**
3. Click **"Import"**

### Step 3: Configure (Just Click Deploy!)
- **Framework Preset:** Other (or leave auto-detected)
- **Root Directory:** `./` (default)
- **Build Command:** *(leave empty)*
- **Output Directory:** `./` (default)
- Click **"Deploy"** 🎉

### Step 4: Your Site is LIVE!
- You'll get a URL like: `https://ai-agents-xyz.vercel.app`
- Visit it and test your contact form!

### Step 5 (Optional): Add Custom Domain
1. In Vercel dashboard, go to **Settings → Domains**
2. Add your domain (e.g., `softsystems.studio`)
3. Follow DNS instructions
4. SSL certificate is automatic! ✅

---

## Update API URL After Deployment

Once your API backend is deployed (see Railway instructions in DEPLOYMENT.md), update the contact form:

1. Open `landing.html`
2. Find this line (near bottom of file):
```javascript
const response = await fetch('http://localhost:8000/api/v1/contact', {
```

3. Change to your live API URL:
```javascript
const response = await fetch('https://your-api.railway.app/api/v1/contact', {
```

4. Commit and push - Vercel auto-deploys!

---

## Viewing Your Leads

While API is on localhost, view leads at:
- **All leads:** http://localhost:8000/api/v1/leads
- **API docs:** http://localhost:8000/api/docs

---

## That's It! 🎉

Your professional landing page is now live and collecting leads!

**Next steps:**
1. Share your live URL with friends
2. Deploy API backend to Railway (see DEPLOYMENT.md)
3. Set up email notifications
4. Add Google Analytics
5. Start marketing!

**Need help?** Check full deployment guide in `DEPLOYMENT.md`
