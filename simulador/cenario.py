"""Gera o cenário no formato da AEVO: portfólios, usuários, projetos, tarefas e movimentações.

_mundo simula tudo até o horizonte; gerar corta na data de referência."""
import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import numpy as np
from faker import Faker

from simulador import catalogos as cat
from simulador.fluxo import Corte, Trajeto, simular
from simulador.tempo import iso, no_expediente


@dataclass(frozen=True)
class Config:
    semente: int = 42
    data_referencia: date = date(2026, 9, 30)
    inicio: date = date(2024, 1, 8)
    fim_portfolio: date = date(2026, 9, 26)
    horizonte: date = date(2028, 12, 31)
    p_cancelado: float = 0.08
    p_pausado: float = 0.08
    recencia: float = 2.4
    otimismo: tuple[float, float] = (0.6, 1.05)
    dispersao_saude: float = 0.4
    arrasto: float = 2.0


@dataclass
class _Tarefa:
    criada: datetime
    projeto: int
    tipo: str
    titulo: str
    prioridade: str
    responsavel: dict
    estimativa: int
    prazo: date | None
    trajeto: Trajeto
    horas_total: float
    fracao_parcial: float


@dataclass
class _Projeto:
    n: int
    nome: str
    portfolio_id: int
    gestor: dict
    prioridade: str
    inicio: datetime
    duracao: int
    escopo_fecha_em: datetime
    dias_planejados: int
    corte: Corte | None
    tarefas: list[_Tarefa] = field(default_factory=list)


def _email(nome: str) -> str:
    base = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    partes = base.split()
    return f"{partes[0]}.{partes[-1]}@empresa-demo.com.br"


def _pessoas(rng: np.random.Generator, fake: Faker, cfg: Config) -> list[dict]:
    pessoas, nomes, emails = [], set(), set()
    for eq in cat.PORTFOLIOS:
        for i in range(int(rng.integers(16, 25))):
            while True:
                nome = f"{fake.first_name()} {fake.last_name()}"
                if nome not in nomes and _email(nome) not in emails:
                    break
            nomes.add(nome)
            emails.add(_email(nome))
            pessoas.append({
                "id": f"USR-{len(pessoas) + 1:03d}",
                "nome": nome,
                "email": _email(nome),
                "portfolio_id": eq.id,
                "cargo": cat.CARGOS["gestor"] if i == 0 else str(rng.choice(cat.CARGOS["membro"])),
                "data_admissao": cfg.inicio - timedelta(days=int(rng.integers(30, 3000))),
                "_saida": None,
                "_ritmo": float(np.clip(rng.lognormal(0, 0.2), 0.6, 1.6)),
            })
    janela = (cfg.fim_portfolio - cfg.inicio).days
    for i in rng.choice(len(pessoas), size=14, replace=False):
        if pessoas[i]["cargo"] != cat.CARGOS["gestor"]:
            pessoas[i]["_saida"] = cfg.inicio + timedelta(days=int(rng.uniform(0.3, 0.95) * janela))
    return pessoas


def _prioridade(rng: np.random.Generator) -> str:
    valor = str(rng.choice(cat.PRIORIDADES, p=cat.PESO_PRIORIDADES))
    sorte = rng.random()
    return valor.lower() if sorte < 0.07 else valor.upper() if sorte < 0.10 else valor


def _titulo(rng: np.random.Generator, tipo: str) -> str:
    titulo = str(rng.choice(cat.TITULOS[tipo])).format(obj=rng.choice(cat.OBJETOS))
    return titulo + "  " if rng.random() < 0.05 else titulo


