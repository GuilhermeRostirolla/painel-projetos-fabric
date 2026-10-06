"""Roda os notebooks do Fabric na sua máquina, sem Fabric.

Sobe a API simulada numa porta local, cria uma sessão Spark e executa o orquestrador
(nb_00) exatamente como está no repositório. Só os parâmetros de caminho e formato são
trocados: arquivos vão para <pasta>/Files e tabelas para <pasta>/Tables, em Parquet
(o Delta exige jars que o Fabric já traz).

    python tools/rodar_local.py --pasta .local/lakehouse --modo completo
    python tools/rodar_local.py --pasta .local/lakehouse --modo incremental --data-referencia 2026-09-30
"""
import argparse
import re
import shutil
import socket
import sys
import threading
import time
from datetime import date
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

MARCADOR = re.compile(r"^# (CELL|PARAMETERS CELL|MARKDOWN|METADATA) \*+\s*$")


class _Saida(Exception):
    def __init__(self, valor):
        self.valor = valor


def celulas(caminho: Path) -> list[tuple[str, str]]:
    """Lê um notebook-content.py do Fabric e devolve [(tipo, código)], sem markdown e metadados."""
    tipo, linhas, saida = None, [], []
    for linha in caminho.read_text(encoding="utf-8").splitlines() + ["# METADATA ****"]:
        m = MARCADOR.match(linha)
        if m:
            if tipo in ("CELL", "PARAMETERS CELL"):
                saida.append((tipo, "\n".join(linhas)))
            tipo, linhas = m.group(1), []
        else:
            linhas.append(linha)
    return saida


class Executor:
    def __init__(self, spark, sobrescrever: dict):
        self.spark = spark
        self.sobrescrever = sobrescrever  # parâmetros locais aplicados a todo notebook
        self.notebookutils = SimpleNamespace(
            notebook=SimpleNamespace(run=self.rodar, exit=self._sair),
            credentials=SimpleNamespace(getSecret=self._segredo),
        )

    @staticmethod
    def _sair(valor):
        raise _Saida(valor)

    @staticmethod
    def _segredo(*_):
        raise RuntimeError("Key Vault não existe localmente: passe TOKEN_API")

    def rodar(self, nome: str, _tempo_limite: int = 0, parametros: dict | None = None):
        caminho = RAIZ / "fabric" / f"{nome}.Notebook" / "notebook-content.py"
        espaco = {"spark": self.spark, "notebookutils": self.notebookutils,
                  "display": lambda df: df.show(50, truncate=False), "__name__": nome}
        print(f"\n=== {nome}")
        try:
            for tipo, codigo in celulas(caminho):
                exec(compile(codigo, f"{nome}", "exec"), espaco)
                if tipo == "PARAMETERS CELL":  # como o Fabric: valores passados vencem os padrões
                    for chave, valor in {**self.sobrescrever, **(parametros or {})}.items():
                        if chave in espaco:
                            espaco[chave] = valor
        except _Saida as saida:
            return saida.valor
        return None


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def subir_api(data_referencia: date, token: str, taxa_falha: float) -> str:
    import uvicorn

    from api.app import criar_app
    from simulador.cenario import Config

    porta = _porta_livre()
    app = criar_app(Config(data_referencia=data_referencia), token=token, taxa_falha=taxa_falha)
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning"))
    threading.Thread(target=servidor.run, daemon=True).start()
    while not servidor.started:
        time.sleep(0.05)
    return f"http://127.0.0.1:{porta}"


def criar_spark(pasta: Path):
    from pyspark.sql import SparkSession
    return (SparkSession.builder.master("local[2]").appName("painel-projetos-local")
            .config("spark.sql.warehouse.dir", str(pasta / "Tables"))
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.ui.enabled", "false")
            .getOrCreate())


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--pasta", type=Path, default=RAIZ / ".local" / "lakehouse")
    args.add_argument("--modo", choices=("completo", "incremental"), default="completo")
    args.add_argument("--data-referencia", type=date.fromisoformat, default=date(2026, 9, 30))
    args.add_argument("--taxa-falha", type=float, default=0.05, help="fração de chamadas que recebem 429")
    args.add_argument("--limpar", action="store_true", help="apaga o lakehouse local antes (bronze inclusive)")
    a = args.parse_args()

    pasta = a.pasta.resolve()
    if a.limpar:
        shutil.rmtree(pasta, ignore_errors=True)
    # silver e gold são reconstruídas inteiras a cada execução; o estado que importa mora em Files
    shutil.rmtree(pasta / "Tables", ignore_errors=True)
    (pasta / "Files").mkdir(parents=True, exist_ok=True)

    token = "token-local"
    url = subir_api(a.data_referencia, token, a.taxa_falha)
    spark = criar_spark(pasta)
    spark.sparkContext.setLogLevel("ERROR")
    executor = Executor(spark, {"PASTA_ARQUIVOS": str(pasta / "Files"),
                                "PASTA_ARQUIVOS_SPARK": str(pasta / "Files"),
                                "FORMATO_TABELA": "parquet"})
    inicio = time.time()
    executor.rodar("nb_00_orquestrador", parametros={"URL_API": url, "TOKEN_API": token, "MODO": a.modo})
    print(f"\nconcluído em {time.time() - inicio:.0f}s · lakehouse local em {pasta}")


if __name__ == "__main__":
    main()
