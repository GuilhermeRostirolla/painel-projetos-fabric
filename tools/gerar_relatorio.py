"""Gera o relatório (PBIR) em fabric/PainelProjetos.Report.

    python -m tools.gerar_relatorio"""
import hashlib
import json
import shutil
from pathlib import Path

from tools.design import layout as L
from tools.gerar_modelo import MEDIDAS

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "fabric" / "PainelProjetos.Report"
NOME = "PainelProjetos"
LARGURA, ALTURA = L.LARGURA, L.ALTURA
FUNDOS = RAIZ / "tools" / "design" / "fundos"

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
TEMA_BASE = "CY26SU04"
TEMA = "TemaPainelProjetos.json"

COR = {"texto": L.COR["texto"], "suave": L.COR["suave"], "apagado": L.COR["apagado"], "fundo": L.COR["pagina"],
       "cartao": "#121B2E", "campo": "#0F1729", "borda": L.COR["borda"], "grade": L.COR["grade"],
       "azul": L.COR["azul"], "neutro": L.COR["neutro"], "bom": L.COR["verde"], "atencao": L.COR["ambar"],
       "critico": L.COR["vermelho"], "concluido": L.COR["concluido"], "cancelado": L.COR["cancelado"],
       "barra_azul": "#2A4473", "barra_vermelha": "#6B2A3A"}

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


def sem_moldura() -> dict:
    return moldura(fundo=None, borda=False, respiro=0.0)


