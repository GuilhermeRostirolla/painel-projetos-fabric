"""Gera o relatório do Power BI (formato PBIR) em fabric/PainelProjetos.Report.

Todas as páginas e visuais estão descritos aqui embaixo; o script escreve os JSON no formato
que o Fabric e o Power BI Desktop leem (o mesmo do Painel de Ideias). Medidas e colunas são
conferidas contra o modelo semântico pelos testes, então o relatório não aponta para campo
que não existe.

    python tools/gerar_relatorio.py

Publicação: o nb_04_publicar_modelo cria ou atualiza o relatório no workspace, ligado ao
modelo PainelProjetos.
"""
import hashlib
import json
import shutil
from pathlib import Path

from tools.gerar_modelo import MEDIDAS

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "fabric" / "PainelProjetos.Report"
NOME = "PainelProjetos"
LARGURA, ALTURA = 1280, 720

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
TEMA_BASE = "CY26SU04"
TEMA = "TemaPainelProjetos.json"

# Tokens do redesign (Figma "Painel de Projetos — Redesign", quadro 05 · Guia de estilo).
# Um assunto por cor: azul conta volume, cinza é referência, verde/âmbar/vermelho só situação.
# Paleta conferida com o validador de daltonismo (status: verde × âmbar × vermelho separados).
COR = {"texto": "#17212B", "suave": "#5A6472", "apagado": "#8A93A0", "fundo": "#F3F5F8", "cartao": "#FFFFFF",
       "borda": "#E4E8EE", "grade": "#EDF0F4", "cabecalho": "#0F2A44", "cabecalho2": "#1C3A5A",
       "cabecalho_texto": "#B9C6D6", "azul": "#2F6DB5", "referencia": "#A3ACB9", "neutro": "#B8C4D3",
       "bom": "#1F8A5B", "atencao": "#D29B00", "atencao_texto": "#9A7000", "critico": "#C2362F",
       "barra_azul": "#C9DAEE", "barra_vermelha": "#F2C9C6"}
TOM = {"n": (COR["azul"], COR["suave"]), "c": (COR["critico"], COR["critico"]),
       "w": (COR["atencao"], COR["atencao_texto"]), "g": (COR["bom"], COR["bom"])}

TABELA_DA_MEDIDA = {m[0]: tabela for tabela, medidas in MEDIDAS.items() for m in medidas}


# --- expressões PBIR -------------------------------------------------------------------

def lit(valor) -> dict:
    if isinstance(valor, bool):
        texto = "true" if valor else "false"
    elif isinstance(valor, int):
        texto = f"{valor}L"
    elif isinstance(valor, float):
        texto = f"{valor}D"
    else:
        texto = "'" + str(valor).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": texto}}}


def cor(hexa: str) -> dict:
    return {"solid": {"color": lit(hexa)}}


def coluna(tabela: str, nome: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabela}}, "Property": nome}}


def campo(ref: str) -> dict:
    """'Medida' (sem ponto) ou 'tabela.coluna'."""
    if "." in ref and ref.split(".")[0] in {"dim_data", "dim_projeto", "dim_pessoa", "dim_status",
                                             "fato_tarefa", "fato_passagem_status", "ref_parametros"}:
        return coluna(*ref.split(".", 1))
    return {"Measure": {"Expression": {"SourceRef": {"Entity": TABELA_DA_MEDIDA[ref]}}, "Property": ref}}


def projecao(ref: str, rotulo: str | None = None, ativo: bool = False) -> dict:
    f = campo(ref)
    tipo = "Column" if "Column" in f else "Measure"
    entidade = f[tipo]["Expression"]["SourceRef"]["Entity"]
    propriedade = f[tipo]["Property"]
    p = {"field": f, "queryRef": f"{entidade}.{propriedade}", "nativeQueryRef": rotulo or propriedade}
    if rotulo:
        p["displayName"] = rotulo
    if ativo:
        p["active"] = True
    return p


