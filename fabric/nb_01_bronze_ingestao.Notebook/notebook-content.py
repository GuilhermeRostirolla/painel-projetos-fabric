# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # 01 - Bronze
#
# Ingestão da API. Grava cada página como veio (JSON) em Files/bronze, com marca d'água por recurso para a carga incremental.
# A marca só avança no fim, quando todos os recursos foram gravados.

# PARAMETERS CELL ********************

URL_API = "https://api-projetos-demo.onrender.com"
TOKEN_API = ""
KEY_VAULT_URL = ""
NOME_SEGREDO = "token-api-projetos"
MODO = "incremental"
PASTA_ARQUIVOS = "/lakehouse/default/Files"
TAMANHO_PAGINA = 500

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests

RECURSOS = {
    "equipes": None,
    "pessoas": None,
    "projetos": "atualizado_em",
    "tarefas": "atualizado_em",
    "historico": "ocorrido_em",
}
SOBREPOSICAO = timedelta(minutes=5)
MAX_TENTATIVAS = 8

if not os.path.isdir(PASTA_ARQUIVOS):
    raise RuntimeError(f"{PASTA_ARQUIVOS} não existe: anexe o lakehouse como padrão deste notebook "
                       "(painel Explorer > Lakehouses > Adicionar)")

BRONZE = os.path.join(PASTA_ARQUIVOS, "bronze")
CONTROLE = os.path.join(BRONZE, "_controle")
ARQ_MARCA = os.path.join(CONTROLE, "marca_dagua.json")

agora = datetime.now(timezone.utc)
EXECUCAO = agora.strftime("%Y%m%dT%H%M%SZ")
DATA_CARGA = agora.strftime("%Y-%m-%d")
print(f"execução {EXECUCAO} | modo {MODO} | API {URL_API}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def obter_token() -> str:
    if TOKEN_API:
        return TOKEN_API
    if not KEY_VAULT_URL:
        raise ValueError("informe TOKEN_API ou KEY_VAULT_URL")
    return notebookutils.credentials.getSecret(KEY_VAULT_URL, NOME_SEGREDO)


sessao = requests.Session()
sessao.headers.update({"Authorization": f"Bearer {obter_token()}", "Accept": "application/json"})


def chamar(url: str, params: dict | None = None) -> dict:
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            r = sessao.get(url, params=params, timeout=90)
        except (requests.ConnectionError, requests.Timeout) as erro:
            espera, motivo = 2 ** tentativa, type(erro).__name__
        else:
            if r.status_code == 200:
                return r.json()
            if r.status_code in (401, 403):
                raise PermissionError(f"API recusou o token ({r.status_code}): confira o segredo")
            if r.status_code != 429 and r.status_code < 500:
                raise RuntimeError(f"erro {r.status_code} em {r.url}: {r.text[:300]}")
            espera = int(r.headers.get("Retry-After", 2 ** tentativa))
            motivo = f"HTTP {r.status_code}"
        if tentativa == MAX_TENTATIVAS:
            raise RuntimeError(f"desisti de {url} após {MAX_TENTATIVAS} tentativas ({motivo})")
        print(f"  {motivo}: nova tentativa em {espera}s")
        time.sleep(min(espera, 60))


def gravar_json(caminho: str, conteudo: dict) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    temporario = caminho + ".tmp"
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False)
    os.replace(temporario, caminho)


def ler_marca() -> dict:
    if MODO == "completo" or not os.path.exists(ARQ_MARCA):
        return {}
    with open(ARQ_MARCA, encoding="utf-8") as f:
        return json.load(f)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

marca_anterior = ler_marca()
marca_nova = dict(marca_anterior)
resumo = []

meta = chamar(f"{URL_API}/v1/meta")
gravar_json(os.path.join(BRONZE, "meta", f"data_carga={DATA_CARGA}", f"{EXECUCAO}.json"), meta)

for recurso, campo_data in RECURSOS.items():
    inicio = time.time()
    params = {"tamanho": TAMANHO_PAGINA}
    desde = marca_anterior.get(recurso) if campo_data else None
    if desde:
        params["atualizado_desde"] = (datetime.fromisoformat(desde) - SOBREPOSICAO).isoformat()

    pagina, registros, maior_data = 1, 0, desde
    url = f"{URL_API}/v1/{recurso}"
    while url:
        corpo = chamar(url, params if pagina == 1 else None)
        corpo["_execucao"] = EXECUCAO
        corpo["_modo"] = "incremental" if desde else "completo"
        destino = os.path.join(BRONZE, recurso, f"data_carga={DATA_CARGA}", f"{EXECUCAO}_p{pagina:04d}.json")
        gravar_json(destino, corpo)
        registros += len(corpo["dados"])
        if campo_data:
            for linha in corpo["dados"]:
                if maior_data is None or datetime.fromisoformat(linha[campo_data]) > datetime.fromisoformat(maior_data):
                    maior_data = linha[campo_data]
        url = f"{URL_API}{corpo['proxima']}" if corpo["proxima"] else None
        pagina += 1

    if campo_data and maior_data:
        marca_nova[recurso] = maior_data
    resumo.append({"recurso": recurso, "modo": "incremental" if desde else "completo",
                   "paginas": pagina - 1, "registros": registros, "desde": desde,
                   "segundos": round(time.time() - inicio, 1)})
    print(f"{recurso:<10} {registros:>6} registros em {pagina - 1} página(s)")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

gravar_json(os.path.join(CONTROLE, "execucoes", f"{EXECUCAO}.json"),
            {"execucao": EXECUCAO, "url_api": URL_API, "modo": MODO,
             "data_referencia": meta["data_referencia"], "recursos": resumo})
gravar_json(ARQ_MARCA, marca_nova)

total = sum(r["registros"] for r in resumo)
print(f"ok: {total} registros gravados no bronze, marca d'água: {marca_nova}")
notebookutils.notebook.exit(json.dumps({"execucao": EXECUCAO, "registros": total}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
