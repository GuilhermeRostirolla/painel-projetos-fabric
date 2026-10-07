"""Gera o HTML do redesign (6 quadros) que foi enviado ao Figma: diagnóstico, as 4 páginas e o guia de estilo.

    python tools/design/mockup_redesign.py      # escreve docs/design/redesign.html

Os números do mockup vêm de dados_mockup.json (agregados da gold local de 30/09/2026).
"""
import json
from pathlib import Path

S = Path(__file__).parent
D = json.loads((S / "dados_mockup.json").read_text())

T = dict(page="#F3F5F8", surf="#FFFFFF", border="#E4E8EE", ink="#17212B", ink2="#5A6472", muted="#8A93A0",
         navy="#0F2A44", navy2="#B9C6D6", blue="#2F6DB5", base="#A3ACB9", good="#1F8A5B", warn="#D29B00",
         crit="#C2362F", grid="#EDF0F4", soft="#E9EFF7")
MES = {"01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai", "06": "jun", "07": "jul", "08": "ago",
       "09": "set", "10": "out", "11": "nov", "12": "dez"}


def br(n, d=0):
    s = f"{n:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def mes(m):
    return f"{MES[m[5:]]}/{m[2:4]}"


# ---------- primitivas ----------
def header(titulo, sub, ativo):
    abas = ["Visão geral", "Projetos", "Fluxo e gargalos", "Pessoas e esforço"]
    tabs = "".join(f'<div class="tab{" on" if a == ativo else ""}">{a}</div>' for a in abas)
    return f"""<div class="hdr">
  <div class="ttl">{titulo}</div><div class="sub">{sub}</div>
  <div class="tabs">{tabs}</div>
  <div class="flt"><div class="sl"><span>Equipe</span><b>Todas</b><i>▾</i></div>
  <div class="sl"><span>Status</span><b>Todos</b><i>▾</i></div>
  <div class="ref">● Dados até 30/09/2026</div></div></div>"""


def kpis(itens):
    out = []
    for rot, val, ctx, tom in itens:
        cor = {"n": T["blue"], "c": T["crit"], "w": T["warn"], "g": T["good"]}[tom]
        ccor = {"n": T["ink2"], "c": T["crit"], "w": "#9A7000", "g": T["good"]}[tom]
        out.append(f"""<div class="kpi"><div class="acc" style="background:{cor}"></div>
  <div class="kl">{rot}</div><div class="kv">{val}</div><div class="kc" style="color:{ccor}">{ctx}</div></div>""")
    return f'<div class="kpis">{"".join(out)}</div>'


def card(x, y, w, h, titulo, sub, corpo):
    return f"""<div class="card" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">
  <div class="ct">{titulo}</div><div class="cs">{sub}</div>{corpo}</div>"""


