"""Gera o relatório (PBIR) em fabric/PainelProjetos.Report.

    python -m tools.gerar_relatorio"""
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

COR = {"texto": "#1A202C", "suave": "#5F6B7A", "apagado": "#98A2B3", "fundo": "#F7F8FA", "cartao": "#FFFFFF",
       "borda": "#ECEEF2", "grade": "#F1F3F5", "azul": "#2F6DB5", "azul_suave": "#EAF1FA", "neutro": "#C6CFDB",
       "bom": "#1F8A5B", "atencao": "#D29B00", "critico": "#C2362F", "concluido": "#A9C1DF",
       "cancelado": "#D5DAE1", "barra_azul": "#DCE7F5", "barra_vermelha": "#F6D9D6"}

TABELA_DA_MEDIDA = {m[0]: tabela for tabela, medidas in MEDIDAS.items() for m in medidas}


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
    return [projecao(*(r if isinstance(r, tuple) else (r,))) for r in refs]


def ordenar(ref: str, decrescente: bool = True) -> dict:
    return {"sort": [{"field": campo(ref), "direction": "Descending" if decrescente else "Ascending"}]}


def quando(ref: str, valor: str) -> dict:
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
            borda: bool = True, raio: float = 12.0, respiro: float = 12.0) -> dict:
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


