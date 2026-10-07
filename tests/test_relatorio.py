"""Checagens estruturais do relatório PBIR gerado."""
import json
from itertools import combinations
from pathlib import Path

import pytest

from tools import gerar_relatorio as gr
from tools.gerar_modelo import MEDIDAS

RAIZ = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((RAIZ / "tools" / "schema_gold.json").read_text())
COLUNAS = {(t, c) for t, cols in SCHEMA.items() for c, _ in cols}
MEDIDA_TABELA = {m[0]: t for t, ms in MEDIDAS.items() for m in ms}
PAGINAS = gr.paginas()
VISUAIS = [(p.nome, v) for p in PAGINAS for v in p.visuais]


def _campos(no):
    if isinstance(no, dict):
        for tipo in ("Column", "Measure"):
            if tipo in no and "Property" in no[tipo] and "Entity" in no[tipo]["Expression"]["SourceRef"]:
                yield tipo, no[tipo]["Expression"]["SourceRef"]["Entity"], no[tipo]["Property"]
        for valor in no.values():
            yield from _campos(valor)
    elif isinstance(no, list):
        for valor in no:
            yield from _campos(valor)


@pytest.mark.parametrize("pagina,visual", VISUAIS, ids=[f"{p}/{v['name']}" for p, v in VISUAIS])
def test_campos_existem_no_modelo(pagina, visual):
    for tipo, tabela, nome in _campos(visual):
        if tipo == "Column":
            assert (tabela, nome) in COLUNAS, f"{tabela}[{nome}] não existe"
        else:
            assert MEDIDA_TABELA.get(nome) == tabela, f"medida [{nome}] não está em {tabela}"


def test_nomes_de_visual_unicos():
    nomes = [v["name"] for _, v in VISUAIS]
    assert len(nomes) == len(set(nomes))


def _caixa(v):
    pos = v["position"]
    return pos["x"], pos["y"], pos["x"] + pos["width"], pos["y"] + pos["height"]


def _sobrepoe(a, b):
    return a[0] < b[2] - 0.5 and b[0] < a[2] - 0.5 and a[1] < b[3] - 0.5 and b[1] < a[3] - 0.5


def _contem(fora, dentro):
    return fora[0] <= dentro[0] + 0.5 and fora[1] <= dentro[1] + 0.5 and \
        fora[2] >= dentro[2] - 0.5 and fora[3] >= dentro[3] - 0.5


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.nome)
def test_cabe_na_pagina_e_nao_sobrepoe(pagina):
    for v in pagina.visuais:
        x0, y0, x1, y1 = _caixa(v)
        assert x0 >= 0 and y0 >= 0
        assert x1 <= gr.LARGURA + 0.5 and y1 <= gr.ALTURA + 0.5, v["name"]
    for a, b in combinations(pagina.visuais, 2):
        ca, cb = _caixa(a), _caixa(b)
        if not _sobrepoe(ca, cb):
            continue
        fundo_a, fundo_b = a["name"] in pagina.fundos, b["name"] in pagina.fundos
        assert fundo_a or fundo_b, f"visuais sobrepostos em {pagina.nome}: {ca} x {cb}"
        assert (fundo_a and _contem(ca, cb)) or (fundo_b and _contem(cb, ca)), \
            f"visual atravessa a borda de um painel em {pagina.nome}: {ca} x {cb}"
        if fundo_a and fundo_b:
            continue
        painel, dentro = (a, b) if fundo_a else (b, a)
        assert painel["position"]["z"] < dentro["position"]["z"]


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.nome)
def test_cartoes_tem_contexto(pagina):
    cartoes = [v for v in pagina.visuais if v["visual"]["visualType"] == "multiRowCard"
               and v["position"]["y"] >= 92 and v["position"]["height"] >= 30]
    assert len(cartoes) == 6
    for c in cartoes:
        embaixo = [v for v in pagina.visuais if abs(v["position"]["x"] - c["position"]["x"]) < 5
                   and 0 < v["position"]["y"] - c["position"]["y"] < 50 and v["name"] not in pagina.fundos]
        assert embaixo, f"cartão sem contexto em {pagina.nome}"


def test_relatorio_gerado_esta_em_dia(tmp_path):
    gr.gerar(tmp_path)
    gerados = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    atuais = sorted(p.relative_to(gr.DESTINO) for p in gr.DESTINO.rglob("*") if p.is_file())
    assert gerados == atuais
    for caminho in gerados:
        assert (tmp_path / caminho).read_bytes() == (gr.DESTINO / caminho).read_bytes(), caminho


def test_json_valido_e_referencias_de_tema():
    for arquivo in gr.DESTINO.rglob("*.json"):
        json.loads(arquivo.read_text(encoding="utf-8"))
    relatorio = json.loads((gr.DESTINO / "definition" / "report.json").read_text())
    for pacote in relatorio["resourcePackages"]:
        for item in pacote["items"]:
            assert (gr.DESTINO / "StaticResources" / pacote["name"] / item["path"]).exists(), item["path"]
