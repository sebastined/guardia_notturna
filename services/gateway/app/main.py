"""Guardia Notturna gateway.

Front door for the platform: terminates auth, then fans requests out to the
scan, enrich and detect services. Only routing and identity live here - no
scanning logic.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gn_schemas import Actor

from .auth import Role, current_actor, require_role
from .config import settings

app = FastAPI(
    title="Guardia Notturna Gateway",
    version="0.1.0",
    description="Authenticated entry point for the Guardia Notturna platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness probe. Unauthenticated by design."""
    return {"status": "ok", "env": settings.env}


@app.get("/me", tags=["auth"])
def me(actor: Actor = Depends(current_actor)) -> Actor:
    """Echo the caller's resolved identity. Useful for debugging tokens."""
    return actor


@app.get("/admin/ping", tags=["auth"])
def admin_ping(actor: Actor = Depends(require_role(Role.ADMIN))) -> dict[str, str]:
    """Placeholder proving the RBAC dependency chain works end to end."""
    return {"pong": actor.subject}
