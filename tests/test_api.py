import pytest
from fastapi.testclient import TestClient

from api.app import criar_app
from simulador.cenario import Config

TOKEN = "token-teste"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(scope="module")
def cliente():
    return TestClient(criar_app(Config(), token=TOKEN, taxa_falha=0.0))


def test_saude_sem_token(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}


@pytest.mark.parametrize("cabecalho", [{}, {"Authorization": "Bearer errado"}])
def test_exige_token(cliente, cabecalho):
    assert cliente.get("/v1/tarefas", headers=cabecalho).status_code == 401


def test_meta(cliente):
    meta = cliente.get("/v1/meta", headers=AUTH).json()
    assert meta["data_referencia"] == "2026-09-30" and meta["totais"]["tarefas"] > 1000
    assert meta["impressao_digital"] == "28e6c08d8addd5f4"


def test_paginacao_percorre_tudo_sem_repetir(cliente):
    ids, url = [], "/v1/tarefas?tamanho=250"
    while url:
        corpo = cliente.get(url, headers=AUTH).json()
        ids += [t["id"] for t in corpo["dados"]]
        url = corpo["proxima"]
    assert len(ids) == len(set(ids)) == corpo["total"]


def test_tamanho_maximo(cliente):
    assert cliente.get("/v1/tarefas?tamanho=501", headers=AUTH).status_code == 422


def test_incremental(cliente):
    desde = "2026-09-01T00:00:00-03:00"
    corpo = cliente.get("/v1/tarefas", params={"atualizado_desde": desde, "tamanho": 500},
                        headers=AUTH).json()
    assert 0 < corpo["total"] < 500
    assert all(t["atualizado_em"] > "2026-09-01" for t in corpo["dados"])


def test_incremental_exige_fuso(cliente):
    r = cliente.get("/v1/tarefas", params={"atualizado_desde": "2026-09-01T00:00:00"}, headers=AUTH)
    assert r.status_code == 400


def test_incremental_recusado_em_cadastro_sem_data(cliente):
    r = cliente.get("/v1/usuarios", params={"atualizado_desde": "2026-09-01T00:00:00-03:00"},
                    headers=AUTH)
    assert r.status_code == 400


def test_proxima_preserva_filtro(cliente):
    corpo = cliente.get("/v1/movimentacoes", params={"atualizado_desde": "2026-01-01T00:00:00-03:00",
                                                 "tamanho": 50}, headers=AUTH).json()
    assert "atualizado_desde" in corpo["proxima"] and "pagina=2" in corpo["proxima"]


def test_limite_de_requisicoes():
    cliente = TestClient(criar_app(Config(), token=TOKEN, taxa_falha=1.0))
    r = cliente.get("/v1/portfolios", headers=AUTH)
    assert r.status_code == 429 and r.headers["Retry-After"] == "1"
    assert cliente.get("/saude").status_code == 200