def _mundo(cfg: Config) -> tuple[list[dict], list[_Projeto]]:
    rng = np.random.default_rng(cfg.semente)
    fake = Faker("pt_BR")
    fake.seed_instance(cfg.semente)
    horizonte = datetime.combine(cfg.horizonte, time(23, 59, 59))

    pessoas = _pessoas(rng, fake, cfg)
    por_portfolio = {eq.id: [p for p in pessoas if p["portfolio_id"] == eq.id] for eq in cat.PORTFOLIOS}
    pesos_tipo = np.array([t.peso for t in cat.TIPOS]) / sum(t.peso for t in cat.TIPOS)
    janela = (cfg.fim_portfolio - cfg.inicio).days

    projetos = []
    for n, (portfolio_id, nome) in enumerate(cat.PROJETOS):
        inicio = no_expediente(cfg.inicio + timedelta(days=int(rng.beta(cfg.recencia, 1.0) * janela)), rng)
        duracao = int(rng.integers(90, 301))
        saude = float(np.clip(rng.lognormal(0, cfg.dispersao_saude), 0.7, 2.2))
        dias_planejados = int(duracao * rng.uniform(*cfg.otimismo))
        janela_tarefas = duracao * 0.85 * max(saude, 1.0) ** cfg.arrasto

        equipe = por_portfolio[portfolio_id]
        outros = [p for p in pessoas if p["portfolio_id"] != portfolio_id]
        membros = [equipe[i] for i in rng.choice(range(1, len(equipe)), size=int(rng.integers(3, 7)), replace=False)]
        membros += [outros[i] for i in rng.choice(len(outros), size=int(rng.integers(0, 3)), replace=False)]

        corte, sorte = None, rng.random()
        quando = no_expediente(inicio.date() + timedelta(days=int(duracao * rng.uniform(0.3, 0.8))), rng)
        if sorte < cfg.p_cancelado + cfg.p_pausado:
            corte = Corte(quando, cancelar=sorte < cfg.p_cancelado)

        projeto = _Projeto(n, nome, portfolio_id, equipe[0],
                           str(rng.choice(cat.PRIORIDADES[1:], p=(0.45, 0.4, 0.15))),
                           inicio, duracao, inicio + timedelta(days=janela_tarefas), dias_planejados, corte)

        for _ in range(int(np.clip(duracao / 4 * rng.uniform(0.8, 1.2), 10, 60))):
            criada = no_expediente(inicio.date() + timedelta(days=int(rng.beta(1.2, 1.8) * janela_tarefas)), rng)
            tipo = cat.TIPOS[int(rng.choice(len(cat.TIPOS), p=pesos_tipo))]
            estimativa = int(rng.choice(tipo.estimativas))
            disponiveis = [m for m in membros if m["_saida"] is None or m["_saida"] > criada.date()]
            responsavel = (disponiveis or [projeto.gestor])[int(rng.integers(0, len(disponiveis) or 1))]
            prazo = None
            if rng.random() > 0.06:
                dias_prazo = (14 + estimativa / 6 * 1.4 * 1.3) * rng.uniform(1.0, 1.8)
                prazo = criada.date() + timedelta(days=int(np.ceil(dias_prazo)))
            trajeto = simular(rng, criada, estimativa, saude, responsavel["_ritmo"], horizonte, corte)
            horas = estimativa * float(rng.lognormal(np.log(tipo.estouro * saude ** 0.5), 0.35))
            tarefa = _Tarefa(criada, n, tipo.nome, _titulo(rng, tipo.nome), _prioridade(rng), responsavel,
                             estimativa, prazo, trajeto, horas, float(rng.uniform(0.15, 0.85)))
            if corte and criada >= corte.quando:
                continue
            projeto.tarefas.append(tarefa)
        projetos.append(projeto)
    return pessoas, projetos


def _cortar(tarefa: _Tarefa, ref: datetime) -> list[tuple[str | None, str, datetime]]:
    return [e for e in tarefa.trajeto.eventos if e[2] <= ref]


def _horas(tarefa: _Tarefa, eventos: list) -> float:
    if not any(novo == cat.EM_ANDAMENTO for _, novo, _ in eventos):
        return 0.0
    if eventos[-1][1] == cat.CONCLUIDA:
        return round(tarefa.horas_total, 1)
    return round(tarefa.horas_total * tarefa.fracao_parcial, 1)


SITUACAO_TAREFA = {s.nome: s.categoria for s in cat.STATUS}
CUSTO_HORA = {p.id: p.custo_hora for p in cat.PORTFOLIOS}


def _etiquetas_tarefa(eventos: list) -> list[str]:
    etiquetas = []
    if eventos[-1][1] == cat.BLOQUEADA:
        etiquetas.append("Bloqueada")
    if any(a == cat.EM_REVISAO and n == cat.EM_ANDAMENTO for a, n, _ in eventos):
        etiquetas.append("Retrabalho")
    return etiquetas


def _origem(nome: str) -> tuple[str, str | None]:
    n = int(hashlib.sha256(nome.encode()).hexdigest()[:8], 16)
    if n % 100 < 40:
        return "Ideia", f"IDE-{1000 + n % 9000}"
    if n % 100 < 55:
        return "Startup", f"STA-{100 + n % 900}"
    return "Direto", None


def _farol(situacao: str, etiquetas: list[str], limite: date, tarefas: list, inicio: date, ref: date) -> str:
    if situacao != "Ativo":
        return "Encerrado"
    if limite < ref:
        return "Vermelho"
    if "Em espera" in etiquetas:
        return "Amarelo"
    decorrido = (ref - inicio).days / max((limite - inicio).days, 1)
    feitas = sum(s == cat.CONCLUIDA for s, _ in tarefas) / max(len(tarefas), 1)
    return "Amarelo" if decorrido - feitas > 0.05 else "Verde"


