"""Teste ponta a ponta DENTRO do Fabric, sem publicar a API: sobe a API simulada na própria
sessão Spark (localhost) e roda o orquestrador contra ela.

Numa célula de um notebook do workspace:

    import requests; exec(requests.get("https://raw.githubusercontent.com/GuilhermeRostirolla/painel-projetos-fabric/main/tools/testar_no_fabric.py").text)

Serve para validar Spark, Delta, o modelo e as medidas antes de a API estar publicada no Render.
Depois que a API estiver no ar, use o nb_00_orquestrador normalmente, com a URL pública.
"""
import io
import subprocess
import sys
import threading
import time
import zipfile

import requests

REPOSITORIO = globals().get("REPOSITORIO", "GuilhermeRostirolla/painel-projetos-fabric")
RAMO = globals().get("RAMO", "main")
MODO = globals().get("MODO", "completo")
PORTA = 8765
TOKEN_TESTE = "token-teste-local"  # só vale para a API que sobe aqui, em localhost

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "fastapi", "uvicorn", "Faker==40.41.0"], check=True)

_destino = "/tmp/painel-projetos-fabric"
_zip = requests.get(f"https://github.com/{REPOSITORIO}/archive/refs/heads/{RAMO}.zip", timeout=120)
_zip.raise_for_status()
with zipfile.ZipFile(io.BytesIO(_zip.content)) as z:
    _raiz = z.namelist()[0].rstrip("/")
    z.extractall("/tmp")
_codigo = f"/tmp/{_raiz}"
if _codigo not in sys.path:
    sys.path.insert(0, _codigo)

import uvicorn  # noqa: E402

from api.app import criar_app  # noqa: E402
from simulador.cenario import Config, gerar, impressao_digital  # noqa: E402

print(f"impressão digital do cenário aqui: {impressao_digital(gerar(Config()))} (esperado f5e3d8e3c86d9d89)")

_servidor = uvicorn.Server(uvicorn.Config(criar_app(token=TOKEN_TESTE, taxa_falha=0.05),
                                          host="127.0.0.1", port=PORTA, log_level="warning"))
threading.Thread(target=_servidor.run, daemon=True).start()
while not _servidor.started:
    time.sleep(0.2)
print(f"API de teste no ar em http://127.0.0.1:{PORTA}")

try:
    _retorno = notebookutils.notebook.run("nb_00_orquestrador", 3600, {  # noqa: F821
        "URL_API": f"http://127.0.0.1:{PORTA}", "TOKEN_API": TOKEN_TESTE, "MODO": MODO})
    print(f"orquestrador terminou: {_retorno}")
finally:
    _servidor.should_exit = True
