# Full-Stack Rollout Checklist (free-tier stack)

You already populated `.env` with the Supabase, Upstash Redis, Sentry, SendGrid, and LLM keys. Follow this checklist to **actually use those values** and stand up the full stack (FastAPI backend + Next.js frontend + free-tier infra).

## 1) Wire the backend to your managed services
- **Database (Supabase Postgres):**
  - Set `DATABASE_URL` to the Supabase connection string (overrides host/port/user/pass). Keep `DATABASE_POOL_SIZE` modest (e.g., 5–10) for free-tier limits.
  - The API will automatically prefer PostgreSQL persistence at startup; if connection fails it logs the error and falls back to the in-memory repository so health and boot still work.
  - Run migrations if present: `alembic upgrade head` (or `make migrate` if you add a target) after installing deps.
- **Cache/Queue (Upstash Redis):**
  - Map the Upstash endpoint into existing Redis fields: `REDIS_HOST=<your-upstash-host>`, `REDIS_PORT=<port>`, `REDIS_PASSWORD=<token>`. For a `rediss://` URL, you can parse host/port/token from the URL or set `REDIS_URL` if you introduce it in config.
  - For REST usage, set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` for any serverless tasks you add later.
- **LLM providers:**
  - Keep `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` filled; the FastAPI entrypoint (`src/api/rest.py`) consumes `get_config()` and expects at least one LLM key in production.
- **Observability:**
  - Set `SENTRY_DSN` (plus optional `SENTRY_ENVIRONMENT`) and install the observability extras: `pip install -e .[observability]`. Wire `OTEL_EXPORTER_ENDPOINT` if you plan to ship traces to Jaeger/Tempo/OTLP.
- **Email/Messaging:**
  - Use `SENDGRID_API_KEY` (or `RESEND_API_KEY` already present) in any outbound email tool you add; keep one provider to stay under free quotas.

## 2) Bring the backend up locally (smoke test)
1. Install deps: `make install-dev`.
2. Copy env: `cp .env.example .env` (already filled by you) and export with `set -a; source .env; set +a`.
3. Run local infra if you want self-hosted services instead of the cloud: `make docker-up` (brings Postgres, Redis, Qdrant, Prometheus, Jaeger).
   - If you want everything containerized, use `docker compose up api postgres redis qdrant` (after `docker compose build api`).
   - Use the container-friendly host overrides in `.env.example` (`postgres`, `redis`, `qdrant`) when running via Compose.
4. Start the API for a smoke test: `uvicorn src.api.rest:app --reload --host 0.0.0.0 --port 8000` (or rely on the Compose-managed `api` service).
5. Check health/metrics:
   - `curl http://localhost:8000/health` (expects `"status": "healthy"` and shows Supabase/Redis/Postgres/Qdrant availability).
4. Start the API for a smoke test: `uvicorn src.api.rest:app --reload --host 0.0.0.0 --port 8000`.
5. Check health/metrics:
   - `curl http://localhost:8000/health` (expects `"status": "healthy"` and shows Supabase/Redis availability).
   - If metrics enabled, `curl http://localhost:9090/metrics` (or whatever `METRICS_PORT` you set).

## 3) Prepare deployment targets
- **Render (backend):**
  - New Web Service → repo root → start command: `uvicorn src.api.rest:app --host 0.0.0.0 --port 8000`.
  - Add environment variables from `.env` (Database, Supabase, Upstash, LLM keys, Sentry, email provider).
  - Attach Supabase Postgres via `DATABASE_URL`; keep autoscaling enabled.
- **Supabase:**
  - Enable Auth providers and copy `SUPABASE_JWT_SECRET` into `.env`; the backend now instantiates a Supabase client when URL + service role key are set so you can reuse Storage/Auth/Database from server code.
  - Create Storage bucket(s) with RLS policies tied to auth user IDs.
- **Upstash Redis:**
  - Copy REST credentials to `.env`; if using direct Redis protocol, allowlisted regions match your Render region.
- **Qdrant (vector store):**
  - If using Render or another host, set `QDRANT_HOST`, `QDRANT_PORT`, optional `QDRANT_API_KEY`, and `QDRANT_USE_HTTPS` so the `/health` endpoint can report its status. Keep Qdrant reachable from the API container or service.
  - Enable Auth providers and copy `SUPABASE_JWT_SECRET` into `.env` for backend JWT verification middleware you add later.
  - Create Storage bucket(s) with RLS policies tied to auth user IDs.
- **Upstash Redis:**
  - Copy REST credentials to `.env`; if using direct Redis protocol, allowlisted regions match your Render region.
- **Sentry:**
  - Add the project DSN to Render environment variables; configure alerts for 5xx spikes.

## 4) Add the Next.js/Tailwind frontend
- Scaffold in a new folder (e.g., `/frontend`):
  ```bash
  npx create-next-app@latest frontend --typescript --tailwind --eslint
  cd frontend
  npm install @supabase/supabase-js
  ```
- Expose client-side envs via `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`; add them to Vercel project settings.
- Point your API calls to the Render base URL (e.g., `https://<render-service>.onrender.com`).
- Deploy to Vercel with the GitHub integration; set the same env vars in Vercel (client-safe keys only).

## 5) CI/CD and guardrails
- Add GitHub Actions secrets for `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, and Render API key if you automate deploys.
- Add checks in your pipeline for formatting (`make format`), lint (`make lint`), and tests (`make test`).
- Budget observability: keep `ENABLE_TRACING=false` until you need distributed tracing; leave `ENABLE_METRICS=true` for Prometheus scraping.

## 6) Prove it end-to-end
- Create a test user in Supabase Auth, log in via the frontend, and hit the protected FastAPI route `GET /auth/supabase/me` with the access token to validate `SUPABASE_JWT_SECRET` end to end.
- Upload a small file to Supabase Storage via the frontend and confirm the backend can access it with the service role key.
- Enqueue a sample task into Redis (or Upstash REST) and process it with `RedisMessageQueue` (`src/infrastructure/message_queue.py`).
- Trigger an error intentionally and confirm it appears in Sentry and Prometheus dashboards.

This sequence ensures every secret you added in `.env` is exercised and that the free-tier providers are part of the running stack.
