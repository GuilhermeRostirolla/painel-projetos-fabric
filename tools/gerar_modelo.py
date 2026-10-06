"""Gera o modelo semântico Direct Lake (TMDL) em fabric/PainelProjetos.SemanticModel.

Fonte da verdade:
  - colunas e tipos: tools/schema_gold.json (o schema real da gold; um teste garante que não envelheceu)
  - relacionamentos, formatação e medidas: definidos aqui embaixo

    python tools/gerar_modelo.py

O modelo lê as tabelas da gold pelo SQL analytics endpoint do lakehouse. Os dois valores do
endpoint ficam em fabric/PainelProjetos.SemanticModel/definition/expressions.tmdl
(ou use --endpoint e --endpoint-id para já gerar preenchido).
"""
import argparse
import json
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "fabric" / "PainelProjetos.SemanticModel"
NOME = "PainelProjetos"
ENDPOINT, ENDPOINT_ID = "COLE_AQUI_O_SQL_ENDPOINT", "COLE_AQUI_O_ID_DO_SQL_ENDPOINT"

TIPOS = {"string": "string", "date": "dateTime", "timestamp": "dateTime", "double": "double",
         "int": "int64", "bigint": "int64", "boolean": "boolean"}
FORMATOS = {"date": "dd/MM/yyyy", "timestamp": "dd/MM/yyyy HH:mm", "double": "#,0.0",
            "int": "0", "bigint": "0"}

TABELAS = ["fato_tarefa", "fato_passagem_status", "dim_projeto", "dim_pessoa",
           "dim_status", "dim_data", "ref_parametros"]
OCULTAS = {  # chaves e colunas técnicas: o usuário filtra pelas dimensões
    "fato_tarefa": {"tarefa_id", "projeto_id", "responsavel_id", "status", "data_criacao", "data_conclusao"},
    "fato_passagem_status": {"passagem_id", "tarefa_id", "projeto_id", "pessoa_id", "ordem_etapa", "sequencia"},
    "dim_projeto": {"projeto_id"},
    "dim_pessoa": {"pessoa_id"},
    "dim_status": {"ordem"},
    "dim_data": {"ano_mes", "dia_semana"},
    "ref_parametros": {"processado_em"},
}
ORDENAR_POR = {("dim_data", "mes_ano"): "ano_mes", ("dim_data", "dia_semana_nome"): "dia_semana",
               ("dim_status", "status"): "ordem", ("fato_passagem_status", "status"): "ordem_etapa"}
FORMATO_COLUNA = {("dim_projeto", "percentual_prazo_decorrido"): "0%", ("dim_data", "ano"): "0"}

# (de, para, ativo). Filtros de projeto, pessoa e data chegam às passagens através da fato_tarefa.
RELACIONAMENTOS = [
    ("fato_tarefa.projeto_id", "dim_projeto.projeto_id", True),
    ("fato_tarefa.responsavel_id", "dim_pessoa.pessoa_id", True),
    ("fato_tarefa.status", "dim_status.status", True),
    ("fato_tarefa.data_criacao", "dim_data.data", True),
    ("fato_tarefa.data_conclusao", "dim_data.data", False),       # USERELATIONSHIP em "Tarefas Entregues"
    ("fato_passagem_status.tarefa_id", "fato_tarefa.tarefa_id", True),
    ("fato_passagem_status.data_entrada", "dim_data.data", False),  # "Mudanças de Status"
]

INT, PCT, DIAS, HORAS = "#,0", "0.0%", "#,0.0", "#,0"
REF = "MAX ( ref_parametros[data_referencia] )"

