# Worker (Celery) Setup

This project includes a minimal Celery scaffold to run background tasks (demo events, agent jobs).

Files added:

- `src/workers/celery_app.py` — Celery app configured to use `REDIS_URL` from `src.config.settings`.
- `src/workers/tasks.py` — Example task `record_demo_event` which saves a demo event to the DB.
- `scripts/start_worker.sh` — Helper script to start a Celery worker.

Quick start (development):

1. Ensure Redis is running locally (or set `REDIS_URL` in your environment).

2. Install Celery:

```bash
pip install celery
```

3. Start the worker:

```bash
export REDIS_URL=redis://localhost:6379/0
./scripts/start_worker.sh
```

Trigger a task from Python (REPL or app):

```python
from src.workers.tasks import record_demo_event
record_demo_event.delay('alice@example.com', 'demo_started', '{"foo":"bar"}')
```

Notes:
- The sample task uses the SQLAlchemy models and `SessionLocal` inside the worker. For production consider connection pool sizing and dedicated DB credentials for workers.
- For running tasks that call async application logic, adapt tasks to call `asyncio.run(...)` as appropriate, or use an async worker strategy.
