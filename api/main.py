# api/main.py

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from modules.search.advanced_search import search_multiple_sources
from core.api_tokens import verify_api_token

app = FastAPI(
    title="QuasarIII API",
    version="0.1.0",
    description="API interna de QuasarIII para búsquedas OSINT autenticadas por token",
)


class SearchRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = None
    email: Optional[str] = None
    username: Optional[str] = None
    user_id: int


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/search")
def api_search(
    req: SearchRequest,
    x_api_token: str = Header(None, alias="X-API-Token"),
):
    """
    Endpoint principal de búsqueda para uso por herramientas externas.

    Autenticación:
      - Header: X-API-Token: <token_del_usuario>
      - Body: user_id debe ser el dueño del token

    Flujo:
      1) Verifica token
      2) Ejecuta search_multiple_sources con los mismos parámetros que usa la UI
    """
    if not x_api_token:
        raise HTTPException(status_code=401, detail="Missing X-API-Token header")

    if not verify_api_token(req.user_id, x_api_token):
        raise HTTPException(status_code=401, detail="Invalid API token or user_id")

    results = search_multiple_sources(
        query=req.query,
        selected_sources=req.sources or [],
        email=req.email or "",
        username=req.username,
        user_id=req.user_id,
    )

    return results

# Si quisieras lanzarla manualmente (sin app.py):
# uvicorn api.main:app --host 0.0.0.0 --port 8081
