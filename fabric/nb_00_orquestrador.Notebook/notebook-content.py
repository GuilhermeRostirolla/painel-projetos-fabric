# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # 00 - Orquestrador
#
# Roda bronze, silver e gold em sequência. É o notebook agendado; se uma etapa falhar, as seguintes não rodam.

# PARAMETERS CELL ********************

URL_API = "https://api-projetos-demo.onrender.com"
KEY_VAULT_URL = ""
NOME_SEGREDO = "token-api-projetos"
TOKEN_API = ""
MODO = "incremental"
TEMPO_LIMITE = 1800

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import time

etapas = [
    ("nb_01_bronze_ingestao", {"URL_API": URL_API, "KEY_VAULT_URL": KEY_VAULT_URL,
                               "NOME_SEGREDO": NOME_SEGREDO, "TOKEN_API": TOKEN_API, "MODO": MODO}),
    ("nb_02_silver_tratamento", {}),
    ("nb_03_gold_modelo", {}),
]

for nome, parametros in etapas:
    inicio = time.time()
    retorno = notebookutils.notebook.run(nome, TEMPO_LIMITE, parametros)
    print(f"{nome:<26} ok em {time.time() - inicio:6.1f}s {retorno or ''}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
