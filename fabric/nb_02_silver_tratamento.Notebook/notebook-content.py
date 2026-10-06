# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # 02 · Silver: tratamento
#
# Lê todo o JSON bruto do bronze e entrega uma tabela limpa por recurso:
#
# - **Contrato de dados:** cada recurso tem um schema fixo. Se a API mudar um campo, o erro aparece aqui, não no painel.
# - **Padronização:** textos sem espaço sobrando, prioridade com grafia única, datas convertidas com fuso.
# - **Uma linha por registro:** a mesma tarefa pode chegar em várias execuções (carga incremental com sobreposição); fica a versão mais recente.
# - **Quarentena:** registro que quebra uma regra (status desconhecido, chave órfã) vai para `silver_rejeitados` com o motivo, em vez de sumir.
#
# Reprocessar o bronze inteiro a cada execução é barato neste volume e deixa a silver sem estado: rodar duas vezes dá o mesmo resultado.

# PARAMETERS CELL ********************

PASTA_ARQUIVOS_SPARK = "Files"   # caminho do lakehouse padrão visto pelo Spark
FORMATO_TABELA = "delta"         # delta no Fabric; o teste local usa parquet

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from functools import reduce

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (ArrayType, BooleanType, DoubleType, IntegerType,
                               LongType, StringType, StructField, StructType)

spark.conf.set("spark.sql.session.timeZone", "UTC")   # timestamps guardados como instante UTC
BRONZE = f"{PASTA_ARQUIVOS_SPARK}/bronze"

PRIORIDADES = ["Baixa", "Média", "Alta", "Crítica"]
STATUS_TAREFA = ["Backlog", "A Fazer", "Em Andamento", "Bloqueada", "Em Revisão", "Concluída", "Cancelada"]
STATUS_PROJETO = ["Planejamento", "Em Andamento", "Pausado", "Cancelado", "Concluído"]


def campos(*definicoes: tuple[str, object]) -> StructType:
    return StructType([StructField(nome, tipo, True) for nome, tipo in definicoes])


S, I, D = StringType(), IntegerType(), DoubleType()
CONTRATOS = {
    "equipes": campos(("id", I), ("nome", S), ("sigla", S), ("gestor_id", S)),
    "pessoas": campos(("id", S), ("nome", S), ("email", S), ("equipe_id", I), ("cargo", S),
                      ("data_admissao", S), ("ativo", BooleanType())),
    "projetos": campos(("id", S), ("nome", S), ("equipe_id", I), ("gestor_id", S), ("prioridade", S),
                       ("status", S), ("data_inicio", S), ("data_fim_planejada", S), ("data_conclusao", S),
                       ("horas_orcadas", I), ("criado_em", S), ("atualizado_em", S)),
    "tarefas": campos(("id", S), ("projeto_id", S), ("titulo", S), ("tipo", S), ("prioridade", S),
                      ("responsavel_id", S), ("estimativa_horas", D), ("horas_apontadas", D), ("status", S),
                      ("criada_em", S), ("prazo", S), ("concluida_em", S), ("atualizado_em", S)),
    "historico": campos(("id", S), ("tarefa_id", S), ("status_anterior", S), ("status_novo", S),
                        ("pessoa_id", S), ("ocorrido_em", S)),
    "meta": campos(("versao", S), ("data_referencia", S), ("semente", LongType())),
}


def ler_bronze(recurso: str) -> DataFrame:
    """Uma linha por registro, com a execução de origem para desempate."""
    caminho = f"{BRONZE}/{recurso}/*/*.json"
    if recurso == "meta":
        return spark.read.schema(CONTRATOS["meta"]).option("multiLine", True).json(caminho) \
            .withColumn("_arquivo", F.col("_metadata.file_path"))
    envelope = campos(("dados", ArrayType(CONTRATOS[recurso])), ("_execucao", S))
    return (spark.read.schema(envelope).option("multiLine", True).json(caminho)
            .select(F.explode("dados").alias("r"), "_execucao")
            .select("r.*", "_execucao"))


def mais_recente(df: DataFrame, ordem: list) -> DataFrame:
    janela = Window.partitionBy("id").orderBy(*ordem)
    return df.withColumn("_n", F.row_number().over(janela)).filter("_n = 1").drop("_n", "_execucao")


def texto(coluna: str):
    """Tira espaços nas pontas e repetidos no meio; vazio vira nulo."""
    limpo = F.regexp_replace(F.trim(F.col(coluna)), r"\s+", " ")
    return F.when(limpo == "", None).otherwise(limpo)


def instante(coluna: str):
    return F.to_timestamp(F.col(coluna))   # o texto traz o fuso (-03:00); vira instante UTC


