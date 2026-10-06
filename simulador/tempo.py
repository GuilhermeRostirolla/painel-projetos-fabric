"""Relógio do simulador: avança no tempo respeitando dias úteis e horário comercial."""
from datetime import date, datetime, time, timedelta

import numpy as np

FUSO = "-03:00"  # horário de Brasília; a API devolve as datas com o fuso explícito
INICIO_EXPEDIENTE, FIM_EXPEDIENTE = 8, 18


def dia_util(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def horario(rng: np.random.Generator) -> time:
    minutos = int(rng.integers(0, (FIM_EXPEDIENTE - INICIO_EXPEDIENTE) * 60))
    return time(INICIO_EXPEDIENTE + minutos // 60, minutos % 60)


def no_expediente(d: date, rng: np.random.Generator) -> datetime:
    return datetime.combine(dia_util(d), horario(rng))


def avancar(anterior: datetime, dias: float, rng: np.random.Generator) -> datetime:
    """Momento `dias` corridos depois de `anterior`, sempre em dia útil, horário comercial
    e estritamente depois de `anterior`."""
    candidato = no_expediente(anterior.date() + timedelta(days=int(round(dias))), rng)
    if candidato <= anterior:
        candidato = anterior + timedelta(minutes=int(rng.integers(15, 180)))
        if candidato.hour >= FIM_EXPEDIENTE or candidato.date() != anterior.date():
            candidato = no_expediente(anterior.date() + timedelta(days=1), rng)
    return candidato


def iso(dt: datetime | date | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%dT%H:%M:%S") + FUSO
    return dt.isoformat()
