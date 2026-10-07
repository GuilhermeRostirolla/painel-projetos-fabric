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

COR = {"texto": "#1B2430", "suave": "#5B6573", "fundo": "#F4F6F9", "cartao": "#FFFFFF",
       "azul": "#1F5A96", "verde": "#1E8A6E", "laranja": "#D9822B", "vermelho": "#C2413A",
       "cinza": "#9AA3AF", "roxo": "#6B5CA5"}

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


def campo(ref: str) -> dict:
    """'Medida' (sem ponto) ou 'tabela.coluna'."""
    if "." in ref and ref.split(".")[0] in {"dim_data", "dim_projeto", "dim_pessoa", "dim_status",
                                             "fato_tarefa", "fato_passagem_status", "ref_parametros"}:
        tabela, coluna = ref.split(".", 1)
        return {"Column": {"Expression": {"SourceRef": {"Entity": tabela}}, "Property": coluna}}
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


def moldura(titulo: str | None, fundo: bool = True, respiro: float = 8.0) -> dict:
    objetos = {
        "title": [{"properties": {"show": lit(bool(titulo)), **({"text": lit(titulo), "fontColor": cor(COR["texto"]),
                                                                  "fontSize": lit(11.0), "bold": lit(True)}
                                                                 if titulo else {})}}],
        "background": [{"properties": {"show": lit(fundo), "color": cor(COR["cartao"]),
                                       "transparency": lit(0.0)}}],
        "border": [{"properties": {"show": lit(fundo), "color": cor("#E3E7ED"), "radius": lit(8.0)}}],
        "dropShadow": [{"properties": {"show": lit(False)}}],
        "visualHeader": [{"properties": {"show": lit(False)}}],
        "padding": [{"properties": {k: lit(respiro) for k in ("top", "bottom", "left", "right")}}],
    }
    return objetos


# --- visuais -------------------------------------------------------------------------------

class Pagina:
    def __init__(self, nome: str, titulo: str, subtitulo: str):
        self.nome, self.titulo = nome, titulo
        self.visuais: list[dict] = []
        self.texto(titulo, 24, 8, 760, 42, 20, COR["texto"], negrito=True)
        self.texto(subtitulo, 24, 52, 900, 24, 10.5, COR["suave"])
        self.cartao("Texto Referência", 1036, 18, 220, 46, rotulo=False, tamanho=11.0, cor_valor=COR["suave"],
                    fundo=False)
        self.segmentacao("dim_projeto.equipe", "Equipe", 24, 82, 220, 52)
        self.segmentacao("dim_projeto.status", "Status do projeto", 256, 82, 220, 52)

    def _id(self) -> str:
        return hashlib.sha1(f"{self.nome}/{len(self.visuais)}".encode()).hexdigest()[:20]

    def _add(self, x, y, w, h, visual: dict) -> None:
        z = len(self.visuais) * 100
        self.visuais.append({
            "$schema": f"{SCHEMA}/visualContainer/2.11.0/schema.json",
            "name": self._id(),
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
            "visual": visual,
        })

    def texto(self, conteudo, x, y, w, h, tamanho, cor_texto, negrito=False):
        estilo = {"fontFamily": "Segoe UI Semibold" if negrito else "Segoe UI",
                  "fontSize": f"{tamanho}pt", "color": cor_texto}
        self._add(x, y, w, h, {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": conteudo, "textStyle": estilo}], "horizontalTextAlignment": "left"}]}}]},
            "visualContainerObjects": moldura(None, fundo=False, respiro=0.0),
            "drillFilterOtherVisuals": True})

    def cartao(self, medida, x, y, w=190, h=96, rotulo=True, tamanho=22.0, cor_valor=None, fundo=True):
        self._add(x, y, w, h, {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": campos([medida])}}},
            "objects": {
                "labels": [{"properties": {"fontSize": lit(tamanho), "color": cor(cor_valor or COR["texto"]),
                                           "labelDisplayUnits": lit(1.0)}}],
                "categoryLabels": [{"properties": {"show": lit(rotulo), "fontSize": lit(9.0),
                                                   "color": cor(COR["suave"])}}],
            },
            "visualContainerObjects": moldura(None, fundo=fundo),
            "drillFilterOtherVisuals": True})

    def segmentacao(self, coluna, titulo, x, y, w, h):
        self._add(x, y, w, h, {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": campos([coluna])}}},
            "objects": {"data": [{"properties": {"mode": lit("Dropdown")}}],
                        "header": [{"properties": {"show": lit(True), "text": lit(titulo),
                                                   "fontColor": cor(COR["suave"]), "textSize": lit(9.0)}}]},
            "visualContainerObjects": moldura(None, fundo=False),
            "drillFilterOtherVisuals": True})

    def grafico(self, tipo, titulo, categoria, medidas, x, y, w, h, cores=None, ordem=None,
                ordem_crescente=False, legenda=True):
        objetos = {"categoryAxis": [{"properties": {"fontSize": lit(9.0), "labelColor": cor(COR["suave"]),
                                                    "showAxisTitle": lit(False)}}],
                   "valueAxis": [{"properties": {"fontSize": lit(9.0), "labelColor": cor(COR["suave"]),
                                                 "showAxisTitle": lit(False), "labelDisplayUnits": lit(1.0)}}],
                   "legend": [{"properties": {"show": lit(legenda and len(medidas) > 1), "position": lit("Top"),
                                              "fontSize": lit(9.0)}}],
                   "labels": [{"properties": {"show": lit(tipo != "lineChart"), "fontSize": lit(9.0),
                                              "labelDisplayUnits": lit(1.0)}}]}
        if cores:
            objetos["dataPoint"] = [
                {"properties": {"fill": cor(c)}, "selector": {"metadata": projecao(m)["queryRef"]}}
                for m, c in zip([m if isinstance(m, str) else m[0] for m in medidas], cores)]
        query = {"queryState": {"Category": {"projections": [projecao(categoria, ativo=True)]},
                                "Y": {"projections": campos(medidas)}}}
        if ordem:
            query["sortDefinition"] = ordenar(ordem, not ordem_crescente)
        self._add(x, y, w, h, {"visualType": tipo, "query": query, "objects": objetos,
                               "visualContainerObjects": moldura(titulo), "drillFilterOtherVisuals": True})

    def tabela(self, titulo, colunas, x, y, w, h, ordem, crescente=False):
        self._add(x, y, w, h, {
            "visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": campos(colunas)}},
                      "sortDefinition": ordenar(ordem, not crescente)},
            "objects": {"columnHeaders": [{"properties": {"fontColor": cor(COR["texto"]), "bold": lit(True),
                                                          "backColor": cor("#EEF1F5"), "fontSize": lit(9.0)}}],
                        "values": [{"properties": {"fontSize": lit(9.0)}}],
                        "grid": [{"properties": {"gridHorizontal": lit(True), "rowPadding": lit(3)}}]},
            "visualContainerObjects": moldura(titulo),
            "drillFilterOtherVisuals": True})

    def linha_de_cartoes(self, medidas, y=146, h=96):
        n = len(medidas)
        espaco = 12
        w = (LARGURA - 48 - espaco * (n - 1)) / n
        for i, m in enumerate(medidas):
            self.cartao(m, round(24 + i * (w + espaco), 1), y, round(w, 1), h)