def prioridade(coluna: str):
    p = F.initcap(F.lower(texto(coluna)))
    return F.when(p.isin(PRIORIDADES), p).otherwise(F.lit("Não informada"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

equipes = mais_recente(ler_bronze("equipes"), [F.desc("_execucao")]).select(
    "id", texto("nome").alias("nome"), F.upper(texto("sigla")).alias("sigla"), "gestor_id")

pessoas = mais_recente(ler_bronze("pessoas"), [F.desc("_execucao")]).select(
    "id", texto("nome").alias("nome"), F.lower(texto("email")).alias("email"), "equipe_id",
    texto("cargo").alias("cargo"), F.to_date("data_admissao").alias("data_admissao"),
    F.coalesce("ativo", F.lit(True)).alias("ativo"))

projetos = mais_recente(ler_bronze("projetos"), [F.desc(instante("atualizado_em")), F.desc("_execucao")]).select(
    "id", texto("nome").alias("nome"), "equipe_id", "gestor_id",
    prioridade("prioridade").alias("prioridade"), texto("status").alias("status"),
    F.to_date("data_inicio").alias("data_inicio"), F.to_date("data_fim_planejada").alias("data_fim_planejada"),
    F.to_date("data_conclusao").alias("data_conclusao"), "horas_orcadas",
    instante("criado_em").alias("criado_em"), instante("atualizado_em").alias("atualizado_em"))

tarefas = mais_recente(ler_bronze("tarefas"), [F.desc(instante("atualizado_em")), F.desc("_execucao")]).select(
    "id", "projeto_id", texto("titulo").alias("titulo"), texto("tipo").alias("tipo"),
    prioridade("prioridade").alias("prioridade"), "responsavel_id",
    "estimativa_horas", "horas_apontadas", texto("status").alias("status"),
    instante("criada_em").alias("criada_em"), F.to_date("prazo").alias("prazo"),
    instante("concluida_em").alias("concluida_em"), instante("atualizado_em").alias("atualizado_em"))

historico = mais_recente(ler_bronze("historico"), [F.desc("_execucao")]).select(
    "id", "tarefa_id", texto("status_anterior").alias("status_anterior"),
    texto("status_novo").alias("status_novo"), "pessoa_id", instante("ocorrido_em").alias("ocorrido_em"))

meta = (ler_bronze("meta").orderBy(F.desc("_arquivo")).limit(1)
        .select(F.to_date("data_referencia").alias("data_referencia"), "versao", "semente",
                F.current_timestamp().alias("processado_em")))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Regras de qualidade: (tabela, condição que REPROVA o registro, motivo)
ids = lambda df: df.select(F.col("id").alias("_ref"))
regras = {
    "projetos": [
        (~F.col("status").isin(STATUS_PROJETO) | F.col("status").isNull(), "status de projeto desconhecido"),
        (F.col("data_fim_planejada") < F.col("data_inicio"), "fim planejado antes do início"),
    ],
    "tarefas": [
        (~F.col("status").isin(STATUS_TAREFA) | F.col("status").isNull(), "status de tarefa desconhecido"),
        (F.col("estimativa_horas") < 0, "estimativa negativa"),
        (F.col("horas_apontadas") < 0, "horas negativas"),
    ],
    "historico": [
        (~F.col("status_novo").isin(STATUS_TAREFA) | F.col("status_novo").isNull(), "status desconhecido"),
    ],
}
# chaves estrangeiras: (tabela, coluna, tabela referenciada), na ordem das dependências
chaves = [("pessoas", "equipe_id", "equipes"), ("projetos", "equipe_id", "equipes"),
          ("projetos", "gestor_id", "pessoas"), ("tarefas", "projeto_id", "projetos"),
          ("tarefas", "responsavel_id", "pessoas"), ("historico", "tarefa_id", "tarefas"),
          ("historico", "pessoa_id", "pessoas")]

tabelas = {"equipes": equipes, "pessoas": pessoas, "projetos": projetos,
           "tarefas": tarefas, "historico": historico}
rejeitados = []


def separar(nome: str, df: DataFrame, condicao, motivo: str) -> DataFrame:
    ruins = df.filter(F.coalesce(condicao, F.lit(False)))
    rejeitados.append(ruins.select(F.lit(nome).alias("tabela"), F.col("id").cast("string").alias("id"),
                                   F.lit(motivo).alias("motivo"), F.to_json(F.struct("*")).alias("registro")))
    return df.filter(~F.coalesce(condicao, F.lit(False)))


for nome, lista in regras.items():
    for condicao, motivo in lista:
        tabelas[nome] = separar(nome, tabelas[nome], condicao, motivo)

for nome, coluna, referencia in chaves:
    df = tabelas[nome]
    validos = ids(tabelas[referencia])
    orfaos = df.join(validos, df[coluna] == validos["_ref"], "left_anti")
    rejeitados.append(orfaos.select(F.lit(nome).alias("tabela"), F.col("id").cast("string").alias("id"),
                                    F.lit(f"{coluna} sem correspondente").alias("motivo"),
                                    F.to_json(F.struct("*")).alias("registro")))
    tabelas[nome] = df.join(validos, df[coluna] == validos["_ref"], "left_semi")

rejeitados_df = reduce(DataFrame.unionByName, rejeitados).withColumn("processado_em", F.current_timestamp())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def salvar(df: DataFrame, nome: str) -> int:
    (df.write.format(FORMATO_TABELA).mode("overwrite").option("overwriteSchema", "true")
       .saveAsTable(nome))
    return spark.table(nome).count()


contagens = {f"silver_{n}": salvar(df, f"silver_{n}") for n, df in tabelas.items()}
contagens["silver_meta"] = salvar(meta, "silver_meta")
contagens["silver_rejeitados"] = salvar(rejeitados_df, "silver_rejeitados")

for nome, qtd in contagens.items():
    print(f"{nome:<20} {qtd:>6}")
if contagens["silver_rejeitados"]:
    display(spark.table("silver_rejeitados").groupBy("tabela", "motivo").count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
