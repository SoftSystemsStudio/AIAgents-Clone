# Architecture - AI Automation Agency (Product-focused)

This document defines a product-first structure and operating model for the "AI Automation Agency" built on top of the existing repository.

Goal: make the repo easy to navigate for building the agency product (intake → client_config → proposal → demo agents) while leaving the core platform intact for future work.

High-level layers

- Core platform (`src/domain`, `src/application`, `src/infrastructure`): reusable engine for agents. Treated as a library for now.
- Product layer (`src/client_config`, `src/agency`, `apps/agency-web`): where the intake, mapping, admin, and agent instantiation live.
- Examples & legacy (`examples/`, `scripts/`, `website/`): reference-only assets for now.

Recommended minimal structure

```
AIAgents-Clone/
  apps/
    agency-web/        # Next.js app (intake, admin, demos)
  src/
    client_config/     # Pydantic models + mapping functions
      models.py
      mapping.py
    agency/            # product agents that consume ClientConfig
      support_agent.py
      content_agent.py
      ...
    domain/             # core engine (leave as-is)
    application/        # core orchestrator (leave as-is)
    infrastructure/     # provider implementations (leave as-is)
  docs/
    ARCHITECTURE_AGENCY.md
    IMPLEMENTATION_PLAN.md
  prisma/               # keep for TypeScript API (if needed)
  website/              # static marketing site (optional merge later)
```

Practical next steps (zero-risk)

1. Create `docs/ARCHITECTURE_AGENCY.md` (this file) and add the high-level plan.
2. Add `src/client_config/models.py` and `src/client_config/mapping.py` with explicit Pydantic models and a single mapping function `build_client_config_from_intake`.
3. Keep your Next.js intake and Prisma-based persistence if you prefer — have the Next.js app POST to a product API (Python or Node) that calls the mapping function and persists the `ClientConfig`.
4. Defer refactors of `src/domain` and `src/infrastructure` until the agency product has shipped an initial demo.

When to reorganize files physically

- You don't need to move everything now. Start by introducing `src/client_config` and documenting the architecture. Once product components stabilize, you can perform a physical re-org into `apps/` and `packages/`.

This doc is intentionally concise. Use it as the anchor for future pull requests: if a change touches core vs product, reference this doc and the relevant layer.
