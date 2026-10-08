"""Checagens estruturais do modelo semântico (não há parser oficial de TMDL fora do .NET)."""
import json
import re
from pathlib import Path

import pytest

from tools import gerar_modelo as gm

RAIZ = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((RAIZ / "tools" / "schema_gold.json").read_text())
COLUNAS = {(t, c) for t, cols in SCHEMA.items() for c, _ in cols}
MEDIDAS = [(t, *m) for t, lista in gm.MEDIDAS.items() for m in lista]
NOMES_MEDIDAS = {m[1] for m in MEDIDAS}


def test_nomes_de_medida_unicos():
    assert len(NOMES_MEDIDAS) == len(MEDIDAS)


def test_medida_nao_colide_com_coluna():
    assert not NOMES_MEDIDAS & {c for _, c in COLUNAS}


@pytest.mark.parametrize("tabela,nome,pasta,formato,dax", MEDIDAS, ids=[m[1] for m in MEDIDAS])
def test_referencias_do_dax_existem(tabela, nome, pasta, formato, dax):
    sem_texto = re.sub(r'"[^"]*"', '""', re.sub(r"//[^\n]*", "", dax))
    for t, c in re.findall(r"(\w+)\[([^\]]+)\]", sem_texto):
        assert (t, c) in COLUNAS, f"{t}[{c}] não existe"
    for m in re.findall(r"(?<![\w\]])\[([^\]]+)\]", sem_texto):
        assert m in NOMES_MEDIDAS, f"[{m}] não é medida"
    assert sem_texto.count("(") == sem_texto.count(")"), "parênteses desbalanceados"
    assert tabela in SCHEMA


def test_medida_nao_se_referencia():
    for _, nome, _, _, dax in MEDIDAS:
        assert f"[{nome}]" not in dax


def test_relacionamentos_e_ordenacao_apontam_para_colunas_reais():
    for de, para, _ in gm.RELACIONAMENTOS:
        assert tuple(de.split(".")) in COLUNAS and tuple(para.split(".")) in COLUNAS
    for (t, c), por in gm.ORDENAR_POR.items():
        assert (t, c) in COLUNAS and (t, por) in COLUNAS
    for t, ocultas in gm.OCULTAS.items():
        assert {(t, c) for c in ocultas} <= COLUNAS


def test_um_unico_caminho_ativo_entre_tabelas():
    pares = [tuple(sorted((d.split(".")[0], p.split(".")[0]))) for d, p, ativo in gm.RELACIONAMENTOS if ativo]
    assert len(pares) == len(set(pares))


def test_tmdl_gerado_esta_em_dia(tmp_path):
    gm.gerar(destino=tmp_path)
    for arquivo in tmp_path.rglob("*"):
        if arquivo.is_file():
            atual = gm.DESTINO / arquivo.relative_to(tmp_path)
            texto = atual.read_text()
            if arquivo.name == "expressions.tmdl":
                texto = re.sub(r'Sql\.Database\("[^"]*", "[^"]*"\)',
                               f'Sql.Database("{gm.ENDPOINT}", "{gm.ENDPOINT_ID}")', texto)
            assert texto == arquivo.read_text(), f"{atual} desatualizado"


def test_tmdl_bem_formado():
    for arquivo in (gm.DESTINO / "definition").rglob("*.tmdl"):
        texto = arquivo.read_text()
        assert texto.count("```") % 2 == 0, f"bloco ``` aberto em {arquivo.name}"
        for linha in texto.splitlines():
            assert not linha.startswith(" "), f"recuo com espaço em {arquivo.name}: {linha!r}"


def test_nada_que_o_direct_lake_recuse():
    for arquivo in (gm.DESTINO / "definition").rglob("*.tmdl"):
        texto = arquivo.read_text()
        assert "joinOnDateBehavior" not in texto, arquivo.name
        assert "mode: import" not in texto, arquivo.name


def test_um_papel_por_portfolio():
    from simulador.catalogos import PORTFOLIOS
    assert sorted(gm.PAPEIS.values()) == sorted(e.nome for e in PORTFOLIOS)
    modelo = (gm.DESTINO / "definition" / "model.tmdl").read_text()
    for nome, portfolio in gm.PAPEIS.items():
        texto = (gm.DESTINO / "definition" / "roles" / f"{nome}.tmdl").read_text()
        assert texto.startswith(f"role {nome}\n") and f'[portfolio] = "{portfolio}"' in texto
        assert f"ref role {nome}" in modelo
        assert nome.isidentifier() and nome.isascii()


def test_format_string_com_aspas_escapado():
    for arquivo in (gm.DESTINO / "definition" / "tables").glob("*.tmdl"):
        for linha in arquivo.read_text().splitlines():
            valor = linha.strip().removeprefix("formatString: ")
            if linha.strip().startswith("formatString:") and '"' in valor:
                miolo = valor[1:-1]
                assert valor[0] == valor[-1] == '"' and '"' not in miolo.replace('""', ''), linha
