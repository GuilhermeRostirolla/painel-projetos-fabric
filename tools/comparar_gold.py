"""Compara as tabelas gold de dois lakehouses locais linha a linha.

    python tools/comparar_gold.py <pasta_a> <pasta_b>

Sai com erro se alguma tabela diferir. Usado para provar que a carga incremental chega
ao mesmo resultado que a carga completa.
"""
import sys
from pathlib import Path

from pyspark.sql import SparkSession

TABELAS = ("fato_tarefa", "fato_passagem_status", "dim_projeto", "dim_pessoa",
           "dim_status", "dim_data", "ref_parametros", "silver_rejeitados")
IGNORAR = {"processado_em"}  # muda a cada execução


def main(a: Path, b: Path) -> int:
    spark = SparkSession.builder.master("local[2]").config("spark.ui.enabled", "false").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    falhas = 0
    for nome in TABELAS:
        da = spark.read.parquet(str(a / "Tables" / nome))
        db = spark.read.parquet(str(b / "Tables" / nome))
        colunas = [c for c in da.columns if c not in IGNORAR]
        if colunas != [c for c in db.columns if c not in IGNORAR]:
            print(f"DIFERE  {nome}: colunas diferentes")
            falhas += 1
            continue
        so_a = da.select(colunas).exceptAll(db.select(colunas)).count()
        so_b = db.select(colunas).exceptAll(da.select(colunas)).count()
        ok = so_a == so_b == 0
        falhas += not ok
        print(f"{'igual ' if ok else 'DIFERE'}  {nome:<22} {da.count():>6} linhas"
              + ("" if ok else f" (só em A: {so_a}, só em B: {so_b})"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
