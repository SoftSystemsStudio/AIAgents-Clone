from .celery_app import app

import asyncio


@app.task(bind=True)
def record_demo_event(self, user_email: str, event_type: str, payload: str):
    """Record a demo event into the database.

    This is a simple example showing how a Celery worker can perform
    blocking DB operations by using the application's SQLAlchemy layer
    directly. The task uses `asyncio.run` for clarity; in production you
    may prefer a fully sync implementation or a dedicated DB connection
    pooling config.
    """
    try:
        # Import locally to avoid import-time cycles in the main app
        from src.infrastructure.db import SessionLocal
        from src.infrastructure.models_sql import User, DemoEvent

        def _work():
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.email == user_email).first()
                if not user:
                    user = User(email=user_email)
                    db.add(user)
                    db.commit()
                    db.refresh(user)

                ev = DemoEvent(user_id=user.id, event_type=event_type, payload=payload)
                db.add(ev)
                db.commit()
                db.refresh(ev)
                return {"event_id": ev.id}
            finally:
                db.close()

        return asyncio.run(asyncio.to_thread(_work))
    except Exception as exc:
        # Let Celery record the failure and requeue if configured
        raise
