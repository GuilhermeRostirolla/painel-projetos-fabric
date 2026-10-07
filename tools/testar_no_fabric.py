"""Sobe a API simulada dentro da sessão do Fabric e roda o orquestrador contra ela.

    import requests; exec(requests.get("https://raw.githubusercontent.com/GuilhermeRostirolla/painel-projetos-fabric/main/tools/testar_no_fabric.py").text)"""
import io
import os
import subprocess
import sys
import time
import zipfile

import requests

REPOSITORIO = globals().get("REPOSITORIO", "GuilhermeRostirolla/painel-projetos-fabric")
RAMO = globals().get("RAMO", "main")
MODO = globals().get("MODO", "completo")
RECOMECAR = globals().get("RECOMECAR", False)
PORTA = 8765
TOKEN_TESTE = "token-teste-local"

_destino = "/tmp/painel_api"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target", f"{_destino}/libs",
                "-r", "/dev/stdin"], input="\n".join(requests.get(
                    f"https://raw.githubusercontent.com/{REPOSITORIO}/{RAMO}/requirements-api.txt", timeout=60
                ).text.splitlines()).encode(), check=True)

_zip = requests.get(f"https://github.com/{REPOSITORIO}/archive/{RAMO}.zip", timeout=120)
_zip.raise_for_status()
with zipfile.ZipFile(io.BytesIO(_zip.content)) as z:
    _raiz = z.namelist()[0].rstrip("/")
    z.extractall(_destino)
_codigo = f"{_destino}/{_raiz}"

_ambiente = dict(os.environ, PYTHONPATH=f"{_destino}/libs:{_codigo}", API_TOKEN=TOKEN_TESTE, TAXA_FALHA="0.05")
_processo = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.app:criar_app", "--factory",
                              "--host", "127.0.0.1", "--port", str(PORTA), "--log-level", "warning"],
                             cwd=_codigo, env=_ambiente)
URL = f"http://127.0.0.1:{PORTA}"
for _ in range(60):
    try:
        if requests.get(f"{URL}/saude", timeout=2).ok:
            break
    except requests.ConnectionError:
        time.sleep(1)
else:
    raise RuntimeError("a API de teste não subiu")
_meta = requests.get(f"{URL}/v1/meta", headers={"Authorization": f"Bearer {TOKEN_TESTE}"}, timeout=10).json()
print(f"API de teste no ar em {URL}, impressão digital {_meta['impressao_digital']} (esperado 28e6c08d8addd5f4)")

try:
    if RECOMECAR:
        for _pasta in ("Files/bronze",):
            try:
                notebookutils.fs.rm(_pasta, True)  # noqa: F821
                print(f"apagado {_pasta}")
            except Exception as _erro:
                print(f"{_pasta} não existia ({type(_erro).__name__})")
    _retorno = notebookutils.notebook.run("nb_00_orquestrador", 3600, {  # noqa: F821
        "URL_API": URL, "TOKEN_API": TOKEN_TESTE, "MODO": MODO})
    print(f"orquestrador terminou: {_retorno}")
finally:
    _processo.terminate()
