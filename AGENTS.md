# Outfit-AI Agent Instructions

Before implementation, read:

1. `CLAUDE.md` for project rules and architecture.
2. `docs/SPEC.md` for the current backend and API contract.
3. `docs/frontend/CURRENT_FRONTEND_INTEGRATION.md` for the current frontend, screens, entry points, and API mapping.

The frontend baseline is the user-approved Google AI Studio / Stitch ZIP, now migrated to `frontend/src`. Do not rebuild it from archived PRDs or restore the old uni-app/Vue implementation.

Documentation is part of every change. In the same commit, update the relevant current document whenever code changes a screen, navigation path, interaction, API route or payload, data model, runtime command, dependency, or architecture decision. A code change with stale current documentation is incomplete.

Keep MiniMax credentials in the backend only. Never write keys to frontend code, documentation, logs, or commits.
