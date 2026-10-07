"""Gera docs/design/redesign.html, o mockup das 3 páginas enviado ao Figma.

    python tools/design/mockup_redesign.py
"""
import json
from datetime import date
from pathlib import Path

S = Path(__file__).parent
D = json.loads((S / "dados_mockup.json").read_text())
G = json.loads((S / "dados_gantt.json").read_text())

T = dict(page="#F7F8FA", surf="#FFFFFF", line="#ECEEF2", ink="#1A202C", ink2="#5F6B7A", muted="#98A2B3",
         blue="#2F6DB5", blue_soft="#EAF1FA", light="#A9C1DF", gray="#D5DAE1", warn="#D29B00", crit="#C2362F",
         neutral="#C6CFDB")
MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def br(n, d=0):
    return f"{n:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def lateral(ativa):
    paginas = ["Portfólio", "Projetos e tarefas", "Cronograma"]
    botoes = "".join(f'<div class="nav{" on" if p == ativa else ""}">{p}</div>' for p in paginas)
    return f"""<div class="side">
  <div class="brand">Painel de Projetos</div>
  <div class="navs">{botoes}</div>
  <div class="flabel">Equipe</div><div class="sel">Todas<i>▾</i></div>
  <div class="flabel">Status do projeto</div><div class="sel">Todos<i>▾</i></div>
  <div class="ref">Dados até 30/09/2026</div>
</div>"""


def topo(titulo, sub):
    return f'<div class="ttl">{titulo}</div><div class="sub">{sub}</div>'


def kpis(itens):
    out = []
    for rot, val, ctx, alerta in itens:
        out.append(f'<div class="k"><div class="kl">{rot}</div>'
                   f'<div class="kv"{" style=color:" + T["crit"] if alerta else ""}>{val}</div>'
                   f'<div class="kc">{ctx}</div></div>')
    return f'<div class="kpis">{"".join(out)}</div>'


def card(x, y, w, h, titulo, sub, corpo):
    return (f'<div class="card" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<div class="ct">{titulo}</div><div class="cs">{sub}</div>{corpo}</div>')


def hbars(itens, w, h, cores, lab=140, fmt=lambda v: br(v)):
    n, mx = len(itens), max(v for _, v in itens)
    passo = h / n
    bh = min(16, passo * 0.6)
    g = []
    for i, (r, v) in enumerate(itens):
        y = i * passo + (passo - bh) / 2
        bw = max(2, (w - lab - 44) * v / mx)
        c = cores[i] if isinstance(cores, list) else cores
        g.append(f'<text x="{lab - 10}" y="{y + bh / 2 + 4}" text-anchor="end" class="al">{r}</text>'
                 f'<rect x="{lab}" y="{y}" width="{bw}" height="{bh}" rx="3" fill="{c}"/>'
                 f'<text x="{lab + bw + 6}" y="{y + bh / 2 + 4}" class="dl">{fmt(v)}</text>')
    return f'<svg width="{w}" height="{h}">{"".join(g)}</svg>'


def hbars2(itens, w, h, c1, c2, n1, n2, lab=130):
    n, mx = len(itens), max(max(a, b) for _, a, b in itens)
    top = 24
    passo = (h - top) / n
    bh = min(12, passo * 0.3)
    g = [f'<circle cx="{lab + 4}" cy="9" r="4" fill="{c1}"/><text x="{lab + 12}" y="13" class="lg">{n1}</text>'
         f'<circle cx="{lab + 84}" cy="9" r="4" fill="{c2}"/><text x="{lab + 92}" y="13" class="lg">{n2}</text>']
    for i, (r, a, b) in enumerate(itens):
        y = top + i * passo + (passo - 2 * bh - 3) / 2
        g.append(f'<text x="{lab - 10}" y="{y + bh + 4}" text-anchor="end" class="al">{r}</text>')
        for j, (v, c) in enumerate(((a, c1), (b, c2))):
            yy = y + j * (bh + 3)
            bw = max(2, (w - lab - 50) * v / mx)
            g.append(f'<rect x="{lab}" y="{yy}" width="{bw}" height="{bh}" rx="2" fill="{c}"/>'
                     f'<text x="{lab + bw + 5}" y="{yy + bh - 2}" class="dl s">{br(v)}</text>')
    return f'<svg width="{w}" height="{h}">{"".join(g)}</svg>'


