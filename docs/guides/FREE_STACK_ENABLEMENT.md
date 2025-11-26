# Free-Tier Stack Enablement for the AI Automation Agency

This guide maps the existing FastAPI-based backend to a full-stack setup using free-tier providers. Choices favor tighter integration, generous limits, and operational simplicity.

## Recommended stack choices

- **Frontend:** Next.js + TypeScript + Tailwind CSS on **Vercel** (best free-tier DX, built-in Next.js optimizations). Netlify is a viable fallback.
- **Backend:** **FastAPI** (already in `src/api/`) on **Render** free tier for simplicity and autoscaling. Railway is a close alternative if you prefer infra-as-code.
- **Database:** **Supabase Postgres** (bundled auth/storage and SQL extensions). Neon is fine for pure Postgres, but Supabase reduces integration overhead.
- **Auth:** **Supabase Auth** (social login, JWTs, RLS). Use `SUPABASE_JWT_SECRET` for backend verification.
- **File storage:** **Supabase Storage** (same project + CDN). Firebase Storage only if you already rely on Firebase tooling.
- **Cache/Queue:** **Upstash Redis** free tier, using a single database for caching and lightweight queues (Redis streams/lists). Works with existing Redis abstractions in `src/infrastructure/message_queue.py` and `src/api/demo.py`.
- **CI/CD:** **GitHub Actions** (already configured in `.github/workflows/` if present) deploying to Vercel/Render via tokens.
- **Observability:** **Sentry** for errors + existing Prometheus metrics (`prometheus.yml`).
- **Messaging/Email:** **SendGrid** free tier for alerts and user messaging.
- **AI/LLM:** OpenAI/Anthropic via existing adapters (`src/infrastructure/llm_providers.py`). For vectors, run **Chroma** or **Qdrant** locally via `docker-compose` or a lightweight managed instance.

## Environment configuration

Populate `.env` using these variables (added to `.env.example`):

- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`
  - Service role key for server-side auth, anon key for client-side calls. Use JWT secret to validate Supabase-issued tokens in FastAPI dependencies.
- `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`
  - Use `UPSTASH_REDIS_URL` with existing Redis configs in `src/config.py` to back cache/queue features.
- `SENDGRID_API_KEY`
  - Wire into notification modules (e.g., `RESEND_API_KEY` already present; prefer one provider to reduce surface area).
- `SENTRY_DSN`
  - Connect Sentry SDK alongside existing OpenTelemetry/Prometheus hooks in `src/infrastructure/observability.py`.

## Deployment blueprint

### Frontend (Vercel)
1. Create a Next.js app in `/website` or a new `/frontend` package with Tailwind.
2. Add `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` as repo secrets; configure GitHub integration for auto-deploys on push.
3. Point environment variables for client needs (e.g., `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).

### Backend (Render)
1. Use the FastAPI entrypoint at `src/api/main.py` or `src/api/rest.py` with `uvicorn` command `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`.
2. Add Render environment variables from `.env` (database, Supabase, Upstash, LLM keys).
3. Attach a free Postgres instance in Supabase; set `DATABASE_URL` accordingly.
4. Expose Prometheus metrics on `METRICS_PORT` if you attach self-hosted Prometheus/Grafana.

### Database, auth, storage (Supabase)
- Create one Supabase project; use its Postgres connection string for `DATABASE_URL`.
- Enable email/password and OAuth providers in Supabase Auth; download the JWT secret and set `SUPABASE_JWT_SECRET`.
- Use Supabase Storage buckets for user uploads; restrict access with RLS policies tied to Auth user IDs.

### Cache/queue (Upstash Redis)
- Create a free Upstash Redis database and copy the REST credentials into `.env`.
- For queues, use Redis lists or streams with `RedisMessageQueue` (`src/infrastructure/message_queue.py`). Keep payloads small to stay within free limits.

### Observability
- Configure `SENTRY_DSN` for backend error capture.
- Keep Prometheus scraping `METRICS_PORT` per `prometheus.yml`; optional Grafana can run via Docker alongside the API.

## Not strictly required

- **Firebase Auth/Storage**: redundant if Supabase is adopted.
- **Queueing service (SQS, etc.)**: use Upstash Redis unless you expect high throughput.
- **Separate Neon Postgres**: only if you want posture isolation from Supabase features.

This setup keeps the current codebase compatible while leaning on integrated free-tier services that minimize operational overhead.
