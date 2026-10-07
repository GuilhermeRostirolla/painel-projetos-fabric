# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # 03 - Gold
#
# Star schema para o Direct Lake: fato_tarefa, fato_passagem_status, dim_projeto, dim_pessoa, dim_status, dim_data e ref_parametros.
# Tempos (ciclo, bloqueio, retrabalho) calculados a partir do histórico de status. Datas no horário de Brasília,
# medidas contra a data de referência dos dados.

# PARAMETERS CELL ********************

FORMATO_TABELA = "delta"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

spark.conf.set("spark.sql.session.timeZone", "UTC")
FUSO = "America/Sao_Paulo"
FINAIS = ["Concluído", "Arquivada"]


def local(coluna: str):
    return F.from_utc_timestamp(F.col(coluna), FUSO)


def dias_entre(inicio, fim):
    return F.round((F.unix_timestamp(fim) - F.unix_timestamp(inicio)) / 86400, 2)


ref = spark.table("silver_meta").first()
DATA_REF = ref["data_referencia"]
FIM_REF = F.to_timestamp(F.lit(f"{DATA_REF} 23:59:59"))
print(f"data de referência: {DATA_REF}")

portfolios = spark.table("silver_portfolios")
pessoas = spark.table("silver_usuarios")
projetos = spark.table("silver_projetos")
tarefas = spark.table("silver_tarefas")
historico = (spark.table("silver_movimentacoes")
    .withColumnRenamed("etapa_anterior", "status_anterior").withColumnRenamed("etapa_nova", "status_novo")
    .withColumnRenamed("usuario_id", "pessoa_id"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

ORDEM_ETAPA = {"Backlog": 1, "A fazer": 2, "Fazendo": 3, "Impedido": 4, "Em revisão": 5,
               "Concluído": 6, "Arquivada": 7}
ordem_etapa = F.create_map(*[F.lit(x) for kv in ORDEM_ETAPA.items() for x in kv])
ordem = Window.partitionBy("tarefa_id").orderBy("ocorrido_em", "id")
passagens = (historico
    .withColumn("entrada_em", local("ocorrido_em"))
    .withColumn("saida_em", F.lead("entrada_em").over(ordem))
    .withColumn("sequencia", F.row_number().over(ordem))
    .join(tarefas.select(F.col("id").alias("tarefa_id"), "projeto_id"), "tarefa_id")
    .withColumn("etapa_final", F.col("status_novo").isin(FINAIS))
    .withColumn("etapa_atual", F.col("saida_em").isNull())
    .withColumn("dias_na_etapa", F.when(F.col("etapa_final"), F.lit(None).cast("double"))
                .otherwise(dias_entre(F.col("entrada_em"), F.coalesce("saida_em", FIM_REF))))
    .select(F.col("id").alias("passagem_id"), "tarefa_id", "projeto_id", "sequencia",
            F.col("status_anterior"), F.col("status_novo").alias("status"),
            ordem_etapa[F.col("status_novo")].alias("ordem_etapa"), "pessoa_id",
            "entrada_em", "saida_em", F.to_date("entrada_em").alias("data_entrada"),
            "dias_na_etapa", "etapa_atual", "etapa_final"))

por_tarefa = passagens.groupBy("tarefa_id").agg(
    F.min(F.when(F.col("status") == "Fazendo", F.col("entrada_em"))).alias("inicio_execucao_em"),
    F.sum(F.when(F.col("status") == "Impedido", 1).otherwise(0)).alias("qtd_bloqueios"),
    F.round(F.sum(F.when(F.col("status") == "Impedido", F.col("dias_na_etapa")).otherwise(0)), 2)
        .alias("dias_bloqueada"),
    F.sum(F.when((F.col("status_anterior") == "Em revisão") & (F.col("status") == "Fazendo"), 1)
          .otherwise(0)).alias("qtd_retrabalho"),
    F.max("entrada_em").alias("ultima_mudanca_em"),
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

t = (tarefas
     .withColumnRenamed("etapa", "status").withColumnRenamed("limite", "prazo")
     .withColumn("criada_em", local("criada_em"))
     .withColumn("concluida_em", local("concluida_em"))
     .join(por_tarefa, tarefas["id"] == por_tarefa["tarefa_id"], "left"))

aberta = ~F.col("status").isin(FINAIS)
concluida = F.col("status") == "Concluído"
data_conclusao = F.to_date("concluida_em")

fato_tarefa = t.select(
    F.col("id").alias("tarefa_id"), "projeto_id", "responsavel_id", "titulo", "tipo", "prioridade", "status",
    "situacao", F.array_join("etiquetas", ", ").alias("etiquetas"),
    F.to_date("criada_em").alias("data_criacao"), "criada_em",
    F.to_date("inicio_execucao_em").alias("data_inicio_execucao"),
    data_conclusao.alias("data_conclusao"), "concluida_em",
    F.col("prazo").alias("data_limite"),
    F.col("estimativa_horas"), F.col("horas_apontadas"),
    F.when(concluida, F.round(F.col("horas_apontadas") - F.col("estimativa_horas"), 1)).alias("desvio_horas"),
    aberta.alias("aberta"),
    F.when(concluida, dias_entre(F.col("criada_em"), F.col("concluida_em"))).alias("lead_time_dias"),
    F.when(concluida, dias_entre(F.col("inicio_execucao_em"), F.col("concluida_em"))).alias("ciclo_dias"),
    F.when(aberta, dias_entre(F.col("criada_em"), FIM_REF)).alias("idade_dias"),
    F.when(aberta, dias_entre(F.col("ultima_mudanca_em"), FIM_REF)).alias("dias_na_etapa_atual"),
    F.coalesce("qtd_bloqueios", F.lit(0)).alias("qtd_bloqueios"),
    F.coalesce("dias_bloqueada", F.lit(0.0)).alias("dias_bloqueada"),
    F.coalesce("qtd_retrabalho", F.lit(0)).alias("qtd_retrabalho"),
    F.when(F.col("status") == "Arquivada", "Arquivada")
     .when(F.col("prazo").isNull(), "Sem prazo")
     .when(concluida & (data_conclusao <= F.col("prazo")), "Concluída no prazo")
     .when(concluida, "Concluída com atraso")
     .when(F.col("prazo") < F.lit(DATA_REF), "Vencida")
     .otherwise("No prazo").alias("situacao_prazo"),
    F.when(concluida, F.greatest(F.datediff(data_conclusao, "prazo"), F.lit(0)))
     .when(aberta, F.greatest(F.datediff(F.lit(DATA_REF), "prazo"), F.lit(0)))
     .alias("dias_atraso"),
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

gerentes = pessoas.select(F.col("id").alias("gerente_id"), F.col("nome").alias("gerente"))
nomes_portfolio = portfolios.select(F.col("id").alias("portfolio_id"), F.col("nome").alias("portfolio"))

status_projeto = (F.when(F.col("situacao") == "Arquivado", "Arquivado")
                  .when(F.col("situacao") == "Concluído", "Concluído")
                  .when(F.array_contains("etiquetas", "Em espera"), "Em espera")
                  .when(F.col("etapa") == "Planejamento", "Planejamento")
                  .otherwise("Em execução"))

projetos_status = (projetos.withColumn("status", status_projeto)
                   .withColumnRenamed("inicio", "data_inicio").withColumnRenamed("limite", "data_limite")
                   .withColumnRenamed("concluido_em", "data_conclusao"))

ativo_ou_planejado = F.col("status").isin("Em execução", "Planejamento")
fim_real_ou_ref = F.coalesce("data_conclusao", F.lit(DATA_REF).cast("date"))

dim_projeto = (projetos_status
    .join(nomes_portfolio, "portfolio_id", "left")
    .join(gerentes, "gerente_id", "left")
    .select(
        F.col("id").alias("projeto_id"), F.col("nome").alias("projeto"), "portfolio", "gerente", "prioridade",
        "status", "etapa", "situacao", "farol", "origem", "origem_id",
        F.array_join("etiquetas", ", ").alias("etiquetas"),
        "data_inicio", "data_limite", "data_conclusao", "horas_orcadas", "orcamento",
        F.datediff("data_limite", "data_inicio").alias("dias_planejados"),
        F.when(F.col("status") == "Concluído",
               F.when(F.col("data_conclusao") <= F.col("data_limite"), "Concluído no prazo")
                .otherwise("Concluído com atraso"))
         .when(ativo_ou_planejado & (F.lit(DATA_REF) > F.col("data_limite")), "Atrasado")
         .when(ativo_ou_planejado, "No prazo")
         .otherwise(F.col("status")).alias("situacao_prazo"),
        F.when(F.col("status").isin("Concluído", "Em execução", "Planejamento"),
               F.greatest(F.datediff(fim_real_ou_ref, "data_limite"), F.lit(0))).alias("dias_atraso"),
        F.when(ativo_ou_planejado,
               F.round(F.datediff(F.lit(DATA_REF), "data_inicio") / F.datediff("data_limite", "data_inicio"), 4))
         .alias("percentual_prazo_decorrido"),
    ))

dim_pessoa = (pessoas.join(nomes_portfolio, "portfolio_id", "left")
    .select(F.col("id").alias("pessoa_id"), F.col("nome").alias("pessoa"), "portfolio", "cargo", "ativo",
            "data_admissao"))

CATEGORIA = {"Backlog": "Não iniciada", "A fazer": "Não iniciada", "Fazendo": "Em andamento",
             "Impedido": "Em andamento", "Em revisão": "Em andamento", "Concluído": "Concluída",
             "Arquivada": "Arquivada"}
dim_status = spark.createDataFrame([(s, CATEGORIA[s], o) for s, o in ORDEM_ETAPA.items()],
                                   "status string, categoria string, ordem int")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

limites = (fato_tarefa.select(F.min("data_criacao").alias("d")).union(dim_projeto.select(F.min("data_inicio")))
           .union(dim_projeto.select(F.max("data_limite"))).union(spark.createDataFrame([(DATA_REF,)], "d date")))
inicio_cal, fim_cal = limites.agg(F.min("d"), F.max("d")).first()
inicio_cal, fim_cal = inicio_cal.replace(month=1, day=1), fim_cal.replace(month=12, day=31)

MESES = F.array(*[F.lit(m) for m in ("jan", "fev", "mar", "abr", "mai", "jun",
                                      "jul", "ago", "set", "out", "nov", "dez")])
DIAS = F.array(*[F.lit(d) for d in ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")])
dia_semana = (F.dayofweek("data") + 5) % 7 + 1

dim_data = (spark.sql(f"SELECT explode(sequence(DATE'{inicio_cal}', DATE'{fim_cal}')) AS data")
    .select(
        "data", F.year("data").alias("ano"), F.month("data").alias("mes"),
        F.element_at(MESES, F.month("data")).alias("mes_nome"),
        F.concat(F.element_at(MESES, F.month("data")), F.lit("/"), F.date_format("data", "yy")).alias("mes_ano"),
        (F.year("data") * 100 + F.month("data")).alias("ano_mes"),
        F.concat(F.lit("T"), F.quarter("data")).alias("trimestre"),
        F.date_sub("data", dia_semana - 1).alias("semana_inicio"),
        dia_semana.alias("dia_semana"), F.element_at(DIAS, dia_semana).alias("dia_semana_nome"),
        (dia_semana <= 5).alias("dia_util"),
        (F.col("data") <= F.lit(DATA_REF)).alias("ate_referencia"),
    ))

ref_parametros = (spark.createDataFrame([(DATA_REF,)], "data_referencia date")
                  .withColumn("processado_em", F.from_utc_timestamp(F.current_timestamp(), FUSO)))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def salvar(df: DataFrame, nome: str) -> int:
    df.write.format(FORMATO_TABELA).mode("overwrite").option("overwriteSchema", "true").saveAsTable(nome)
    return spark.table(nome).count()


saida = {"fato_tarefa": fato_tarefa, "fato_passagem_status": passagens, "dim_projeto": dim_projeto,
         "dim_pessoa": dim_pessoa, "dim_status": dim_status, "dim_data": dim_data,
         "ref_parametros": ref_parametros}
for nome, df in saida.items():
    print(f"{nome:<22} {salvar(df, nome):>7}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

checagens = {
    "toda tarefa tem projeto": spark.sql("""SELECT count(*) FROM fato_tarefa f
        LEFT ANTI JOIN dim_projeto p ON f.projeto_id = p.projeto_id""").first()[0] == 0,
    "todo responsável existe": spark.sql("""SELECT count(*) FROM fato_tarefa f
        LEFT ANTI JOIN dim_pessoa p ON f.responsavel_id = p.pessoa_id""").first()[0] == 0,
    "status da tarefa = última passagem": spark.sql("""SELECT count(*) FROM fato_tarefa f
        JOIN fato_passagem_status p ON p.tarefa_id = f.tarefa_id AND p.etapa_atual
        WHERE p.status <> f.status""").first()[0] == 0,
    "uma etapa atual por tarefa": spark.sql("""SELECT count(*) FROM (SELECT tarefa_id FROM fato_passagem_status
        WHERE etapa_atual GROUP BY tarefa_id HAVING count(*) <> 1)""").first()[0] == 0,
    "tempos não negativos": spark.sql("""SELECT count(*) FROM fato_tarefa
        WHERE ciclo_dias < 0 OR lead_time_dias < 0 OR dias_bloqueada < 0""").first()[0] == 0,
    "ciclo ≤ lead time": spark.sql("""SELECT count(*) FROM fato_tarefa
        WHERE ciclo_dias > lead_time_dias""").first()[0] == 0,
    "calendário cobre todas as datas": spark.sql("""SELECT count(*) FROM fato_tarefa f
        LEFT ANTI JOIN dim_data d ON f.data_criacao = d.data""").first()[0] == 0,
}
for nome, ok in checagens.items():
    print(("ok    " if ok else "FALHOU") + f"  {nome}")
falhas = [n for n, ok in checagens.items() if not ok]
if falhas:
    raise AssertionError(f"gold inconsistente: {falhas}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