class Pagina:

    def __init__(self, nome: str, titulo: str):
        self.nome, self.titulo = nome, titulo
        self.fundo = f"fundo_{nome}.png"
        self.visuais: list[dict] = []
        self.fundos: set[str] = set()
        self.cartoes: list[tuple[str, str]] = []
        for i, (destino, rotulo, _) in enumerate(L.PAGINAS):
            self.botao(rotulo, destino, 12, 96 + i * 60, 48, 48)
        for col, rotulo, x, y, w, h in L.SLICERS:
            self.segmentacao(col, rotulo, x, y, w, h)
        self.cartao_simples("Texto Referência", *L.DATA_REF, 8.5, COR["suave"])
        if nome in L.KPIS:
            self.faixa_de_cartoes(L.KPIS[nome])

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

    def area(self, chave):
        return L.area(L.CARTOES[self.nome][chave])

    def texto(self, conteudo, x, y, w, h, tamanho, cor_texto, negrito=False):
        estilo = {"fontFamily": "Segoe UI Semibold" if negrito else "Segoe UI",
                  "fontSize": f"{tamanho}pt", "color": cor_texto}
        self._add(x, y, w, h, {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": conteudo, "textStyle": estilo}], "horizontalTextAlignment": "left"}]}}]},
            "visualContainerObjects": sem_moldura(),
            "drillFilterOtherVisuals": True})

    def botao(self, rotulo, destino, x, y, w, h):
        padrao = {"id": "default"}
        self._add(x, y, w, h, {
            "visualType": "actionButton",
            "objects": {
                "icon": [{"properties": {"show": lit(False)}, "selector": padrao}],
                "text": [{"properties": {"show": lit(False)}, "selector": padrao}],
                "fill": [{"properties": {"show": lit(False)}, "selector": padrao}],
                "outline": [{"properties": {"show": lit(False)}, "selector": padrao}],
            },
            "visualContainerObjects": {
                **sem_moldura(),
                "visualLink": [{"properties": {"show": lit(True), "type": lit("PageNavigation"),
                                               "navigationSection": lit(destino), "tooltip": lit(rotulo)}}],
            },
            "drillFilterOtherVisuals": True})

    def valor(self, medida, x, y, w, h, tamanho, cor_valor, negrito=False):
        fonte = lit("Segoe UI Semibold" if negrito else "Segoe UI")
        self._add(x, y, w, h, {
            "visualType": "multiRowCard",
            "query": {"queryState": {"Values": {"projections": campos([medida])}}},
            "objects": {
                "dataLabels": [{"properties": {"fontSize": lit(float(tamanho)), "color": cor(cor_valor),
                                               "fontFamily": fonte}}],
                "cardTitle": [{"properties": {"fontSize": lit(float(tamanho)), "color": cor(cor_valor),
                                              "fontFamily": fonte}}],
                "categoryLabels": [{"properties": {"show": lit(False)}}],
                "card": [{"properties": {"barShow": lit(False), "outline": lit("None"), "cardPadding": lit(0.0),
                                         "cardBackground": cor(COR["cartao"]),
                                         "cardBackgroundTransparency": lit(100.0)}}],
            },
            "visualContainerObjects": sem_moldura(),
            "drillFilterOtherVisuals": True})

    def cartao_simples(self, medida, x, y, w, h, tamanho, cor_valor):
        self._add(x, y, w, h, {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": campos([medida])}}},
            "objects": {"labels": [{"properties": {"fontSize": lit(float(tamanho)), "color": cor(cor_valor)}}],
                        "categoryLabels": [{"properties": {"show": lit(False)}}]},
            "visualContainerObjects": sem_moldura(),
            "drillFilterOtherVisuals": True})

    def faixa_de_cartoes(self, itens):
        for (x, y, w, h), (_, medida, contexto, cor_icone, _) in zip(L.kpis(len(itens)), itens):
            alerta = cor_icone == "vermelho"
            self.valor(medida, x + 70, y + 38, w - 88, 36, 20, COR["critico"] if alerta else COR["texto"],
                       negrito=True)
            if contexto in TABELA_DA_MEDIDA:
                self.valor(contexto, x + 70, y + 74, w - 88, 20, 8.5, COR["suave"])
            else:
                self.texto(contexto, x + 72, y + 74, w - 90, 20, 8.5, COR["suave"])
            self.cartoes.append((medida, contexto))

    def segmentacao(self, col, titulo, x, y, w, h):
        self._add(x, y, w, h, {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": campos([col])}}},
            "objects": {"data": [{"properties": {"mode": lit("Dropdown")}}],
                        "header": [{"properties": {"show": lit(True), "text": lit(titulo),
                                                   "fontColor": cor(COR["apagado"]), "textSize": lit(7.5)}}],
                        "items": [{"properties": {"fontColor": cor(COR["texto"]), "background": cor(COR["campo"]),
                                                  "textSize": lit(9.5), "outlineColor": cor(COR["campo"])}}]},
            "visualContainerObjects": moldura(fundo=None, borda=False, respiro=4.0),
            "drillFilterOtherVisuals": True})

    def grafico(self, tipo, chave, categoria, medidas, cores=None, destaques=None, ordem=None, ordem_crescente=False):
        x, y, w, h = self.area(chave)
        barras = tipo not in ("lineChart", "donutChart")
        horizontal = tipo == "clusteredBarChart"
        objetos = {
            "categoryAxis": [{"properties": {"show": lit(True), "fontSize": lit(9.0 if horizontal else 8.0),
                                             "labelColor": cor(COR["texto"] if horizontal else COR["suave"]),
                                             "showAxisTitle": lit(False), "innerPadding": lit(30.0 if barras else 0.0),
                                             "maxMarginFactor": lit(45 if horizontal else 25),
                                             "gridlineShow": lit(False)}}],
            "valueAxis": [{"properties": {"show": lit(not barras), "fontSize": lit(8.0),
                                          "labelColor": cor(COR["apagado"]), "showAxisTitle": lit(False),
                                          "labelDisplayUnits": lit(1.0), "gridlineShow": lit(not barras),
                                          "gridlineColor": cor(COR["grade"]), "gridlineStyle": lit("solid")}}],
            "legend": [{"properties": {"show": lit(len(medidas) > 1 or tipo == "donutChart"),
                                       "position": lit("Right" if tipo == "donutChart" else "TopLeft"),
                                       "fontSize": lit(8.5), "labelColor": cor(COR["suave"])}}],
            "labels": [{"properties": {"show": lit(barras), "fontSize": lit(8.5), "color": cor(COR["texto"]),
                                       "labelDisplayUnits": lit(1.0)}}],
        }
        if tipo == "donutChart":
            objetos = {
                "legend": objetos["legend"],
                "labels": [{"properties": {"show": lit(True), "labelStyle": lit("Data value"),
                                           "color": cor(COR["texto"]), "fontSize": lit(9.0),
                                           "labelDisplayUnits": lit(1.0)}}],
                "slices": [{"properties": {"innerRadiusRatio": lit(72)}}],
            }
        if tipo == "lineChart":
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
                               "visualContainerObjects": sem_moldura(), "drillFilterOtherVisuals": True})

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

    def tabela(self, chave, colunas_, ordem, crescente=False, barras=None, filtro=None):
        x, y, w, h = self.area(chave)
        objetos = {**self._estilo_tabela(), "total": [{"properties": {"totals": lit(False)}}]}
        if barras:
            objetos["columnFormatting"] = [
                {"properties": {"dataBars": {"positiveColor": cor(c), "negativeColor": cor(COR["barra_vermelha"]),
                                             "axisColor": cor(COR["borda"]), "reverseDirection": lit(False),
                                             "hideText": lit(False)}},
                 "selector": {"metadata": projecao(ref)["queryRef"]}}
                for ref, c in barras.items()]
        extra = {"filterConfig": filtro_igual(*filtro, nome=hashlib.sha1(f"{self.nome}/{chave}".encode())
                                              .hexdigest()[:20])} if filtro else None
        self._add(x, y, w, h, {
            "visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": campos(colunas_)}},
                      "sortDefinition": ordenar(ordem, not crescente)},
            "objects": objetos,
            "visualContainerObjects": sem_moldura(),
            "drillFilterOtherVisuals": True}, extra)

    def gantt(self, chave):
        x, y, w, h = self.area(chave)
        celula = projecao("Cronograma")
        cor_da_medida = {"solid": {"color": {"expr": campo("Cronograma Cor")}}}
        todas = {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": celula["queryRef"]}
        objetos = {
            **self._estilo_tabela(),
            "rowHeaders": [{"properties": {"fontSize": lit(9.0), "fontColor": cor(COR["texto"]),
                                           "backColor": cor(COR["cartao"]),
                                           "showExpandCollapseButtons": lit(True), "wordWrap": lit(False)}}],
            "columnHeaders": [{"properties": {"fontColor": cor(COR["apagado"]), "fontSize": lit(8.0),
                                              "backColor": cor(COR["cartao"]), "alignment": lit("Center"),
                                              "outline": lit("BottomOnly")}}],
            "values": [{"properties": {"fontSize": lit(8.0), "backColorPrimary": cor(COR["cartao"]),
                                       "backColorSecondary": cor(COR["cartao"])}},
                       {"properties": {"backColor": cor_da_medida, "fontColor": cor_da_medida}, "selector": todas}],
            "grid": [{"properties": {"gridHorizontal": lit(True), "gridHorizontalColor": cor(COR["grade"]),
                                     "gridVertical": lit(False), "outlineColor": cor(COR["borda"]),
                                     "rowPadding": lit(5)}}],
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
            "visualContainerObjects": sem_moldura(),
            "drillFilterOtherVisuals": True})