def campos(refs) -> list[dict]:
    """refs: lista de 'ref' ou ('ref', 'rótulo')."""
    return [projecao(*(r if isinstance(r, tuple) else (r,))) for r in refs]


def ordenar(ref: str, decrescente: bool = True) -> dict:
    return {"sort": [{"field": campo(ref), "direction": "Descending" if decrescente else "Ascending"}]}


def quando(ref: str, valor: str) -> dict:
    """seletor de um ponto pela categoria (ex.: só a barra 'Atrasado')"""
    return {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": campo(ref),
                                                 "Right": {"Literal": {"Value": "'" + valor + "'"}}}}}]}


def filtro_igual(ref: str, valor: str, nome: str) -> dict:
    tabela, col = ref.split(".", 1)
    return {"filters": [{
        "name": nome, "field": campo(ref), "type": "Categorical",
        "filter": {"Version": 2, "From": [{"Name": "t", "Entity": tabela, "Type": 0}],
                   "Where": [{"Condition": {"In": {
                       "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": col}}],
                       "Values": [[{"Literal": {"Value": "'" + valor + "'"}}]]}}}]},
        "howCreated": "User"}]}


def moldura(titulo: str | None = None, subtitulo: str | None = None, fundo: str | None = COR["cartao"],
            borda: bool = True, raio: float = 10.0, respiro: float = 12.0) -> dict:
    objetos = {
        "title": [{"properties": {"show": lit(bool(titulo)), **({"text": lit(titulo), "fontColor": cor(COR["texto"]),
                                                                  "fontSize": lit(12.0), "bold": lit(False),
                                                                  "fontFamily": lit("Segoe UI Semibold")}
                                                                 if titulo else {})}}],
        "background": [{"properties": {"show": lit(fundo is not None),
                                       **({"color": cor(fundo), "transparency": lit(0.0)} if fundo else {})}}],
        "border": [{"properties": {"show": lit(borda), "color": cor(COR["borda"]), "radius": lit(raio)}}],
        "dropShadow": [{"properties": {"show": lit(False)}}],
        "visualHeader": [{"properties": {"show": lit(False)}}],
        "padding": [{"properties": {k: lit(respiro) for k in ("top", "bottom", "left", "right")}}],
    }
    if subtitulo:
        objetos["subTitle"] = [{"properties": {"show": lit(True), "text": lit(subtitulo),
                                               "fontColor": cor(COR["suave"]), "fontSize": lit(9.0)}}]
    return objetos


# --- visuais -------------------------------------------------------------------------------

