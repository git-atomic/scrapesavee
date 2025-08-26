# ScrapeSavee - Professional Oracle VM Deployment

A production-ready web scraping platform for Savee.com content, optimized for Oracle Cloud Always Free VM deployment.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORACLE CLOUD VM                         │
│                      (Always Free Tier)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   Scraper API   │    │   Admin Panel   │                    │
│  │   (FastAPI)     │◄──►│   (Next.js)     │                    │
│  │   Port: 8001    │    │   Port: 3000    │                    │
│  └─────────────────┘    └─────────────────┘                    │
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   Nginx Proxy   │    │   SSL Certs     │                    │
│  │   Port: 80/443  │    │   (Let's Encrypt)│                    │
│  └─────────────────┘    └─────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES (Free Tier)               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Neon DB       │  │   CloudAMQP     │  │  Cloudflare R2  │ │
│  │  (PostgreSQL)   │  │   (RabbitMQ)    │  │  (Object Store) │ │
│  │   Free Tier     │  │   Free Tier     │  │   Free Tier     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Deploy to Oracle VM

### **One-Command Deployment:**

```bash
# SSH to your Oracle VM
ssh ubuntu@your-oracle-vm-ip

# Run deployment script
curl -fsSL https://raw.githubusercontent.com/yourusername/scrapesavee/main/deployment/scripts/deploy-oracle-vm.sh | bash
```

### **Manual Deployment:**

1. **Setup External Services** (5 minutes):

   - [Neon PostgreSQL](https://neon.tech) - Free 10GB database
   - [CloudAMQP](https://cloudamqp.com) - Free 1M messages/month
   - [Cloudflare R2](https://cloudflare.com/products/r2/) - Free 10GB storage

2. **Deploy to Oracle VM**:

   ```bash
   git clone https://github.com/yourusername/scrapesavee.git
   cd scrapesavee
   cp .env.example .env
   # Edit .env with your service URLs
   ./deployment/scripts/deploy-oracle-vm.sh
   ```

3. **Access Your Application**:
   - 🎨 **Admin Dashboard**: `https://your-domain.com`
   - 🔧 **API Documentation**: `https://your-domain.com/api/docs`

## 📁 Project Structure

```
scrapesavee/
├── apps/
│   ├── worker/                    # FastAPI Scraper API
│   │   ├── app/
│   │   │   ├── main.py           # Main API application
│   │   │   ├── models/           # Database models
│   │   │   ├── scraper/          # Scraping logic
│   │   │   ├── queue/            # RabbitMQ integration
│   │   │   ├── storage/          # R2 storage
│   │   │   └── auth/             # JWT authentication
│   │   ├── alembic/              # Database migrations
│   │   └── requirements.txt      # Python dependencies
│   │
│   └── admin-ui/                 # Next.js Admin Dashboard
│       ├── src/
│       │   ├── app/              # App router pages
│       │   ├── components/       # React components (shadcn/ui)
│       │   └── lib/              # API client
│       └── package.json          # Node dependencies
│
├── deployment/
│   ├── nginx/                    # Nginx configuration
│   ├── ssl/                      # SSL certificate configs
│   └── scripts/                  # Deployment scripts
│
├── docker-compose.prod.yml       # Production orchestration
├── .env.example                  # Environment template
└── DEPLOYMENT.md                 # Detailed deployment guide
```

## 🎯 Features

### **Core Functionality:**

- ✅ **Savee.com Scraping**: Complete item discovery and extraction
- ✅ **Queue Processing**: RabbitMQ-based job management
- ✅ **Media Storage**: Cloudflare R2 with thumbnails and presigned URLs
- ✅ **Admin Dashboard**: Beautiful Next.js interface with shadcn/ui
- ✅ **Authentication**: JWT with role-based access control
- ✅ **Database**: PostgreSQL with comprehensive schema

### **Production Features:**

- ✅ **SSL/TLS**: Automatic Let's Encrypt certificates
- ✅ **Reverse Proxy**: Nginx with rate limiting and security headers
- ✅ **Monitoring**: Health checks and structured logging
- ✅ **Backups**: Automated database backups
- ✅ **Security**: Firewall, CORS, input validation
- ✅ **Performance**: Connection pooling, caching, compression

## 📊 Database Schema

### **Core Tables:**

- `sources` - Scraping sources and configuration
- `items` - Global item registry with metadata
- `runs` - Scraping job execution history
- `item_sources` - Many-to-many source relationships

### **Advanced Schema:**

- `core.blocks` - Raw scraped data (ingestion truth)
- `cms.block_overrides` - Editorial overrides and customizations
- `cms.v_blocks` - Merged view combining raw + editorial data
- `media` - R2 object metadata with multiple sizes

### **Features:**

- UUID primary keys for scalability
- JSONB columns for flexible metadata
- Full-text search indexes
- Proper foreign key constraints
- Audit timestamps on all tables

## 🔐 Security

- **SSL/TLS**: Let's Encrypt certificates with automatic renewal
- **Authentication**: JWT tokens with role-based permissions
- **Rate Limiting**: API and admin interface protection
- **Security Headers**: XSS, CSRF, and clickjacking protection
- **Firewall**: Oracle Cloud Security Lists configuration
- **Input Validation**: Comprehensive sanitization and validation
- **Secrets Management**: Environment-based configuration

## 💰 Cost Breakdown

| Service             | Tier           | Monthly Cost |
| ------------------- | -------------- | ------------ |
| Oracle VM           | Always Free    | $0           |
| Neon PostgreSQL     | Free (10GB)    | $0           |
| CloudAMQP RabbitMQ  | Free (1M msgs) | $0           |
| Cloudflare R2       | Free (10GB)    | $0           |
| Domain Registration | Annual         | $10-15/year  |

**Total Monthly Cost: $0** (except domain)

## 🛠️ Management

### **Common Commands:**

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Update application
cd /opt/scrapesavee
git pull
docker-compose -f docker-compose.prod.yml up -d --build

# Database migrations
docker-compose -f docker-compose.prod.yml exec worker-api alembic upgrade head

# Backup database
docker-compose -f docker-compose.prod.yml exec worker-api python manage.py backup

# Monitor system resources
htop
docker stats
```

### **Default Credentials:**

- **Username**: `admin`
- **Password**: `admin123`
- ⚠️ **Change immediately in production!**

## 🆘 Troubleshooting

### **Common Issues:**

1. **SSL Certificate Fails**:

   ```bash
   # Ensure domain points to your VM IP
   # Check firewall allows ports 80/443
   sudo certbot --nginx -d your-domain.com --dry-run
   ```

2. **Services Won't Start**:

   ```bash
   # Check environment variables
   docker-compose -f docker-compose.prod.yml config

   # Check service logs
   docker-compose -f docker-compose.prod.yml logs worker-api
   ```

3. **Database Connection Issues**:
   ```bash
   # Test database connectivity
   docker-compose -f docker-compose.prod.yml exec worker-api python -c "
   from app.database import engine
   print('Database connection successful')
   "
   ```

### **Support:**

- 📧 [Create an issue](https://github.com/yourusername/scrapesavee/issues)
- 📚 [Check API docs](https://your-domain.com/api/docs)
- 🔍 [Review deployment logs](DEPLOYMENT.md)

---

**Built for Oracle Cloud Always Free VM deployment** 🏗️
