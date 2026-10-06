"""Regras de coerência do cenário. Se alguma falhar, a API não sobe."""
from collections import defaultdict
from datetime import date, datetime

from simulador.catalogos import CONCLUIDA, STATUS, STATUS_FINAIS

STATUS_VALIDOS = {s.nome for s in STATUS}


def _dt(texto: str) -> datetime:
    return datetime.fromisoformat(texto)


def problemas(dados: dict[str, list[dict]], referencia: date) -> list[str]:
    erros: list[str] = []
    for nome, linhas in dados.items():
        ids = [l["id"] for l in linhas]
        if len(ids) != len(set(ids)):
            erros.append(f"{nome}: id duplicado")

    pessoas = {p["id"] for p in dados["pessoas"]}
    projetos = {p["id"] for p in dados["projetos"]}
    if len({p["nome"] for p in dados["pessoas"]}) != len(pessoas):
        erros.append("pessoas: nome duplicado")

    historico = defaultdict(list)
    for e in dados["historico"]:
        historico[e["tarefa_id"]].append(e)
        if e["pessoa_id"] not in pessoas:
            erros.append(f"{e['id']}: pessoa inexistente")

    for t in dados["tarefas"]:
        tid = t["id"]
        if t["projeto_id"] not in projetos or t["responsavel_id"] not in pessoas:
            erros.append(f"{tid}: chave estrangeira quebrada")
        if t["status"] not in STATUS_VALIDOS:
            erros.append(f"{tid}: status desconhecido {t['status']}")
        evs = sorted(historico[tid], key=lambda e: e["id"])
        if not evs or evs[0]["status_anterior"] is not None:
            erros.append(f"{tid}: histórico não começa na criação")
            continue
        for a, b in zip(evs, evs[1:]):
            if b["status_anterior"] != a["status_novo"]:
                erros.append(f"{tid}: histórico pula etapa ({a['status_novo']} -> {b['status_anterior']})")
            if _dt(b["ocorrido_em"]) <= _dt(a["ocorrido_em"]):
                erros.append(f"{tid}: histórico fora de ordem")
        if evs[-1]["status_novo"] != t["status"]:
            erros.append(f"{tid}: status atual difere do último evento")
        if evs[0]["ocorrido_em"] != t["criada_em"] or evs[-1]["ocorrido_em"] != t["atualizado_em"]:
            erros.append(f"{tid}: datas da tarefa não batem com o histórico")
        if _dt(t["atualizado_em"]).date() > referencia:
            erros.append(f"{tid}: data depois da referência")
        if (t["concluida_em"] is not None) != (t["status"] == CONCLUIDA):
            erros.append(f"{tid}: data de conclusão incoerente com o status")
        if t["status"] not in STATUS_FINAIS and t["horas_apontadas"] < 0:
            erros.append(f"{tid}: horas negativas")

    for p in dados["projetos"]:
        if p["data_fim_planejada"] <= p["data_inicio"]:
            erros.append(f"{p['id']}: fim planejado antes do início")
        if (p["data_conclusao"] is not None) != (p["status"] == "Concluído"):
            erros.append(f"{p['id']}: data de conclusão incoerente com o status")
    return erros


def exigir(dados: dict[str, list[dict]], referencia: date) -> None:
    erros = problemas(dados, referencia)
    if erros:
        raise ValueError(f"{len(erros)} problema(s) no cenário, ex.: {erros[:5]}")