def hbars(itens, w, h, cores, fmt=lambda v: br(v), lab=150, pad_top=0):
    """itens: [(rótulo, valor)] · barras horizontais com rótulo direto, sem eixo."""
    n = len(itens)
    mx = max(v for _, v in itens)
    passo = (h - pad_top) / n
    bh = min(18, passo * 0.62)
    area = w - lab - 48
    g = []
    for i, (r, v) in enumerate(itens):
        y = pad_top + i * passo + (passo - bh) / 2
        bw = max(2, area * v / mx)
        c = cores[i] if isinstance(cores, list) else cores
        g.append(f'<text x="{lab - 10}" y="{y + bh / 2 + 4}" text-anchor="end" class="al">{r}</text>'
                 f'<rect x="{lab}" y="{y}" width="{bw}" height="{bh}" rx="3" fill="{c}"/>'
                 f'<text x="{lab + bw + 6}" y="{y + bh / 2 + 4}" class="dl">{fmt(v)}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(g)}</svg>'


def hbars2(itens, w, h, c1, c2, n1, n2, lab=130, fmt=lambda v: br(v)):
    """duas séries agrupadas horizontais; itens: [(rótulo, v1, v2)]"""
    n = len(itens)
    mx = max(max(a, b) for _, a, b in itens)
    top = 26
    passo = (h - top) / n
    bh = min(16, passo * 0.3)
    area = w - lab - 52
    g = [f'<rect x="{lab}" y="4" width="10" height="10" rx="2" fill="{c1}"/><text x="{lab + 15}" y="13" class="lg">{n1}</text>'
         f'<rect x="{lab + 90}" y="4" width="10" height="10" rx="2" fill="{c2}"/><text x="{lab + 105}" y="13" class="lg">{n2}</text>']
    for i, (r, a, b) in enumerate(itens):
        y = top + i * passo + (passo - 2 * bh - 3) / 2
        g.append(f'<text x="{lab - 10}" y="{y + bh + 4}" text-anchor="end" class="al">{r}</text>')
        for j, (v, c) in enumerate(((a, c1), (b, c2))):
            yy = y + j * (bh + 3)
            bw = max(2, area * v / mx)
            g.append(f'<rect x="{lab}" y="{yy}" width="{bw}" height="{bh}" rx="2" fill="{c}"/>'
                     f'<text x="{lab + bw + 5}" y="{yy + bh - 2}" class="dl s">{fmt(v)}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(g)}</svg>'


def linhas(series, w, h, rotulos, ticks=4, legenda=True):
    """series: [(nome, valores, cor, destaque)] · linha 2px, grade leve, rótulo direto no último ponto."""
    L, R, top, bot = 36, 70, 30 if legenda else 10, 22
    mx = max(max(v) for _, v, _, _ in series)
    passo = 10 ** len(str(int(mx))) / 10
    teto = ((mx // passo) + 1) * passo
    pw, ph = w - L - R, h - top - bot
    n = len(rotulos)
    X = lambda i: L + pw * i / (n - 1)
    Y = lambda v: top + ph * (1 - v / teto)
    g = []
    for k in range(ticks + 1):
        v = teto * k / ticks
        g.append(f'<line x1="{L}" x2="{L + pw}" y1="{Y(v)}" y2="{Y(v)}" stroke="{T["grid"]}"/>'
                 f'<text x="{L - 8}" y="{Y(v) + 4}" text-anchor="end" class="ax">{br(v)}</text>')
    for i, r in enumerate(rotulos):
        if i % 3 == 0 or i == n - 1:
            g.append(f'<text x="{X(i)}" y="{h - 6}" text-anchor="middle" class="ax">{r}</text>')
    if legenda:
        x = L
        for nome, _, c, _ in series:
            g.append(f'<rect x="{x}" y="6" width="14" height="3" rx="1.5" fill="{c}" transform="translate(0,4)"/>'
                     f'<text x="{x + 19}" y="15" class="lg">{nome}</text>')
            x += 26 + 7 * len(nome)
    for nome, v, c, dest in series:
        pts = " ".join(f"{X(i):.1f},{Y(a):.1f}" for i, a in enumerate(v))
        g.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="{2.5 if dest else 2}" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
        g.append(f'<circle cx="{X(n - 1)}" cy="{Y(v[-1])}" r="4" fill="{c}" stroke="#fff" stroke-width="2"/>')
        dy = -6 if dest else 12
        g.append(f'<text x="{X(n - 1) + 8}" y="{Y(v[-1]) + dy + 4}" class="dl" fill="{c}">{br(v[-1])}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(g)}</svg>'


def colunas(rotulos, v, w, h, cor, destaque=0):
    L, top, bot = 8, 18, 22
    n = len(v)
    mx = max(v)
    passo = (w - 2 * L) / n
    bw = passo * 0.62
    g = [f'<line x1="{L}" x2="{w - L}" y1="{h - bot}" y2="{h - bot}" stroke="{T["border"]}"/>']
    for i, a in enumerate(v):
        bh = (h - top - bot) * a / mx
        x = L + i * passo + (passo - bw) / 2
        c = cor if (not destaque or i >= n - destaque) else "#C9D0DA"
        g.append(f'<rect x="{x}" y="{h - bot - bh}" width="{bw}" height="{bh}" rx="3" fill="{c}"/>')
        if not destaque or i >= n - destaque:
            g.append(f'<text x="{x + bw / 2}" y="{h - bot - bh - 5}" text-anchor="middle" class="dl s">{a}</text>')
        if i % 3 == 0 or i == n - 1:
            g.append(f'<text x="{x + bw / 2}" y="{h - 6}" text-anchor="middle" class="ax">{rotulos[i]}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(g)}</svg>'


def tabela(cab, linhas_, larg, barras=None):
    """barras: {índice_coluna: (cor, máximo)} → barra de dados atrás do número"""
    barras = barras or {}
    th = "".join(f'<th style="width:{l}px;text-align:{"right" if i in barras or a == "r" else "left"}">{c}</th>'
                 for i, ((c, a), l) in enumerate(zip(cab, larg)))
    trs = []
    for ln in linhas_:
        tds = []
        for i, (v, l) in enumerate(zip(ln, larg)):
            if i in barras:
                cor, mx = barras[i]
                num = float(str(v).replace(".", "").replace(",", ".").replace("%", "").replace("+", "")) if v != "" else 0
                bw = max(0, (l - 12) * abs(num) / mx)
                tds.append(f'<td style="text-align:right"><div class="db"><div style="width:{bw}px;background:{cor}"></div>'
                           f'<span>{v}</span></div></td>')
            elif isinstance(v, tuple):
                txt, cor = v
                tds.append(f'<td><span class="pill" style="color:{cor};background:{cor}14"><i style="background:{cor}"></i>{txt}</span></td>')
            else:
                tds.append(f'<td style="text-align:{"right" if cab[i][1] == "r" else "left"}">{v}</td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


PRAZO = {"Atrasado": T["crit"], "Concluído com atraso": T["warn"], "Concluído no prazo": T["good"],
         "No prazo": T["blue"], "Pausado": T["muted"], "Cancelado": T["muted"]}

# ---------- páginas ----------
def p1():
    meses = [m for m, _ in D["criadas"]]
    ent = dict(D["entregues"])
    corpo = header("Painel de Projetos", "Portfólio, prazos e entregas · 45 projetos de 5 equipes", "Visão geral")
    corpo += kpis([("PROJETOS ATIVOS", "26", "de 45 no portfólio", "n"),
                   ("PROJETOS ATRASADOS", "7", "▲ 27% dos ativos", "c"),
                   ("TAREFAS ABERTAS", "140", "7 bloqueadas agora", "n"),
                   ("TAREFAS VENCIDAS", "39", "▲ 31% das abertas", "c"),
                   ("ENTREGUES NO PRAZO", "76,2%", "das tarefas concluídas", "n"),
                   ("DESVIO DE ESFORÇO", "+33,6%", "▲ apontado acima do estimado", "w")])
    corpo += card(24, 204, 760, 244, "Entregas acompanham a demanda",
                  "Tarefas criadas × entregues por mês",
                  linhas([("Criadas", [v for _, v in D["criadas"]], T["base"], False),
                          ("Entregues", [ent.get(m, 0) for m in meses], T["blue"], True)],
                         728, 186, [mes(m) for m in meses]))
    eq = [("Tecnologia", 7, 3), ("Comercial", 6, 1), ("Dados & BI", 5, 1), ("Operações", 5, 1), ("Pessoas & Cultura", 3, 1)]
    corpo += card(796, 204, 460, 244, "Tecnologia concentra os atrasos", "Projetos ativos e atrasados por equipe",
                  hbars2(eq, 428, 186, T["blue"], T["crit"], "Ativos", "Atrasados"))
    sit = [("No prazo", 19), ("Concluído com atraso", 11), ("Atrasado", 7), ("Concluído no prazo", 3),
           ("Pausado", 3), ("Cancelado", 2)]
    corpo += card(24, 460, 460, 244, "Situação de prazo do portfólio", "Projetos por situação · vermelho e âmbar pedem ação",
                  hbars(sit, 428, 186, [PRAZO[r] if r in ("Atrasado", "Concluído com atraso") else "#B8C4D3" for r, _ in sit]))
    linhas_ = [(r[0], r[1], r[2], str(r[6])) for r in D["proj"] if r[4] == "Atrasado"]
    corpo += card(496, 460, 760, 244, "Precisam de atenção", "Projetos em andamento já depois do fim planejado",
                  tabela([("Projeto", "l"), ("Equipe", "l"), ("Gestor", "l"), ("Dias de atraso", "r")],
                         linhas_, [250, 140, 150, 170], {3: (T["crit"] + "33", 407)}))
    return corpo


def p2():
    corpo = header("Projetos", "Quem está atrasado, quanto, e quanto do orçamento de horas já foi", "Projetos")
    corpo += kpis([("PROJETOS", "45", "5 equipes · 9 gestores", "n"),
                   ("EM ANDAMENTO", "25", "1 em planejamento", "n"),
                   ("CONCLUÍDOS", "14", "desde jan/25", "g"),
                   ("% ATRASADOS", "26,9%", "▲ 7 de 26 ativos", "c"),
                   ("ENTREGUES NO PRAZO", "21,4%", "▼ 3 de 14 concluídos", "c"),
                   ("ATRASO MÉDIO", "89 dias", "entre os atrasados", "w")])
    orc = [(e, v * 100) for e, v in D["orc_equipe"]]
    corpo += card(24, 204, 380, 500, "Orçamento de horas consumido", "% das horas orçadas já apontadas, por equipe",
                  hbars(orc, 348, 180, [T["warn"] if v > 100 else T["blue"] for _, v in orc],
                        fmt=lambda v: br(v, 1) + "%", lab=120)
                  + '<div class="note"><b>Leitura:</b> acima de 100% (âmbar) a equipe já gastou mais horas do que '
                    'orçou para o portfólio inteiro.</div>'
                  + '<div class="ct2">Situação de prazo</div>'
                  + hbars([("No prazo", 19), ("Concluído com atraso", 11), ("Atrasado", 7), ("Concluído no prazo", 3),
                          ("Pausado", 3), ("Cancelado", 2)], 348, 150,
                          ["#B8C4D3", T["warn"], T["crit"], "#B8C4D3", "#B8C4D3", "#B8C4D3"], lab=130))
    linhas_ = []
    for r in D["proj"]:
        linhas_.append((r[0], r[1], r[2], (r[4], PRAZO[r[4]]), r[5], str(r[6])))
    corpo += card(416, 204, 840, 500, "Todos os projetos, do maior atraso para o menor",
                  "Clique numa linha para filtrar as outras páginas",
                  tabela([("Projeto", "l"), ("Equipe", "l"), ("Gestor", "l"), ("Prazo", "l"), ("Fim planejado", "r"),
                          ("Dias de atraso", "r")], linhas_, [230, 120, 130, 150, 90, 100],
                         {5: (T["crit"] + "33", 407)}))
    return corpo


def p3():
    corpo = header("Fluxo e gargalos", "Tempo por etapa, onde as tarefas travam e quanto voltam",
                   "Fluxo e gargalos")
    corpo += kpis([("LEAD TIME MÉDIO", "20,6 d", "da criação à conclusão", "n"),
                   ("CICLO MÉDIO", "9,1 d", "do início à conclusão", "n"),
                   ("CICLO MEDIANO", "6,8 d", "metade termina em até 7 dias", "n"),
                   ("COM RETRABALHO", "18,0%", "▲ voltaram da revisão", "w"),
                   ("BLOQUEADAS", "7", "tarefas travadas agora", "c"),
                   ("PARADAS > 15 DIAS", "27", "sem mudar de etapa", "w")])
    ordem = ["Backlog", "A Fazer", "Em Andamento", "Em Revisão", "Bloqueada"]
    tempo = {"Backlog": 8.5, "A Fazer": 4.7, "Em Andamento": 4.7, "Em Revisão": 2.4, "Bloqueada": 6.8}
    par = dict(D["paradas"])
    cores = [T["crit"] if e == "Bloqueada" else T["blue"] for e in ordem]
    corpo += card(24, 204, 610, 244, "Backlog é a etapa mais lenta", "Dias médios em cada etapa, na ordem do fluxo",
                  hbars([(e, tempo[e]) for e in ordem], 578, 186, cores, fmt=lambda v: br(v, 1) + " d", lab=120))
    corpo += card(646, 204, 610, 244, "Onde as tarefas estão paradas agora", "Tarefas abertas por etapa atual",
                  hbars([(e, par[e]) for e in ordem], 578, 186,
                        [T["crit"] if e == "Bloqueada" else T["blue"] for e in ordem], lab=120))
    meses = [m for m, _ in D["mudancas"]]
    corpo += card(24, 460, 610, 244, "O ritmo de trabalho triplicou em um ano", "Mudanças de status por mês",
                  linhas([("Mudanças", [v for _, v in D["mudancas"]], T["blue"], True)], 578, 186,
                         [mes(m) for m in meses], legenda=False))
    bl = D["bloqueios"]
    corpo += card(646, 460, 610, 244, "Bloqueios dobraram desde junho", "Tarefas que entraram em bloqueio, por mês",
                  colunas([mes(m) for m, _ in bl], [v for _, v in bl], 578, 186, T["crit"], destaque=3))
    return corpo


def p4():
    corpo = header("Pessoas e esforço", "Carga de cada pessoa e horas apontadas contra o estimado", "Pessoas e esforço")
    corpo += kpis([("HORAS ORÇADAS", "22.750 h", "para os 45 projetos", "n"),
                   ("HORAS ESTIMADAS", "18.630 h", "soma das tarefas", "n"),
                   ("HORAS APONTADAS", "21.920 h", "▲ 18% acima do estimado", "w"),
                   ("ORÇAMENTO CONSUMIDO", "96,3%", "restam 830 h", "w"),
                   ("TAREFAS CONCLUÍDAS", "1.235", "86% de todas as tarefas", "g"),
                   ("IDADE DAS ABERTAS", "42 dias", "média desde a criação", "n")])
    corpo += card(24, 204, 460, 500, "Todas as equipes apontam mais do que estimam",
                  "Horas estimadas × apontadas por equipe",
                  hbars2([(e, a, b) for e, a, b in D["horas"]], 428, 440, T["base"], T["blue"], "Estimadas",
                         "Apontadas", lab=120))
    linhas_ = []
    for p in D["pessoas"]:
        d = p[7] * 100
        linhas_.append((p[0], p[1], str(p[3]), str(p[4]), br(p[6]), ((f"{'+' if d >= 0 else ''}{br(d, 1)}%"),
                                                                     T["warn"] if d > 15 else T["ink2"])))
    corpo += card(496, 204, 760, 500, "Carga por pessoa", "Ordenado por tarefas abertas · barras mostram vencidas",
                  tabela([("Pessoa", "l"), ("Equipe", "l"), ("Abertas", "r"), ("Vencidas", "r"), ("Horas", "r"),
                          ("Desvio", "l")], linhas_, [180, 140, 100, 110, 80, 100],
                         {2: (T["blue"] + "33", 11), 3: (T["crit"] + "33", 8)}))
    return corpo


def diagnostico():
    itens = [
        ("Sem hierarquia", "Título, filtros, cartões e gráficos têm o mesmo peso visual. Nada diz onde olhar primeiro.",
         "Faixa de cabeçalho escura com título, abas e filtros; cartões logo abaixo; gráficos depois."),
        ("Filtros desperdiçam espaço", "As duas segmentações ocupam uma linha inteira (9% da página) e deixam um vazio à direita.",
         "Filtros compactos dentro do cabeçalho, ao lado da data de referência."),
        ("KPIs sem contexto", "Número solto com rótulo cinza embaixo. ‘7 atrasados’ tem o mesmo tratamento que ‘140 abertas’.",
         "Rótulo em cima, número grande, linha de contexto e uma barra de cor que diz se é alerta."),
        ("Cor sem significado", "Azul padrão em tudo, roxo aleatório, e ‘Atrasado’ é vermelho num gráfico e roxo no outro.",
         "Azul = volume, cinza = referência, vermelho/âmbar/verde só para situação. Paleta validada para daltonismo."),
        ("Linha domina a página", "O gráfico de linha ocupa metade da tela, com 21 meses inclinados e sem rótulo final.",
         "Mais largo e mais baixo, entregues em destaque, criadas em cinza, valor do último mês direto na linha."),
        ("Colunas com nomes longos", "‘Concluído com atraso’ e ‘Pessoas & Cultura’ quebram em duas linhas embaixo das colunas.",
         "Barras horizontais: o rótulo cabe inteiro à esquerda e o valor fica na ponta da barra."),
        ("Dupla codificação", "Eixo Y com escala + rótulo em cada barra + grade forte: o mesmo número dito três vezes.",
         "Sem eixo nas barras (o rótulo basta); grade bem clara só nas linhas do tempo."),
        ("Tabelas cruas", "Dias de atraso e % de orçamento como texto puro; o olho não acha o pior caso.",
         "Barras de dados no atraso, selo colorido de situação, ordenação pelo que importa."),
        ("Sem chamada para ação", "A visão geral mostra totais, mas não diz quais projetos precisam de alguém agora.",
         "Bloco ‘Precisam de atenção’ com os projetos atrasados e o gestor responsável."),
        ("Títulos descritivos", "‘Projetos ativos e atrasados por equipe’ descreve o gráfico, não o que ele mostra.",
         "Título com a conclusão (‘Tecnologia concentra os atrasos’) e subtítulo com o que está sendo medido."),
    ]
    cards = "".join(f"""<div class="dg"><div class="dn">{i + 1:02d}</div><div class="dh">{t}</div>
<div class="dp"><b>Hoje</b>{p}</div><div class="ds"><b>Proposta</b>{s}</div></div>""" for i, (t, p, s) in enumerate(itens))
    return f"""<div class="dtt">Diagnóstico do relatório atual</div>
<div class="dst">10 problemas encontrados nas 4 páginas, e o que muda em cada um. Tudo aqui é reproduzível no Power BI (formato PBIR).</div>
<div class="dgrid">{cards}</div>"""


def guia():
    cores = [("Página", T["page"]), ("Cartão", T["surf"]), ("Borda", T["border"]), ("Cabeçalho", T["navy"]),
             ("Texto", T["ink"]), ("Texto 2", T["ink2"]), ("Volume", T["blue"]), ("Referência", T["base"]),
             ("Bom", T["good"]), ("Atenção", T["warn"]), ("Crítico", T["crit"])]
    sw = "".join(f'<div class="sw"><div style="background:{c};border:1px solid {T["border"]}"></div><b>{n}</b><span>{c}</span></div>'
                 for n, c in cores)
    tipo = [("Título da página", "20 / Semibold", 20, 600), ("Valor do KPI", "26 / Semibold", 26, 600),
            ("Título do visual", "13 / Semibold", 13, 600), ("Subtítulo do visual", "10.5 / Regular", 10.5, 400),
            ("Rótulo do KPI", "9.5 / Semibold · caixa alta", 9.5, 600), ("Eixos e rótulos", "9 / Regular", 9, 400)]
    tp = "".join(f'<div class="tp"><div style="font-size:{s}px;font-weight:{w}">{n}</div><span>{d}</span></div>'
                 for n, d, s, w in tipo)
    regras = ["Um assunto por cor: azul conta volume, cinza é referência, vermelho/âmbar/verde só situação.",
              "Barras horizontais para categorias com nome; colunas só para tempo.",
              "Barras sem eixo de valor: o rótulo na ponta já diz o número.",
              "Linhas de 2 px; a série principal em azul e um pouco mais grossa; valor final escrito na linha.",
              "Título do visual diz a conclusão; o subtítulo diz o que está sendo medido.",
              "Cartões brancos com raio 10, borda 1 px, sem sombra; 12 px entre cartões, 24 px de margem.",
              "Status nunca só pela cor: sempre com texto (selo, rótulo ou seta ▲▼)."]
    rg = "".join(f"<li>{r}</li>" for r in regras)
    return f"""<div class="dtt">Guia de estilo</div><div class="dst">Tokens usados nas 4 páginas, para replicar no tema e no gerador do relatório.
Fonte no Power BI: Segoe UI (aqui, Inter como equivalente).</div>
<div class="gwrap"><div class="gcol"><div class="gh">Cores</div><div class="sws">{sw}</div>
<div class="gh" style="margin-top:20px">Anatomia do KPI</div>
{kpis([("RÓTULO EM CAIXA ALTA", "26", "▲ linha de contexto colorida", "c")]).replace('class="kpis"', 'class="kpis one"')}
<div class="ann">barra de 4 px = situação · rótulo 9,5 · valor 26 · contexto 10,5</div></div>
<div class="gcol"><div class="gh">Tipografia</div>{tp}</div>
<div class="gcol" style="width:420px"><div class="gh">Regras</div><ol>{rg}</ol></div></div>"""


CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,'Segoe UI',sans-serif;background:#D9DEE5;padding:40px;display:flex;flex-direction:column;gap:60px}}
.frame{{position:relative;width:1280px;height:720px;background:{T['page']};overflow:hidden;color:{T['ink']}}}
.hdr{{position:absolute;left:0;top:0;width:1280px;height:76px;background:{T['navy']}}}
.ttl{{position:absolute;left:24px;top:12px;font-size:20px;font-weight:600;color:#fff}}
.sub{{position:absolute;left:24px;top:42px;font-size:11px;color:{T['navy2']}}}
.tabs{{position:absolute;left:400px;top:0;height:76px;display:flex;gap:4px;align-items:flex-end}}
.tab{{font-size:11.5px;color:{T['navy2']};padding:0 10px 14px;border-bottom:3px solid transparent}}
.tab.on{{color:#fff;font-weight:600;border-bottom-color:#6FA8E8}}
.flt{{position:absolute;right:24px;top:20px;display:flex;gap:8px;align-items:center}}
.sl{{width:120px;height:36px;border-radius:6px;background:#1C3A5A;padding:3px 10px;position:relative}}
.sl span{{display:block;font-size:9px;color:{T['navy2']}}}.sl b{{font-size:12px;font-weight:600;color:#fff}}
.sl i{{position:absolute;right:10px;top:10px;font-style:normal;color:{T['navy2']};font-size:11px}}
.ref{{font-size:10.5px;color:{T['navy2']};margin-left:6px;width:132px}}
.kpis{{position:absolute;left:24px;top:92px;display:flex;gap:12px}}
.kpis.one{{position:relative;left:0;top:0;margin-top:8px}}
.kpi{{position:relative;width:195px;height:96px;background:#fff;border:1px solid {T['border']};border-radius:10px;overflow:hidden;padding:12px 14px 0 18px}}
.acc{{position:absolute;left:0;top:0;width:4px;height:96px}}
.kl{{font-size:9.5px;font-weight:600;letter-spacing:.06em;color:{T['ink2']}}}
.kv{{font-size:26px;font-weight:600;margin-top:4px;letter-spacing:-.01em}}
.kc{{font-size:10.5px;margin-top:4px;white-space:nowrap}}
.card{{position:absolute;background:#fff;border:1px solid {T['border']};border-radius:10px;padding:14px 16px}}
.ct{{font-size:13px;font-weight:600}}.cs{{font-size:10.5px;color:{T['ink2']};margin:2px 0 10px}}
.ct2{{font-size:12px;font-weight:600;margin:18px 0 6px}}
.note{{font-size:10.5px;color:{T['ink2']};background:{T['page']};border-radius:6px;padding:8px 10px;margin-top:6px;line-height:1.45}}
svg text{{font-family:Inter,'Segoe UI',sans-serif}}
.al{{font-size:10.5px;fill:{T['ink']}}}.dl{{font-size:10.5px;font-weight:600;fill:{T['ink']}}}.dl.s{{font-size:9.5px}}
.ax{{font-size:9px;fill:{T['muted']}}}.lg{{font-size:10px;fill:{T['ink2']}}}
table{{border-collapse:collapse;font-size:10.5px;width:100%}}
th{{font-size:9.5px;font-weight:600;color:{T['ink2']};padding:6px 6px;border-bottom:1px solid {T['border']};letter-spacing:.02em}}
td{{padding:0 6px;height:31px;border-bottom:1px solid {T['grid']};white-space:nowrap}}
.db{{position:relative;height:20px;display:flex;align-items:center;justify-content:flex-end}}
.db div{{position:absolute;left:0;top:2px;height:16px;border-radius:3px}}.db span{{position:relative;font-weight:600}}
.pill{{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600}}
.pill i{{width:6px;height:6px;border-radius:3px;display:inline-block}}
.pad{{padding:32px 40px}}
.dtt{{font-size:24px;font-weight:700}}.dst{{font-size:12.5px;color:{T['ink2']};margin:6px 0 22px;max-width:900px}}
.dgrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}}
.dg{{background:#fff;border:1px solid {T['border']};border-radius:10px;padding:14px;height:236px}}
.dn{{font-size:11px;font-weight:700;color:{T['crit']}}}.dh{{font-size:13.5px;font-weight:600;margin:4px 0 10px}}
.dp,.ds{{font-size:10.5px;line-height:1.45;color:{T['ink2']};margin-bottom:10px}}
.dp b,.ds b{{display:block;font-size:9px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:2px}}
.dp b{{color:{T['crit']}}}.ds b{{color:{T['good']}}}
.gwrap{{display:flex;gap:28px}}.gcol{{width:380px;flex:none}}
.gh{{font-size:13px;font-weight:600;margin-bottom:10px}}
.sws{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
.sw div{{height:34px;border-radius:6px}}.sw b{{display:block;font-size:10px;margin-top:4px}}.sw span{{font-size:9px;color:{T['muted']}}}
.tp{{background:#fff;border:1px solid {T['border']};border-radius:8px;padding:10px 12px;margin-bottom:8px}}
.tp span{{font-size:9.5px;color:{T['muted']}}}
.ann{{font-size:10px;color:{T['muted']};margin-top:6px}}
ol{{padding-left:18px}}li{{font-size:11.5px;line-height:1.5;margin-bottom:10px;color:{T['ink']}}}
"""

quadros = [("00 · Diagnóstico", '<div class="pad">' + diagnostico() + "</div>"),
           ("01 · Visão geral", p1()), ("02 · Projetos", p2()), ("03 · Fluxo e gargalos", p3()),
           ("04 · Pessoas e esforço", p4()), ("05 · Guia de estilo", '<div class="pad">' + guia() + "</div>")]
html = (f'<!doctype html><html><head><meta charset="utf-8"><title>Painel de Projetos · Redesign</title>'
        f'<style>{CSS}</style></head><body>'
        + "".join(f'<div class="frame" data-name="{n}" id="q{i}">{c}</div>' for i, (n, c) in enumerate(quadros))
        + "</body></html>")
(S.parents[1] / "docs" / "design" / "redesign.html").write_text(html, encoding="utf-8")
print(len(html))
