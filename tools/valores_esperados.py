"""Recalcula cada medida do modelo semântico em SQL, direto na gold, e grava a tabela de conferência.

É uma segunda implementação, independente do DAX: no Power BI, cada cartão tem que bater com
docs/valores_esperados.md (sem filtros, e no mês indicado para as medidas de período).

    python tools/rodar_local.py --limpar        # gera a gold local
    python tools/valores_esperados.py           # escreve docs/valores_esperados.md
"""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from tools.gerar_modelo import MEDIDAS, PAPEIS  # noqa: E402

MES = "2026-09"  # mês usado nas medidas de período
MES_ANO = "set/26"  # o mesmo mês como aparece em dim_data[mes_ano]
FINAIS = "('Concluída', 'Cancelada')"
SQL = {
    "Projetos": "SELECT count(*) FROM dim_projeto",
    "Projetos Ativos": "SELECT count(*) FROM dim_projeto WHERE status IN ('Em Andamento', 'Planejamento')",
    "Projetos em Andamento": "SELECT count(*) FROM dim_projeto WHERE status = 'Em Andamento'",
    "Projetos Concluídos": "SELECT count(*) FROM dim_projeto WHERE status = 'Concluído'",
    "Projetos Atrasados": "SELECT count(*) FROM dim_projeto WHERE situacao_prazo = 'Atrasado'",
    "% Projetos Atrasados": """SELECT sum(int(situacao_prazo = 'Atrasado')) / count(*) FROM dim_projeto
                               WHERE status IN ('Em Andamento', 'Planejamento')""",
    "% Projetos Entregues no Prazo": """SELECT avg(int(situacao_prazo = 'Concluído no prazo')) FROM dim_projeto
                                        WHERE status = 'Concluído'""",
    "Atraso Médio dos Projetos (dias)": """SELECT avg(dias_atraso) FROM dim_projeto
                                           WHERE situacao_prazo IN ('Atrasado', 'Concluído com atraso')""",
    "Horas Orçadas": "SELECT sum(horas_orcadas) FROM dim_projeto",
    "% Orçamento Consumido": """SELECT (SELECT sum(horas_apontadas) FROM fato_tarefa)
                                       / (SELECT sum(horas_orcadas) FROM dim_projeto)""",
    "Tarefas": "SELECT count(*) FROM fato_tarefa",
    "Tarefas Abertas": f"SELECT count(*) FROM fato_tarefa WHERE status NOT IN {FINAIS}",
    "Tarefas Concluídas": "SELECT count(*) FROM fato_tarefa WHERE status = 'Concluída'",
    "Tarefas Bloqueadas": "SELECT count(*) FROM fato_tarefa WHERE status = 'Bloqueada'",
    "Tarefas Vencidas": f"""SELECT count(*) FROM fato_tarefa WHERE status NOT IN {FINAIS}
                            AND data_prazo < (SELECT data_referencia FROM ref_parametros)""",
    "% Abertas Vencidas": f"""SELECT avg(int(data_prazo < (SELECT data_referencia FROM ref_parametros)))
                              FROM fato_tarefa WHERE status NOT IN {FINAIS} AND data_prazo IS NOT NULL""",
    "% Entregues no Prazo": """SELECT avg(int(to_date(concluida_em) <= data_prazo)) FROM fato_tarefa
                               WHERE status = 'Concluída' AND data_prazo IS NOT NULL""",
    "Atraso Médio das Tarefas (dias)": """SELECT avg(dias_atraso) FROM fato_tarefa
                                          WHERE situacao_prazo IN ('Vencida', 'Concluída com atraso')""",
    "Lead Time Médio (dias)": """SELECT avg((unix_timestamp(concluida_em) - unix_timestamp(criada_em)) / 86400)
                                 FROM fato_tarefa WHERE status = 'Concluída'""",
    "Ciclo Médio (dias)": "SELECT avg(ciclo_dias) FROM fato_tarefa",
    "Ciclo Mediano (dias)": "SELECT median(ciclo_dias) FROM fato_tarefa",
    # dias fracionados até o fim do dia de referência (23:59:59), como na gold
    "Idade Média das Abertas (dias)": f"""SELECT avg((unix_timestamp((SELECT timestamp(data_referencia)
                                         + INTERVAL 86399 SECONDS FROM ref_parametros)) - unix_timestamp(criada_em))
                                         / 86400) FROM fato_tarefa WHERE status NOT IN {FINAIS}""",
    "Dias Bloqueada": "SELECT sum(dias_na_etapa) FROM fato_passagem_status WHERE status = 'Bloqueada'",
    "% Concluídas com Retrabalho": """SELECT avg(int(t.tarefa_id IN (SELECT tarefa_id FROM fato_passagem_status
                                      WHERE status_anterior = 'Em Revisão' AND status = 'Em Andamento')))
                                      FROM fato_tarefa t WHERE status = 'Concluída'""",
    "Horas Estimadas": "SELECT sum(estimativa_horas) FROM fato_tarefa",
    "Horas Apontadas": "SELECT sum(horas_apontadas) FROM fato_tarefa",
    "Desvio de Esforço %": """SELECT sum(horas_apontadas) / sum(estimativa_horas) - 1 FROM fato_tarefa
                              WHERE status = 'Concluída'""",
    "Tarefas Criadas": f"SELECT count(*) FROM fato_tarefa WHERE date_format(data_criacao, 'yyyy-MM') = '{MES}'",
    "Tarefas Entregues": f"""SELECT count(*) FROM fato_tarefa WHERE status = 'Concluída'
                             AND date_format(data_conclusao, 'yyyy-MM') = '{MES}'""",
    "Saldo do Período": f"""SELECT sum(int(date_format(data_criacao, 'yyyy-MM') = '{MES}'))
                            - sum(int(status = 'Concluída' AND date_format(data_conclusao, 'yyyy-MM') = '{MES}'))
                            FROM fato_tarefa""",
    "Tempo Médio na Etapa (dias)": "SELECT avg(dias_na_etapa) FROM fato_passagem_status WHERE saida_em IS NOT NULL",
    "Tarefas Paradas na Etapa": f"SELECT count(*) FROM fato_tarefa WHERE status NOT IN {FINAIS}",
    "Paradas há mais de 15 dias": f"""SELECT count(*) FROM fato_tarefa WHERE status NOT IN {FINAIS}
                                      AND dias_na_etapa_atual > 15""",
    "Mudanças de Status": f"SELECT count(*) FROM fato_passagem_status WHERE date_format(data_entrada, 'yyyy-MM') = '{MES}'",
    "Bloqueios no Período": f"""SELECT count(*) FROM fato_passagem_status WHERE status = 'Bloqueada'
                                AND date_format(data_entrada, 'yyyy-MM') = '{MES}'""",
    "Data de Referência": "SELECT date_format(data_referencia, 'dd/MM/yyyy') FROM ref_parametros",
    "Texto Referência": "SELECT concat('Dados até ', date_format(data_referencia, 'dd/MM/yyyy')) FROM ref_parametros",
    # contexto dos cartões: o mesmo texto que o DAX monta (sem filtro, todos abaixo de 1.000)
    "Contexto Projetos Ativos": "SELECT concat('de ', count(*), ' no portfólio') FROM dim_projeto",
    "Contexto Projetos Atrasados": """SELECT concat(cast(round(sum(int(situacao_prazo = 'Atrasado')) / count(*) * 100) AS INT),
                                     '% dos ativos') FROM dim_projeto WHERE status IN ('Em Andamento', 'Planejamento')""",
    "Contexto Atrasados de Ativos": """SELECT concat(sum(int(situacao_prazo = 'Atrasado')), ' de ',
                                      sum(int(status IN ('Em Andamento', 'Planejamento'))), ' ativos') FROM dim_projeto""",
    "Contexto Entregues no Prazo": """SELECT concat(sum(int(situacao_prazo = 'Concluído no prazo')), ' de ',
                                     sum(int(status = 'Concluído')), ' concluídos') FROM dim_projeto""",
    "Contexto Tarefas Abertas": "SELECT concat(count(*), ' bloqueadas agora') FROM fato_tarefa WHERE status = 'Bloqueada'",
    "Contexto Tarefas Vencidas": f"""SELECT concat(cast(round(avg(int(data_prazo < (SELECT data_referencia FROM ref_parametros)))
                                   * 100) AS INT), '% das abertas')
                                   FROM fato_tarefa WHERE status NOT IN {FINAIS} AND data_prazo IS NOT NULL""",
    "Contexto Tarefas Concluídas": """SELECT concat(cast(round(avg(int(status = 'Concluída')) * 100) AS INT),
                                     '% de todas as tarefas') FROM fato_tarefa""",
    "Contexto Horas Apontadas": """SELECT concat(CASE WHEN r >= 0 THEN '+' ELSE '-' END, cast(abs(round(r * 100)) AS INT),
                                  '% vs. o estimado')
                                  FROM (SELECT sum(horas_apontadas) / sum(estimativa_horas) - 1 AS r FROM fato_tarefa)""",
    "Contexto Orçamento": """SELECT concat(CASE WHEN s >= 0 THEN 'restam ' ELSE 'estourou em ' END,
                            cast(round(abs(s)) AS BIGINT), ' h')
                            FROM (SELECT (SELECT sum(horas_orcadas) FROM dim_projeto)
                                       - (SELECT sum(horas_apontadas) FROM fato_tarefa) AS s)""",
}
PERIODO = {"Tarefas Criadas", "Tarefas Entregues", "Saldo do Período", "Mudanças de Status", "Bloqueios no Período"}


