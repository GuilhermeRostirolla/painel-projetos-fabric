"""Regras de coerência do cenário. Se alguma falhar, a API não sobe."""
from collections import defaultdict
from datetime import date, datetime

from simulador.catalogos import CONCLUIDA, STATUS, STATUS_FINAIS

STATUS_VALIDOS = {s.nome for s in STATUS}
FAROIS = {"Verde", "Amarelo", "Vermelho", "Encerrado"}


def _dt(texto: str) -> datetime:
    return datetime.fromisoformat(texto)


def problemas(dados: dict[str, list[dict]], referencia: date) -> list[str]:
    erros: list[str] = []
    for nome, linhas in dados.items():
        ids = [l["id"] for l in linhas]
        if len(ids) != len(set(ids)):
            erros.append(f"{nome}: id duplicado")

    pessoas = {p["id"] for p in dados["usuarios"]}
    projetos = {p["id"] for p in dados["projetos"]}
    if len({p["nome"] for p in dados["usuarios"]}) != len(pessoas):
        erros.append("usuarios: nome duplicado")

    historico = defaultdict(list)
    for e in dados["movimentacoes"]:
        historico[e["tarefa_id"]].append(e)
        if e["usuario_id"] not in pessoas:
            erros.append(f"{e['id']}: usuário inexistente")

    for t in dados["tarefas"]:
        tid = t["id"]
        if t["projeto_id"] not in projetos or t["responsavel_id"] not in pessoas:
            erros.append(f"{tid}: chave estrangeira quebrada")
        if t["etapa"] not in STATUS_VALIDOS:
            erros.append(f"{tid}: status desconhecido {t['status']}")
        evs = sorted(historico[tid], key=lambda e: e["id"])
        if not evs or evs[0]["etapa_anterior"] is not None:
            erros.append(f"{tid}: histórico não começa na criação")
            continue
        for a, b in zip(evs, evs[1:]):
            if b["etapa_anterior"] != a["etapa_nova"]:
                erros.append(f"{tid}: histórico pula etapa ({a['etapa_nova']} -> {b['etapa_anterior']})")
            if _dt(b["ocorrido_em"]) <= _dt(a["ocorrido_em"]):
                erros.append(f"{tid}: histórico fora de ordem")
        if evs[-1]["etapa_nova"] != t["etapa"]:
            erros.append(f"{tid}: status atual difere do último evento")
        if evs[0]["ocorrido_em"] != t["criada_em"] or evs[-1]["ocorrido_em"] != t["atualizado_em"]:
            erros.append(f"{tid}: datas da tarefa não batem com o histórico")
        if _dt(t["atualizado_em"]).date() > referencia:
            erros.append(f"{tid}: data depois da referência")
        if (t["concluida_em"] is not None) != (t["etapa"] == CONCLUIDA):
            erros.append(f"{tid}: data de conclusão incoerente com o status")
        if t["etapa"] not in STATUS_FINAIS and t["horas_apontadas"] < 0:
            erros.append(f"{tid}: horas negativas")

    for p in dados["projetos"]:
        if p["limite"] <= p["inicio"]:
            erros.append(f"{p['id']}: fim planejado antes do início")
        if (p["concluido_em"] is not None) != (p["situacao"] == "Concluído"):
            erros.append(f"{p['id']}: data de conclusão incoerente com o status")
        if p["situacao"] not in {"Ativo", "Concluído", "Arquivado"} or p["farol"] not in FAROIS:
            erros.append(f"{p['id']}: situação ou farol desconhecido")
    return erros


def exigir(dados: dict[str, list[dict]], referencia: date) -> None:
    erros = problemas(dados, referencia)
    if erros:
        raise ValueError(f"{len(erros)} problema(s) no cenário, ex.: {erros[:5]}")