# tabela -> [(nome, pasta, formato, DAX)]
MEDIDAS = {
    "dim_projeto": [
        ("Projetos", "Portfólio", INT, "COUNTROWS ( dim_projeto )"),
        ("Projetos Ativos", "Portfólio", INT,
         'CALCULATE ( [Projetos], dim_projeto[status] IN { "Em Andamento", "Planejamento" } )'),
        ("Projetos em Andamento", "Portfólio", INT, 'CALCULATE ( [Projetos], dim_projeto[status] = "Em Andamento" )'),
        ("Projetos Concluídos", "Portfólio", INT, 'CALCULATE ( [Projetos], dim_projeto[status] = "Concluído" )'),
        ("Projetos Atrasados", "Prazo", INT, 'CALCULATE ( [Projetos], dim_projeto[situacao_prazo] = "Atrasado" )'),
        ("% Projetos Atrasados", "Prazo", PCT, "DIVIDE ( [Projetos Atrasados], [Projetos Ativos] )"),
        ("% Projetos Entregues no Prazo", "Prazo", PCT,
         'DIVIDE ( CALCULATE ( [Projetos], dim_projeto[situacao_prazo] = "Concluído no prazo" ), [Projetos Concluídos] )'),
        ("Atraso Médio dos Projetos (dias)", "Prazo", DIAS,
         'CALCULATE ( AVERAGE ( dim_projeto[dias_atraso] ), dim_projeto[situacao_prazo] IN { "Atrasado", "Concluído com atraso" } )'),
        ("Horas Orçadas", "Esforço", HORAS, "SUM ( dim_projeto[horas_orcadas] )"),
        ("% Orçamento Consumido", "Esforço", PCT, "DIVIDE ( [Horas Apontadas], [Horas Orçadas] )"),
    ],
    "fato_tarefa": [
        ("Tarefas", "Tarefas", INT, "COUNTROWS ( fato_tarefa )"),
        ("Tarefas Abertas", "Tarefas", INT, "CALCULATE ( [Tarefas], fato_tarefa[aberta] = TRUE () )"),
        ("Tarefas Concluídas", "Tarefas", INT, 'CALCULATE ( [Tarefas], fato_tarefa[status] = "Concluída" )'),
        ("Tarefas Bloqueadas", "Tarefas", INT, 'CALCULATE ( [Tarefas], fato_tarefa[status] = "Bloqueada" )'),
        ("Tarefas Vencidas", "Prazo", INT, 'CALCULATE ( [Tarefas], fato_tarefa[situacao_prazo] = "Vencida" )'),
        ("% Abertas Vencidas", "Prazo", PCT,
         "DIVIDE ( [Tarefas Vencidas], CALCULATE ( [Tarefas Abertas], NOT ISBLANK ( fato_tarefa[data_prazo] ) ) )"),
        ("% Entregues no Prazo", "Prazo", PCT,
         'DIVIDE (\n    CALCULATE ( [Tarefas], fato_tarefa[situacao_prazo] = "Concluída no prazo" ),\n'
         '    CALCULATE ( [Tarefas], fato_tarefa[situacao_prazo] IN { "Concluída no prazo", "Concluída com atraso" } )\n)'),
        ("Atraso Médio das Tarefas (dias)", "Prazo", DIAS,
         'CALCULATE ( AVERAGE ( fato_tarefa[dias_atraso] ), fato_tarefa[situacao_prazo] IN { "Vencida", "Concluída com atraso" } )'),
        ("Lead Time Médio (dias)", "Tempo", DIAS, "AVERAGE ( fato_tarefa[lead_time_dias] )"),
        ("Ciclo Médio (dias)", "Tempo", DIAS, "AVERAGE ( fato_tarefa[ciclo_dias] )"),
        ("Ciclo Mediano (dias)", "Tempo", DIAS, "MEDIAN ( fato_tarefa[ciclo_dias] )"),
        ("Idade Média das Abertas (dias)", "Tempo", DIAS, "AVERAGE ( fato_tarefa[idade_dias] )"),
        ("Dias Bloqueada", "Tempo", DIAS, "SUM ( fato_tarefa[dias_bloqueada] )"),
        ("% Concluídas com Retrabalho", "Tempo", PCT,
         "DIVIDE ( CALCULATE ( [Tarefas Concluídas], fato_tarefa[qtd_retrabalho] > 0 ), [Tarefas Concluídas] )"),
        ("Horas Estimadas", "Esforço", HORAS, "SUM ( fato_tarefa[estimativa_horas] )"),
        ("Horas Apontadas", "Esforço", HORAS, "SUM ( fato_tarefa[horas_apontadas] )"),
        ("Desvio de Esforço %", "Esforço", "+0.0%;-0.0%;0.0%",
         'VAR concluidas = FILTER ( fato_tarefa, fato_tarefa[status] = "Concluída" )\n'
         "RETURN\n    DIVIDE ( SUMX ( concluidas, fato_tarefa[horas_apontadas] ), "
         "SUMX ( concluidas, fato_tarefa[estimativa_horas] ) ) - 1"),
        ("Tarefas Criadas", "Período", INT, "[Tarefas]"),
        ("Tarefas Entregues", "Período", INT,
         "CALCULATE ( [Tarefas Concluídas], USERELATIONSHIP ( fato_tarefa[data_conclusao], dim_data[data] ) )"),
        ("Saldo do Período", "Período", "+#,0;-#,0;0", "[Tarefas Criadas] - [Tarefas Entregues]"),
    ],
    "fato_passagem_status": [
        ("Tempo Médio na Etapa (dias)", "Fluxo", DIAS,
         "CALCULATE ( AVERAGE ( fato_passagem_status[dias_na_etapa] ), fato_passagem_status[etapa_atual] = FALSE () )"),
        ("Tarefas Paradas na Etapa", "Fluxo", INT,
         "CALCULATE (\n    DISTINCTCOUNT ( fato_passagem_status[tarefa_id] ),\n"
         "    fato_passagem_status[etapa_atual] = TRUE (),\n    fato_passagem_status[etapa_final] = FALSE ()\n)"),
        ("Paradas há mais de 15 dias", "Fluxo", INT,
         "CALCULATE ( [Tarefas Paradas na Etapa], fato_passagem_status[dias_na_etapa] > 15 )"),
        ("Mudanças de Status", "Fluxo", INT,
         "// conta pela data da mudança, não pela data de criação da tarefa\n"
         "CALCULATE (\n    COUNTROWS ( fato_passagem_status ),\n"
         "    USERELATIONSHIP ( fato_passagem_status[data_entrada], dim_data[data] ),\n"
         "    CROSSFILTER ( fato_tarefa[data_criacao], dim_data[data], NONE )\n)"),
        ("Bloqueios no Período", "Fluxo", INT,
         'CALCULATE ( [Mudanças de Status], fato_passagem_status[status] = "Bloqueada" )'),
    ],
    "ref_parametros": [
        ("Data de Referência", "Referência", "dd/MM/yyyy", REF),
        ("Texto Referência", "Referência", None, f'"Dados até " & FORMAT ( {REF}, "dd/MM/yyyy" )'),
    ],
}