class Pagina:

    X0, W = 224, 1032
    Y_KPI, H_KPI = 80, 80
    Y2 = 176
    PAGINAS = [("P1Portfolio", "Portfólio"), ("P2ProjetosTarefas", "Projetos e tarefas"), ("P3Cronograma", "Cronograma")]

    def __init__(self, nome: str, titulo: str, subtitulo: str):
        self.nome, self.titulo = nome, titulo
        self.visuais: list[dict] = []
        self.fundos: set[str] = set()
        self.cartoes: list[tuple[str, str]] = []
        self.lateral()
        self.texto(titulo, self.X0, 14, 380, 32, 16, COR["texto"], negrito=True)
        self.texto(subtitulo, self.X0, 46, 700, 22, 9, COR["suave"])

    def lateral(self):
        self.painel(0, 0, 200, ALTURA, COR["cartao"], borda=False, raio=0.0)
        self.texto("Painel de Projetos", 18, 16, 170, 32, 12, COR["texto"], negrito=True)
        for i, (destino, rotulo) in enumerate(self.PAGINAS):
            self.botao(rotulo, destino, 14, 64 + i * 40, 172, 34, ativo=destino == self.nome)
        self.segmentacao("dim_projeto.equipe", "Equipe", 14, 200, 172, 58)
        self.segmentacao("dim_projeto.status", "Status do projeto", 14, 266, 172, 58)
        self.cartao_simples("Texto Referência", 14, 668, 172, 30, 8.0, COR["apagado"])

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

    def painel(self, x, y, w, h, fundo, borda=True, raio=12.0):
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

    def legenda(self, itens, x, y, w, h):
        runs = []
        for rotulo, c in itens:
            runs.append({"value": "■ ", "textStyle": {"fontSize": "11pt", "color": c}})
            runs.append({"value": rotulo + "     ", "textStyle": {"fontFamily": "Segoe UI", "fontSize": "8.5pt",
                                                                 "color": COR["suave"]}})
        self._add(x, y, w, h, {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": runs, "horizontalTextAlignment": "right"}]}}]},
            "visualContainerObjects": moldura(fundo=None, borda=False, respiro=0.0),
            "drillFilterOtherVisuals": True})

    def botao(self, rotulo, destino, x, y, w, h, ativo=False):
        padrao = {"id": "default"}
        self._add(x, y, w, h, {
            "visualType": "actionButton",
            "objects": {
                "icon": [{"properties": {"show": lit(False)}, "selector": padrao}],
                "text": [{"properties": {"show": lit(True), "text": lit(rotulo), "fontSize": lit(10.0),
                                         "fontColor": cor(COR["azul"] if ativo else COR["suave"]),
                                         "fontFamily": lit("Segoe UI Semibold" if ativo else "Segoe UI"),
                                         "horizontalAlignment": lit("left"), "leftMargin": lit(10.0)},
                          "selector": padrao}],
                "fill": [{"properties": {"show": lit(ativo), "fillColor": cor(COR["azul_suave"]),
                                         "transparency": lit(0.0)}, "selector": padrao}],
                "outline": [{"properties": {"show": lit(False)}, "selector": padrao}],
            },
            "visualContainerObjects": {
                **moldura(fundo=None, borda=False, respiro=0.0),
                "visualLink": [{"properties": {"show": lit(True), "type": lit("PageNavigation"),
                                               "navigationSection": lit(destino)}}],
            },
            "drillFilterOtherVisuals": True})

    def valor(self, medida, x, y, w, h, tamanho, cor_valor, negrito=False):
        self._add(x, y, w, h, {
            "visualType": "multiRowCard",
            "query": {"queryState": {"Values": {"projections": campos([medida])}}},
            "objects": {
                "dataLabels": [{"properties": {"fontSize": lit(float(tamanho)), "color": cor(cor_valor),
                                               "fontFamily": lit("Segoe UI Semibold" if negrito else "Segoe UI")}}],
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
        self._add(x, y, w, h, {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": campos([medida])}}},
            "objects": {"labels": [{"properties": {"fontSize": lit(float(tamanho)), "color": cor(cor_valor)}}],
                        "categoryLabels": [{"properties": {"show": lit(False)}}]},
            "visualContainerObjects": moldura(fundo=None, borda=False, respiro=0.0),
            "drillFilterOtherVisuals": True})

    def faixa_de_cartoes(self, itens):
        """itens: (medida, rótulo, contexto, alerta). Uma faixa branca dividida em colunas."""
        x0, y, h = self.X0, self.Y_KPI, self.H_KPI
        self.painel(x0, y, self.W, h, COR["cartao"])
        w = self.W / len(itens)
        for i, (medida, rotulo, contexto, alerta) in enumerate(itens):
            x = x0 + i * w
            if i:
                self.painel(x, y + 16, 1, h - 32, COR["borda"], borda=False, raio=0.0)
            self.texto(rotulo, x + 18, y + 8, w - 30, 18, 8.5, COR["suave"])
            self.valor(medida, x + 15, y + 26, w - 26, 32, 18, COR["critico"] if alerta else COR["texto"],
                       negrito=True)
            if contexto in TABELA_DA_MEDIDA:
                self.valor(contexto, x + 15, y + 58, w - 26, 20, 8, COR["apagado"])
            else:
                self.texto(contexto, x + 18, y + 58, w - 30, 20, 8, COR["apagado"])
            self.cartoes.append((medida, contexto))

    def segmentacao(self, col, titulo, x, y, w, h):
        self._add(x, y, w, h, {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": campos([col])}}},
            "objects": {"data": [{"properties": {"mode": lit("Dropdown")}}],
                        "header": [{"properties": {"show": lit(True), "text": lit(titulo),
                                                   "fontColor": cor(COR["apagado"]), "textSize": lit(8.0)}}],
                        "items": [{"properties": {"fontColor": cor(COR["texto"]), "background": cor(COR["cartao"]),
                                                  "textSize": lit(9.5), "outlineColor": cor(COR["borda"])}}]},
            "visualContainerObjects": moldura(fundo=None, borda=False, respiro=2.0),
            "drillFilterOtherVisuals": True})

    def grafico(self, tipo, titulo, subtitulo, categoria, medidas, x, y, w, h, cores=None, destaques=None,
                ordem=None, ordem_crescente=False):
        barras = tipo != "lineChart"
        horizontal = tipo == "clusteredBarChart"
        objetos = {
            "categoryAxis": [{"properties": {"show": lit(True), "fontSize": lit(9.0 if horizontal else 8.0),
                                             "labelColor": cor(COR["texto"] if horizontal else COR["apagado"]),
                                             "showAxisTitle": lit(False), "innerPadding": lit(30.0 if barras else 0.0),
                                             "maxMarginFactor": lit(45 if horizontal else 25)}}],
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

    def _estilo_tabela(self):
        return {
            "columnHeaders": [{"properties": {"fontColor": cor(COR["apagado"]), "bold": lit(True),
                                              "backColor": cor(COR["cartao"]), "fontSize": lit(8.0),
                                              "outline": lit("BottomOnly")}}],
            "values": [{"properties": {"fontSize": lit(9.0), "fontColorPrimary": cor(COR["texto"]),
                                       "fontColorSecondary": cor(COR["texto"]),
                                       "backColorPrimary": cor(COR["cartao"]),
                                       "backColorSecondary": cor(COR["cartao"])}}],
            "grid": [{"properties": {"gridHorizontal": lit(True), "gridHorizontalColor": cor(COR["grade"]),
                                     "gridVertical": lit(False), "outlineColor": cor(COR["borda"]),
                                     "rowPadding": lit(6)}}],
        }

    def tabela(self, titulo, subtitulo, colunas_, x, y, w, h, ordem, crescente=False, barras=None, filtro=None):
        objetos = {**self._estilo_tabela(), "total": [{"properties": {"totals": lit(False)}}]}
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

    def gantt(self, x, y, w, h):
        """Matriz projeto > tarefa × mês; a célula é pintada pela medida Cronograma Cor."""
        celula = projecao("Cronograma")
        cor_da_medida = {"solid": {"color": {"expr": campo("Cronograma Cor")}}}
        todas = {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": celula["queryRef"]}
        objetos = {
            **self._estilo_tabela(),
            "rowHeaders": [{"properties": {"fontSize": lit(9.0), "fontColor": cor(COR["texto"]),
                                           "showExpandCollapseButtons": lit(True), "wordWrap": lit(False)}}],
            "columnHeaders": [{"properties": {"fontColor": cor(COR["apagado"]), "fontSize": lit(8.0),
                                              "backColor": cor(COR["cartao"]), "alignment": lit("Center"),
                                              "outline": lit("BottomOnly")}}],
            "values": [{"properties": {"fontSize": lit(8.0), "backColorPrimary": cor(COR["cartao"]),
                                       "backColorSecondary": cor(COR["cartao"])}},
                       {"properties": {"backColor": cor_da_medida, "fontColor": cor_da_medida},
                        "selector": todas}],
            "grid": [{"properties": {"gridHorizontal": lit(True), "gridHorizontalColor": cor(COR["grade"]),
                                     "gridVertical": lit(False), "rowPadding": lit(5)}}],
            "subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}],
            "total": [{"properties": {"totals": lit(False)}}],
        }
        self._add(x, y, w, h, {
            "visualType": "pivotTable",
            "query": {"queryState": {
                "Rows": {"projections": [projecao("dim_projeto.projeto", "Projeto", ativo=True),
                                         projecao("fato_tarefa.titulo", "Tarefa")]},
                "Columns": {"projections": [projecao("dim_data.mes_ano", "Mês", ativo=True)]},
                "Values": {"projections": [celula]}},
                "sortDefinition": ordenar("dim_projeto.projeto", decrescente=False)},
            "objects": objetos,
            "visualContainerObjects": moldura(None),
            "drillFilterOtherVisuals": True})


SITUACAO = {"Atrasado": COR["critico"], "Concluído com atraso": COR["atencao"]}
ETAPAS_ABERTAS = {"Bloqueada": COR["critico"]}


def paginas() -> list[Pagina]:
    x0, W, y2 = Pagina.X0, Pagina.W, Pagina.Y2
    meia = (W - 16) / 2
    alto = ALTURA - 16 - y2

    portfolio = Pagina("P1Portfolio", "Portfólio", "Situação dos projetos por equipe, prazo e esforço")
    portfolio.faixa_de_cartoes([
        ("Projetos Ativos", "Projetos ativos", "Contexto Projetos Ativos", False),
        ("Projetos Atrasados", "Projetos atrasados", "Contexto Projetos Atrasados", True),
        ("% Entregues no Prazo", "Entregues no prazo", "das tarefas concluídas", False),
        ("% Orçamento Consumido", "Orçamento consumido", "Contexto Orçamento", False),
        ("Desvio de Esforço %", "Desvio de esforço", "apontado vs. estimado", False)])
    linha2 = 260
    y3 = y2 + linha2 + 16
    portfolio.grafico("clusteredBarChart", "Situação de prazo", "Projetos por situação",
                      "dim_projeto.situacao_prazo", ["Projetos"], x0, y2, meia, linha2, cores=[COR["neutro"]],
                      destaques=SITUACAO, ordem="Projetos")
    portfolio.grafico("clusteredBarChart", "Projetos por equipe", "Ativos e atrasados", "dim_projeto.equipe",
                      [("Projetos Ativos", "Ativos"), ("Projetos Atrasados", "Atrasados")],
                      x0 + meia + 16, y2, meia, linha2, cores=[COR["azul"], COR["critico"]], ordem="Projetos Ativos")
    portfolio.grafico("lineChart", "Tarefas criadas e entregues", "Por mês", "dim_data.mes_ano",
                      [("Tarefas Criadas", "Criadas"), ("Tarefas Entregues", "Entregues")],
                      x0, y3, meia, ALTURA - 16 - y3, cores=[COR["neutro"], COR["azul"]], ordem="dim_data.mes_ano",
                      ordem_crescente=True)
    portfolio.grafico("clusteredBarChart", "Horas por equipe", "Estimadas e apontadas", "dim_pessoa.equipe",
                      [("Horas Estimadas", "Estimadas"), ("Horas Apontadas", "Apontadas")],
                      x0 + meia + 16, y3, meia, ALTURA - 16 - y3, cores=[COR["neutro"], COR["azul"]],
                      ordem="Horas Apontadas")

    tarefas = Pagina("P2ProjetosTarefas", "Projetos e tarefas", "Clique num projeto para ver as tarefas dele")
    tarefas.faixa_de_cartoes([
        ("Tarefas Abertas", "Tarefas abertas", "Contexto Tarefas Abertas", False),
        ("Tarefas Vencidas", "Vencidas", "Contexto Tarefas Vencidas", True),
        ("% Tarefas Concluídas", "Concluídas", "do total de tarefas", False),
        ("Lead Time Médio (dias)", "Lead time médio (dias)", "da criação à conclusão", False),
        ("% Concluídas com Retrabalho", "Com retrabalho", "voltaram da revisão", False)])
    esquerda = 620
    direita = W - esquerda - 16
    tarefas.tabela("Projetos", "Do maior atraso para o menor",
                   [("dim_projeto.projeto", "Projeto"), ("dim_projeto.equipe", "Equipe"),
                    ("dim_projeto.situacao_prazo", "Prazo"), ("% Tarefas Concluídas", "Concluído"),
                    ("dim_projeto.dias_atraso", "Dias de atraso")],
                   x0, y2, esquerda, alto, ordem="dim_projeto.dias_atraso",
                   barras={"% Tarefas Concluídas": COR["barra_azul"], "dim_projeto.dias_atraso": COR["barra_vermelha"]})
    tarefas.grafico("clusteredBarChart", "Tarefas abertas por etapa", "Onde estão paradas agora",
                    "fato_passagem_status.status", ["Tarefas Paradas na Etapa"], x0 + esquerda + 16, y2, direita, 250,
                    cores=[COR["azul"]], destaques=ETAPAS_ABERTAS, ordem="fato_passagem_status.status",
                    ordem_crescente=True)
    tarefas.tabela("Tarefas vencidas", "Mais atrasadas primeiro",
                   [("fato_tarefa.titulo", "Tarefa"), ("dim_pessoa.pessoa", "Responsável"),
                    ("fato_tarefa.dias_atraso", "Dias")],
                   x0 + esquerda + 16, y2 + 266, direita, alto - 266, ordem="fato_tarefa.dias_atraso",
                   filtro=("fato_tarefa.situacao_prazo", "Vencida"))

    cronograma = Pagina("P3Cronograma", "Cronograma", "Projetos e tarefas no tempo; use o + para abrir as tarefas")
    cronograma.legenda([("Em andamento", COR["azul"]), ("Atrasado ou vencida", COR["critico"]),
                        ("Bloqueada", COR["atencao"]), ("Concluído", COR["concluido"]),
                        ("Cancelado", COR["cancelado"])], x0 + 400, 18, W - 400, 26)
    cronograma.gantt(x0, 80, W, ALTURA - 16 - 80)
    return [portfolio, tarefas, cronograma]


def tema() -> dict:
    return {"name": "TemaPainelProjetos",
            "dataColors": [COR[c] for c in ("azul", "neutro", "bom", "atencao", "critico", "concluido")],
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