class Pagina:
    """Grade de 1280 × 720: cabeçalho 0–76, cartões 92–188, linhas de gráficos em 204 e 460."""

    Y_KPI, H_KPI = 92, 96
    Y2, Y3, H_LINHA = 204, 460, 244

    def __init__(self, nome: str, titulo: str, subtitulo: str):
        self.nome, self.titulo = nome, titulo
        self.visuais: list[dict] = []
        self.fundos: set[str] = set()   # painéis decorativos: os visuais de cima ficam dentro deles
        # cabeçalho escuro com título, filtros e data de referência
        self.painel(0, 0, LARGURA, 76, COR["cabecalho"], borda=False, raio=0.0)
        self.texto(titulo, 24, 8, 560, 34, 17, "#FFFFFF", negrito=True)
        self.texto(subtitulo, 24, 42, 560, 24, 9.5, COR["cabecalho_texto"])
        self.segmentacao("dim_projeto.equipe", "Equipe", 860, 8, 128, 60)
        self.segmentacao("dim_projeto.status", "Status do projeto", 996, 8, 128, 60)
        self.cartao_simples("Texto Referência", 1132, 22, 136, 32, 9.0, COR["cabecalho_texto"])

    def _id(self) -> str:
        return hashlib.sha1(f"{self.nome}/{len(self.visuais)}".encode()).hexdigest()[:20]

    def _add(self, x, y, w, h, visual: dict, extra: dict | None = None) -> str:
        z = len(self.visuais) * 100
        nome = self._id()
        self.visuais.append({
            "$schema": f"{SCHEMA}/visualContainer/2.11.0/schema.json",
            "name": nome,
            "position": {"x": round(x, 1), "y": round(y, 1), "z": z, "height": round(h, 1), "width": round(w, 1),
                         "tabOrder": z},
            "visual": visual,
            **(extra or {}),
        })
        return nome

    def painel(self, x, y, w, h, fundo, borda=True, raio=10.0):
        """caixa de fundo (caixa de texto vazia): só cor, borda e cantos"""
        nome = self._add(x, y, w, h, {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": ""}]}]}}]},
            "visualContainerObjects": moldura(fundo=fundo, borda=borda, raio=raio, respiro=0.0),
            "drillFilterOtherVisuals": True})
        self.fundos.add(nome)

    def texto(self, conteudo, x, y, w, h, tamanho, cor_texto, negrito=False):
        estilo = {"fontFamily": "Segoe UI Semibold" if negrito else "Segoe UI",
                  "fontSize": f"{tamanho}pt", "color": cor_texto}
        self._add(x, y, w, h, {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": conteudo, "textStyle": estilo}], "horizontalTextAlignment": "left"}]}}]},
            "visualContainerObjects": moldura(fundo=None, borda=False, respiro=0.0),
            "drillFilterOtherVisuals": True})

    def valor(self, medida, x, y, w, h, tamanho, cor_valor, negrito=False):
        """um número (ou texto) alinhado à esquerda, sem rótulo: cartão de várias linhas enxuto"""
        self._add(x, y, w, h, {
            "visualType": "multiRowCard",
            "query": {"queryState": {"Values": {"projections": campos([medida])}}},
            "objects": {
                "dataLabels": [{"properties": {"fontSize": lit(float(tamanho)), "color": cor(cor_valor),
                                               "fontFamily": lit("Segoe UI Semibold" if negrito else "Segoe UI")}}],
                # medida de texto aparece como título do cartão, que tem estilo próprio (azul por padrão)
                "cardTitle": [{"properties": {"fontSize": lit(float(tamanho)), "color": cor(cor_valor),
                                              "fontFamily": lit("Segoe UI Semibold" if negrito else "Segoe UI")}}],
                "categoryLabels": [{"properties": {"show": lit(False)}}],
                "card": [{"properties": {"barShow": lit(False), "outline": lit("None"),
                                         "cardPadding": lit(0.0), "cardBackground": cor("#FFFFFF"),
                                         "cardBackgroundTransparency": lit(100.0)}}],
            },
            "visualContainerObjects": moldura(fundo=None, borda=False, respiro=0.0),
            "drillFilterOtherVisuals": True})

    def cartao_simples(self, medida, x, y, w, h, tamanho, cor_valor):
        """cartão clássico sem rótulo nem fundo (centralizado): usado na data de referência"""
        self._add(x, y, w, h, {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": campos([medida])}}},
            "objects": {"labels": [{"properties": {"fontSize": lit(float(tamanho)), "color": cor(cor_valor)}}],
                        "categoryLabels": [{"properties": {"show": lit(False)}}]},
            "visualContainerObjects": moldura(fundo=None, borda=False, respiro=0.0),
            "drillFilterOtherVisuals": True})

    def kpi(self, medida, rotulo, contexto, tom, x, y, w, h):
        """cartão: barra de situação, rótulo em caixa alta, número grande e linha de contexto"""
        barra, cor_contexto = TOM[tom]
        self.painel(x, y, w, h, COR["cartao"])
        self.painel(x + 10, y + 14, 3, h - 28, barra, borda=False, raio=2.0)
        self.texto(rotulo.upper(), x + 20, y + 8, w - 28, 18, 8, COR["suave"], negrito=True)
        self.valor(medida, x + 17, y + 26, w - 26, 42, 20, COR["texto"], negrito=True)
        if contexto in TABELA_DA_MEDIDA:
            self.valor(contexto, x + 17, y + 68, w - 26, 24, 9, cor_contexto)
        else:
            self.texto(contexto, x + 20, y + 68, w - 28, 22, 9, cor_contexto)

    def linha_de_cartoes(self, itens):
        n, espaco = len(itens), 12
        w = (LARGURA - 48 - espaco * (n - 1)) / n
        for i, item in enumerate(itens):
            self.kpi(*item, 24 + i * (w + espaco), self.Y_KPI, w, self.H_KPI)

    def segmentacao(self, col, titulo, x, y, w, h):
        self._add(x, y, w, h, {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": campos([col])}}},
            "objects": {"data": [{"properties": {"mode": lit("Dropdown")}}],
                        "header": [{"properties": {"show": lit(True), "text": lit(titulo),
                                                   "fontColor": cor(COR["cabecalho_texto"]), "textSize": lit(8.0)}}],
                        "items": [{"properties": {"fontColor": cor("#FFFFFF"), "background": cor(COR["cabecalho2"]),
                                                  "textSize": lit(10.0)}}]},
            "visualContainerObjects": moldura(fundo=COR["cabecalho2"], borda=False, raio=6.0, respiro=2.0),
            "drillFilterOtherVisuals": True})

    def grafico(self, tipo, titulo, subtitulo, categoria, medidas, x, y, w, h, cores=None, destaques=None,
                ordem=None, ordem_crescente=False):
        """tipo: barras horizontais (clusteredBarChart), colunas ou linha.
        cores: uma por medida. destaques: {valor da categoria: cor} (o resto fica com a cor da medida)."""
        barras = tipo != "lineChart"
        horizontal = tipo == "clusteredBarChart"
        objetos = {
            "categoryAxis": [{"properties": {"show": lit(True), "fontSize": lit(9.0 if horizontal else 8.0),
                                             "labelColor": cor(COR["texto"] if horizontal else COR["apagado"]),
                                             "showAxisTitle": lit(False), "innerPadding": lit(28.0 if barras else 0.0),
                                             "maxMarginFactor": lit(45 if horizontal else 25)}}],
            # barras: sem eixo de valor nem grade (o rótulo na ponta já diz o número); linha: grade bem clara
            "valueAxis": [{"properties": {"show": lit(not barras), "fontSize": lit(8.0),
                                          "labelColor": cor(COR["apagado"]), "showAxisTitle": lit(False),
                                          "labelDisplayUnits": lit(1.0), "gridlineShow": lit(not barras),
                                          "gridlineColor": cor(COR["grade"]), "gridlineStyle": lit("solid")}}],
            "legend": [{"properties": {"show": lit(len(medidas) > 1), "position": lit("Top"),
                                       "fontSize": lit(8.0), "labelColor": cor(COR["suave"])}}],
            "labels": [{"properties": {"show": lit(barras), "fontSize": lit(8.5), "color": cor(COR["texto"]),
                                       "labelDisplayUnits": lit(1.0)}}],
        }
        if not barras:
            objetos["lineStyles"] = [{"properties": {"strokeWidth": lit(2.0), "showMarker": lit(False)}}]
        pontos = []
        nomes = [m if isinstance(m, str) else m[0] for m in medidas]
        if len(nomes) == 1 and cores:
            pontos.append({"properties": {"defaultColor": cor(cores[0])}})
        else:
            for m, c in zip(nomes, cores or []):
                pontos.append({"properties": {"fill": cor(c)}, "selector": {"metadata": projecao(m)["queryRef"]}})
        for valor_categoria, c in (destaques or {}).items():
            pontos.append({"properties": {"fill": cor(c)}, "selector": quando(categoria, valor_categoria)})
        if pontos:
            objetos["dataPoint"] = pontos
        query = {"queryState": {"Category": {"projections": [projecao(categoria, ativo=True)]},
                                "Y": {"projections": campos(medidas)}}}
        if ordem:
            query["sortDefinition"] = ordenar(ordem, not ordem_crescente)
        self._add(x, y, w, h, {"visualType": tipo, "query": query, "objects": objetos,
                               "visualContainerObjects": moldura(titulo, subtitulo), "drillFilterOtherVisuals": True})

    def tabela(self, titulo, subtitulo, colunas_, x, y, w, h, ordem, crescente=False, barras=None, filtro=None):
        """barras: {campo: cor} → barra de dados atrás do número"""
        objetos = {
            "columnHeaders": [{"properties": {"fontColor": cor(COR["suave"]), "bold": lit(True),
                                              "backColor": cor(COR["cartao"]), "fontSize": lit(8.5),
                                              "outline": lit("BottomOnly")}}],
            "values": [{"properties": {"fontSize": lit(9.0), "fontColorPrimary": cor(COR["texto"]),
                                       "fontColorSecondary": cor(COR["texto"]),
                                       "backColorPrimary": cor(COR["cartao"]),
                                       "backColorSecondary": cor(COR["cartao"])}}],
            "grid": [{"properties": {"gridHorizontal": lit(True), "gridHorizontalColor": cor(COR["grade"]),
                                     "gridVertical": lit(False), "outlineColor": cor(COR["borda"]),
                                     "rowPadding": lit(6)}}],
            "total": [{"properties": {"totals": lit(False)}}],
        }
        if barras:
            objetos["columnFormatting"] = [
                {"properties": {"dataBars": {"positiveColor": cor(c), "negativeColor": cor(COR["barra_vermelha"]),
                                             "axisColor": cor(COR["borda"]), "reverseDirection": lit(False),
                                             "hideText": lit(False)}},
                 "selector": {"metadata": projecao(ref)["queryRef"]}}
                for ref, c in barras.items()]
        extra = {"filterConfig": filtro_igual(*filtro, nome=hashlib.sha1(titulo.encode()).hexdigest()[:20])} \
            if filtro else None
        self._add(x, y, w, h, {
            "visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": campos(colunas_)}},
                      "sortDefinition": ordenar(ordem, not crescente)},
            "objects": objetos,
            "visualContainerObjects": moldura(titulo, subtitulo),
            "drillFilterOtherVisuals": True}, extra)


