# Production readiness gaps for multi-page, live agent experience

This document lists the missing pieces between the current codebase and the stated goal: a production-grade, multi-page marketing site with working AI agents, interactive demos, and real-time tracking. Items are grouped by priority order so they can be executed in sequence.

## 1) Platform foundations (highest priority)
- **Reliable persistence**: Swap in-memory demo and lead capture for a database (PostgreSQL) and/or Redis with schemas for users, leads, demo events, and agent runs.
- **Background execution**: Add a worker queue (e.g., Celery/RQ + Redis) for long-running agent jobs, retries, and scheduled tasks (cron for report emails, cache refreshes).
- **Configuration & secrets**: Replace ad-hoc environment reads with a centralized settings module that validates required keys (LLM credentials, Redis/DB URLs, demo secret keys) and supports per-environment overrides.
- **Authentication & session management**: Implement login (email/OAuth) plus signed session cookies or tokens so demo runs and dashboards are scoped to authenticated users.

## 2) Production API hardening
- **Storage-backed demo feed**: Ensure `/demo/record` and `/demo/stream` persist to Redis/database by default, include trace/log context, and enforce authentication or signed demo keys to deter spam.
- **Rate limiting & abuse controls**: Move the in-memory limiter in `src/api/demo.py` to a shared middleware backed by Redis so limits survive process restarts and scale horizontally.
- **Validation & quotas**: Enforce per-tenant quotas on agent invocations (requests, tokens, cost ceilings) with clear 4xx errors and audit logging.
- **Health and readiness**: Add `/healthz` and `/readyz` endpoints that verify database, Redis, queue, and LLM connectivity for orchestration tools and uptime checks.

## 3) Frontend & UX
- **Multi-page framework**: Replace static `website/*.html` with a framework (Next.js/React or Astro) that provides routing, layouts, and shared components for Solutions, Pricing, Platform, Docs, and Dashboard pages.
- **Live demo widgets**: Build client components that start a demo run, stream tokens/results over SSE/WebSocket, and post completions back to `/demo/record` with user identity attached.
- **Real-time activity display**: Use WebSocket or SSE clients with reconnect/backoff, graceful degradation to polling, and visual loading/error states.
- **Forms & lead capture**: Connect contact forms to a server route that persists to the database/CRM and triggers notifications (email/Slack) with spam protection (hCaptcha/Turnstile).

## 4) Observability & governance
- **Metrics and tracing**: Export FastAPI, queue, and agent metrics (latency, throughput, token/cost usage) to Prometheus/OpenTelemetry, and sample traces for LLM + tool calls.
- **Structured logging**: Standardize JSON logs with correlation IDs across API, workers, and frontend edge functions; forward to a log sink (e.g., Loki/Datadog).
- **Audit trails**: Persist user actions, admin changes, and data exports with immutable logs for compliance.
- **Error budgets and alerts**: Define SLOs, add alerting for queue depth, error rates, and LLM/provider failures.

## 5) Security & compliance
- **Secrets management**: Store credentials in a vault (e.g., AWS Secrets Manager) with rotation; remove secrets from plaintext `.env` in production.
- **Input/attachment scanning**: Validate and scan user uploads or fetched content before tools process them.
- **Data retention**: Add retention policies for demo events and user data with scheduled cleanup jobs.
- **Privacy/consent UX**: Add cookie/consent banners, terms/privacy pages, and telemetry opt-outs on the website.

## 6) Delivery & QA
- **CI/CD gating**: Expand CI beyond `pytest` to include type checks, linting, security scans (Bandit, Snyk), and frontend tests; block merges on failures.
- **Preview environments**: Deploy per-PR preview builds (frontend + API) for QA and stakeholder sign-off.
- **Load and chaos testing**: Add k6/Locust suites and periodic chaos drills (redis/DB outages) to verify graceful degradation.

## Suggested implementation order
1. Stand up database/Redis + worker queue; migrate demo/lead storage and rate limiting to shared infra.
2. Add auth/session handling and validated settings; expose health/readiness probes.
3. Replace static site with a routed frontend, wiring demo widgets to live agent endpoints with SSE/WebSocket streaming.
4. Layer in observability (metrics/traces/logs) and security controls (secrets, quotas, abuse prevention).
5. Harden delivery: CI gating, preview environments, and load/chaos testing.

Tracking these items and closing them in order will bridge the gap between the current demo-friendly setup and a production-grade, multi-page experience with real, observable AI agents.
