"""Roda os notebooks de verdade (Spark local) e confere a gold contra contas feitas à mão.

Lento (~1 min) e precisa de pyspark + Java: `pytest -m pipeline`. Fica fora da rodada padrão.
"""
import json
from collections import Counter
from datetime import date

import pytest

pytest.importorskip("pyspark")
pytestmark = pytest.mark.pipeline

from simulador.cenario import Config, gerar  # noqa: E402
from tools.rodar_local import Executor, criar_spark, subir_api  # noqa: E402

REF = date(2026, 9, 30)
FINAIS = {"Concluída", "Cancelada"}


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("lakehouse")
    (pasta / "Files").mkdir()
    url = subir_api(REF, "t", taxa_falha=0.2)
    spark = criar_spark(pasta)
    executor = Executor(spark, {"PASTA_ARQUIVOS": str(pasta / "Files"),
                                "PASTA_ARQUIVOS_SPARK": str(pasta / "Files"),
                                "FORMATO_TABELA": "parquet"})
    executor.rodar("nb_00_orquestrador", parametros={"URL_API": url, "TOKEN_API": "t", "MODO": "completo"})
    return spark, executor, pasta, gerar(Config(data_referencia=REF))


def contar(spark, sql: str) -> dict:
    return {tuple(r)[0]: tuple(r)[1] for r in spark.sql(sql).collect()}


def test_status_das_tarefas(ambiente):
    spark, _, _, dados = ambiente
    esperado = Counter(t["status"] for t in dados["tarefas"])
    assert contar(spark, "SELECT status, count(*) FROM fato_tarefa GROUP BY 1") == esperado


def test_situacao_de_prazo_das_tarefas(ambiente):
    spark, _, _, dados = ambiente

    def situacao(t):
        if t["status"] == "Cancelada":
            return "Cancelada"
        if t["prazo"] is None:
            return "Sem prazo"
        if t["status"] == "Concluída":
            return "Concluída no prazo" if t["concluida_em"][:10] <= t["prazo"] else "Concluída com atraso"
        return "Vencida" if t["prazo"] < REF.isoformat() else "No prazo"

    esperado = Counter(situacao(t) for t in dados["tarefas"])
    assert contar(spark, "SELECT situacao_prazo, count(*) FROM fato_tarefa GROUP BY 1") == esperado


def test_retrabalho_e_bloqueios(ambiente):
    spark, _, _, dados = ambiente
    eventos = dados["historico"]
    retrabalho = sum(e["status_anterior"] == "Em Revisão" and e["status_novo"] == "Em Andamento" for e in eventos)
    bloqueios = sum(e["status_novo"] == "Bloqueada" for e in eventos)
    linha = spark.sql("SELECT sum(qtd_retrabalho), sum(qtd_bloqueios) FROM fato_tarefa").first()
    assert (linha[0], linha[1]) == (retrabalho, bloqueios)


def test_horas(ambiente):
    spark, _, _, dados = ambiente
    linha = spark.sql("SELECT sum(estimativa_horas), round(sum(horas_apontadas), 1) FROM fato_tarefa").first()
    assert linha[0] == sum(t["estimativa_horas"] for t in dados["tarefas"])
    assert linha[1] == pytest.approx(sum(t["horas_apontadas"] for t in dados["tarefas"]), abs=0.05)


def test_projetos_atrasados(ambiente):
    spark, _, _, dados = ambiente
    vivos = [p for p in dados["projetos"] if p["status"] in ("Em Andamento", "Planejamento")]
    atrasados = sum(p["data_fim_planejada"] < REF.isoformat() for p in vivos)
    assert contar(spark, "SELECT situacao_prazo, count(*) FROM dim_projeto GROUP BY 1").get("Atrasado", 0) == atrasados


def test_horario_de_brasilia(ambiente):
    spark, _, _, dados = ambiente
    t = dados["tarefas"][0]
    criada = spark.sql(f"SELECT date_format(criada_em, 'yyyy-MM-dd HH:mm') FROM fato_tarefa "
                       f"WHERE tarefa_id = '{t['id']}'").first()[0]
    assert criada == t["criada_em"][:16].replace("T", " ")


def test_textos_padronizados(ambiente):
    spark, *_ = ambiente
    assert set(contar(spark, "SELECT prioridade, count(*) FROM fato_tarefa GROUP BY 1")) <= \
        {"Baixa", "Média", "Alta", "Crítica"}
    assert spark.sql("SELECT count(*) FROM fato_tarefa WHERE titulo <> trim(titulo) OR titulo LIKE '%  %'").first()[0] == 0