# --- páginas -------------------------------------------------------------------------------

SITUACAO = {"Atrasado": COR["critico"], "Concluído com atraso": COR["atencao"]}


def paginas() -> list[Pagina]:
    y2, y3, h = Pagina.Y2, Pagina.Y3, Pagina.H_LINHA
    alto = y3 + h - y2   # visual que ocupa as duas linhas

    geral = Pagina("P1Geral", "Painel de Projetos", "Portfólio, prazos e entregas · dados simulados de uma "
                                                     "ferramenta de gestão de projetos")
    geral.linha_de_cartoes([
        ("Projetos Ativos", "Projetos ativos", "Contexto Projetos Ativos", "n"),
        ("Projetos Atrasados", "Projetos atrasados", "Contexto Projetos Atrasados", "c"),
        ("Tarefas Abertas", "Tarefas abertas", "Contexto Tarefas Abertas", "n"),
        ("Tarefas Vencidas", "Tarefas vencidas", "Contexto Tarefas Vencidas", "c"),
        ("% Entregues no Prazo", "Entregues no prazo", "das tarefas concluídas", "n"),
        ("Desvio de Esforço %", "Desvio de esforço", "horas apontadas vs. estimadas", "w")])
    geral.grafico("lineChart", "Tarefas criadas × entregues por mês",
                  "Entregas (azul) acompanhando a demanda (cinza)", "dim_data.mes_ano",
                  [("Tarefas Criadas", "Criadas"), ("Tarefas Entregues", "Entregues")],
                  24, y2, 760, h, cores=[COR["referencia"], COR["azul"]], ordem="dim_data.mes_ano",
                  ordem_crescente=True)
    geral.grafico("clusteredBarChart", "Projetos ativos e atrasados por equipe",
                  "Vermelho: já passaram do fim planejado", "dim_projeto.equipe",
                  [("Projetos Ativos", "Ativos"), ("Projetos Atrasados", "Atrasados")],
                  796, y2, 460, h, cores=[COR["azul"], COR["critico"]], ordem="Projetos Ativos")
    geral.grafico("clusteredBarChart", "Situação de prazo do portfólio",
                  "Vermelho e âmbar pedem ação", "dim_projeto.situacao_prazo", ["Projetos"],
                  24, y3, 460, h, cores=[COR["neutro"]], destaques=SITUACAO, ordem="Projetos")
    geral.tabela("Precisam de atenção", "Projetos em andamento que já passaram do fim planejado",
                 [("dim_projeto.projeto", "Projeto"), ("dim_projeto.equipe", "Equipe"),
                  ("dim_projeto.gestor", "Gestor"), ("dim_projeto.data_fim_planejada", "Fim planejado"),
                  ("dim_projeto.dias_atraso", "Dias de atraso")],
                 496, y3, 760, h, ordem="dim_projeto.dias_atraso",
                 barras={"dim_projeto.dias_atraso": COR["barra_vermelha"]},
                 filtro=("dim_projeto.situacao_prazo", "Atrasado"))

    projetos = Pagina("P2Projetos", "Projetos", "Quem está atrasado, quanto, e quanto do orçamento de horas já foi")
    projetos.linha_de_cartoes([
        ("Projetos", "Projetos", "no portfólio", "n"),
        ("Projetos em Andamento", "Em andamento", "em execução agora", "n"),
        ("Projetos Concluídos", "Concluídos", "já entregues", "g"),
        ("% Projetos Atrasados", "% atrasados", "Contexto Atrasados de Ativos", "c"),
        ("% Projetos Entregues no Prazo", "Entregues no prazo", "Contexto Entregues no Prazo", "c"),
        ("Atraso Médio dos Projetos (dias)", "Atraso médio (dias)", "entre os projetos atrasados", "w")])
    projetos.grafico("clusteredBarChart", "Orçamento de horas consumido",
                     "% das horas orçadas já apontadas, por equipe", "dim_projeto.equipe",
                     [("% Orçamento Consumido", "% consumido")], 24, y2, 380, h, cores=[COR["azul"]],
                     ordem="% Orçamento Consumido")
    projetos.grafico("clusteredBarChart", "Situação de prazo", "Projetos por situação",
                     "dim_projeto.situacao_prazo", ["Projetos"], 24, y3, 380, h, cores=[COR["neutro"]],
                     destaques=SITUACAO, ordem="Projetos")
    projetos.tabela("Todos os projetos, do maior atraso para o menor",
                    "Clique numa linha para filtrar o resto da página",
                    [("dim_projeto.projeto", "Projeto"), ("dim_projeto.equipe", "Equipe"),
                     ("dim_projeto.situacao_prazo", "Prazo"),
                     ("dim_projeto.data_fim_planejada", "Fim planejado"), ("dim_projeto.dias_atraso", "Dias de atraso"),
                     ("% Orçamento Consumido", "% orçamento")],
                    416, y2, 840, alto, ordem="dim_projeto.dias_atraso",
                    barras={"dim_projeto.dias_atraso": COR["barra_vermelha"],
                            "% Orçamento Consumido": COR["barra_azul"]})

    fluxo = Pagina("P3Fluxo", "Fluxo e gargalos", "Tempo em cada etapa, onde as tarefas travam e quanto voltam")
    fluxo.linha_de_cartoes([
        ("Lead Time Médio (dias)", "Lead time médio (dias)", "da criação à conclusão", "n"),
        ("Ciclo Médio (dias)", "Ciclo médio (dias)", "do início à conclusão", "n"),
        ("Ciclo Mediano (dias)", "Ciclo mediano (dias)", "metade termina antes disso", "n"),
        ("% Concluídas com Retrabalho", "Com retrabalho", "voltaram da revisão", "w"),
        ("Tarefas Bloqueadas", "Bloqueadas", "tarefas travadas agora", "c"),
        ("Paradas há mais de 15 dias", "Paradas > 15 dias", "sem mudar de etapa", "w")])
    bloqueada = {"Bloqueada": COR["critico"]}
    fluxo.grafico("clusteredBarChart", "Tempo médio em cada etapa (dias)", "Na ordem do fluxo · vermelho: bloqueio",
                  "fato_passagem_status.status", ["Tempo Médio na Etapa (dias)"], 24, y2, 610, h,
                  cores=[COR["azul"]], destaques=bloqueada, ordem="fato_passagem_status.status", ordem_crescente=True)
    fluxo.grafico("clusteredBarChart", "Onde as tarefas estão paradas agora", "Tarefas abertas por etapa atual",
                  "fato_passagem_status.status", ["Tarefas Paradas na Etapa"], 646, y2, 610, h,
                  cores=[COR["azul"]], destaques=bloqueada, ordem="fato_passagem_status.status", ordem_crescente=True)
    fluxo.grafico("lineChart", "Mudanças de status por mês", "Ritmo de trabalho do portfólio", "dim_data.mes_ano",
                  [("Mudanças de Status", "Mudanças")], 24, y3, 610, h, cores=[COR["azul"]],
                  ordem="dim_data.mes_ano", ordem_crescente=True)
    fluxo.grafico("clusteredColumnChart", "Bloqueios por mês", "Tarefas que entraram em bloqueio",
                  "dim_data.mes_ano", [("Bloqueios no Período", "Bloqueios")], 646, y3, 610, h,
                  cores=[COR["critico"]], ordem="dim_data.mes_ano", ordem_crescente=True)

    pessoas = Pagina("P4Pessoas", "Pessoas e esforço", "Carga de cada pessoa e horas apontadas contra o estimado")
    pessoas.linha_de_cartoes([
        ("Horas Orçadas", "Horas orçadas", "para todo o portfólio", "n"),
        ("Horas Estimadas", "Horas estimadas", "soma das tarefas", "n"),
        ("Horas Apontadas", "Horas apontadas", "Contexto Horas Apontadas", "w"),
        ("% Orçamento Consumido", "Orçamento consumido", "Contexto Orçamento", "w"),
        ("Tarefas Concluídas", "Tarefas concluídas", "Contexto Tarefas Concluídas", "g"),
        ("Idade Média das Abertas (dias)", "Idade das abertas (dias)", "média desde a criação", "n")])
    pessoas.grafico("clusteredBarChart", "Horas estimadas × apontadas por equipe",
                    "Cinza: estimado · azul: apontado", "dim_pessoa.equipe",
                    [("Horas Estimadas", "Estimadas"), ("Horas Apontadas", "Apontadas")],
                    24, y2, 460, alto, cores=[COR["referencia"], COR["azul"]], ordem="Horas Apontadas")
    pessoas.tabela("Carga por pessoa", "Ordenado por tarefas abertas · barras: abertas (azul) e vencidas (vermelho)",
                   [("dim_pessoa.pessoa", "Pessoa"), ("dim_pessoa.equipe", "Equipe"), ("dim_pessoa.cargo", "Cargo"),
                    ("Tarefas Abertas", "Abertas"), ("Tarefas Vencidas", "Vencidas"),
                    ("Tarefas Concluídas", "Concluídas"), ("Horas Apontadas", "Horas"),
                    ("Desvio de Esforço %", "Desvio")],
                   496, y2, LARGURA - 496 - 24, alto, ordem="Tarefas Abertas",
                   barras={"Tarefas Abertas": COR["barra_azul"], "Tarefas Vencidas": COR["barra_vermelha"]})
    return [geral, projetos, fluxo, pessoas]


