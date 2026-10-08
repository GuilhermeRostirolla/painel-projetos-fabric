"""Grade das 3 páginas (1280 x 720). Usada pelo mockup, pelos fundos e pelo gerador do relatório."""

LARGURA, ALTURA = 1280, 720
NAV = 72
X0, W = 88, 1176
KPI_Y, KPI_H = 84, 100

COR = {
    "pagina": "#0A1020", "cartao": "#111A2C", "borda": "#1E2940", "texto": "#E8EDF5", "suave": "#9AA7BD",
    "apagado": "#62718B", "grade": "#1A2438", "azul": "#4682F5", "azul_suave": "#1B2B4D", "vermelho": "#E44A5D",
    "ambar": "#C4851A", "verde": "#1D9A74", "concluido": "#5D7398", "cancelado": "#364259", "neutro": "#33415E",
}

PAGINAS = [("P1Portfolio", "Portfólio", "Visão executiva da Central de Iniciativas da AEVO"),
           ("P2ProjetosTarefas", "Projetos e tarefas", "Andamento de cada projeto e o que está travando as entregas"),
           ("P3Cronograma", "Cronograma", "Projetos e tarefas no tempo")]

SLICERS = [("dim_projeto.portfolio", "Portfólio", 888, 14, 180, 54),
           ("dim_projeto.status", "Status do projeto", 1084, 14, 180, 54)]
DATA_REF = (660, 30, 210, 26)


def kpis(n):
    w = (W - 16 * (n - 1)) / n
    return [(X0 + i * (w + 16), KPI_Y, w, KPI_H) for i in range(n)]


CARTOES = {
    "P1Portfolio": {
        "saude": (88, 200, 360, 252, "Saúde do portfólio", "Farol dos projetos"),
        "entregas": (464, 200, 500, 252, "Entregas x demanda", "Tarefas criadas e entregues por mês, desde jan/2025"),
        "risco": (980, 200, 284, 252, "Projetos em risco", "Atrasados, por dias de atraso"),
        "equipes": (88, 468, 580, 236, "Desempenho por portfólio", "Projetos ativos e atrasados"),
        "esforco": (684, 468, 580, 236, "Projetos por etapa", "Kanban do portfólio"),
    },
    "P2ProjetosTarefas": {
        "projetos": (88, 200, 700, 504, "Projetos", "Do maior atraso para o menor; clique para filtrar"),
        "etapas": (804, 200, 460, 236, "Tarefas abertas por etapa", "Onde o trabalho está parado"),
        "vencidas": (804, 452, 460, 252, "Tarefas vencidas", "Mais atrasadas primeiro"),
    },
    "P3Cronograma": {
        "gantt": (88, 84, 1176, 620, "Cronograma de projetos", "Clique no + para abrir as tarefas de um projeto"),
    },
}

KPIS = {
    "P1Portfolio": [
        ("Projetos ativos", "Projetos Ativos", "Contexto Projetos de Ideias", "azul", "pasta"),
        ("Projetos atrasados", "Projetos Atrasados", "Contexto Projetos Atrasados", "vermelho", "alerta"),
        ("Entregues no prazo", "% Entregues no Prazo", "das tarefas concluídas", "verde", "check"),
        ("Orçamento do portfólio", "Texto Orçamento", "Contexto Orçamento Consumido", "ambar", "relogio"),
    ],
    "P2ProjetosTarefas": [
        ("Tarefas abertas", "Tarefas Abertas", "Contexto Tarefas Abertas", "azul", "lista"),
        ("Tarefas vencidas", "Tarefas Vencidas", "Contexto Tarefas Vencidas", "vermelho", "alerta"),
        ("Tarefas concluídas", "% Tarefas Concluídas", "Contexto Tarefas Concluídas", "verde", "check"),
        ("Lead time médio (dias)", "Lead Time Médio (dias)", "da criação à conclusão", "ambar", "relogio"),
    ],
}

LEGENDA_GANTT = [("Em andamento", "azul"), ("Atrasado ou vencida", "vermelho"), ("Impedido", "ambar"),
                 ("Concluído", "concluido"), ("Arquivado", "cancelado")]


def area(caixa):
    x, y, w, h = caixa[:4]
    return x + 12, y + 58, w - 24, h - 66
