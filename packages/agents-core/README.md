# agents-core (core platform library)

This package is the platform/engine that implements core agent abstractions:

- Domain models (Agent, Message, Tool)
- Application orchestration (use cases, orchestrators)
- Infrastructure adapters (LLM providers, vector DB, repos)

Guidance:
- Treat `agents-core` as a stable library the product layer depends on.
- We will not refactor the internals during the initial product-focused work; instead we will call into it from `agency` product modules.
