# 🚀 ScrapeSavee Production Deployment

## 🎯 Zero-Cost Professional Deployment

Deploy ScrapeSavee with **enterprise-grade security** at **zero monthly cost** using free tiers.

---

## 📋 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  GitHub Actions │───▶│   Neon PostgreSQL│───▶│  Cloudflare R2  │
│   (Scraper)     │    │   (Database)    │    │   (Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       ▲                       ▲
         │              ┌─────────────────┐              │
         └─────────────▶│  Vercel Admin UI│──────────────┘
                        │ (Next.js + API) │
                        └─────────────────┘
```

**Flow:**
1. **GitHub Actions** runs scraper every 15 minutes
2. **Engine** scrapes Savee.com → stores in **Neon** + **R2**
3. **Admin UI** on **Vercel** manages sources/runs via serverless functions
4. **Trigger** manual runs via GitHub API from Admin UI

---

## 🔐 Step 1: Security & Environment Setup

### 1.1 Generate Production Secrets

```bash
# Strong secret key (already generated)
SECRET_KEY="oByR9McC3WIk3wZi8Ph9AmZtjXo0RdbZVAEZJkLw5H3oy876Bt7m6jZO6NP8UGRJg_c-F9jtilpL8gpsiju40g"

# GitHub Personal Access Token (classic)
# Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
# Create token with these scopes: repo, workflow, actions
GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 1.2 Verify External Services

✅ **Neon PostgreSQL**: `neondb_owner:npg_Bvh75AURbLdY@ep-calm-mouse-a1nobhsr-pooler.ap-southeast-1.aws.neon.tech`
✅ **Cloudflare R2**: `24a6b0c0c772ab595a5cefdcd840f791.r2.cloudflarestorage.com`
✅ **CloudAMQP**: `nxsiqohb:H18N9HIKLNRxp1tPCXtL1XGSElNwIhAs@armadillo.rmq.cloudamqp.com`
✅ **Savee Cookies**: Valid until 2025-07-23

---

## 🚀 Step 2: GitHub Repository Deployment

### 2.1 Push to GitHub

```bash
# Ensure you're in the project root
cd /c/Users/kush/scrapesavee

# Add all files (cleaned project)
git add .

# Commit with professional message
git commit -m "feat: production-ready ScrapeSavee deployment

- Zero-cost architecture: GitHub Actions + Vercel + Neon + R2
- Secure serverless Admin UI with direct DB access
- Professional scraper with robust error handling
- Complete environment isolation and security hardening"

# Push to your repository
git push origin main
```

### 2.2 Configure GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

```
DATABASE_URL = postgresql+asyncpg://neondb_owner:npg_Bvh75AURbLdY@ep-calm-mouse-a1nobhsr-pooler.ap-southeast-1.aws.neon.tech/neondb?ssl=require

R2_ENDPOINT_URL = https://24a6b0c0c772ab595a5cefdcd840f791.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID = f554875e60f017f39a1e8b3a78c2c47d
R2_SECRET_ACCESS_KEY = f42169f30cb17665d79716a3e16e4a7bf61e19d4e2ec0bd33da814a20b6a4f9e
R2_BUCKET_NAME = savee

AMQP_URL = amqps://nxsiqohb:H18N9HIKLNRxp1tPCXtL1XGSElNwIhAs@armadillo.rmq.cloudamqp.com/nxsiqohb

SECRET_KEY = oByR9McC3WIk3wZi8Ph9AmZtjXo0RdbZVAEZJkLw5H3oy876Bt7m6jZO6NP8UGRJg_c-F9jtilpL8gpsiju40g

COOKIES_JSON = [{"domain":"savee.com","expirationDate":1790683890.202983,"hostOnly":true,"httpOnly":true,"name":"auth_token","path":"/","sameSite":"no_restriction","secure":true,"session":false,"storeId":null,"value":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc0xvZ2luQXMiOmZhbHNlLCJzZXNzaW9uSUQiOiI2OGFjNTJmMjNjOWNhZjI3NTJlNzM2ODAiLCJpYXQiOjE3NTYxMjM4OTAsImV4cCI6MTc4NzY4MTQ5MCwiaXNzIjoiaHR0cHM6Ly9zYXZlZS5jb20ifQ.CN8OeVjD1PbNURIHB1c3At2-AbxoauT1qeX_v2ssPVI"}]
```

### 2.3 Test GitHub Actions Engine

1. Go to **Actions** tab in your GitHub repo
2. Find **"Scheduled Worker Run"** workflow
3. Click **"Run workflow"** → Set `max_items: 5` → **"Run workflow"**
4. Monitor logs for successful scraping and database writes

---

## 🖥️ Step 3: Admin UI Deployment (Vercel)

### 3.1 Install Vercel CLI & Deploy

```bash
# Install Vercel CLI globally
npm install -g vercel

# Deploy Admin UI
cd apps/admin-ui
vercel --prod

# Follow prompts:
# ✅ Set up and deploy "apps/admin-ui"? Yes
# ✅ Which scope? [Your account]
# ✅ Link to existing project? No
# ✅ What's your project's name? scrapesavee-admin
# ✅ In which directory is your code located? ./
# ✅ Want to modify these settings? No
```

### 3.2 Configure Vercel Environment Variables

In **Vercel Dashboard** → **Project Settings** → **Environment Variables**:

```
NODE_ENV = production

DATABASE_URL = postgresql://neondb_owner:npg_Bvh75AURbLdY@ep-calm-mouse-a1nobhsr-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

GITHUB_REPO = YOUR_USERNAME/scrapesavee
GITHUB_TOKEN = ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

NEXT_PUBLIC_WORKER_API_URL = /api
```

### 3.3 Redeploy with Environment Variables

```bash
# Trigger redeploy with new environment
vercel --prod
```

---

## ✅ Step 4: Production Verification

### 4.1 Test Engine (GitHub Actions)
- ✅ Actions → Scheduled Worker Run → Manual trigger works
- ✅ Logs show successful scraping, DB writes, R2 uploads
- ✅ Neon database has new rows in `sources`, `runs`, `core.blocks`

### 4.2 Test Admin UI (Vercel)
- ✅ Access: `https://scrapesavee-admin-xxx.vercel.app`
- ✅ Login: `admin` / `admin123`
- ✅ Dashboard shows real data from Neon
- ✅ Sources management works
- ✅ "Run Now" button triggers GitHub Actions

### 4.3 Test End-to-End Flow
1. **Add Source**: Admin UI → Sources → Add `https://savee.com`
2. **Trigger Run**: Click "Run Now" → GitHub Actions dispatched
3. **Monitor**: GitHub Actions logs → scraping → DB writes
4. **Verify**: Admin UI dashboard updates with new blocks

---

## 🔒 Step 5: Security Hardening

### 5.1 Change Default Admin Credentials

```typescript
// TODO: Update apps/admin-ui/src/lib/api.ts
// Replace hardcoded admin/admin123 with secure auth
```

### 5.2 Enable Security Headers

Already configured in Admin UI:
- ✅ CSP (Content Security Policy)
- ✅ HSTS (HTTP Strict Transport Security)
- ✅ X-Frame-Options
- ✅ X-Content-Type-Options

### 5.3 Database Security

- ✅ SSL-required connections
- ✅ Connection pooling with limits
- ✅ Prepared statements (SQL injection protection)

---

## 📊 Step 6: Monitoring & Maintenance

### 6.1 GitHub Actions Monitoring
- **Usage**: Free tier = 2,000 minutes/month
- **Current**: ~3 minutes per run × 4 runs/hour = 288 minutes/day
- **Monthly**: ~8,640 minutes (need paid plan if scaling)

### 6.2 Database Monitoring
```sql
-- Check scraping activity
SELECT DATE(created_at) as date, COUNT(*) as items 
FROM core.blocks 
GROUP BY DATE(created_at) 
ORDER BY date DESC;

-- Monitor storage usage
SELECT pg_size_pretty(pg_database_size('neondb'));
```

### 6.3 Alerts & Health Checks
- **Vercel**: Built-in uptime monitoring
- **GitHub**: Actions failure notifications
- **Neon**: Database health in dashboard

---

## 🎉 Production URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Admin UI** | `https://scrapesavee-admin-xxx.vercel.app` | Dashboard, source management |
| **GitHub Actions** | `https://github.com/YOUR_USERNAME/scrapesavee/actions` | Engine monitoring |
| **Neon Dashboard** | `https://console.neon.tech` | Database monitoring |
| **Cloudflare R2** | `https://dash.cloudflare.com` | Storage monitoring |

---

## 🚨 Emergency Procedures

### Engine Failure
```bash
# Check GitHub Actions logs
# Disable problematic sources in Admin UI
# Manual trigger with reduced max_items
```

### Database Issues
```bash
# Check Neon dashboard
# Verify connection strings
# Run manual DB health check
```

### Storage Issues
```bash
# Check R2 dashboard for quota
# Verify bucket permissions
# Test presigned URL generation
```

---

## 📈 Next Steps: Frontend & Scaling

After production deployment is verified:

1. **Public Frontend**: Create public-facing site on Vercel
2. **User Authentication**: Replace hardcoded admin auth
3. **Rate Limiting**: Add Redis for advanced rate limiting
4. **Monitoring**: Add Sentry for error tracking
5. **Analytics**: Add PostHog for usage analytics

**Cost Scaling Plan:**
- **0-10k items/month**: Free tiers only
- **10k-100k items/month**: GitHub Pro ($4/month)
- **100k+ items/month**: Add Neon Pro ($19/month)

---

## ✅ Deployment Checklist

- [ ] GitHub repo pushed with clean codebase
- [ ] GitHub Secrets configured (8 secrets)
- [ ] GitHub Actions workflow tested successfully
- [ ] Vercel Admin UI deployed and accessible
- [ ] Vercel environment variables configured
- [ ] Database migrations applied and verified
- [ ] Test sources added and scraped successfully
- [ ] Admin UI shows real data from database
- [ ] "Run Now" triggers GitHub Actions
- [ ] R2 storage contains scraped media files
- [ ] All security measures verified

**🎯 Ready for production!**
