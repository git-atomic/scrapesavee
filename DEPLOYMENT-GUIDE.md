# 🚀 ScrapeSavee Production Deployment Guide

## 🎯 Zero-Cost Production Setup

This guide deploys ScrapeSavee with **NO monthly costs** using free tiers:

- **Engine**: GitHub Actions (free for public repos)
- **Database**: Neon PostgreSQL (free 10GB)
- **Storage**: Cloudflare R2 (free 10GB)
- **Admin UI**: Vercel (free hosting)
- **Queue**: CloudAMQP (free 1M messages/month)

---

## 📋 Prerequisites

- GitHub account
- Vercel account
- External services already set up (you have these):
  - ✅ Neon PostgreSQL database
  - ✅ Cloudflare R2 bucket
  - ✅ CloudAMQP RabbitMQ instance
  - ✅ Savee.com cookies

---

## 🔧 Step 1: GitHub Repository Setup

### 1.1 Push Code to GitHub

```bash
# Create GitHub repo and push
git init
git add .
git commit -m "Initial ScrapeSavee deployment"
git remote add origin https://github.com/YOUR_USERNAME/scrapesavee.git
git push -u origin main
```

### 1.2 Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

```
DATABASE_URL = <your Neon connection string>

R2_ENDPOINT_URL = <your R2 endpoint URL>
R2_ACCESS_KEY_ID = <your R2 key id>
R2_SECRET_ACCESS_KEY = <your R2 secret>
R2_BUCKET_NAME = savee

AMQP_URL = <optional>

SECRET_KEY = <64-char random secret>

COOKIES_JSON = <Savee cookie JSON>
```

---

## 🤖 Step 2: GitHub Actions Engine

### 2.1 Test the Workflow

1. Go to **Actions** tab in your GitHub repo
2. Click **"Scheduled Worker Run"**
3. Click **"Run workflow"**
4. Set `max_items` to `5` for testing
5. Click **"Run workflow"**

### 2.2 Monitor Execution

- Check the workflow logs
- Verify items are scraped and stored in Neon + R2
- Confirm runs are recorded in the database

### 2.3 Automatic Schedule

The workflow runs every 15 minutes automatically. To adjust:

```yaml
# Edit .github/workflows/worker.yml
schedule:
  - cron: "*/30 * * * *" # Every 30 minutes
```

---

## 🖥️ Step 3: Admin UI Deployment (Vercel)

### 3.1 Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy Admin UI
cd apps/admin-ui
vercel

# Follow prompts:
# Set up and deploy? Yes
# Which scope? Your account
# Link to existing project? No
# Project name: scrapesavee-admin
# Directory: ./
# Override settings? No
```

### 3.2 Configure Environment Variables

In Vercel Dashboard → Project → Settings → Environment Variables:

```
NEXT_PUBLIC_WORKER_API_URL = https://your-api-domain.com/api
```

**Note**: For GitHub Actions-only setup (no always-on API), you'll add serverless routes to read from Neon directly.

### 3.3 Custom Domain (Optional)

- Vercel provides a free subdomain: `scrapesavee-admin.vercel.app`
- Or add your own domain in Project Settings

---

## 🔄 Step 4: Admin UI Serverless Routes (No API Needed)

Since you're using GitHub Actions, add serverless API routes to the Admin UI:

### 4.1 Create API Routes

```typescript
// apps/admin-ui/src/app/api/stats/route.ts
import { NextResponse } from "next/server";
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

