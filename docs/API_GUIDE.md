# Gmail Cleanup API

Multi-tenant SaaS API for automated Gmail inbox cleanup with AI-powered categorization.

## 🚀 Quick Start

```bash
# Start the API server
./start_api.sh

# Or manually
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**API Documentation:** http://localhost:8000/api/docs

## 📋 API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /health/ready` - Readiness check

### Gmail Operations
- `POST /api/v1/gmail/analyze` - Analyze inbox (free, no quota)
- `POST /api/v1/gmail/cleanup/dry-run` - Preview cleanup (free)
- `POST /api/v1/gmail/cleanup/execute` - Execute cleanup (uses quota)
- `GET /api/v1/gmail/history` - Get cleanup history
- `GET /api/v1/gmail/usage` - Get usage stats & quotas

### Authentication (Coming Soon)
- `POST /api/v1/auth/signup` - Create account
- `POST /api/v1/auth/login` - Login (get JWT token)
- `POST /api/v1/auth/refresh` - Refresh token

### Customer Management (Coming Soon)
- `GET /api/v1/customer/me` - Get current customer
- `PATCH /api/v1/customer/me` - Update profile
- `POST /api/v1/customer/oauth/gmail` - Connect Gmail

### Billing (Coming Soon)
- `GET /api/v1/billing/plans` - List plan tiers
- `POST /api/v1/billing/upgrade` - Upgrade plan
- `POST /api/v1/billing/portal` - Stripe customer portal

## 🔐 Authentication

All endpoints (except signup/login) require JWT authentication:

```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Returns: {"access_token": "eyJ...", "token_type": "bearer"}

# Use token in subsequent requests
curl -X POST http://localhost:8000/api/v1/gmail/analyze \
  -H "Authorization: Bearer eyJ..."
```

## 📊 Usage Example

```bash
# 1. Analyze inbox (free, no quota)
curl -X POST http://localhost:8000/api/v1/gmail/analyze \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "total_emails": 15420,
#   "categories": {"newsletters": 8234, "promotions": 4122},
#   "total_size_mb": 3456.78
# }

# 2. Dry run cleanup (preview, free)
curl -X POST http://localhost:8000/api/v1/gmail/cleanup/dry-run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "categories_to_delete": ["newsletters", "promotions"],
    "older_than_days": 90,
    "exclude_starred": true
  }'

# Response:
# {
#   "emails_to_delete": 3421,
#   "total_size_mb": 842.3,
#   "sample_subjects": ["Weekly Newsletter #234", ...]
# }

# 3. Execute cleanup (uses quota)
curl -X POST http://localhost:8000/api/v1/gmail/cleanup/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "categories_to_delete": ["newsletters"],
    "older_than_days": 90
  }'

# Response:
# {
#   "cleanup_run_id": "uuid",
#   "emails_deleted": 3421,
#   "quota_used": 3421,
#   "quota_remaining": 1579
# }

# 4. Check usage/quota
curl -X GET http://localhost:8000/api/v1/gmail/usage \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "plan_tier": "FREE",
#   "emails_per_month_limit": 500,
#   "emails_used_this_month": 3421,
#   "emails_remaining": -2921,
#   "is_on_trial": true
# }
```

## 💰 Plan Tiers & Quotas

| Plan | Price | Emails/Month | Cleanups/Day | Features |
|------|-------|--------------|--------------|----------|
| **Free** | $0 | 500 | 1 | Basic cleanup |
| **Basic** | $9 | 5,000 | 10 | + Priority support |
| **Pro** | $29 | 50,000 | 100 | + Scheduled cleanups<br>+ Advanced rules |
| **Enterprise** | $99 | 500,000 | 1,000 | + White-label<br>+ API access<br>+ SLA |