def linhas(series, w, h, rotulos):
    L, R, top, bot = 34, 40, 26, 20
    mx = max(max(v) for _, v, _ in series)
    teto = 200
    pw, ph = w - L - R, h - top - bot
    n = len(rotulos)
    X = lambda i: L + pw * i / (n - 1)
    Y = lambda v: top + ph * (1 - v / teto)
    g = []
    for k in range(5):
        v = teto * k / 4
        g.append(f'<line x1="{L}" x2="{L + pw}" y1="{Y(v)}" y2="{Y(v)}" stroke="{T["line"]}"/>'
                 f'<text x="{L - 8}" y="{Y(v) + 4}" text-anchor="end" class="ax">{br(v)}</text>')
    for i, r in enumerate(rotulos):
        if i % 3 == 0 or i == n - 1:
            g.append(f'<text x="{X(i)}" y="{h - 4}" text-anchor="middle" class="ax">{r}</text>')
    x = L
    for nome, _, c in series:
        g.append(f'<circle cx="{x + 4}" cy="9" r="4" fill="{c}"/><text x="{x + 12}" y="13" class="lg">{nome}</text>')
        x += 24 + 7 * len(nome)
    for nome, v, c in series:
        pts = " ".join(f"{X(i):.1f},{Y(a):.1f}" for i, a in enumerate(v))
        g.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/>')
    return f'<svg width="{w}" height="{h}">{"".join(g)}</svg>'


