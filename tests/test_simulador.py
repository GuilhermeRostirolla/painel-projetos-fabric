from collections import Counter
from datetime import date

import numpy as np
import pytest

from simulador import catalogos as cat
from simulador.cenario import Config, gerar
from simulador.fluxo import Corte, simular
from simulador.tempo import avancar, no_expediente
from simulador.validar import problemas


@pytest.fixture(scope="module")
def dados():
    return gerar(Config())


def test_cenario_sem_problemas(dados):
    assert problemas(dados, Config().data_referencia) == []


@pytest.mark.parametrize("semente", [1, 7, 123, 2024])
def test_outras_sementes_tambem_coerentes(semente):
    cfg = Config(semente=semente)
    assert problemas(gerar(cfg), cfg.data_referencia) == []


def test_mesma_semente_mesmo_cenario(dados):
    assert gerar(Config()) == dados


def test_semente_diferente_muda_cenario(dados):
    assert gerar(Config(semente=43))["tarefas"] != dados["tarefas"]


def test_portfolio_tem_todos_os_status_de_projeto():
    vistos = set()
    for semente in (42, 7, 123):
        vistos |= {p["status"] for p in gerar(Config(semente=semente))["projetos"]}
    assert vistos == {"Planejamento", "Em Andamento", "Pausado", "Cancelado", "Concluído"}


def test_tarefas_abertas_em_todas_as_etapas(dados):
    status = Counter(t["status"] for t in dados["tarefas"])
    assert set(status) == {s.nome for s in cat.STATUS}


def test_proporcao_de_atraso_plausivel(dados):
    com_prazo = [t for t in dados["tarefas"] if t["concluida_em"] and t["prazo"]]
    atrasadas = sum(t["concluida_em"][:10] > t["prazo"] for t in com_prazo)
    assert 0.10 < atrasadas / len(com_prazo) < 0.35


def test_horas_so_em_tarefas_iniciadas(dados):
    iniciadas = {e["tarefa_id"] for e in dados["historico"] if e["status_novo"] == cat.EM_ANDAMENTO}
    for t in dados["tarefas"]:
        if t["id"] not in iniciadas:
            assert t["horas_apontadas"] == 0


def test_projeto_cancelado_nao_tem_tarefa_aberta(dados):
    cancelados = {p["id"] for p in dados["projetos"] if p["status"] == "Cancelado"}
    for t in dados["tarefas"]:
        if t["projeto_id"] in cancelados:
            assert t["status"] in cat.STATUS_FINAIS


def test_sujeira_proposital_presente(dados):
    assert any(t["prioridade"] not in cat.PRIORIDADES for t in dados["tarefas"])
    assert any(t["titulo"] != t["titulo"].strip() for t in dados["tarefas"])


def test_datas_com_fuso(dados):
    assert all(t["atualizado_em"].endswith("-03:00") for t in dados["tarefas"])


def test_avancar_sempre_em_dia_util_e_depois():
    rng = np.random.default_rng(0)
    momento = no_expediente(date(2026, 1, 2), rng)
    for _ in range(500):
        novo = avancar(momento, float(rng.uniform(0, 5)), rng)
        assert novo > momento and novo.weekday() < 5 and 8 <= novo.hour < 18
        momento = novo


def test_corte_cancela_tarefa_aberta():
    rng = np.random.default_rng(1)
    criada = no_expediente(date(2026, 3, 2), rng)
    corte = Corte(no_expediente(date(2026, 3, 4), rng), cancelar=True)
    trajeto = simular(rng, criada, 40, 1.0, 1.0, no_expediente(date(2026, 9, 30), rng), corte)
    assert trajeto.status == cat.CANCELADA and trajeto.momento == corte.quando


def test_relogio_andando_nao_muda_o_passado(dados):
    antes = gerar(Config(data_referencia=date(2026, 8, 31)))
    eventos_depois = {e["id"]: e for e in dados["historico"]}
    assert all(eventos_depois[e["id"]] == e for e in antes["historico"])
    tarefas_depois = {t["id"]: t for t in dados["tarefas"]}
    for t in antes["tarefas"]:
        depois = tarefas_depois[t["id"]]
        assert (t["titulo"], t["criada_em"], t["projeto_id"]) == (depois["titulo"], depois["criada_em"], depois["projeto_id"])
        if t != depois:
            assert depois["atualizado_em"] > "2026-09-01"
    projetos_depois = {p["id"]: p for p in dados["projetos"]}
    for p in antes["projetos"]:
        if p != projetos_depois[p["id"]]:
            assert projetos_depois[p["id"]]["atualizado_em"] > "2026-09-01"
    assert len(antes["tarefas"]) < len(dados["tarefas"])


def test_impressao_digital_travada(dados):
    from simulador.cenario import impressao_digital
    assert impressao_digital(dados) == "f5e3d8e3c86d9d89"
