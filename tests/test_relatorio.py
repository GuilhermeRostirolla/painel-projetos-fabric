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
            if tipo in no and "Property" in no[tipo]:
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


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.nome)
def test_cabe_na_pagina_e_nao_sobrepoe(pagina):
    caixas = []
    for v in pagina.visuais:
        pos = v["position"]
        assert pos["x"] >= 0 and pos["y"] >= 0
        assert pos["x"] + pos["width"] <= gr.LARGURA + 0.5 and pos["y"] + pos["height"] <= gr.ALTURA + 0.5, v["name"]
        caixas.append((pos["x"], pos["y"], pos["x"] + pos["width"], pos["y"] + pos["height"]))
    for a, b in combinations(caixas, 2):
        sobrepoe = a[0] < b[2] - 0.5 and b[0] < a[2] - 0.5 and a[1] < b[3] - 0.5 and b[1] < a[3] - 0.5
        assert not sobrepoe, f"visuais sobrepostos em {pagina.nome}: {a} x {b}"


def test_relatorio_gerado_esta_em_dia(tmp_path):
    """fabric/PainelProjetos.Report é gerado: se falhar, rode python -m tools.gerar_relatorio"""
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