export async function GET() {
  try {
    const sources = await pool.query(
      "SELECT COUNT(*) as total FROM sources WHERE enabled = true"
    );
    const runs = await pool.query("SELECT COUNT(*) as total FROM runs");
    const blocks = await pool.query(
      "SELECT COUNT(*) as total FROM core.blocks"
    );

    return NextResponse.json({
      sources: { total: sources.rows[0].total, enabled: sources.rows[0].total },
      runs: { total: runs.rows[0].total },
      blocks: { total: blocks.rows[0].total },
    });
  } catch (error) {
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
```

### 4.2 Update API Client

```typescript
// apps/admin-ui/src/lib/api.ts
const API_BASE_URL = "/api"; // Use serverless routes

export const workerApi = {
  getStats: () => fetch("/api/stats").then((res) => res.json()),
  getSources: () => fetch("/api/sources").then((res) => res.json()),
  getRuns: () => fetch("/api/runs").then((res) => res.json()),
  getBlocks: () => fetch("/api/blocks").then((res) => res.json()),
  // ... other routes
};
```

---

## 🌐 Step 5: Alternative API Hosting (Optional)

If you want an always-on API (not just GitHub Actions):

### Option A: Railway (Free Tier)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy API
cd apps/worker
railway login
railway init
railway up
```

### Option B: Render (Free Tier)

1. Connect GitHub repo to Render
2. Create new **Web Service**
3. Build Command: `cd apps/worker && pip install -r requirements.txt`
4. Start Command: `cd apps/worker && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Option C: Heroku (Free alternative)

```bash
# Create Procfile
echo "web: cd apps/worker && uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create scrapesavee-api
git push heroku main
```

---

## 📊 Step 6: Monitoring & Maintenance

### 6.1 Database Monitoring

```sql
-- Check scraping activity
SELECT
    DATE(created_at) as date,
    COUNT(*) as items_scraped
FROM core.blocks
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Check run status
SELECT status, COUNT(*)
FROM runs
GROUP BY status;
```

### 6.2 Storage Monitoring

```bash
# Check R2 usage via Cloudflare Dashboard
# Monitor free tier limits: 10GB storage, 10M requests/month
```

### 6.3 GitHub Actions Monitoring

- **Actions** tab shows execution history
- Free tier: 2,000 minutes/month (plenty for scraping)
- Each run takes ~2-5 minutes

---

## 🚨 Step 7: Security & Production Hardening

### 7.1 Generate Strong Secret Key

```python
import secrets
print(secrets.token_urlsafe(64))
```

### 7.2 Rotate Credentials

- Update `SECRET_KEY` in GitHub Secrets
- Refresh Savee cookies if authentication fails
- Monitor external service quotas

### 7.3 CORS Configuration

```python
# Update CORS_ORIGINS in production
CORS_ORIGINS=["https://scrapesavee-admin.vercel.app"]
```

---

## 📈 Step 8: Scaling & Optimization

### 8.1 Increase Scraping Frequency

```yaml
# .github/workflows/worker.yml
schedule:
  - cron: "*/5 * * * *" # Every 5 minutes
```

### 8.2 Add More Sources

```python
# Add via Admin UI or database
INSERT INTO sources (name, type, url, enabled)
VALUES ('Savee User Profile', 'user', 'https://savee.com/username', true);
```

### 8.3 Monitor Performance

- GitHub Actions execution time
- Database query performance
- R2 storage usage

---

## ✅ Final Checklist

- [ ] GitHub repo created and pushed
- [ ] GitHub Secrets configured
- [ ] GitHub Actions workflow tested
- [ ] Admin UI deployed to Vercel
- [ ] Serverless routes configured (if no API)
- [ ] Database migrations applied
- [ ] Sources seeded
- [ ] Monitoring dashboard accessible
- [ ] Production secret key generated
- [ ] CORS configured for production domains

---

## 🎉 Success!

Your ScrapeSavee platform is now running in production with:

1. **Automated scraping** every 15 minutes via GitHub Actions
2. **Professional admin interface** on Vercel
3. **Secure data storage** in Neon + Cloudflare R2
4. **Zero monthly costs** using free tiers
5. **Production-ready** security and monitoring

**Access URLs:**

- 🖥️ **Admin UI**: `https://scrapesavee-admin.vercel.app`
- 📊 **API** (if deployed): `https://your-api-domain.com`
- 🔧 **GitHub Actions**: Repository → Actions tab

**Default Login:**

- Username: `admin`
- Password: `admin123`
- ⚠️ **Change immediately in production!**
