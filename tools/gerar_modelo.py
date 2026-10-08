"""Gera o modelo semântico (TMDL) em fabric/PainelProjetos.SemanticModel.

    python tools/gerar_modelo.py [--endpoint ... --endpoint-id ...]"""
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
OCULTAS = {
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

RELACIONAMENTOS = [
    ("fato_tarefa.projeto_id", "dim_projeto.projeto_id", True),
    ("fato_tarefa.responsavel_id", "dim_pessoa.pessoa_id", True),
    ("fato_tarefa.status", "dim_status.status", True),
    ("fato_tarefa.data_criacao", "dim_data.data", True),
    ("fato_tarefa.data_conclusao", "dim_data.data", False),
    ("fato_passagem_status.tarefa_id", "fato_tarefa.tarefa_id", True),
    ("fato_passagem_status.data_entrada", "dim_data.data", False),
]

INT, PCT, DIAS, HORAS = "#,0", "0.0%", "#,0.0", "#,0"
REF = "MAX ( ref_parametros[data_referencia] )"

CRONOGRAMA_COR = """VAR ini = MIN ( dim_data[data] )
VAR fim = MAX ( dim_data[data] )
VAR ref = MAX ( ref_parametros[data_referencia] )
RETURN
    IF (
        ISINSCOPE ( fato_tarefa[titulo] ),
        VAR t_ini = CALCULATE ( MIN ( fato_tarefa[data_criacao] ), REMOVEFILTERS ( dim_data ) )
        VAR t_fim = CALCULATE ( MAX ( fato_tarefa[data_conclusao] ), REMOVEFILTERS ( dim_data ) )
        VAR situacao = CALCULATE ( MAX ( fato_tarefa[status] ), REMOVEFILTERS ( dim_data ) )
        VAR prazo = CALCULATE ( MAX ( fato_tarefa[situacao_prazo] ), REMOVEFILTERS ( dim_data ) )
        VAR ate = IF ( ISBLANK ( t_fim ), ref, t_fim )
        RETURN
            IF (
                NOT ISBLANK ( t_ini ) && t_ini <= fim && ate >= ini,
                SWITCH (
                    TRUE (),
                    situacao = "Concluído", "#5D7398",
                    situacao = "Arquivada", "#364259",
                    situacao = "Impedido", "#C4851A",
                    prazo = "Vencida", "#E44A5D",
                    "#4682F5"
                )
            ),
        IF (
            HASONEVALUE ( dim_projeto[projeto] ),
            VAR p_ini = MAX ( dim_projeto[data_inicio] )
            VAR p_status = MAX ( dim_projeto[status] )
            VAR p_fim =
                SWITCH (
                    TRUE (),
                    NOT ISBLANK ( MAX ( dim_projeto[data_conclusao] ) ), MAX ( dim_projeto[data_conclusao] ),
                    p_status = "Arquivado", MAX ( dim_projeto[data_limite] ),
                    MAX ( MAX ( dim_projeto[data_limite] ), ref )
                )
            RETURN
                IF (
                    p_ini <= fim && p_fim >= ini,
                    SWITCH (
                        TRUE (),
                        MAX ( dim_projeto[situacao_prazo] ) = "Atrasado", "#E44A5D",
                        p_status = "Arquivado", "#364259",
                        p_status = "Concluído", "#5D7398",
                        p_status = "Em espera", "#33415E",
                        "#4682F5"
                    )
                )
        )
    )"""

SEM_CONFERENCIA = {"Cronograma"}

MEDIDAS = {
    "dim_projeto": [
        ("Projetos", "Portfólio", INT, "COUNTROWS ( dim_projeto )"),
        ("Projetos Ativos", "Portfólio", INT,
         'CALCULATE ( [Projetos], dim_projeto[status] IN { "Em execução", "Planejamento" } )'),
        ("Projetos em Execução", "Portfólio", INT, 'CALCULATE ( [Projetos], dim_projeto[status] = "Em execução" )'),
        ("Projetos Concluídos", "Portfólio", INT, 'CALCULATE ( [Projetos], dim_projeto[status] = "Concluído" )'),
        ("Projetos Atrasados", "Prazo", INT, 'CALCULATE ( [Projetos], dim_projeto[situacao_prazo] = "Atrasado" )'),
        ("% Projetos Atrasados", "Prazo", PCT, "DIVIDE ( [Projetos Atrasados], [Projetos Ativos] )"),
        ("% Projetos Entregues no Prazo", "Prazo", PCT,
         'DIVIDE ( CALCULATE ( [Projetos], dim_projeto[situacao_prazo] = "Concluído no prazo" ), [Projetos Concluídos] )'),
        ("Atraso Médio dos Projetos (dias)", "Prazo", DIAS,
         'CALCULATE ( AVERAGE ( dim_projeto[dias_atraso] ), dim_projeto[situacao_prazo] IN { "Atrasado", "Concluído com atraso" } )'),
        ("Horas Orçadas", "Esforço", HORAS, "SUM ( dim_projeto[horas_orcadas] )"),
        ("% Orçamento Consumido", "Esforço", PCT, "DIVIDE ( [Horas Apontadas], [Horas Orçadas] )"),
        ("Orçamento", "Portfólio", '"R$" #,0', "SUM ( dim_projeto[orcamento] )"),
        ("Projetos Farol Vermelho", "Portfólio", INT, 'CALCULATE ( [Projetos], dim_projeto[farol] = "Vermelho" )'),
        ("Projetos de Ideias", "Portfólio", INT, 'CALCULATE ( [Projetos], dim_projeto[origem] = "Ideia" )'),
    ],
    "fato_tarefa": [
        ("Tarefas", "Tarefas", INT, "COUNTROWS ( fato_tarefa )"),
        ("Tarefas Abertas", "Tarefas", INT, "CALCULATE ( [Tarefas], fato_tarefa[aberta] = TRUE () )"),
        ("Tarefas Concluídas", "Tarefas", INT, 'CALCULATE ( [Tarefas], fato_tarefa[status] = "Concluído" )'),
        ("Tarefas Impedidas", "Tarefas", INT, 'CALCULATE ( [Tarefas], fato_tarefa[status] = "Impedido" )'),
        ("Tarefas Vencidas", "Prazo", INT, 'CALCULATE ( [Tarefas], fato_tarefa[situacao_prazo] = "Vencida" )'),
        ("% Abertas Vencidas", "Prazo", PCT,
         "DIVIDE ( [Tarefas Vencidas], CALCULATE ( [Tarefas Abertas], NOT ISBLANK ( fato_tarefa[data_limite] ) ) )"),
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
         'VAR concluidas = FILTER ( fato_tarefa, fato_tarefa[status] = "Concluído" )\n'
         "RETURN\n    DIVIDE ( SUMX ( concluidas, fato_tarefa[horas_apontadas] ), "
         "SUMX ( concluidas, fato_tarefa[estimativa_horas] ) ) - 1"),
        ("Tarefas Criadas", "Período", INT, "[Tarefas]"),
        ("Tarefas Entregues", "Período", INT,
         "CALCULATE ( [Tarefas Concluídas], USERELATIONSHIP ( fato_tarefa[data_conclusao], dim_data[data] ) )"),
        ("Saldo do Período", "Período", "+#,0;-#,0;0", "[Tarefas Criadas] - [Tarefas Entregues]"),
        ("% Tarefas Concluídas", "Tarefas", PCT, "DIVIDE ( [Tarefas Concluídas], [Tarefas] )"),
        ("Cronograma Cor", "Cronograma", None, CRONOGRAMA_COR),
        ("Cronograma", "Cronograma", None, 'IF ( NOT ISBLANK ( [Cronograma Cor] ), " " )'),
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
         'CALCULATE ( [Mudanças de Status], fato_passagem_status[status] = "Impedido" )'),
    ],
    "ref_parametros": [
        ("Data de Referência", "Referência", "dd/MM/yyyy", REF),
        ("Texto Referência", "Referência", None, f'"Dados até " & FORMAT ( {REF}, "dd/MM/yyyy" )'),
        ("Contexto Projetos Ativos", "Contexto dos cartões", None,
         '"de " & FORMAT ( [Projetos] + 0, "#,0" ) & " no portfólio"'),
        ("Contexto Projetos Atrasados", "Contexto dos cartões", None,
         'FORMAT ( [% Projetos Atrasados] + 0, "0%" ) & " dos ativos"'),
        ("Contexto Atrasados de Ativos", "Contexto dos cartões", None,
         'FORMAT ( [Projetos Atrasados] + 0, "#,0" ) & " de " & FORMAT ( [Projetos Ativos] + 0, "#,0" ) & " ativos"'),
        ("Contexto Entregues no Prazo", "Contexto dos cartões", None,
         'FORMAT ( CALCULATE ( [Projetos], dim_projeto[situacao_prazo] = "Concluído no prazo" ) + 0, "#,0" )\n'
         '    & " de " & FORMAT ( [Projetos Concluídos] + 0, "#,0" ) & " concluídos"'),
        ("Contexto Tarefas Abertas", "Contexto dos cartões", None,
         'FORMAT ( [Tarefas Impedidas] + 0, "#,0" ) & " impedidas agora"'),
        ("Contexto Tarefas Vencidas", "Contexto dos cartões", None,
         'FORMAT ( [% Abertas Vencidas] + 0, "0%" ) & " das abertas"'),
        ("Contexto Tarefas Concluídas", "Contexto dos cartões", None,
         'FORMAT ( DIVIDE ( [Tarefas Concluídas], [Tarefas] ) + 0, "0%" ) & " de todas as tarefas"'),
        ("Contexto Horas Apontadas", "Contexto dos cartões", None,
         'FORMAT ( DIVIDE ( [Horas Apontadas], [Horas Estimadas] ) - 1, "+0%;-0%;0%" ) & " vs. o estimado"'),
        ("Contexto Orçamento Consumido", "Contexto dos cartões", None,
         'FORMAT ( [% Orçamento Consumido] + 0, "0%" ) & " das horas orçadas já usadas"'),
        ("Texto Orçamento", "Contexto dos cartões", None,
         '"R$ " & FORMAT ( [Orçamento] / 1000000, "#,0.0" ) & " mi"'),
        ("Contexto Projetos de Ideias", "Contexto dos cartões", None,
         'FORMAT ( [Projetos de Ideias] + 0, "#,0" ) & " vieram de ideias"'),
    ],
}