def tag(*partes: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "painel-projetos/" + "/".join(partes)))


def nome_tmdl(nome: str) -> str:
    return nome if nome.replace("_", "").isalnum() and nome.isascii() else "'" + nome.replace("'", "''") + "'"


def bloco_dax(dax: str, recuo: str) -> str:
    if "\n" not in dax:
        return " " + dax
    # mesmo recuo do modelo do Painel de Ideias: corpo dois níveis abaixo da medida
    linhas = "\n".join(recuo + "\t\t" + l for l in dax.splitlines())
    return f" ```\n{linhas}\n{recuo}\t\t```"


def tabela(nome: str, colunas: list[list[str]]) -> str:
    saida = [f"table {nome}", f"\tlineageTag: {tag(nome)}", f"\tsourceLineageTag: [dbo].[{nome}]"]
    if nome == "dim_data":
        saida.append("\tdataCategory: Time")
    saida.append("")
    for medida, pasta, formato, dax in MEDIDAS.get(nome, []):
        saida.append(f"\tmeasure {nome_tmdl(medida)} ={bloco_dax(dax, chr(9))}")
        if formato:
            saida.append(f"\t\tformatString: {formato}")
        saida += [f"\t\tdisplayFolder: {pasta}", f"\t\tlineageTag: {tag(nome, 'medida', medida)}", ""]
    for coluna, tipo in colunas:
        saida += [f"\tcolumn {coluna}", f"\t\tdataType: {TIPOS[tipo]}"]
        if (nome, coluna) == ("dim_data", "data"):
            saida.append("\t\tisKey")
        formato = FORMATO_COLUNA.get((nome, coluna), FORMATOS.get(tipo))
        if formato:
            saida.append(f"\t\tformatString: {formato}")
        if coluna in OCULTAS.get(nome, set()):
            saida.append("\t\tisHidden")
        saida += [f"\t\tlineageTag: {tag(nome, coluna)}", f"\t\tsourceLineageTag: {coluna}",
                  "\t\tsummarizeBy: none", f"\t\tsourceColumn: {coluna}"]
        if (nome, coluna) in ORDENAR_POR:
            saida.append(f"\t\tsortByColumn: {ORDENAR_POR[(nome, coluna)]}")
        saida += ["", "\t\tannotation SummarizationSetBy = Automatic", ""]
    saida += [f"\tpartition {nome} = entity", "\t\tmode: directLake", "\t\tsource",
              f"\t\t\tentityName: {nome}", "\t\t\tschemaName: dbo", "\t\t\texpressionSource: DatabaseQuery", ""]
    return "\n".join(saida)