def test_quarentena(ambiente):
    """Registros que quebram regras vão para silver_rejeitados com o motivo; o resto segue."""
    spark, executor, pasta, dados = ambiente
    boa = dados["tarefas"][0]
    ruins = [
        boa | {"id": "TSK-99901", "status": "Em Pausa"},
        boa | {"id": "TSK-99902", "projeto_id": "PRJ-999"},
        boa | {"id": "TSK-99903", "horas_apontadas": -3},
    ]
    destino = pasta / "Files" / "bronze" / "tarefas" / "data_carga=2026-10-01" / "20261001T000000Z_p0001.json"
    destino.parent.mkdir(parents=True)
    destino.write_text(json.dumps({"dados": ruins, "proxima": None, "_execucao": "20261001T000000Z"}))
    try:
        executor.rodar("nb_02_silver_tratamento")
        motivos = contar(spark, "SELECT id, motivo FROM silver_rejeitados")
        assert motivos == {"TSK-99901": "status de tarefa desconhecido",
                           "TSK-99902": "projeto_id sem correspondente",
                           "TSK-99903": "horas negativas"}
        assert spark.table("silver_tarefas").count() == len(dados["tarefas"])
    finally:
        destino.unlink()
        executor.rodar("nb_02_silver_tratamento")


def test_exclusao_na_fonte_some_da_silver(ambiente):
    """Pessoas chegam completas a cada carga: quem sumiu da última carga sai da silver."""
    spark, executor, pasta, dados = ambiente
    sem_tarefa = {p["id"] for p in dados["pessoas"]} - {t["responsavel_id"] for t in dados["tarefas"]} \
        - {e["pessoa_id"] for e in dados["historico"]} - {p["gestor_id"] for p in dados["projetos"]} \
        - {e["gestor_id"] for e in dados["equipes"]}
    removida = sorted(sem_tarefa)[0]
    restantes = [p for p in dados["pessoas"] if p["id"] != removida]
    destino = pasta / "Files" / "bronze" / "pessoas" / "data_carga=2099-01-01" / "20990101T000000Z_p0001.json"
    destino.parent.mkdir(parents=True)
    destino.write_text(json.dumps({"dados": restantes, "proxima": None, "_execucao": "20990101T000000Z"}))
    try:
        executor.rodar("nb_02_silver_tratamento")
        ids = {r[0] for r in spark.sql("SELECT id FROM silver_pessoas").collect()}
        assert removida not in ids and len(ids) == len(dados["pessoas"]) - 1
    finally:
        destino.unlink()
        executor.rodar("nb_02_silver_tratamento")


def test_schema_da_gold_igual_ao_do_modelo(ambiente):
    """O modelo semântico é gerado de tools/schema_gold.json; se a gold mudar, regenere os dois."""
    from pathlib import Path
    spark, *_ = ambiente
    salvo = json.loads((Path(__file__).resolve().parents[1] / "tools" / "schema_gold.json").read_text())
    for tabela, colunas in salvo.items():
        real = [[f.name, f.dataType.simpleString()] for f in spark.table(tabela).schema]
        assert real == colunas, f"{tabela} mudou: rode tools/rodar_local.py e atualize schema_gold.json"


def test_medidas_conferem_com_calculo_independente(ambiente):
    """As colunas que o DAX soma/média na gold batem com o recálculo independente de valores_esperados."""
    from tools.valores_esperados import SQL
    spark, *_ = ambiente
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    pela_gold = {
        "Idade Média das Abertas (dias)": "SELECT avg(idade_dias) FROM fato_tarefa",
        "Dias Bloqueada": "SELECT sum(dias_bloqueada) FROM fato_tarefa",
        "Lead Time Médio (dias)": "SELECT avg(lead_time_dias) FROM fato_tarefa",
        "% Entregues no Prazo": """SELECT sum(int(situacao_prazo = 'Concluída no prazo'))
            / sum(int(situacao_prazo IN ('Concluída no prazo', 'Concluída com atraso'))) FROM fato_tarefa""",
        "% Concluídas com Retrabalho": "SELECT avg(int(qtd_retrabalho > 0)) FROM fato_tarefa WHERE status = 'Concluída'",
        "Tarefas Paradas na Etapa": """SELECT count(DISTINCT tarefa_id) FROM fato_passagem_status
            WHERE etapa_atual AND NOT etapa_final""",
        "Paradas há mais de 15 dias": """SELECT count(DISTINCT tarefa_id) FROM fato_passagem_status
            WHERE etapa_atual AND NOT etapa_final AND dias_na_etapa > 15""",
        "Tempo Médio na Etapa (dias)": "SELECT avg(dias_na_etapa) FROM fato_passagem_status WHERE NOT etapa_atual",
        "Tarefas Vencidas": "SELECT count(*) FROM fato_tarefa WHERE situacao_prazo = 'Vencida'",
        "Projetos Atrasados": "SELECT count(*) FROM dim_projeto WHERE situacao_prazo = 'Atrasado'",
    }
    for nome, consulta in pela_gold.items():
        a, b = spark.sql(consulta).first()[0], spark.sql(SQL[nome]).first()[0]
        assert float(a) == pytest.approx(float(b), abs=0.006), nome