def tag(*partes: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "painel-projetos/" + "/".join(partes)))


def nome_tmdl(nome: str) -> str:
    return nome if nome.replace("_", "").isalnum() and nome.isascii() else "'" + nome.replace("'", "''") + "'"


def bloco_dax(dax: str, recuo: str) -> str:
    if "\n" not in dax:
        return " " + dax
    linhas = "\n".join(recuo + "\t\t" + l for l in dax.splitlines())
    return f" ```\n{linhas}\n{recuo}\t\t```"


def texto_tmdl(valor: str) -> str:
    return '"' + valor.replace('"', '""') + '"' if '"' in valor else valor


def tabela(nome: str, colunas: list[list[str]]) -> str:
    saida = [f"table {nome}", f"\tlineageTag: {tag(nome)}", f"\tsourceLineageTag: [dbo].[{nome}]"]
    if nome == "dim_data":
        saida.append("\tdataCategory: Time")
    saida.append("")
    for medida, pasta, formato, dax in MEDIDAS.get(nome, []):
        saida.append(f"\tmeasure {nome_tmdl(medida)} ={bloco_dax(dax, chr(9))}")
        if formato:
            saida.append(f"\t\tformatString: {texto_tmdl(formato)}")
        saida += [f"\t\tdisplayFolder: {pasta}", f"\t\tlineageTag: {tag(nome, 'medida', medida)}", ""]
    for coluna, tipo in colunas:
        saida += [f"\tcolumn {coluna}", f"\t\tdataType: {TIPOS[tipo]}"]
        if (nome, coluna) == ("dim_data", "data"):
            saida.append("\t\tisKey")
        formato = FORMATO_COLUNA.get((nome, coluna), FORMATOS.get(tipo))
        if formato:
            saida.append(f"\t\tformatString: {texto_tmdl(formato)}")
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
    saida = []
    for de, para, ativo in RELACIONAMENTOS:
        saida.append(f"relationship {tag('rel', de, para)}")
        if not ativo:
            saida.append("\tisActive: false")
        saida += [f"\tfromColumn: {de}", f"\ttoColumn: {para}", ""]
    return "\n".join(saida)


