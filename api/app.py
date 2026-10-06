"""API REST que imita uma ferramenta de gestão de projetos (estilo Jira/Asana).

Os dados vêm do simulador, gerados uma vez quando a API sobe. Comportamentos de uma
API real que a ingestão precisa tratar:
  - autenticação por token (cabeçalho Authorization: Bearer <token>)
  - paginação (pagina, tamanho) com link para a próxima página
  - carga incremental (atualizado_desde)
  - limite de requisições: parte das chamadas devolve 429 com Retry-After

Variáveis de ambiente: API_TOKEN, SEMENTE, DATA_REFERENCIA (AAAA-MM-DD), TAXA_FALHA (0 a 1).
"""
import os
import random
from datetime import date, datetime
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from simulador.cenario import Config, gerar, impressao_digital
from simulador.validar import exigir

VERSAO = "1.0.0"
TAMANHO_PADRAO, TAMANHO_MAXIMO = 100, 500


def _config() -> Config:
    ref = os.environ.get("DATA_REFERENCIA")
    return Config(semente=int(os.environ.get("SEMENTE", 42)),
                  data_referencia=date.fromisoformat(ref) if ref else Config.data_referencia)


def criar_app(cfg: Config | None = None, token: str | None = None,
              taxa_falha: float | None = None) -> FastAPI:
    cfg = cfg or _config()
    token = token or os.environ.get("API_TOKEN", "token-demo")
    taxa_falha = float(os.environ.get("TAXA_FALHA", 0.03)) if taxa_falha is None else taxa_falha
    dados = gerar(cfg)
    exigir(dados, cfg.data_referencia)
    assinatura = impressao_digital(dados)
    sorteio = random.Random()

    app = FastAPI(title="API de Projetos (simulada)", version=VERSAO,
                  description="Fonte de dados do Painel de Projetos. Dados 100% fictícios.")
    seguranca = HTTPBearer(auto_error=False)

    def autenticar(cred: HTTPAuthorizationCredentials | None = Depends(seguranca)) -> None:
        if cred is None or cred.credentials != token:
            raise HTTPException(401, "token ausente ou inválido",
                                headers={"WWW-Authenticate": "Bearer"})

    @app.middleware("http")
    async def limite_de_requisicoes(request: Request, chamar):
        if request.url.path.startswith("/v1/") and sorteio.random() < taxa_falha:
            return JSONResponse({"detail": "muitas requisições, tente de novo"},
                                status_code=429, headers={"Retry-After": "1"})
        return await chamar(request)

    def paginar(request: Request, linhas: list[dict], campo_data: str | None,
                pagina: int, tamanho: int, atualizado_desde: datetime | None) -> dict:
        if atualizado_desde is not None:
            if campo_data is None:
                raise HTTPException(400, "este recurso não aceita atualizado_desde")
            if atualizado_desde.tzinfo is None:
                raise HTTPException(400, "atualizado_desde precisa de fuso, ex.: 2026-01-01T00:00:00-03:00")
            linhas = [l for l in linhas if datetime.fromisoformat(l[campo_data]) > atualizado_desde]
        total = len(linhas)
        inicio = (pagina - 1) * tamanho
        proxima = None
        if inicio + tamanho < total:
            params = dict(request.query_params) | {"pagina": pagina + 1, "tamanho": tamanho}
            proxima = f"{request.url.path}?{urlencode(params)}"
        return {"dados": linhas[inicio:inicio + tamanho], "pagina": pagina,
                "tamanho": tamanho, "total": total, "proxima": proxima}

    def recurso(nome: str, campo_data: str | None):
        def listar(request: Request,
                   pagina: int = Query(1, ge=1),
                   tamanho: int = Query(TAMANHO_PADRAO, ge=1, le=TAMANHO_MAXIMO),
                   atualizado_desde: datetime | None = Query(None),
                   _: None = Depends(autenticar)):
            return paginar(request, dados[nome], campo_data, pagina, tamanho, atualizado_desde)
        listar.__name__ = f"listar_{nome}"
        return listar

    for nome, campo in (("equipes", None), ("pessoas", None), ("projetos", "atualizado_em"),
                        ("tarefas", "atualizado_em"), ("historico", "ocorrido_em")):
        app.get(f"/v1/{nome}", tags=["dados"])(recurso(nome, campo))

    @app.get("/v1/meta", tags=["dados"])
    def meta(_: None = Depends(autenticar)):
        return {"versao": VERSAO, "data_referencia": cfg.data_referencia.isoformat(),
                "semente": cfg.semente, "impressao_digital": assinatura, "totais": {k: len(v) for k, v in dados.items()}}

    @app.get("/saude", tags=["infra"])
    def saude():
        return {"status": "ok"}

    return app
