"""Instala (ou atualiza) os notebooks deste repositório num workspace do Fabric.

Roda DENTRO de um notebook do Fabric, no workspace de destino. Numa célula:

    import requests; exec(requests.get("https://raw.githubusercontent.com/GuilhermeRostirolla/painel-projetos-fabric/main/tools/instalar_no_fabric.py").text)

O que faz:
  - baixa fabric/ipynb/*.ipynb do GitHub
  - já anexa o lakehouse (lh_projetos) como padrão de cada notebook
  - cria cada notebook pela API REST do Fabric, ou atualiza se já existir com o mesmo nome

Alternativa sem script: integração Git do workspace com a pasta fabric/ (exige token do GitHub).
"""
import base64
import json
import time

import requests
from sempy.fabric import FabricRestClient

REPOSITORIO = globals().get("REPOSITORIO", "GuilhermeRostirolla/painel-projetos-fabric")
RAMO = globals().get("RAMO", "main")
NOME_LAKEHOUSE = globals().get("NOME_LAKEHOUSE", "lh_projetos")
NOTEBOOKS = ["nb_00_orquestrador", "nb_01_bronze_ingestao", "nb_02_silver_tratamento",
             "nb_03_gold_modelo", "nb_04_publicar_modelo"]

_cliente = FabricRestClient()
_ws = notebookutils.runtime.context["currentWorkspaceId"]  # noqa: F821 (existe no Fabric)


def _esperar(resposta, o_que):
    if resposta.status_code not in (200, 201, 202):
        raise RuntimeError(f"{o_que}: HTTP {resposta.status_code} {resposta.text[:400]}")
    if resposta.status_code != 202:
        return
    operacao = resposta.headers["x-ms-operation-id"]
    for _ in range(60):
        time.sleep(int(resposta.headers.get("Retry-After", 3)))
        estado = _cliente.get(f"v1/operations/{operacao}").json()
        if estado["status"] == "Succeeded":
            return
        if estado["status"] == "Failed":
            raise RuntimeError(f"{o_que} falhou: {estado.get('error')}")
    raise TimeoutError(o_que)


_lakehouse = next(l for l in _cliente.get(f"v1/workspaces/{_ws}/lakehouses").json()["value"]
                  if l["displayName"] == NOME_LAKEHOUSE)
_existentes = {n["displayName"]: n["id"] for n in _cliente.get(f"v1/workspaces/{_ws}/notebooks").json()["value"]}

for _nome in NOTEBOOKS:
    _url = f"https://raw.githubusercontent.com/{REPOSITORIO}/{RAMO}/fabric/ipynb/{_nome}.ipynb"
    _nb = requests.get(_url, timeout=60).json()
    _nb["metadata"]["dependencies"] = {"lakehouse": {
        "default_lakehouse": _lakehouse["id"],
        "default_lakehouse_name": NOME_LAKEHOUSE,
        "default_lakehouse_workspace_id": _ws,
        "known_lakehouses": [{"id": _lakehouse["id"]}],
    }}
    _definicao = {"format": "ipynb", "parts": [{
        "path": "notebook-content.ipynb",
        "payload": base64.b64encode(json.dumps(_nb, ensure_ascii=False).encode("utf-8")).decode(),
        "payloadType": "InlineBase64"}]}
    if _nome in _existentes:
        _esperar(_cliente.post(f"v1/workspaces/{_ws}/notebooks/{_existentes[_nome]}/updateDefinition",
                               json={"definition": _definicao}), f"atualizar {_nome}")
        print(f"atualizado  {_nome}")
    else:
        _esperar(_cliente.post(f"v1/workspaces/{_ws}/notebooks",
                               json={"displayName": _nome, "definition": _definicao}), f"criar {_nome}")
        print(f"criado      {_nome}")

print(f"\n{len(NOTEBOOKS)} notebooks prontos, todos com {NOME_LAKEHOUSE} como lakehouse padrão")

# Atenção: não deixe estes notebooks abertos no navegador enquanto instala. O editor guarda um
# rascunho em cache e o salvamento automático grava esse rascunho por cima da versão nova.
if globals().get("PUBLICAR", False):
    print("\nrodando nb_04_publicar_modelo (modelo, relatório, medidas e segurança)...")
    print(notebookutils.notebook.run("nb_04_publicar_modelo", 3600))  # noqa: F821