# --- arquivos ------------------------------------------------------------------------------

def tema() -> dict:
    return {"name": "TemaPainelProjetos",
            "dataColors": [COR[c] for c in ("azul", "referencia", "bom", "atencao", "critico", "neutro")],
            "foreground": COR["texto"], "foregroundNeutralSecondary": COR["suave"],
            "foregroundNeutralTertiary": COR["apagado"], "background": COR["cartao"],
            "backgroundLight": COR["fundo"], "backgroundNeutral": COR["borda"], "tableAccent": COR["azul"],
            "good": COR["bom"], "neutral": COR["atencao"], "bad": COR["critico"],
            "maximum": COR["azul"], "center": COR["neutro"], "minimum": COR["barra_azul"],
            "textClasses": {"callout": {"fontFace": "Segoe UI Semibold", "color": COR["texto"]},
                            "title": {"fontFace": "Segoe UI Semibold", "color": COR["texto"], "fontSize": 12},
                            "header": {"fontFace": "Segoe UI Semibold", "color": COR["texto"]},
                            "label": {"fontFace": "Segoe UI", "color": COR["suave"]}}}


def escrever(caminho: Path, conteudo) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = conteudo if isinstance(conteudo, str) else json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n"
    caminho.write_text(texto, encoding="utf-8")