All plans include:
- 14-day free trial
- Gmail OAuth integration
- AI-powered categorization
- Dry-run previews (unlimited, free)
- Audit logs

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                  │
├─────────────────────────────────────────────────────────┤
│ Authentication │ Rate Limiting │ Quota Enforcement      │
├─────────────────────────────────────────────────────────┤
│         Application Layer (Use Cases)                    │
│  - AnalyzeInboxUseCase                                   │
│  - DryRunCleanupUseCase                                  │
│  - ExecuteCleanupUseCase                                 │
├─────────────────────────────────────────────────────────┤
│            Domain Layer (Business Logic)                 │
│  - Customer (plan tiers, quotas)                         │
│  - EmailThread (categorization)                          │
│  - CleanupRule (deletion logic)                          │
├─────────────────────────────────────────────────────────┤
│          Infrastructure Layer (Adapters)                 │
│  - GmailClient (Gmail API)                               │
│  - PostgreSQL (multi-tenant data)                        │
│  - Redis (rate limiting)                                 │
└─────────────────────────────────────────────────────────┘
```

## 🗄️ Database Schema

**Multi-tenant with row-level security:**

- `customers` - Customer accounts, plan tiers, billing
- `oauth_tokens` - Encrypted Gmail OAuth tokens per customer
- `usage_tracking` - Monthly email quotas and usage
- `cleanup_runs` - Cleanup history per customer
- `audit_logs` - Security audit trail

**Row-level security ensures data isolation** - customers can only access their own data.

## ⚙️ Configuration

Environment variables (`.env`):

```bash
# Security
JWT_SECRET_KEY=your-secret-key-here  # MUST change in production

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/gmail_cleanup

# Redis (rate limiting)
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=production
DEBUG=false

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4  # Production: use CPU count
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Test API endpoints
pytest tests/api/

# Test with coverage
pytest --cov=src --cov-report=html

# View coverage
open htmlcov/index.html
```

## 🚀 Deployment

### Docker

```bash
# Build
docker build -t gmail-cleanup-api .

# Run
docker run -p 8000:8000 --env-file .env gmail-cleanup-api
```

### Docker Compose

```bash
docker-compose up -d
```

Includes:
- FastAPI application
- PostgreSQL database
- Redis cache
- Prometheus monitoring

### Production Checklist

- [ ] Change `JWT_SECRET_KEY` to long random string
- [ ] Set up PostgreSQL with multi-tenant schema
- [ ] Configure Redis for rate limiting
- [ ] Run database migrations
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure CORS allowed origins
- [ ] Set up SSL/TLS (nginx reverse proxy)
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Set up logging (structured JSON logs)
- [ ] Configure backup strategy
- [ ] Load test with expected traffic
- [ ] Set up alerting (PagerDuty/Slack)

## 📈 Monitoring

**Health Checks:**
- `/health` - Basic liveness check
- `/health/ready` - Readiness (checks dependencies)

**Metrics (Prometheus format):**
- `http_requests_total` - Total requests by endpoint
- `http_request_duration_seconds` - Latency histogram
- `gmail_cleanups_total` - Total cleanups executed
- `gmail_emails_deleted_total` - Total emails deleted
- `quota_exceeded_total` - Quota limit hits

**Logs:**
- Structured JSON format
- Customer ID in all logs
- Audit trail for deletions
- Error tracking with stack traces

## 🔒 Security

- **Authentication:** JWT tokens with expiration
- **Authorization:** Row-level security in database
- **Passwords:** bcrypt hashing (12 rounds)
- **OAuth Tokens:** Encrypted at rest
- **Rate Limiting:** Redis-based per customer
- **Audit Logs:** All cleanup operations logged
- **HTTPS Only:** In production (nginx)
- **CORS:** Restricted to frontend domain

## 📚 Next Steps

**Week 1 - API Foundation:**
- [x] Multi-tenant database schema
- [x] Customer domain model
- [x] JWT authentication
- [x] FastAPI core setup
- [x] Gmail cleanup endpoints
- [ ] Install dependencies
- [ ] Apply database migration
- [ ] Update use cases for multi-tenancy
- [ ] Create usage tracking service
- [ ] Test API with curl

**Week 2 - Integration:**
- [ ] Stripe billing integration
- [ ] Rate limiting with Redis
- [ ] Email verification
- [ ] Password reset flow
- [ ] OAuth flow for Gmail
- [ ] Usage tracking service
- [ ] Admin dashboard

**Week 3 - Frontend:**
- [ ] Build customer dashboard (Next.js + AI/Cursor)
- [ ] Landing page
- [ ] Onboarding flow
- [ ] Billing portal integration
- [ ] Usage/quota UI

**Week 4 - Launch:**
- [ ] Beta testing
- [ ] Load testing
- [ ] Security audit
- [ ] Deploy to production
- [ ] Marketing materials
- [ ] First paying customers! 🎉

## 🤝 Contributing

This is a commercial SaaS product. For questions:
- Email: support@yourdomain.com
- Docs: https://docs.yourdomain.com

## 📝 License

Proprietary - All rights reserved.
