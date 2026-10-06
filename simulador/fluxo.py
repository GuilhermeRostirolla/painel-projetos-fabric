"""Máquina de estados de uma tarefa.

Cada tarefa nasce no Backlog e anda pelas etapas com tempos lognormais. Pode ser
bloqueada, voltar da revisão para retrabalho ou ser cancelada. A simulação para na
data de referência, então tarefas ainda abertas ficam na etapa em que estavam.
"""
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from simulador.catalogos import (A_FAZER, BACKLOG, BLOQUEADA, CANCELADA, CONCLUIDA,
                                 EM_ANDAMENTO, EM_REVISAO, STATUS_FINAIS)
from simulador.tempo import avancar

SIGMA = 0.6  # dispersão dos tempos de cada etapa

# Chances de desvio do caminho feliz
P_CANCELAR_NO_BACKLOG = 0.04
P_BLOQUEIO = 0.12
P_RETRABALHO = 0.18


@dataclass
class Corte:
    """Projeto cancelado ou pausado: a partir de `quando`, a tarefa não anda mais."""
    quando: datetime
    cancelar: bool


@dataclass
class Trajeto:
    eventos: list[tuple[str | None, str, datetime]] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.eventos[-1][1]

    @property
    def momento(self) -> datetime:
        return self.eventos[-1][2]

    def iniciou(self) -> bool:
        return any(novo == EM_ANDAMENTO for _, novo, _ in self.eventos)


def _dias(rng: np.random.Generator, mediana: float) -> float:
    return float(rng.lognormal(np.log(max(mediana, 0.1)), SIGMA))


def _proximo(rng: np.random.Generator, status: str, estimativa: float,
             saude: float, ritmo: float) -> tuple[str, float]:
    """Sorteia a próxima etapa e quantos dias corridos a tarefa fica na atual."""
    if status == BACKLOG:
        if rng.random() < P_CANCELAR_NO_BACKLOG:
            return CANCELADA, _dias(rng, 10 * saude)
        return A_FAZER, _dias(rng, 5 * saude)
    if status == A_FAZER:
        return EM_ANDAMENTO, _dias(rng, 3 * saude)
    if status == EM_ANDAMENTO:
        if rng.random() < P_BLOQUEIO * saude:
            return BLOQUEADA, _dias(rng, 2 * saude)
        # horas estimadas viram dias úteis (6 h produtivas) e depois dias corridos
        return EM_REVISAO, _dias(rng, estimativa / 6 * 1.4 * saude * ritmo)
    if status == BLOQUEADA:
        return EM_ANDAMENTO, _dias(rng, 4 * saude)
    if status == EM_REVISAO:
        if rng.random() < P_RETRABALHO:
            return EM_ANDAMENTO, _dias(rng, 1.5)
        return CONCLUIDA, _dias(rng, 1.5)
    raise ValueError(f"etapa sem saída: {status}")


def simular(rng: np.random.Generator, criada_em: datetime, estimativa: float,
            saude: float, ritmo: float, referencia: datetime,
            corte: Corte | None = None) -> Trajeto:
    trajeto = Trajeto([(None, BACKLOG, criada_em)])
    while trajeto.status not in STATUS_FINAIS:
        novo, dias = _proximo(rng, trajeto.status, estimativa, saude, ritmo)
        quando = avancar(trajeto.momento, dias, rng)
        if corte and quando > corte.quando:
            if corte.cancelar and corte.quando > trajeto.momento:
                trajeto.eventos.append((trajeto.status, CANCELADA, corte.quando))
            break
        if quando > referencia:
            break
        trajeto.eventos.append((trajeto.status, novo, quando))
    return trajeto

