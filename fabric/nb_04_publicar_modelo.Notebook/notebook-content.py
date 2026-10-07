# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # 04 · Publicar e conferir o modelo, o relatório e a segurança
#
# Cria (ou atualiza) o modelo semântico **PainelProjetos** neste workspace pela API REST do Fabric e depois confere cada medida.
#
# 1. Descobre sozinho o **SQL analytics endpoint** do lakehouse: ninguém precisa copiar endereço nem GUID.
# 2. Baixa o TMDL do repositório no GitHub e troca os dois valores do endpoint.
# 3. Publica a definição e enquadra o modelo (refresh do Direct Lake).
# 3b. Publica o **relatório** (4 páginas, formato PBIR) ligado ao modelo.
# 4. **Roda as 46 medidas em DAX** e compara com `docs/valores_esperados.json`, que foi calculado em SQL sem passar pelo DAX.
#    Se alguma não bater, o notebook falha e mostra qual.
# 5. **Entra como cada papel de segurança** (RLS por equipe) e confere que ele só enxerga os projetos e as tarefas da própria equipe.
#
# Rode depois do orquestrador (a gold precisa existir). Pode rodar de novo sempre que o modelo mudar no repositório.

# PARAMETERS CELL ********************

REPOSITORIO = "GuilhermeRostirolla/painel-projetos-fabric"
RAMO = "main"
NOME_LAKEHOUSE = "lh_projetos"
NOME_MODELO = "PainelProjetos"
CONFERIR_MEDIDAS = True   # só faz sentido com os dados padrão da API (semente 42, referência 30/09/2026)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import base64
import json
import re
import time

import requests
import sempy.fabric as fabric
from sempy.fabric import FabricRestClient

cliente = FabricRestClient()
WORKSPACE = notebookutils.runtime.context["currentWorkspaceId"]
PASTA_MODELO = f"fabric/{NOME_MODELO}.SemanticModel/"


def esperar(resposta, o_que: str):
    """A API do Fabric responde 202 para operações longas; acompanha até terminar."""
    if resposta.status_code not in (200, 201, 202):
        raise RuntimeError(f"{o_que}: HTTP {resposta.status_code} {resposta.text[:500]}")
    if resposta.status_code != 202:
        return
    operacao = resposta.headers["x-ms-operation-id"]
    for _ in range(120):
        time.sleep(int(resposta.headers.get("Retry-After", 5)))
        estado = cliente.get(f"v1/operations/{operacao}").json()
        if estado["status"] == "Succeeded":
            return
        if estado["status"] == "Failed":
            raise RuntimeError(f"{o_que} falhou: {json.dumps(estado.get('error'), ensure_ascii=False)}")
    raise TimeoutError(f"{o_que}: operação {operacao} não terminou em 10 minutos")


# 1. SQL analytics endpoint do lakehouse
lakehouses = cliente.get(f"v1/workspaces/{WORKSPACE}/lakehouses").json()["value"]
lakehouse = next((l for l in lakehouses if l["displayName"] == NOME_LAKEHOUSE), None)
if lakehouse is None:
    raise ValueError(f"lakehouse {NOME_LAKEHOUSE} não encontrado neste workspace")
for _ in range(30):  # logo após criar o lakehouse, o endpoint pode levar alguns minutos para existir
    endpoint = cliente.get(f"v1/workspaces/{WORKSPACE}/lakehouses/{lakehouse['id']}").json() \
        .get("properties", {}).get("sqlEndpointProperties", {})
    if endpoint.get("provisioningStatus") == "Success" and endpoint.get("connectionString"):
        break
    time.sleep(10)
else:
    raise TimeoutError("SQL analytics endpoint ainda não está pronto; rode de novo em alguns minutos")