FAROL = {"Verde": COR["bom"], "Amarelo": COR["atencao"], "Vermelho": COR["critico"], "Encerrado": COR["cancelado"]}


def paginas() -> list[Pagina]:
    titulos = {p[0]: p[1] for p in L.PAGINAS}

    portfolio = Pagina("P1Portfolio", titulos["P1Portfolio"])
    portfolio.grafico("donutChart", "saude", "dim_projeto.farol", ["Projetos"], destaques=FAROL, ordem="Projetos")
    portfolio.grafico("lineChart", "entregas", "dim_data.mes_ano",
                      [("Tarefas Criadas", "Criadas"), ("Tarefas Entregues", "Entregues")],
                      cores=[COR["concluido"], COR["azul"]], ordem="dim_data.mes_ano", ordem_crescente=True)
    portfolio.tabela("risco", [("dim_projeto.projeto", "Projeto"), ("dim_projeto.dias_atraso", "Dias")],
                     ordem="dim_projeto.dias_atraso", barras={"dim_projeto.dias_atraso": COR["barra_vermelha"]},
                     filtro=("dim_projeto.situacao_prazo", "Atrasado"))
    portfolio.grafico("clusteredColumnChart", "equipes", "dim_projeto.portfolio",
                      [("Projetos Ativos", "Ativos"), ("Projetos Atrasados", "Atrasados")],
                      cores=[COR["azul"], COR["critico"]], ordem="Projetos Ativos")
    portfolio.grafico("clusteredColumnChart", "esforco", "dim_projeto.etapa", ["Projetos"],
                      cores=[COR["azul"]], destaques={"Concluído": COR["concluido"]}, ordem="Projetos")

    tarefas = Pagina("P2ProjetosTarefas", titulos["P2ProjetosTarefas"])
    tarefas.tabela("projetos", [("dim_projeto.projeto", "Projeto"), ("dim_projeto.portfolio", "Portfólio"),
                                ("dim_projeto.etapa", "Etapa"), ("dim_projeto.farol", "Farol"),
                                ("% Tarefas Concluídas", "Concluído"), ("dim_projeto.dias_atraso", "Dias de atraso")],
                   ordem="dim_projeto.dias_atraso",
                   barras={"% Tarefas Concluídas": COR["barra_azul"], "dim_projeto.dias_atraso": COR["barra_vermelha"]})
    tarefas.grafico("clusteredBarChart", "etapas", "fato_passagem_status.status", ["Tarefas Paradas na Etapa"],
                    cores=[COR["azul"]], destaques={"Impedido": COR["critico"]},
                    ordem="fato_passagem_status.status", ordem_crescente=True)
    tarefas.tabela("vencidas", [("fato_tarefa.titulo", "Tarefa"), ("dim_pessoa.pessoa", "Responsável"),
                                ("fato_tarefa.dias_atraso", "Dias")],
                   ordem="fato_tarefa.dias_atraso", filtro=("fato_tarefa.situacao_prazo", "Vencida"))

    cronograma = Pagina("P3Cronograma", titulos["P3Cronograma"])
    cronograma.gantt("gantt")
    return [portfolio, tarefas, cronograma]


