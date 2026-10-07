"""Recalcula as medidas em SQL na gold local e grava docs/valores_esperados.md/.json."""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from tools.gerar_modelo import MEDIDAS, PAPEIS, SEM_CONFERENCIA  # noqa: E402

MES = "2026-09"
MES_ANO = "set/26"
FINAIS = "('Concluído', 'Arquivada')"
SQL = {
    "Projetos": "SELECT count(*) FROM dim_projeto",
    "Projetos Ativos": "SELECT count(*) FROM dim_projeto WHERE status IN ('Em execução', 'Planejamento')",
    "Projetos em Execução": "SELECT count(*) FROM dim_projeto WHERE status = 'Em execução'",
    "Projetos Concluídos": "SELECT count(*) FROM dim_projeto WHERE status = 'Concluído'",
    "Projetos Atrasados": "SELECT count(*) FROM dim_projeto WHERE situacao_prazo = 'Atrasado'",
    "% Projetos Atrasados": """SELECT sum(int(situacao_prazo = 'Atrasado')) / count(*) FROM dim_projeto
                               WHERE status IN ('Em execução', 'Planejamento')""",
    "% Projetos Entregues no Prazo": """SELECT avg(int(situacao_prazo = 'Concluído no prazo')) FROM dim_projeto
                                        WHERE status = 'Concluído'""",
    "Atraso Médio dos Projetos (dias)": """SELECT avg(dias_atraso) FROM dim_projeto
                                           WHERE situacao_prazo IN ('Atrasado', 'Concluído com atraso')""",
    "Horas Orçadas": "SELECT sum(horas_orcadas) FROM dim_projeto",
    "% Orçamento Consumido": """SELECT (SELECT sum(horas_apontadas) FROM fato_tarefa)
                                       / (SELECT sum(horas_orcadas) FROM dim_projeto)""",
    "Tarefas": "SELECT count(*) FROM fato_tarefa",
    "Tarefas Abertas": f"SELECT count(*) FROM fato_tarefa WHERE status NOT IN {FINAIS}",
    "Tarefas Concluídas": "SELECT count(*) FROM fato_tarefa WHERE status = 'Concluído'",
    "Tarefas Impedidas": "SELECT count(*) FROM fato_tarefa WHERE status = 'Impedido'",
    "Tarefas Vencidas": f"""SELECT count(*) FROM fato_tarefa WHERE status NOT IN {FINAIS}
                            AND data_limite < (SELECT data_referencia FROM ref_parametros)""",
    "% Abertas Vencidas": f"""SELECT avg(int(data_limite < (SELECT data_referencia FROM ref_parametros)))
                              FROM fato_tarefa WHERE status NOT IN {FINAIS} AND data_limite IS NOT NULL""",
    "% Entregues no Prazo": """SELECT avg(int(to_date(concluida_em) <= data_limite)) FROM fato_tarefa
                               WHERE status = 'Concluído' AND data_limite IS NOT NULL""",
    "Atraso Médio das Tarefas (dias)": """SELECT avg(dias_atraso) FROM fato_tarefa
                                          WHERE situacao_prazo IN ('Vencida', 'Concluída com atraso')""",
    "Lead Time Médio (dias)": """SELECT avg((unix_timestamp(concluida_em) - unix_timestamp(criada_em)) / 86400)
                                 FROM fato_tarefa WHERE status = 'Concluído'""",
    "Ciclo Médio (dias)": "SELECT avg(ciclo_dias) FROM fato_tarefa",
    "Ciclo Mediano (dias)": "SELECT median(ciclo_dias) FROM fato_tarefa",
    "Idade Média das Abertas (dias)": f"""SELECT avg((unix_timestamp((SELECT timestamp(data_referencia)
                                         + INTERVAL 86399 SECONDS FROM ref_parametros)) - unix_timestamp(criada_em))
                                         / 86400) FROM fato_tarefa WHERE status NOT IN {FINAIS}""",
    "Dias Bloqueada": "SELECT sum(dias_na_etapa) FROM fato_passagem_status WHERE status = 'Impedido'",
    "% Concluídas com Retrabalho": """SELECT avg(int(t.tarefa_id IN (SELECT tarefa_id FROM fato_passagem_status
                                      WHERE status_anterior = 'Em revisão' AND status = 'Fazendo')))
                                      FROM fato_tarefa t WHERE status = 'Concluído'""",
    "Horas Estimadas": "SELECT sum(estimativa_horas) FROM fato_tarefa",
    "Horas Apontadas": "SELECT sum(horas_apontadas) FROM fato_tarefa",
    "Desvio de Esforço %": """SELECT sum(horas_apontadas) / sum(estimativa_horas) - 1 FROM fato_tarefa
                              WHERE status = 'Concluído'""",
    "Tarefas Criadas": f"SELECT count(*) FROM fato_tarefa WHERE date_format(data_criacao, 'yyyy-MM') = '{MES}'",
    "Tarefas Entregues": f"""SELECT count(*) FROM fato_tarefa WHERE status = 'Concluído'
                             AND date_format(data_conclusao, 'yyyy-MM') = '{MES}'""",
    "Saldo do Período": f"""SELECT sum(int(date_format(data_criacao, 'yyyy-MM') = '{MES}'))
                            - sum(int(status = 'Concluído' AND date_format(data_conclusao, 'yyyy-MM') = '{MES}'))
                            FROM fato_tarefa""",
    "Tempo Médio na Etapa (dias)": "SELECT avg(dias_na_etapa) FROM fato_passagem_status WHERE saida_em IS NOT NULL",
    "Tarefas Paradas na Etapa": f"SELECT count(*) FROM fato_tarefa WHERE status NOT IN {FINAIS}",
    "Paradas há mais de 15 dias": f"""SELECT count(*) FROM fato_tarefa WHERE status NOT IN {FINAIS}
                                      AND dias_na_etapa_atual > 15""",
    "Mudanças de Status": f"SELECT count(*) FROM fato_passagem_status WHERE date_format(data_entrada, 'yyyy-MM') = '{MES}'",
    "Bloqueios no Período": f"""SELECT count(*) FROM fato_passagem_status WHERE status = 'Impedido'
                                AND date_format(data_entrada, 'yyyy-MM') = '{MES}'""",
    "Data de Referência": "SELECT date_format(data_referencia, 'dd/MM/yyyy') FROM ref_parametros",
    "Texto Referência": "SELECT concat('Dados até ', date_format(data_referencia, 'dd/MM/yyyy')) FROM ref_parametros",
    "Orçamento": "SELECT sum(orcamento) FROM dim_projeto",
    "Projetos Farol Vermelho": "SELECT count(*) FROM dim_projeto WHERE farol = 'Vermelho'",
    "Projetos de Ideias": "SELECT count(*) FROM dim_projeto WHERE origem = 'Ideia'",
    "Contexto Orçamento Consumido": """SELECT concat(cast(round((SELECT sum(horas_apontadas) FROM fato_tarefa)
                                      / (SELECT sum(horas_orcadas) FROM dim_projeto) * 100) AS INT),
                                      '% das horas orçadas já usadas')""",
    "Contexto Projetos de Ideias": "SELECT concat(count(*), ' vieram de ideias') FROM dim_projeto WHERE origem = 'Ideia'",
    "% Tarefas Concluídas": "SELECT avg(int(status = 'Concluído')) FROM fato_tarefa",
    "Contexto Projetos Ativos": "SELECT concat('de ', count(*), ' no portfólio') FROM dim_projeto",
    "Contexto Projetos Atrasados": """SELECT concat(cast(round(sum(int(situacao_prazo = 'Atrasado')) / count(*) * 100) AS INT),
                                     '% dos ativos') FROM dim_projeto WHERE status IN ('Em execução', 'Planejamento')""",
    "Contexto Atrasados de Ativos": """SELECT concat(sum(int(situacao_prazo = 'Atrasado')), ' de ',
                                      sum(int(status IN ('Em execução', 'Planejamento'))), ' ativos') FROM dim_projeto""",
    "Contexto Entregues no Prazo": """SELECT concat(sum(int(situacao_prazo = 'Concluído no prazo')), ' de ',
                                     sum(int(status = 'Concluído')), ' concluídos') FROM dim_projeto""",
    "Contexto Tarefas Abertas": "SELECT concat(count(*), ' impedidas agora') FROM fato_tarefa WHERE status = 'Impedido'",
    "Contexto Tarefas Vencidas": f"""SELECT concat(cast(round(avg(int(data_limite < (SELECT data_referencia FROM ref_parametros)))
                                   * 100) AS INT), '% das abertas')
                                   FROM fato_tarefa WHERE status NOT IN {FINAIS} AND data_limite IS NOT NULL""",
    "Contexto Tarefas Concluídas": """SELECT concat(cast(round(avg(int(status = 'Concluído')) * 100) AS INT),
                                     '% de todas as tarefas') FROM fato_tarefa""",
    "Contexto Horas Apontadas": """SELECT concat(CASE WHEN r >= 0 THEN '+' ELSE '-' END, cast(abs(round(r * 100)) AS INT),
                                  '% vs. o estimado')
                                  FROM (SELECT sum(horas_apontadas) / sum(estimativa_horas) - 1 AS r FROM fato_tarefa)""",
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
            if pasta in SEM_CONFERENCIA:
                continue
            valor = spark.sql(SQL[nome]).first()[0]
            contexto = f"mês {MES[5:]}/{MES[:4]}" if nome in PERIODO else "sem filtro"
            linhas.append((pasta, nome, formatar(valor, formato), contexto))
            brutos[nome] = {"valor": valor if isinstance(valor, str) else float(valor),
                            "periodo": nome in PERIODO}
    return linhas, brutos


def por_portfolio(spark) -> dict:
    linhas = spark.sql(f"""
        SELECT p.portfolio,
               count(DISTINCT p.projeto_id) AS projetos,
               count(t.tarefa_id) AS tarefas,
               sum(int(t.status NOT IN {FINAIS})) AS abertas
        FROM dim_projeto p LEFT JOIN fato_tarefa t ON t.projeto_id = p.projeto_id
        GROUP BY p.portfolio""").collect()
    return {r["portfolio"]: {"Projetos": r["projetos"], "Tarefas": r["tarefas"], "Tarefas Abertas": r["abertas"]}
            for r in sorted(linhas, key=lambda r: r["portfolio"])}


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--pasta", type=Path, default=RAIZ / ".local" / "lakehouse")
    a = args.parse_args()
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.master("local[2]").config("spark.ui.enabled", "false").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    for tabela in ("fato_tarefa", "fato_passagem_status", "dim_projeto", "ref_parametros"):
        spark.read.parquet(str(a.pasta / "Tables" / tabela)).createOrReplaceTempView(tabela)
    faltando = {m[0] for ms in MEDIDAS.values() for m in ms if m[1] not in SEM_CONFERENCIA} - set(SQL)
    if faltando:
        raise SystemExit(f"medidas sem conferência: {faltando}")

    linhas, brutos = calcular(spark)
    import json
    (RAIZ / "docs").mkdir(exist_ok=True)
    (RAIZ / "docs" / "valores_esperados.json").write_text(json.dumps(
        {"mes_ano": MES_ANO, "medidas": brutos, "por_portfolio": por_portfolio(spark), "papeis": PAPEIS},
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