print(f"SQL endpoint: {endpoint['connectionString']} ({endpoint['id']})")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 2. TMDL do GitHub (repositório público: sem token)
# fixa o commit: o raw.githubusercontent.com guarda o ramo em cache por alguns minutos, e publicar
# logo depois de um push traria arquivos da versão anterior
COMMIT = requests.get(f"https://api.github.com/repos/{REPOSITORIO}/commits/{RAMO}", timeout=60).json()["sha"]
print(f"publicando a partir do commit {COMMIT[:7]} ({RAMO})")
arvore = requests.get(f"https://api.github.com/repos/{REPOSITORIO}/git/trees/{COMMIT}?recursive=1", timeout=60)
arvore.raise_for_status()
caminhos = [i["path"] for i in arvore.json()["tree"]
            if i["type"] == "blob" and i["path"].startswith(PASTA_MODELO) and not i["path"].endswith(".platform")]
partes = []
for caminho in caminhos:
    texto = requests.get(f"https://raw.githubusercontent.com/{REPOSITORIO}/{COMMIT}/{caminho}", timeout=60).text
    if caminho.endswith("expressions.tmdl"):
        texto = re.sub(r'Sql\.Database\("[^"]*", "[^"]*"\)',
                       f'Sql.Database("{endpoint["connectionString"]}", "{endpoint["id"]}")', texto)
    partes.append({"path": caminho[len(PASTA_MODELO):],
                   "payload": base64.b64encode(texto.encode("utf-8")).decode(),
                   "payloadType": "InlineBase64"})
print(f"{len(partes)} arquivos de definição: " + ", ".join(sorted(p["path"] for p in partes)))

# 3. Cria ou atualiza
modelos = cliente.get(f"v1/workspaces/{WORKSPACE}/semanticModels").json()["value"]
existente = next((m for m in modelos if m["displayName"] == NOME_MODELO), None)
definicao = {"definition": {"parts": partes}}
if existente:
    esperar(cliente.post(f"v1/workspaces/{WORKSPACE}/semanticModels/{existente['id']}/updateDefinition",
                         json=definicao), "atualizar o modelo")
    print(f"modelo {NOME_MODELO} atualizado")
else:
    esperar(cliente.post(f"v1/workspaces/{WORKSPACE}/semanticModels",
                         json={"displayName": NOME_MODELO, **definicao}), "criar o modelo")
    print(f"modelo {NOME_MODELO} criado")

# enquadra o Direct Lake nas tabelas atuais (ele também faz isso sozinho quando a gold muda)
fabric.refresh_dataset(NOME_MODELO, workspace=WORKSPACE)
time.sleep(20)
try:
    print(fabric.list_refresh_requests(NOME_MODELO, workspace=WORKSPACE).head(1).to_string())
except Exception as erro:  # só informativo
    print(f"não consegui listar o refresh ({erro}); seguindo para a conferência")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 3b. Relatório (PBIR do repositório), ligado ao modelo deste workspace
PASTA_RELATORIO = f"fabric/{NOME_MODELO}.Report/"
modelo_id = next(m["id"] for m in cliente.get(f"v1/workspaces/{WORKSPACE}/semanticModels").json()["value"]
                 if m["displayName"] == NOME_MODELO)
partes_relatorio = []
for caminho in [i["path"] for i in arvore.json()["tree"] if i["type"] == "blob"
                and i["path"].startswith(PASTA_RELATORIO) and not i["path"].endswith(".platform")]:
    conteudo = requests.get(f"https://raw.githubusercontent.com/{REPOSITORIO}/{COMMIT}/{caminho}", timeout=60).content
    if caminho.endswith("definition.pbir"):
        # no repositório o relatório aponta para a pasta do modelo; aqui, para o modelo publicado
        pbir = json.loads(conteudo)
        pbir["datasetReference"] = {"byConnection": {"connectionString": f"semanticmodelid={modelo_id}"}}
        conteudo = json.dumps(pbir).encode("utf-8")
    partes_relatorio.append({"path": caminho[len(PASTA_RELATORIO):],
                             "payload": base64.b64encode(conteudo).decode(), "payloadType": "InlineBase64"})