def gerar(destino: Path = DESTINO) -> list[Pagina]:
    if destino.exists():
        shutil.rmtree(destino)
    lista = paginas()
    escrever(destino / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NOME},
        "config": {"version": "2.0", "logicalId": "5a1c3f7e-2b9d-5e4a-8c61-7d0f3e9b2a14"}})
    escrever(destino / "definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NOME}.SemanticModel"}}})
    versao = {"visual": "2.8.0", "report": "3.2.0", "page": "2.3.1"}
    escrever(destino / "definition" / "report.json", {
        "$schema": f"{SCHEMA}/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": TEMA_BASE, "reportVersionAtImport": versao, "type": "SharedResources"},
                            "customTheme": {"name": TEMA, "reportVersionAtImport": versao,
                                            "type": "RegisteredResources"}},
        "resourcePackages": [
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": TEMA, "path": TEMA, "type": "CustomTheme"}]},
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": TEMA_BASE, "path": f"BaseThemes/{TEMA_BASE}.json", "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                     "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}})
    escrever(destino / "definition" / "version.json", {
        "$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    escrever(destino / "definition" / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [p.nome for p in lista], "activePageName": lista[0].nome})
    for p in lista:
        pasta = destino / "definition" / "pages" / p.nome
        escrever(pasta / "page.json", {
            "$schema": f"{SCHEMA}/page/2.1.0/schema.json", "name": p.nome, "displayName": p.titulo,
            "displayOption": "FitToPage", "height": ALTURA, "width": LARGURA,
            "objects": {"background": [{"properties": {"color": cor(COR["fundo"]), "transparency": lit(0.0)}}],
                        "outspace": [{"properties": {"color": cor(COR["fundo"])}}]}})
        for v in p.visuais:
            escrever(pasta / "visuals" / v["name"] / "visual.json", v)
    shutil.copy(RAIZ / "tools" / "recursos" / f"{TEMA_BASE}.json",
                _mkdir(destino / "StaticResources" / "SharedResources" / "BaseThemes") / f"{TEMA_BASE}.json")
    escrever(destino / "StaticResources" / "RegisteredResources" / TEMA, tema())
    return lista


def _mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


if __name__ == "__main__":
    lista = gerar()
    print(f"relatório gerado em {DESTINO.relative_to(RAIZ)}: "
          + ", ".join(f"{p.titulo} ({len(p.visuais)} visuais)" for p in lista))