def tema() -> dict:
    return {"name": "TemaPainelProjetos",
            "dataColors": [COR[c] for c in ("azul", "critico", "atencao", "bom", "concluido", "neutro")],
            "foreground": COR["texto"], "foregroundNeutralSecondary": COR["suave"],
            "foregroundNeutralTertiary": COR["apagado"], "background": COR["cartao"],
            "backgroundLight": COR["campo"], "backgroundNeutral": COR["borda"], "tableAccent": COR["azul"],
            "good": COR["bom"], "neutral": COR["atencao"], "bad": COR["critico"],
            "textClasses": {"callout": {"fontFace": "Segoe UI Semibold", "color": COR["texto"]},
                            "title": {"fontFace": "Segoe UI Semibold", "color": COR["texto"], "fontSize": 12},
                            "header": {"fontFace": "Segoe UI Semibold", "color": COR["texto"]},
                            "label": {"fontFace": "Segoe UI", "color": COR["suave"]}},
            "visualStyles": {"*": {"*": {"background": [{"show": False}], "border": [{"show": False}],
                                          "dropShadow": [{"show": False}], "visualHeader": [{"show": False}]}}}}


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
             "items": [{"name": TEMA, "path": TEMA, "type": "CustomTheme"}]
             + [{"name": p.fundo, "path": p.fundo, "type": "Image"} for p in lista]},
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
            "objects": {"background": [{"properties": {
                "image": {"image": {"name": lit(p.fundo),
                                    "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources",
                                                                            "PackageType": 1, "ItemName": p.fundo}}},
                                    "scaling": lit("Fit")}},
                "transparency": lit(0.0)}}],
                        "outspace": [{"properties": {"color": cor(COR["fundo"])}}]}})
        for v in p.visuais:
            escrever(pasta / "visuals" / v["name"] / "visual.json", v)
    shutil.copy(RAIZ / "tools" / "recursos" / f"{TEMA_BASE}.json",
                _mkdir(destino / "StaticResources" / "SharedResources" / "BaseThemes") / f"{TEMA_BASE}.json")
    escrever(destino / "StaticResources" / "RegisteredResources" / TEMA, tema())
    for p in lista:
        shutil.copy(FUNDOS / f"{p.nome}.png", destino / "StaticResources" / "RegisteredResources" / p.fundo)
    return lista


def _mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


if __name__ == "__main__":
    lista = gerar()
    print(f"relatório gerado em {DESTINO.relative_to(RAIZ)}: "
          + ", ".join(f"{p.titulo} ({len(p.visuais)} visuais)" for p in lista))