def gerar(cfg: Config = Config()) -> dict[str, list[dict]]:
    ref = datetime.combine(cfg.data_referencia, time(23, 59, 59))
    pessoas, projetos = _mundo(cfg)

    projetos_vivos = sorted((p for p in projetos if p.inicio <= ref), key=lambda p: (p.inicio, p.n))
    id_projeto = {p.n: f"PRJ-{i:03d}" for i, p in enumerate(sorted(projetos, key=lambda p: (p.inicio, p.n)), 1)}
    todas = sorted((t for p in projetos for t in p.tarefas), key=lambda t: (t.criada, t.projeto, t.titulo))
    id_tarefa = {id(t): f"TSK-{i:05d}" for i, t in enumerate(todas, 1)}
    todos_eventos = sorted(((e[2], id_tarefa[id(t)], j) for t in todas for j, e in enumerate(t.trajeto.eventos)))
    id_evento = {(tid, j): f"EVT-{i:06d}" for i, (_, tid, j) in enumerate(todos_eventos, 1)}

    saida_tarefas, saida_eventos, saida_projetos = [], [], []
    for p in projetos_vivos:
        cortadas = []
        for t in p.tarefas:
            if t.criada > ref:
                continue
            evs = _cortar(t, ref)
            tid, status, momento = id_tarefa[id(t)], evs[-1][1], evs[-1][2]
            cortadas.append((status, momento))
            saida_tarefas.append({
                "id": tid,
                "projeto_id": id_projeto[p.n],
                "titulo": t.titulo,
                "etapa": status,
                "situacao": SITUACAO_TAREFA[status],
                "etiquetas": _etiquetas_tarefa(evs),
                "responsavel_id": t.responsavel["id"],
                "prioridade": t.prioridade,
                "tipo": t.tipo,
                "estimativa_horas": t.estimativa,
                "horas_apontadas": _horas(t, evs),
                "criada_em": iso(t.criada),
                "limite": iso(t.prazo),
                "concluida_em": iso(momento) if status == cat.CONCLUIDA else None,
                "atualizado_em": iso(momento),
            })
            for j, (anterior, novo, quando) in enumerate(evs):
                autor = p.gestor if novo in (cat.A_FAZER, cat.CANCELADA) else t.responsavel
                saida_eventos.append({"id": id_evento[(tid, j)], "tarefa_id": tid, "etapa_anterior": anterior,
                                      "etapa_nova": novo, "usuario_id": autor["id"], "ocorrido_em": iso(quando)})

        escopo_original = p.inicio + timedelta(days=p.duracao * 0.85)
        status_tarefas = {s for s, _ in cortadas}
        momentos = [m for _, m in cortadas] + [p.inicio]
        conclusao = None
        etiquetas = []
        if p.corte and p.corte.quando <= ref:
            situacao, etapa = ("Arquivado", "Execução") if p.corte.cancelar else ("Ativo", "Execução")
            if not p.corte.cancelar:
                etiquetas.append("Em espera")
            momentos.append(p.corte.quando)
        elif not status_tarefas or status_tarefas <= {cat.BACKLOG, cat.A_FAZER}:
            situacao, etapa = "Ativo", "Planejamento"
        elif p.escopo_fecha_em <= ref and status_tarefas <= cat.STATUS_FINAIS:
            situacao, etapa = "Concluído", "Concluído"
            conclusao = max(max(momentos), p.escopo_fecha_em)
            momentos.append(conclusao)
        else:
            feitas = sum(s == cat.CONCLUIDA for s, _ in cortadas) / len(cortadas)
            situacao, etapa = "Ativo", "Implantação" if feitas >= 0.8 else "Execução"

        limite = p.inicio.date() + timedelta(days=p.dias_planejados)
        horas_orcadas = int(np.ceil(sum(t.estimativa for t in p.tarefas if t.criada <= escopo_original) * 1.1 / 10) * 10)
        origem, origem_id = _origem(p.nome)
        saida_projetos.append({
            "id": id_projeto[p.n],
            "portfolio_id": p.portfolio_id,
            "nome": p.nome,
            "etapa": etapa,
            "situacao": situacao,
            "etiquetas": etiquetas,
            "farol": _farol(situacao, etiquetas, limite, cortadas, p.inicio.date(), cfg.data_referencia),
            "origem": origem,
            "origem_id": origem_id,
            "gerente_id": p.gestor["id"],
            "prioridade": p.prioridade,
            "inicio": iso(p.inicio.date()),
            "limite": iso(limite),
            "concluido_em": iso(conclusao.date()) if conclusao else None,
            "horas_orcadas": horas_orcadas,
            "orcamento": horas_orcadas * CUSTO_HORA[p.portfolio_id],
            "criado_em": iso(p.inicio),
            "atualizado_em": iso(max(momentos)),
        })

    portfolios = [{"id": e.id, "nome": e.nome, "sigla": e.sigla, "etapas": list(cat.ETAPAS_PORTFOLIO),
                   "dono_id": next(p["id"] for p in pessoas if p["portfolio_id"] == e.id)} for e in cat.PORTFOLIOS]
    usuarios = [{"id": p["id"], "nome": p["nome"], "email": p["email"], "portfolio_id": p["portfolio_id"],
                 "cargo": p["cargo"], "data_admissao": iso(p["data_admissao"]),
                 "ativo": p["_saida"] is None or p["_saida"] > cfg.data_referencia} for p in pessoas]
    return {"portfolios": portfolios, "usuarios": usuarios,
            "projetos": sorted(saida_projetos, key=lambda x: x["id"]),
            "tarefas": sorted(saida_tarefas, key=lambda x: x["id"]),
            "movimentacoes": sorted(saida_eventos, key=lambda x: x["id"])}


def impressao_digital(dados: dict[str, list[dict]]) -> str:
    texto = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode()).hexdigest()[:16]