# --- páginas -------------------------------------------------------------------------------

def paginas() -> list[Pagina]:
    y2, y3 = 254, 486          # linhas da grade abaixo dos cartões
    meia = (LARGURA - 48 - 12) / 2

    geral = Pagina("P1Geral", "Painel de Projetos",
                   "Portfólio, prazos e entregas · dados simulados de uma ferramenta de gestão de projetos")
    geral.linha_de_cartoes(["Projetos Ativos", "Projetos Atrasados", "Tarefas Abertas", "Tarefas Vencidas",
                            "% Entregues no Prazo", "Desvio de Esforço %"])
    geral.grafico("lineChart", "Tarefas criadas × entregues por mês", "dim_data.mes_ano",
                  [("Tarefas Criadas", "Criadas"), ("Tarefas Entregues", "Entregues")],
                  24, y2, round(meia, 1), 452, cores=[COR["azul"], COR["verde"]], ordem="dim_data.mes_ano",
                  ordem_crescente=True)
    geral.grafico("clusteredColumnChart", "Projetos ativos e atrasados por equipe", "dim_projeto.equipe",
                  [("Projetos Ativos", "Ativos"), ("Projetos Atrasados", "Atrasados")],
                  round(36 + meia, 1), y2, round(meia, 1), 220, cores=[COR["azul"], COR["vermelho"]],
                  ordem="Projetos Ativos")
    geral.grafico("clusteredColumnChart", "Situação de prazo dos projetos", "dim_projeto.situacao_prazo",
                  ["Projetos"], round(36 + meia, 1), y3, round(meia, 1), 220, cores=[COR["roxo"]],
                  ordem="Projetos", legenda=False)

    projetos = Pagina("P2Projetos", "Projetos", "Quem está atrasado, quanto e quanto do orçamento de horas já foi")
    projetos.linha_de_cartoes(["Projetos", "Projetos em Andamento", "Projetos Concluídos", "% Projetos Atrasados",
                               "% Projetos Entregues no Prazo", "Atraso Médio dos Projetos (dias)"])
    projetos.tabela("Projetos (ordenados por dias de atraso)",
                    [("dim_projeto.projeto", "Projeto"), ("dim_projeto.equipe", "Equipe"),
                     ("dim_projeto.gestor", "Gestor"), ("dim_projeto.status", "Status"),
                     ("dim_projeto.situacao_prazo", "Prazo"), ("dim_projeto.data_fim_planejada", "Fim planejado"),
                     ("dim_projeto.dias_atraso", "Dias de atraso"), ("Tarefas Abertas", "Abertas"),
                     ("Tarefas Vencidas", "Vencidas"), ("% Orçamento Consumido", "% orçamento")],
                    24, y2, LARGURA - 48, 452, ordem="dim_projeto.dias_atraso")

    fluxo = Pagina("P3Fluxo", "Fluxo e gargalos",
                   "Quanto tempo as tarefas ficam em cada etapa, onde travam e quanto voltam da revisão")
    fluxo.linha_de_cartoes(["Lead Time Médio (dias)", "Ciclo Médio (dias)", "Ciclo Mediano (dias)",
                            "% Concluídas com Retrabalho", "Tarefas Bloqueadas", "Paradas há mais de 15 dias"])
    fluxo.grafico("clusteredColumnChart", "Tempo médio em cada etapa (dias)", "fato_passagem_status.status",
                  ["Tempo Médio na Etapa (dias)"], 24, y2, round(meia, 1), 220, cores=[COR["azul"]],
                  ordem="fato_passagem_status.status", ordem_crescente=True, legenda=False)
    fluxo.grafico("clusteredColumnChart", "Tarefas paradas agora, por etapa", "fato_passagem_status.status",
                  ["Tarefas Paradas na Etapa"], round(36 + meia, 1), y2, round(meia, 1), 220,
                  cores=[COR["laranja"]], ordem="fato_passagem_status.status", ordem_crescente=True,
                  legenda=False)
    fluxo.grafico("lineChart", "Mudanças de status por mês", "dim_data.mes_ano",
                  [("Mudanças de Status", "Mudanças")], 24, y3, round(meia, 1), 220, cores=[COR["azul"]],
                  ordem="dim_data.mes_ano", ordem_crescente=True, legenda=False)
    fluxo.grafico("clusteredColumnChart", "Bloqueios por mês", "dim_data.mes_ano",
                  [("Bloqueios no Período", "Bloqueios")], round(36 + meia, 1), y3, round(meia, 1), 220,
                  cores=[COR["vermelho"]], ordem="dim_data.mes_ano", ordem_crescente=True, legenda=False)

    pessoas = Pagina("P4Pessoas", "Pessoas e esforço",
                     "Carga de cada pessoa e horas apontadas contra o estimado")
    pessoas.linha_de_cartoes(["Horas Orçadas", "Horas Estimadas", "Horas Apontadas", "% Orçamento Consumido",
                              "Tarefas Concluídas", "Idade Média das Abertas (dias)"])
    pessoas.grafico("clusteredBarChart", "Horas estimadas × apontadas por equipe", "dim_pessoa.equipe",
                    [("Horas Estimadas", "Estimadas"), ("Horas Apontadas", "Apontadas")],
                    24, y2, 460, 452, cores=[COR["cinza"], COR["azul"]], ordem="Horas Apontadas")
    pessoas.tabela("Carga por pessoa",
                   [("dim_pessoa.pessoa", "Pessoa"), ("dim_pessoa.equipe", "Equipe"), ("dim_pessoa.cargo", "Cargo"),
                    ("Tarefas Abertas", "Abertas"), ("Tarefas Vencidas", "Vencidas"),
                    ("Tarefas Concluídas", "Concluídas"), ("Horas Apontadas", "Horas"),
                    ("Desvio de Esforço %", "Desvio")],
                   496, y2, LARGURA - 496 - 24, 452, ordem="Tarefas Abertas")
    return [geral, projetos, fluxo, pessoas]


# --- arquivos ------------------------------------------------------------------------------

def tema() -> dict:
    return {"name": "TemaPainelProjetos",
            "dataColors": [COR[c] for c in ("azul", "verde", "laranja", "vermelho", "roxo", "cinza")],
            "foreground": COR["texto"], "foregroundNeutralSecondary": COR["suave"],
            "background": COR["cartao"], "backgroundLight": COR["fundo"], "tableAccent": COR["azul"],
            "good": COR["verde"], "neutral": COR["laranja"], "bad": COR["vermelho"],
            "textClasses": {"callout": {"fontFace": "Segoe UI Semibold", "color": COR["texto"]},
                            "title": {"fontFace": "Segoe UI Semibold", "color": COR["texto"]},
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
