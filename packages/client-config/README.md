# client-config (shared config models + mapping)

This package holds the canonical `ClientConfig` model and mapping logic from intake payloads.

Contents (planned):
- `models` — Pydantic / JSON Schema for `ClientConfig` and nested systems
- `mapping` — deterministic functions to build a `ClientConfig` from a raw intake
- tests and example payloads

Usage:
- The intake web app should POST raw payloads to a product API that uses `client-config.mapping` to normalize and persist the result.
- Keep this package dependency-light so it can be consumed by both Python backend and other tooling.