def relacionamentos(schema: dict) -> str:
    tipos = {f"{t}.{c}": tp for t, cols in schema.items() for c, tp in cols}
    saida = []
    for de, para, ativo in RELACIONAMENTOS:
        saida.append(f"relationship {tag('rel', de, para)}")
        if not ativo:
            saida.append("\tisActive: false")
        # sem joinOnDateBehavior: Direct Lake não aceita relacionamento "datetime-to-date";
        # a gold já grava essas colunas como data pura, então a igualdade simples basta
        saida += [f"\tfromColumn: {de}", f"\ttoColumn: {para}", ""]
    return "\n".join(saida)


def gerar(endpoint: str = ENDPOINT, endpoint_id: str = ENDPOINT_ID, destino: Path = DESTINO) -> None:
    schema = json.loads((RAIZ / "tools" / "schema_gold.json").read_text())
    definicao = destino / "definition"
    (definicao / "tables").mkdir(parents=True, exist_ok=True)
    for antigo in (definicao / "tables").glob("*.tmdl"):
        antigo.unlink()

    (destino / ".platform").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NOME},
        "config": {"version": "2.0", "logicalId": tag("modelo")}}, indent=2) + "\n")
    (destino / "definition.pbism").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}}, indent=2) + "\n")
    (definicao / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1604\n\n")
    (definicao / "model.tmdl").write_text(
        "model Model\n\tculture: pt-BR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n\tsourceQueryCulture: pt-BR\n\n"
        + "".join(f"ref table {t}\n" for t in TABELAS) + "\n")
    (definicao / "expressions.tmdl").write_text(
        "expression DatabaseQuery =\n\t\tlet\n"
        f'\t\t    database = Sql.Database("{endpoint}", "{endpoint_id}")\n'
        "\t\tin\n\t\t    database\n"
        f"\tlineageTag: {tag('expressao')}\n\n\tannotation PBI_IncludeFutureArtifacts = False\n\n")
    (definicao / "relationships.tmdl").write_text(relacionamentos(schema))
    for nome in TABELAS:
        (definicao / "tables" / f"{nome}.tmdl").write_text(tabela(nome, schema[nome]))


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--endpoint", default=ENDPOINT, help="ex.: xxxx.datawarehouse.fabric.microsoft.com")
    args.add_argument("--endpoint-id", default=ENDPOINT_ID, help="id do SQL analytics endpoint (um GUID)")
    a = args.parse_args()
    gerar(a.endpoint, a.endpoint_id)
    n = sum(len(m) for m in MEDIDAS.values())
    print(f"modelo gerado em {DESTINO.relative_to(RAIZ)}: {len(TABELAS)} tabelas, "
          f"{len(RELACIONAMENTOS)} relacionamentos, {n} medidas")


if __name__ == "__main__":
    main()
