import json
from pathlib import Path

import pytest

from tools.exportar_ipynb import blocos, celula
from tools.rodar_local import celulas

RAIZ = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((RAIZ / "fabric").glob("*.Notebook"))


def test_cinco_notebooks():
    assert [n.name for n in NOTEBOOKS] == ["nb_00_orquestrador.Notebook", "nb_01_bronze_ingestao.Notebook",
                                           "nb_02_silver_tratamento.Notebook", "nb_03_gold_modelo.Notebook",
                                           "nb_04_publicar_modelo.Notebook"]


@pytest.mark.parametrize("pasta", NOTEBOOKS, ids=lambda p: p.name)
def test_formato_fabric(pasta):
    texto = (pasta / "notebook-content.py").read_text(encoding="utf-8")
    assert texto.startswith("# Fabric notebook source\n")
    tipos = [t for t, _ in celulas(pasta / "notebook-content.py")]
    assert tipos.count("PARAMETERS CELL") == 1 and tipos[0] == "PARAMETERS CELL"
    plataforma = json.loads((pasta / ".platform").read_text())
    assert plataforma["metadata"] == {"type": "Notebook", "displayName": pasta.name.removesuffix(".Notebook")}


@pytest.mark.parametrize("pasta", NOTEBOOKS, ids=lambda p: p.name)
def test_codigo_compila(pasta):
    for _, codigo in celulas(pasta / "notebook-content.py"):
        compile(codigo, pasta.name, "exec")


@pytest.mark.parametrize("pasta", NOTEBOOKS, ids=lambda p: p.name)
def test_ipynb_em_dia(pasta):
    nome = pasta.name.removesuffix(".Notebook")
    gerado = json.loads((RAIZ / "fabric" / "ipynb" / f"{nome}.ipynb").read_text(encoding="utf-8"))
    esperado = [celula(t, l) for t, l in blocos((pasta / "notebook-content.py").read_text(encoding="utf-8"))]
    assert [{k: v for k, v in c.items() if k != "id"} for c in gerado["cells"]] == esperado
