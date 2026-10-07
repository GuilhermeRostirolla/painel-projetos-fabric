"""Mockup das 3 páginas (docs/design/redesign.html) e fundos do relatório (fabric/.../fundo_*.png).

    python tools/design/mockup_redesign.py            # mockup com dados de exemplo
    python tools/design/mockup_redesign.py --fundos   # só a camada de fundo, para o Power BI

A camada de fundo (cartões, títulos, ícones, menu) vira a imagem de fundo de cada página no Power BI;
os visuais ficam por cima, com fundo transparente, nas mesmas coordenadas de layout.py.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from layout import (ALTURA, CARTOES, COR, DATA_REF, KPIS, LARGURA, LEGENDA_GANTT, NAV, PAGINAS, SLICERS, X0,  # noqa: E402
                    area, kpis)

S = Path(__file__).parent
D = json.loads((S / "dados_mockup.json").read_text())
G = json.loads((S / "dados_gantt.json").read_text())
MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

ICONE = {
    "pasta": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "alerta": '<path d="M12 4 2.5 20h19z"/><path d="M12 10v4"/><circle cx="12" cy="17" r=".6"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    "relogio": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "lista": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="m3.5 6 1 1 2-2M3.5 12l1 1 2-2M3.5 18l1 1 2-2"/>',
    "grade": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>'
             '<rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "gantt": '<path d="M4 6h9M8 12h10M6 18h7"/>',
}


def icone(nome, cor, tam=20, traco=1.8):
    return (f'<svg width="{tam}" height="{tam}" viewBox="0 0 24 24" fill="none" stroke="{cor}" '
            f'stroke-width="{traco}" stroke-linecap="round" stroke-linejoin="round">{ICONE[nome]}</svg>')


def br(n, d=0):
    return f"{n:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def caixa(x, y, w, h, extra=""):
    return f'style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;{extra}"'


# --- camada de fundo -----------------------------------------------------------------------

def fundo(pagina):
    nome, titulo, sub = next(p for p in PAGINAS if p[0] == pagina)
    h = [f'<div class="nav"><div class="logo">PP</div>']
    for i, (destino, rotulo, _) in enumerate(PAGINAS):
        ativo = destino == pagina
        ic = ["grade", "lista", "gantt"][i]
        h.append(f'<div class="navb{" on" if ativo else ""}" style="top:{96 + i * 60}px">'
                 f'{icone(ic, COR["texto"] if ativo else COR["apagado"], 22)}</div>')
    h.append("</div>")
    h.append(f'<div class="t1" {caixa(X0, 18, 560, 30)}>{titulo}</div>')
    h.append(f'<div class="t2" {caixa(X0, 50, 560, 20)}>{sub}</div>')
    for _, rotulo, x, y, w, hh in SLICERS:
        h.append(f'<div class="slot" {caixa(x, y, w, hh)}></div>')
    for (rot, _, _, cor, ic), (x, y, w, hh) in zip(KPIS.get(pagina, []), kpis(len(KPIS.get(pagina, [])) or 1)):
        h.append(f'<div class="card" {caixa(x, y, w, hh)}>'
                 f'<div class="ico" style="background:{COR[cor]}22">{icone(ic, COR[cor], 20)}</div>'
                 f'<div class="kl">{rot}</div></div>')
    for chave, (x, y, w, hh, t, s) in CARTOES[pagina].items():
        extra = ""
        if chave == "gantt":
            extra = '<div class="leg">' + "".join(
                f'<span><i style="background:{COR[c]}"></i>{n}</span>' for n, c in LEGENDA_GANTT) + "</div>"
        h.append(f'<div class="card" {caixa(x, y, w, hh)}><div class="ct">{t}</div><div class="cs">{s}</div>{extra}</div>')
    return "".join(h)


# --- camada de dados (só no mockup) ----------------------------------------------------------

def hbars(itens, w, h, cores, lab=130, fmt=lambda v: br(v)):
    n, mx = len(itens), max(v for _, v in itens)
    passo = h / n
    bh = min(14, passo * 0.55)
    g = []
    for i, (r, v) in enumerate(itens):
        y = i * passo + (passo - bh) / 2
        bw = max(2, (w - lab - 44) * v / mx)
        c = cores[i] if isinstance(cores, list) else cores
        g.append(f'<text x="{lab - 10}" y="{y + bh / 2 + 4}" text-anchor="end" class="al">{r}</text>'
                 f'<rect x="{lab}" y="{y}" width="{bw}" height="{bh}" rx="3" fill="{c}"/>'
                 f'<text x="{lab + bw + 6}" y="{y + bh / 2 + 4}" class="dl">{fmt(v)}</text>')
    return f'<svg width="{w}" height="{h}">{"".join(g)}</svg>'


def colunas2(itens, w, h, c1, c2, n1, n2):
    n, mx = len(itens), max(max(a, b) for _, a, b in itens)
    top, bot = 24, 22
    passo = (w - 20) / n
    bw = min(22, passo * 0.28)
    g = [f'<circle cx="8" cy="8" r="4" fill="{c1}"/><text x="16" y="12" class="lg">{n1}</text>'
         f'<circle cx="90" cy="8" r="4" fill="{c2}"/><text x="98" y="12" class="lg">{n2}</text>']
    for i, (r, a, b) in enumerate(itens):
        x = 10 + i * passo + (passo - 2 * bw - 4) / 2
        for j, (v, c) in enumerate(((a, c1), (b, c2))):
            bh = (h - top - bot - 14) * v / mx
            xx = x + j * (bw + 4)
            g.append(f'<rect x="{xx}" y="{h - bot - bh}" width="{bw}" height="{bh}" rx="3" fill="{c}"/>'
                     f'<text x="{xx + bw / 2}" y="{h - bot - bh - 4}" text-anchor="middle" class="dl s">{br(v)}</text>')
        g.append(f'<text x="{x + bw + 2}" y="{h - 6}" text-anchor="middle" class="ax">{r}</text>')
    return f'<svg width="{w}" height="{h}">{"".join(g)}</svg>'


def area_chart(series, w, h, rotulos):
    L, R, top, bot = 30, 12, 22, 18
    teto = 350
    pw, ph = w - L - R, h - top - bot
    n = len(rotulos)
    X = lambda i: L + pw * i / (n - 1)
    Y = lambda v: top + ph * (1 - v / teto)
    g = ['<defs><linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{COR["azul"]}" stop-opacity=".35"/>'
         f'<stop offset="1" stop-color="{COR["azul"]}" stop-opacity="0"/></linearGradient></defs>']
    for k in range(5):
        v = teto * k / 4
        g.append(f'<line x1="{L}" x2="{L + pw}" y1="{Y(v)}" y2="{Y(v)}" stroke="{COR["grade"]}"/>'
                 f'<text x="{L - 6}" y="{Y(v) + 3}" text-anchor="end" class="ax">{br(v)}</text>')
    for i, r in enumerate(rotulos):
        if i % 3 == 0 or i == n - 1:
            g.append(f'<text x="{X(i)}" y="{h - 3}" text-anchor="middle" class="ax">{r}</text>')
    x = L
    for nome, _, c, _ in series:
        g.append(f'<circle cx="{x + 4}" cy="7" r="4" fill="{c}"/><text x="{x + 12}" y="11" class="lg">{nome}</text>')
        x += 26 + 7 * len(nome)
    for nome, v, c, preenche in series:
        pts = [f"{X(i):.1f},{Y(a):.1f}" for i, a in enumerate(v)]
        if preenche:
            g.append(f'<polygon points="{X(0)},{Y(0)} {" ".join(pts)} {X(n - 1)},{Y(0)}" fill="url(#ga)"/>')
        g.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{c}" stroke-width="2"/>')
    return f'<svg width="{w}" height="{h}">{"".join(g)}</svg>'


def donut(itens, cores, w, h, total):
    import math
    cx, cy, r, esp = h / 2, h / 2, h / 2 - 6, 18
    soma = sum(v for _, v in itens)
    a0 = -math.pi / 2
    g = []
    for (rot, v), c in zip(itens, cores):
        a1 = a0 + 2 * math.pi * v / soma
        grande = 1 if a1 - a0 > math.pi else 0
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1 - .02), cy + r * math.sin(a1 - .02)
        g.append(f'<path d="M{x0},{y0} A{r},{r} 0 {grande} 1 {x1},{y1}" fill="none" stroke="{c}" stroke-width="{esp}"/>')
        a0 = a1
    g.append(f'<text x="{cx}" y="{cy + 2}" text-anchor="middle" class="big">{total}</text>'
             f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" class="ax">projetos</text>')
    ly = 14
    for (rot, v), c in zip(itens, cores):
        g.append(f'<circle cx="{h + 22}" cy="{ly}" r="4.5" fill="{c}"/>'
                 f'<text x="{h + 32}" y="{ly + 4}" class="al">{rot}</text>'
                 f'<text x="{w - 4}" y="{ly + 4}" text-anchor="end" class="dl">{v}</text>')
        ly += 30
    return f'<svg width="{w}" height="{h}">{"".join(g)}</svg>'


def tabela(cab, linhas_, larg, barras=None):
    barras = barras or {}
    th = "".join(f'<th style="width:{l}px;text-align:{"right" if a == "r" else "left"}">{c}</th>'
                 for (c, a), l in zip(cab, larg))
    trs = []
    for ln in linhas_:
        tds = []
        for i, (v, l) in enumerate(zip(ln, larg)):
            if i in barras:
                cor, mx, num = barras[i]
                bw = max(0, (l - 10) * num(v) / mx)
                tds.append(f'<td style="text-align:right"><div class="db"><div style="width:{bw}px;background:{cor}">'
                           f'</div><span>{v}</span></div></td>')
            else:
                tds.append(f'<td style="text-align:{"right" if cab[i][1] == "r" else "left"}">{v}</td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


def no_cartao(pagina, chave, conteudo):
    x, y, w, h = area(CARTOES[pagina][chave])
    return f'<div class="vis" {caixa(x, y, w, h)}>{conteudo}</div>'


def kpis_dados(pagina, valores):
    out = []
    for (x, y, w, h), (valor, ctx, alerta) in zip(kpis(len(valores)), valores):
        out.append(f'<div class="vis" {caixa(x + 72, y + 40, w - 90, 34)}><div class="kv"'
                   f'{" style=color:" + COR["vermelho"] if alerta else ""}>{valor}</div></div>'
                   f'<div class="vis" {caixa(x + 72, y + 74, w - 90, 20)}><div class="kc">{ctx}</div></div>')
    return "".join(out)


def comuns():
    out = []
    for _, rotulo, x, y, w, h in SLICERS:
        out.append(f'<div class="vis sl" {caixa(x, y, w, h)}><span>{rotulo}</span><b>Todos</b><i>▾</i></div>')
    x, y, w, h = DATA_REF
    out.append(f'<div class="vis ref" {caixa(x, y, w, h)}>Dados até 30/09/2026</div>')
    return "".join(out)


CURTO = {"Transformação Digital": "Transf. Digital", "Crescimento Comercial": "Cresc. Comercial",
         "Excelência Operacional": "Excel. Operacional", "Dados & Analytics": "Dados & Analytics",
         "Pessoas & Cultura": "Pessoas & Cultura", "Experiência do Cliente": "Exp. Cliente",
         "Sustentabilidade & ESG": "ESG", "Inovação Aberta": "Inov. Aberta"}
COR_FAROL = {"Verde": COR["verde"], "Amarelo": COR["ambar"], "Vermelho": COR["vermelho"], "Encerrado": COR["cancelado"]}


def dados_portfolio():
    p = "P1Portfolio"
    out = comuns() + kpis_dados(p, [("42", "48 vieram de ideias", False), ("12", "29% dos ativos", True),
                                    ("78,9%", "das tarefas concluídas", False),
                                    ("R$ 10,3 mi", "103% das horas orçadas já usadas", False)])
    farol = sorted(((f, int(n)) for f, n in G["farol"]), key=lambda x: -x[1])
    x, y, w, h = area(CARTOES[p]["saude"])
    out += no_cartao(p, "saude", donut(farol, [COR_FAROL[f] for f, _ in farol], w, h, 122))
    meses = [m for m, _ in D["criadas"]]
    ent = dict(D["entregues"])
    x, y, w, h = area(CARTOES[p]["entregas"])
    out += no_cartao(p, "entregas", area_chart(
        [("Criadas", [v for _, v in D["criadas"]], COR["concluido"], False),
         ("Entregues", [ent.get(m, 0) for m in meses], COR["azul"], True)],
        w, h, [f"{MES[int(m[5:]) - 1]}/{m[2:4]}" for m in meses]))
    risco = [(r[0][:24], r[7]) for r in sorted(G["proj"], key=lambda r: -int(r[7] or 0)) if r[3] == "Atrasado"][:5]
    x, y, w, h = area(CARTOES[p]["risco"])
    out += no_cartao(p, "risco", tabela([("Projeto", "l"), ("Dias", "r")], risco, [w - 90, 90],
                                        {1: ("#E44A5D55", 407, float)}))
    eq = [(CURTO[n], int(a), int(b)) for n, a, b in G["portfolio"]]
    x, y, w, h = area(CARTOES[p]["equipes"])
    out += no_cartao(p, "equipes", colunas2(eq, w, h, COR["azul"], COR["vermelho"], "Ativos", "Atrasados"))
    x, y, w, h = area(CARTOES[p]["esforco"])
    etapas = [(e, int(n)) for e, n in G["etapa"]]
    out += no_cartao(p, "esforco", hbars(etapas, w, h, [COR["concluido"] if e == "Concluído" else COR["azul"]
                                                        for e, _ in etapas], lab=110))
    return out


def dados_tarefas():
    p = "P2ProjetosTarefas"
    out = comuns() + kpis_dados(p, [("176", "6 impedidas agora", False), ("50", "31% das abertas", True),
                                    ("91,0%", "91% de todas as tarefas", False), ("19,9", "da criação à conclusão", False)])
    linhas_ = []
    for r in sorted(G["proj"], key=lambda r: -(int(r[7]) if r[7] else -1))[:14]:
        linhas_.append((r[0][:30], CURTO[r[1]], r[9], r[10], f"{br(float(r[8]) * 100)}%", r[7] or ""))
    x, y, w, h = area(CARTOES[p]["projetos"])
    out += no_cartao(p, "projetos", tabela(
        [("Projeto", "l"), ("Portfólio", "l"), ("Etapa", "l"), ("Farol", "l"), ("Concluído", "r"), ("Dias de atraso", "r")],
        linhas_, [200, 110, 80, 60, 90, 96],
        {4: ("#4682F555", 100, lambda v: float(v[:-1].replace(",", "."))),
         5: ("#E44A5D55", 407, lambda v: float(v or 0))}))
    ordem = ["Backlog", "A fazer", "Fazendo", "Impedido", "Em revisão"]
    par = {e: int(n) for e, n in G["paradas"]}
    x, y, w, h = area(CARTOES[p]["etapas"])
    out += no_cartao(p, "etapas", hbars([(e, par[e]) for e in ordem], w, h,
                                        [COR["vermelho"] if e == "Impedido" else COR["azul"] for e in ordem], lab=110))
    x, y, w, h = area(CARTOES[p]["vencidas"])
    out += no_cartao(p, "vencidas", tabela([("Tarefa", "l"), ("Responsável", "l"), ("Dias", "r")],
                                           [(v[0][:28], v[2], v[3]) for v in G["vencidas"][:6]], [200, 150, 80]))
    return out


def dados_cronograma():
    p = "P3Cronograma"
    out = comuns()
    x, y, w, h = area(CARTOES[p]["gantt"])
    meses = [(a, m) for a in (2025, 2026) for m in range(1, 13)]
    ref = date(2026, 9, 30)
    cw = (w - 250) / len(meses)

    def faixa(ini, fim, cor):
        cel = []
        for a, m in meses:
            c0 = date(a, m, 1)
            c1 = date(a + (m == 12), m % 12 + 1, 1)
            dentro = ini < c1 and fim >= c0
            cel.append(f'<td><div class="gb" style="background:{cor if dentro else "transparent"}"></div></td>')
        return "".join(cel)

    def cor_proj(r):
        if r[3] == "Atrasado":
            return COR["vermelho"]
        return {"Arquivado": COR["cancelado"], "Concluído": COR["concluido"]}.get(r[2], COR["azul"])

    cab = "".join(f'<th style="width:{cw}px">{MES[m - 1]}{"<br>" + str(a)[2:] if m == 1 else ""}</th>' for a, m in meses)
    trs = []
    for r in G["proj"][:13]:
        ini = date.fromisoformat(r[4])
        fim = (date.fromisoformat(r[6]) if r[6] else date.fromisoformat(r[5]) if r[2] == "Arquivado"
               else max(ref, date.fromisoformat(r[5])))
        aberto = r[0] == "Gestão de pátio"
        trs.append(f'<tr><td class="rh"><b>{"−" if aberto else "+"}</b> {r[0]}</td>{faixa(ini, fim, cor_proj(r))}</tr>')
        if aberto:
            for t in G["tarefas_gestao"][-6:]:
                ti = date.fromisoformat(t[3])
                tf = date.fromisoformat(t[4]) if t[4] else ref
                c = (COR["concluido"] if t[1] == "Concluído" else COR["ambar"] if t[1] == "Impedido"
                     else COR["vermelho"] if t[2] == "Vencida" else COR["azul"])
                trs.append(f'<tr><td class="rh sub2">{t[0][:30]}</td>{faixa(ti, tf, c)}</tr>')
    out += (f'<div class="vis" {caixa(x, y, w, h)}><table class="gantt"><thead><tr><th class="rh">Projeto / tarefa</th>'
            f'{cab}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
    return out


CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,'Segoe UI',sans-serif;background:#05080F;padding:40px;display:flex;flex-direction:column;gap:60px}}
body.fundos{{padding:0;gap:0;background:none}}
.frame{{position:relative;width:{LARGURA}px;height:{ALTURA}px;overflow:hidden;color:{COR['texto']};
  background:radial-gradient(900px 420px at 92% -8%,#1B3566 0%,rgba(10,16,32,0) 60%),
             radial-gradient(700px 380px at 10% 110%,#16244A 0%,rgba(10,16,32,0) 60%),{COR['pagina']}}}
.frame>div{{position:absolute}}
.nav{{left:0;top:0;width:{NAV}px;height:{ALTURA}px;background:#0D1526;border-right:1px solid {COR['borda']}}}
.logo{{position:absolute;left:16px;top:20px;width:40px;height:40px;border-radius:12px;
  background:linear-gradient(135deg,#4682F5,#7B5CF5);font-weight:800;font-size:14px;color:#fff;
  display:flex;align-items:center;justify-content:center;letter-spacing:.02em}}
.navb{{position:absolute;left:12px;width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center}}
.navb.on{{background:{COR['azul_suave']};box-shadow:inset 3px 0 0 {COR['azul']}}}
.t1{{font-size:21px;font-weight:700;letter-spacing:-.01em}}
.t2{{font-size:11.5px;color:{COR['suave']}}}
.slot{{border:1px solid {COR['borda']};border-radius:10px;background:#0F1729}}
.card{{background:linear-gradient(180deg,#131D31 0%,{COR['cartao']} 100%);border:1px solid {COR['borda']};
  border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,.25)}}
.ico{{position:absolute;left:20px;top:30px;width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center}}
.kl{{position:absolute;left:72px;top:20px;font-size:11px;color:{COR['suave']};letter-spacing:.02em}}
.ct{{position:absolute;left:20px;top:16px;font-size:13.5px;font-weight:600}}
.cs{{position:absolute;left:20px;top:36px;font-size:10.5px;color:{COR['apagado']}}}
.leg{{position:absolute;right:20px;top:20px;display:flex;gap:16px;font-size:10.5px;color:{COR['suave']}}}
.leg i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.kv{{font-size:26px;font-weight:700;letter-spacing:-.02em;line-height:34px}}
.kc{{font-size:10.5px;color:{COR['suave']}}}
.sl{{padding:5px 12px}}.sl span{{display:block;font-size:9px;color:{COR['apagado']}}}.sl b{{font-size:12px;font-weight:600}}
.sl i{{position:absolute;right:12px;top:15px;font-style:normal;color:{COR['apagado']}}}
.ref{{font-size:10.5px;color:{COR['suave']};text-align:right;line-height:26px}}
svg text{{font-family:Inter,'Segoe UI',sans-serif}}
.al{{font-size:10.5px;fill:{COR['texto']}}}.dl{{font-size:10px;font-weight:600;fill:{COR['texto']}}}.dl.s{{font-size:9px}}
.ax{{font-size:9px;fill:{COR['apagado']}}}.lg{{font-size:10px;fill:{COR['suave']}}}
.big{{font-size:28px;font-weight:700;fill:{COR['texto']}}}
table{{border-collapse:collapse;font-size:10.5px;width:100%;color:{COR['texto']}}}
th{{font-size:9.5px;font-weight:600;color:{COR['apagado']};padding:6px 5px;border-bottom:1px solid {COR['borda']}}}
td{{padding:0 5px;height:29px;border-bottom:1px solid {COR['grade']};white-space:nowrap}}
.db{{position:relative;height:18px;display:flex;align-items:center;justify-content:flex-end}}
.db div{{position:absolute;left:0;top:2px;height:14px;border-radius:3px}}.db span{{position:relative;font-weight:600}}
.gantt th{{font-size:9px;text-align:center;padding:4px 0;line-height:1.2}}
.gantt td{{height:28px;padding:0}}
.gantt .rh{{width:250px;text-align:left;padding-left:4px;font-size:10.5px}}
.gantt .rh b{{display:inline-block;width:14px;color:{COR['apagado']};font-weight:600}}
.gantt .sub2{{padding-left:22px;color:{COR['suave']};font-size:10px}}
.gb{{height:14px}}
body.fundos .vis{{display:none}}
"""


def html(com_dados=True):
    dados = {"P1Portfolio": dados_portfolio, "P2ProjetosTarefas": dados_tarefas, "P3Cronograma": dados_cronograma}
    quadros = "".join(f'<div class="frame" data-name="{p[1]}" id="{p[0]}">{fundo(p[0])}{dados[p[0]]()}</div>'
                      for p in PAGINAS)
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>Painel de Projetos</title>'
            f'<style>{CSS}</style></head><body class="{"" if com_dados else "fundos"}">{quadros}</body></html>')


if __name__ == "__main__":
    raiz = S.parents[1]
    if "--fundos" in sys.argv:
        (raiz / "docs" / "design" / "fundos.html").write_text(html(False), encoding="utf-8")
    else:
        (raiz / "docs" / "design" / "redesign.html").write_text(html(True), encoding="utf-8")
