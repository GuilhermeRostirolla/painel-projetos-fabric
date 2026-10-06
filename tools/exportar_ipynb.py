"""Gera fabric/ipynb/*.ipynb a partir dos notebook-content.py (fonte da verdade).

Para quem prefere importar os notebooks no Fabric (Workspace > Importar > Notebook)
em vez de sincronizar a pasta fabric/ pela integração com Git.

    python tools/exportar_ipynb.py
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MARCADOR = re.compile(r"^# (CELL|PARAMETERS CELL|MARKDOWN|METADATA) \*+\s*$")


def blocos(texto: str) -> list[tuple[str, list[str]]]:
    tipo, linhas, saida = None, [], []
    for linha in texto.splitlines() + ["# METADATA ****"]:
        m = MARCADOR.match(linha)
        if m:
            if tipo in ("CELL", "PARAMETERS CELL", "MARKDOWN"):
                while linhas and not linhas[0].strip():
                    linhas.pop(0)
                while linhas and not linhas[-1].strip():
                    linhas.pop()
                saida.append((tipo, linhas))
            tipo, linhas = m.group(1), []
        else:
            linhas.append(linha)
    return saida


def celula(tipo: str, linhas: list[str]) -> dict:
    if tipo == "MARKDOWN":
        texto = [re.sub(r"^# ?", "", l) for l in linhas]
        return {"cell_type": "markdown", "metadata": {}, "source": [l + "\n" for l in texto[:-1]] + texto[-1:]}
    meta = {"microsoft": {"language": "python", "language_group": "synapse_pyspark"}}
    if tipo == "PARAMETERS CELL":
        meta["tags"] = ["parameters"]
    return {"cell_type": "code", "execution_count": None, "metadata": meta, "outputs": [],
            "source": [l + "\n" for l in linhas[:-1]] + linhas[-1:]}


def main() -> None:
    destino = RAIZ / "fabric" / "ipynb"
    destino.mkdir(exist_ok=True)
    for pasta in sorted((RAIZ / "fabric").glob("*.Notebook")):
        nome = pasta.name.removesuffix(".Notebook")
        celulas = [celula(t, l) for t, l in blocos((pasta / "notebook-content.py").read_text(encoding="utf-8"))]
        for i, c in enumerate(celulas):
            c["id"] = f"{nome[:5]}-{i:02d}"   # id fixo: reexportar não gera diff à toa
        nb = {"cells": celulas,
              "metadata": {"kernel_info": {"name": "synapse_pyspark"},
                           "kernelspec": {"name": "synapse_pyspark", "display_name": "Synapse PySpark"},
                           "language_info": {"name": "python"}},
              "nbformat": 4, "nbformat_minor": 5}
        (destino / f"{nome}.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(destino / f"{nome}.ipynb")


if __name__ == "__main__":
    main()