PAPEIS = {"TransformacaoDigital": "Transformação Digital", "DadosAnalytics": "Dados & Analytics",
          "ExcelenciaOperacional": "Excelência Operacional", "CrescimentoComercial": "Crescimento Comercial",
          "PessoasCultura": "Pessoas & Cultura", "ExperienciaCliente": "Experiência do Cliente",
          "SustentabilidadeESG": "Sustentabilidade & ESG", "InovacaoAberta": "Inovação Aberta"}


def papel(nome: str, portfolio: str) -> str:
    return (f"role {nome}\n\tmodelPermission: read\n\n"
            f'\ttablePermission dim_projeto = [portfolio] = "{portfolio}"\n\n'
            f"\tannotation PBI_Id = {tag('papel', nome).replace('-', '')}\n\n")


def gerar(endpoint: str = ENDPOINT, endpoint_id: str = ENDPOINT_ID, destino: Path = DESTINO) -> None:
    schema = json.loads((RAIZ / "tools" / "schema_gold.json").read_text())
    definicao = destino / "definition"
    (definicao / "tables").mkdir(parents=True, exist_ok=True)
    (definicao / "roles").mkdir(parents=True, exist_ok=True)
    for antigo in [*(definicao / "tables").glob("*.tmdl"), *(definicao / "roles").glob("*.tmdl")]:
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
        + "".join(f"ref table {t}\n" for t in TABELAS) + "\n"
        + "".join(f"ref role {r}\n" for r in PAPEIS) + "\n")
    (definicao / "expressions.tmdl").write_text(
        "expression DatabaseQuery =\n\t\tlet\n"
        f'\t\t    database = Sql.Database("{endpoint}", "{endpoint_id}")\n'
        "\t\tin\n\t\t    database\n"
        f"\tlineageTag: {tag('expressao')}\n\n\tannotation PBI_IncludeFutureArtifacts = False\n\n")
    (definicao / "relationships.tmdl").write_text(relacionamentos(schema))
    for nome in TABELAS:
        (definicao / "tables" / f"{nome}.tmdl").write_text(tabela(nome, schema[nome]))
    for nome, portfolio in PAPEIS.items():
        (definicao / "roles" / f"{nome}.tmdl").write_text(papel(nome, portfolio))


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--endpoint", default=ENDPOINT, help="ex.: xxxx.datawarehouse.fabric.microsoft.com")
    args.add_argument("--endpoint-id", default=ENDPOINT_ID, help="id do SQL analytics endpoint (um GUID)")
    a = args.parse_args()
    gerar(a.endpoint, a.endpoint_id)
    n = sum(len(m) for m in MEDIDAS.values())
    print(f"modelo gerado em {DESTINO.relative_to(RAIZ)}: {len(TABELAS)} tabelas, "
          f"{len(RELACIONAMENTOS)} relacionamentos, {n} medidas, {len(PAPEIS)} papéis de segurança")


if __name__ == "__main__":
    main()