def tabela(cab, linhas_, larg, barras=None):
    barras = barras or {}
    th = "".join(f'<th style="width:{l}px;text-align:{"right" if i in barras or a == "r" else "left"}">{c}</th>'
                 for i, ((c, a), l) in enumerate(zip(cab, larg)))
    trs = []
    for ln in linhas_:
        tds = []
        for i, (v, l) in enumerate(zip(ln, larg)):
            if i in barras:
                cor, mx, num = barras[i][0], barras[i][1], barras[i][2](v)
                bw = max(0, (l - 10) * num / mx)
                tds.append(f'<td style="text-align:right"><div class="db"><div style="width:{bw}px;background:{cor}">'
                           f'</div><span>{v}</span></div></td>')
            else:
                tds.append(f'<td style="text-align:{"right" if cab[i][1] == "r" else "left"}">{v}</td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


X0, W = 224, 1032
METADE = (W - 16) / 2


def portfolio():
    meses = [m for m, _ in D["criadas"]]
    ent = dict(D["entregues"])
    corpo = lateral("Portfólio") + topo("Portfólio", "Situação dos 45 projetos de 5 equipes")
    corpo += kpis([("Projetos ativos", "26", "de 45 no portfólio", False),
                   ("Projetos atrasados", "7", "27% dos ativos", True),
                   ("Entregues no prazo", "76,2%", "das tarefas concluídas", False),
                   ("Orçamento consumido", "96,3%", "restam 831 h", False),
                   ("Desvio de esforço", "+33,6%", "apontado vs. estimado", False)])
    sit = [("No prazo", 19), ("Concluído com atraso", 11), ("Atrasado", 7), ("Concluído no prazo", 3),
           ("Pausado", 3), ("Cancelado", 2)]
    cores = [T["crit"] if r == "Atrasado" else T["warn"] if r == "Concluído com atraso" else T["neutral"]
             for r, _ in sit]
    corpo += card(X0, 176, METADE, 260, "Situação de prazo", "Projetos por situação",
                  hbars(sit, METADE - 40, 196, cores, lab=150))
    eq = [("Tecnologia", 7, 3), ("Comercial", 6, 1), ("Dados & BI", 5, 1), ("Operações", 5, 1),
          ("Pessoas & Cultura", 3, 1)]
    corpo += card(X0 + METADE + 16, 176, METADE, 260, "Projetos por equipe", "Ativos e atrasados",
                  hbars2(eq, METADE - 40, 196, T["blue"], T["crit"], "Ativos", "Atrasados", lab=130))
    corpo += card(X0, 452, METADE, 252, "Tarefas criadas e entregues", "Por mês",
                  linhas([("Criadas", [v for _, v in D["criadas"]], T["neutral"]),
                          ("Entregues", [ent.get(m, 0) for m in meses], T["blue"])],
                         METADE - 40, 188, [f"{MES[int(m[5:]) - 1]}/{m[2:4]}" for m in meses]))
    corpo += card(X0 + METADE + 16, 452, METADE, 252, "Horas por equipe", "Estimadas e apontadas",
                  hbars2([(e, a, b) for e, a, b in D["horas"]], METADE - 40, 188, T["neutral"], T["blue"],
                         "Estimadas", "Apontadas", lab=130))
    return corpo


def projetos_tarefas():
    corpo = lateral("Projetos e tarefas") + topo("Projetos e tarefas", "Clique num projeto para ver as tarefas dele")
    corpo += kpis([("Tarefas abertas", "140", "de 1.435 tarefas", False),
                   ("Vencidas", "39", "31% das abertas", True),
                   ("Bloqueadas", "7", "travadas agora", False),
                   ("Lead time médio", "20,6 d", "da criação à conclusão", False),
                   ("Com retrabalho", "18,0%", "voltaram da revisão", False)])
    linhas_ = []
    for p in sorted(G["proj"], key=lambda r: -(int(r[7]) if r[7] else -1))[:13]:
        linhas_.append((p[0], p[1], p[3], f"{br(float(p[8]) * 100)}%", p[7] or ""))
    corpo += card(X0, 176, 620, 528, "Projetos", "Do maior atraso para o menor",
                  tabela([("Projeto", "l"), ("Equipe", "l"), ("Prazo", "l"), ("Concluído", "r"),
                          ("Dias de atraso", "r")], linhas_, [190, 110, 130, 80, 90],
                         {3: (T["blue_soft"], 100, lambda v: float(v[:-1].replace(",", "."))),
                          4: ("#F6D9D6", 407, lambda v: float(v or 0))}))
    ordem = ["Backlog", "A Fazer", "Em Andamento", "Em Revisão", "Bloqueada"]
    par = dict(D["paradas"])
    corpo += card(X0 + 636, 176, W - 636, 250, "Tarefas abertas por etapa", "Onde estão paradas agora",
                  hbars([(e, par[e]) for e in ordem], W - 636 - 40, 186,
                        [T["crit"] if e == "Bloqueada" else T["blue"] for e in ordem], lab=110))
    venc = [(v[0][:26], v[2], v[3]) for v in G["vencidas"][:6]]
    corpo += card(X0 + 636, 442, W - 636, 262, "Tarefas vencidas", "Mais atrasadas primeiro",
                  tabela([("Tarefa", "l"), ("Responsável", "l"), ("Dias", "r")], venc, [170, 120, 50]))
    return corpo


def cronograma():
    corpo = lateral("Cronograma") + topo("Cronograma", "Projetos e tarefas no tempo · clique no + para abrir as tarefas")
    legenda = [("Em andamento", T["blue"]), ("Atrasado / vencida", T["crit"]), ("Bloqueada", T["warn"]),
               ("Concluído", T["light"]), ("Cancelado", T["gray"])]
    corpo += '<div class="leg">' + "".join(f'<span><i style="background:{c}"></i>{n}</span>' for n, c in legenda) + "</div>"
    meses = [(a, m) for a in (2025, 2026) for m in range(1, 13)]
    ref = date(2026, 9, 30)
    cw = (W - 32 - 250) / len(meses)

    def faixa(ini, fim, cor):
        cel = []
        for a, m in meses:
            c0 = date(a, m, 1)
            c1 = date(a + (m == 12), m % 12 + 1, 1)
            dentro = ini < c1 and fim >= c0
            cel.append(f'<td style="width:{cw}px"><div class="gb" style="background:{cor if dentro else "transparent"}">'
                       f'</div></td>')
        return "".join(cel)

    def cor_proj(p):
        return {"Atrasado": T["crit"], "Cancelado": T["gray"]}.get(p[3], T["light"] if p[2] == "Concluído" else T["blue"])

    cab = "".join(f'<th style="width:{cw}px">{MES[m - 1]}{"<br>" + str(a)[2:] if m == 1 else ""}</th>' for a, m in meses)
    trs = []
    for p in G["proj"][:15]:
        ini = date.fromisoformat(p[4])
        fim = (date.fromisoformat(p[6]) if p[6] else date.fromisoformat(p[5]) if p[2] == "Cancelado"
               else max(ref, date.fromisoformat(p[5])))
        aberto = p[0] == "Gestão de pátio"
        trs.append(f'<tr class="pr"><td class="rh"><b>{"−" if aberto else "+"}</b> {p[0]}</td>{faixa(ini, fim, cor_proj(p))}</tr>')
        if aberto:
            for t in G["tarefas_gestao"][-7:]:
                ti = date.fromisoformat(t[3])
                tf = date.fromisoformat(t[4]) if t[4] else ref
                c = (T["light"] if t[1] == "Concluída" else T["warn"] if t[1] == "Bloqueada"
                     else T["crit"] if t[2] == "Vencida" else T["blue"])
                trs.append(f'<tr class="tr"><td class="rh sub2">{t[0][:30]}</td>{faixa(ti, tf, c)}</tr>')
    corpo += (f'<div class="card" style="left:{X0}px;top:112px;width:{W}px;height:592px">'
              f'<table class="gantt"><thead><tr><th class="rh">Projeto / tarefa</th>{cab}</tr></thead>'
              f'<tbody>{"".join(trs)}</tbody></table></div>')
    return corpo


CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,'Segoe UI',sans-serif;background:#DADFE6;padding:40px;display:flex;flex-direction:column;gap:60px}}
.frame{{position:relative;width:1280px;height:720px;background:{T['page']};overflow:hidden;color:{T['ink']}}}
.side{{position:absolute;left:0;top:0;width:200px;height:720px;background:#fff;border-right:1px solid {T['line']};padding:22px 16px}}
.brand{{font-size:15px;font-weight:700;letter-spacing:-.01em;margin:0 0 26px 6px}}
.navs{{display:flex;flex-direction:column;gap:4px;margin-bottom:30px}}
.nav{{font-size:12.5px;color:{T['ink2']};padding:9px 10px;border-radius:8px}}
.nav.on{{background:{T['blue_soft']};color:{T['blue']};font-weight:600}}
.flabel{{font-size:10.5px;color:{T['muted']};margin:12px 0 5px 4px}}
.sel{{font-size:12px;border:1px solid {T['line']};border-radius:8px;padding:8px 10px;position:relative}}
.sel i{{position:absolute;right:10px;font-style:normal;color:{T['muted']}}}
.ref{{position:absolute;left:20px;bottom:22px;font-size:10.5px;color:{T['muted']}}}
.ttl{{position:absolute;left:224px;top:22px;font-size:20px;font-weight:700;letter-spacing:-.01em}}
.sub{{position:absolute;left:224px;top:52px;font-size:11.5px;color:{T['ink2']}}}
.kpis{{position:absolute;left:224px;top:80px;width:1032px;height:80px;background:#fff;border-radius:12px;
  border:1px solid {T['line']};display:flex}}
.k{{flex:1;padding:12px 18px;border-left:1px solid {T['line']}}}.k:first-child{{border-left:none}}
.kl{{font-size:10.5px;color:{T['ink2']}}}.kv{{font-size:22px;font-weight:700;margin:2px 0 1px;letter-spacing:-.01em}}
.kc{{font-size:10px;color:{T['muted']}}}
.card{{position:absolute;background:#fff;border:1px solid {T['line']};border-radius:12px;padding:14px 18px}}
.ct{{font-size:13px;font-weight:600}}.cs{{font-size:10.5px;color:{T['muted']};margin:2px 0 12px}}
svg text{{font-family:Inter,'Segoe UI',sans-serif}}
.al{{font-size:10.5px;fill:{T['ink']}}}.dl{{font-size:10px;font-weight:600;fill:{T['ink']}}}.dl.s{{font-size:9.5px}}
.ax{{font-size:9px;fill:{T['muted']}}}.lg{{font-size:10px;fill:{T['ink2']}}}
table{{border-collapse:collapse;font-size:10.5px;width:100%}}
th{{font-size:9.5px;font-weight:600;color:{T['muted']};padding:6px 5px;border-bottom:1px solid {T['line']}}}
td{{padding:0 5px;height:30px;border-bottom:1px solid #F3F4F6;white-space:nowrap}}
.db{{position:relative;height:18px;display:flex;align-items:center;justify-content:flex-end}}
.db div{{position:absolute;left:0;top:2px;height:14px;border-radius:3px}}.db span{{position:relative;font-weight:600}}
.leg{{position:absolute;right:24px;top:30px;display:flex;gap:14px;font-size:10.5px;color:{T['ink2']}}}
.leg i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}}
.gantt th{{font-size:9px;text-align:center;padding:4px 0;line-height:1.2}}
.gantt td{{height:28px;padding:0;border-bottom:1px solid #F3F4F6}}
.gantt .rh{{width:250px;text-align:left;padding-left:4px;font-size:10.5px}}
.gantt .rh b{{display:inline-block;width:14px;color:{T['muted']};font-weight:600}}
.gantt .sub2{{padding-left:22px;color:{T['ink2']};font-size:10px}}
.gb{{height:14px}}
.pad{{padding:32px 40px}}
"""

quadros = [("01 · Portfólio", portfolio()), ("02 · Projetos e tarefas", projetos_tarefas()),
           ("03 · Cronograma", cronograma())]
html = (f'<!doctype html><html><head><meta charset="utf-8"><title>Painel de Projetos</title>'
        f'<style>{CSS}</style></head><body>'
        + "".join(f'<div class="frame" data-name="{n}">{c}</div>' for n, c in quadros) + "</body></html>")
(S.parents[1] / "docs" / "design" / "redesign.html").write_text(html, encoding="utf-8")