relatorios = cliente.get(f"v1/workspaces/{WORKSPACE}/reports").json()["value"]
relatorio = next((r for r in relatorios if r["displayName"] == NOME_MODELO), None)
definicao_relatorio = {"definition": {"format": "PBIR", "parts": partes_relatorio}}
if relatorio:
    esperar(cliente.post(f"v1/workspaces/{WORKSPACE}/reports/{relatorio['id']}/updateDefinition",
                         json=definicao_relatorio), "atualizar o relatório")
    print(f"relatório {NOME_MODELO} atualizado ({len(partes_relatorio)} arquivos)")
else:
    esperar(cliente.post(f"v1/workspaces/{WORKSPACE}/reports",
                         json={"displayName": NOME_MODELO, **definicao_relatorio}), "criar o relatório")
    print(f"relatório {NOME_MODELO} criado ({len(partes_relatorio)} arquivos)")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 4. Cada medida em DAX x valor calculado em SQL
if CONFERIR_MEDIDAS:
    url = f"https://raw.githubusercontent.com/{REPOSITORIO}/{COMMIT}/docs/valores_esperados.json"
    esperado = requests.get(url, timeout=60).json()

    def avaliar(nomes: list[str], filtro: str | None) -> dict:
        colunas = ", ".join(f'"{n}", [{n}]' for n in nomes)
        consulta = f"ROW ( {colunas} )"
        if filtro:
            consulta = f"CALCULATETABLE ( {consulta}, {filtro} )"
        linha = fabric.evaluate_dax(NOME_MODELO, f"EVALUATE {consulta}", workspace=WORKSPACE).iloc[0]
        return {re.sub(r"^\[|\]$", "", str(k)): v for k, v in linha.items()}

    medidas = esperado["medidas"]
    obtido = avaliar([n for n, m in medidas.items() if not m["periodo"]], None)
    obtido |= avaliar([n for n, m in medidas.items() if m["periodo"]],
                      f'dim_data[mes_ano] = "{esperado["mes_ano"]}"')

    falhas = []
    for nome, m in medidas.items():
        dax, sql = obtido.get(nome), m["valor"]
        if isinstance(sql, str):
            ok = str(dax) == sql or (hasattr(dax, "strftime") and dax.strftime("%d/%m/%Y") == sql)
        else:
            ok = dax is not None and abs(float(dax) - sql) <= max(0.006, abs(sql) * 1e-6)
        print(f"{'ok    ' if ok else 'DIFERE'}  {nome:<36} DAX={dax!s:<22} SQL={sql}")
        if not ok:
            falhas.append(nome)
    if falhas:
        raise AssertionError(f"{len(falhas)} medida(s) não bateram: {falhas}")
    print(f"\nas {len(medidas)} medidas batem com o cálculo independente")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 5. Segurança por linha: entra como cada papel e confere o que ele enxerga
if CONFERIR_MEDIDAS:
    consulta = 'EVALUATE ROW ( "Projetos", [Projetos], "Tarefas", [Tarefas], "Tarefas Abertas", [Tarefas Abertas] )'
    falhas = []
    for papel_nome, equipe in esperado["papeis"].items():
        linha = fabric.evaluate_dax(NOME_MODELO, consulta, workspace=WORKSPACE, role=papel_nome).iloc[0]
        visto = {re.sub(r"^\[|\]$", "", str(k)): v for k, v in linha.items()}
        for medida, valor in esperado["por_equipe"][equipe].items():
            ok = visto.get(medida) is not None and int(visto[medida]) == int(valor)
            print(f"{'ok    ' if ok else 'DIFERE'}  papel {papel_nome:<15} {medida:<16} DAX={visto.get(medida)!s:<6} SQL={valor}")
            if not ok:
                falhas.append(f"{papel_nome}/{medida}")
    if falhas:
        raise AssertionError(f"RLS não filtrou como esperado: {falhas}")
    print(f"\nos {len(esperado['papeis'])} papéis de segurança enxergam só a própria equipe")
    # resumo para quem chamar este notebook com notebookutils.notebook.run
    notebookutils.notebook.exit(json.dumps({"medidas_ok": len(medidas), "papeis_ok": len(esperado["papeis"])}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