def formatar(valor, formato: str | None) -> str:
    if isinstance(valor, str) or valor is None:
        return str(valor)
    if formato and "%" in formato:
        texto = f"{valor * 100:.1f}%".replace(".", ",")
        return ("+" + texto) if formato.startswith("+") and valor > 0 else texto
    if formato and ".0" in formato:
        return f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    texto = f"{round(valor):,}".replace(",", ".")
    return ("+" + texto) if formato and formato.startswith("+") and valor > 0 else texto


def calcular(spark) -> tuple[list[tuple[str, str, str, str]], dict]:
    linhas, brutos = [], {}
    for tabela, medidas in MEDIDAS.items():
        for nome, pasta, formato, _ in medidas:
            valor = spark.sql(SQL[nome]).first()[0]
            contexto = f"mês {MES[5:]}/{MES[:4]}" if nome in PERIODO else "sem filtro"
            linhas.append((pasta, nome, formatar(valor, formato), contexto))
            brutos[nome] = {"valor": valor if isinstance(valor, str) else float(valor),
                            "periodo": nome in PERIODO}
    return linhas, brutos


def por_equipe(spark) -> dict:
    """O que cada papel de segurança (RLS) deve enxergar: só os projetos da equipe e suas tarefas."""
    linhas = spark.sql(f"""
        SELECT p.equipe,
               count(DISTINCT p.projeto_id) AS projetos,
               count(t.tarefa_id) AS tarefas,
               sum(int(t.status NOT IN {FINAIS})) AS abertas
        FROM dim_projeto p LEFT JOIN fato_tarefa t ON t.projeto_id = p.projeto_id
        GROUP BY p.equipe""").collect()
    return {r["equipe"]: {"Projetos": r["projetos"], "Tarefas": r["tarefas"], "Tarefas Abertas": r["abertas"]}
            for r in sorted(linhas, key=lambda r: r["equipe"])}


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--pasta", type=Path, default=RAIZ / ".local" / "lakehouse")
    a = args.parse_args()
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.master("local[2]").config("spark.ui.enabled", "false").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    spark.conf.set("spark.sql.session.timeZone", "UTC")  # igual à gold; senão o fim do dia anda 3 h
    for tabela in ("fato_tarefa", "fato_passagem_status", "dim_projeto", "ref_parametros"):
        spark.read.parquet(str(a.pasta / "Tables" / tabela)).createOrReplaceTempView(tabela)
    faltando = {m[0] for ms in MEDIDAS.values() for m in ms} - set(SQL)
    if faltando:
        raise SystemExit(f"medidas sem conferência: {faltando}")

    linhas, brutos = calcular(spark)
    import json
    (RAIZ / "docs").mkdir(exist_ok=True)
    (RAIZ / "docs" / "valores_esperados.json").write_text(json.dumps(
        {"mes_ano": MES_ANO, "medidas": brutos, "por_equipe": por_equipe(spark), "papeis": PAPEIS},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    destino = RAIZ / "docs" / "valores_esperados.md"
    destino.parent.mkdir(exist_ok=True)
    corpo = ["# Valores esperados das medidas", "",
             "Calculados em SQL direto na gold, sem passar pelo DAX (`tools/valores_esperados.py`).",
             "No Power BI, cada medida em um cartão tem que mostrar o mesmo valor.",
             f"As medidas de período usam o mês **{MES[5:]}/{MES[:4]}** num filtro de `dim_data[mes_ano]`; "
             "as demais, nenhum filtro.", "",
             "| Pasta | Medida | Valor esperado | Contexto |", "|---|---|---:|---|"]
    corpo += [f"| {p} | {n} | {v} | {c} |" for p, n, v, c in linhas]
    destino.write_text("\n".join(corpo) + "\n", encoding="utf-8")
    print("\n".join(corpo[7:]))


if __name__ == "__main__":
    main()
