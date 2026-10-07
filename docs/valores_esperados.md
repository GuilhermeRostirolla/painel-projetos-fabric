# Valores esperados das medidas

Calculados em SQL direto na gold, sem passar pelo DAX (`tools/valores_esperados.py`).
No Power BI, cada medida em um cartão tem que mostrar o mesmo valor.
As medidas de período usam o mês **09/2026** num filtro de `dim_data[mes_ano]`; as demais, nenhum filtro.

| Pasta | Medida | Valor esperado | Contexto |
|---|---|---:|---|
| Portfólio | Projetos | 122 | sem filtro |
| Portfólio | Projetos Ativos | 42 | sem filtro |
| Portfólio | Projetos em Execução | 39 | sem filtro |
| Portfólio | Projetos Concluídos | 63 | sem filtro |
| Prazo | Projetos Atrasados | 12 | sem filtro |
| Prazo | % Projetos Atrasados | 28,6% | sem filtro |
| Prazo | % Projetos Entregues no Prazo | 33,3% | sem filtro |
| Prazo | Atraso Médio dos Projetos (dias) | 96,6 | sem filtro |
| Esforço | Horas Orçadas | 69.200 | sem filtro |
| Esforço | % Orçamento Consumido | 102,7% | sem filtro |
| Portfólio | Orçamento | 10.335.800 | sem filtro |
| Portfólio | Projetos Farol Vermelho | 17 | sem filtro |
| Portfólio | Projetos de Ideias | 48 | sem filtro |
| Tarefas | Tarefas | 4.467 | sem filtro |
| Tarefas | Tarefas Abertas | 176 | sem filtro |
| Tarefas | Tarefas Concluídas | 4.064 | sem filtro |
| Tarefas | Tarefas Impedidas | 6 | sem filtro |
| Prazo | Tarefas Vencidas | 50 | sem filtro |
| Prazo | % Abertas Vencidas | 30,7% | sem filtro |
| Prazo | % Entregues no Prazo | 78,9% | sem filtro |
| Prazo | Atraso Médio das Tarefas (dias) | 21,9 | sem filtro |
| Tempo | Lead Time Médio (dias) | 19,9 | sem filtro |
| Tempo | Ciclo Médio (dias) | 9,2 | sem filtro |
| Tempo | Ciclo Mediano (dias) | 6,7 | sem filtro |
| Tempo | Idade Média das Abertas (dias) | 75,0 | sem filtro |
| Tempo | Dias Bloqueada | 5.056,8 | sem filtro |
| Tempo | % Concluídas com Retrabalho | 17,0% | sem filtro |
| Esforço | Horas Estimadas | 58.718 | sem filtro |
| Esforço | Horas Apontadas | 71.084 | sem filtro |
| Esforço | Desvio de Esforço % | +31,2% | sem filtro |
| Período | Tarefas Criadas | 226 | mês 09/2026 |
| Período | Tarefas Entregues | 213 | mês 09/2026 |
| Período | Saldo do Período | +13 | mês 09/2026 |
| Tarefas | % Tarefas Concluídas | 91,0% | sem filtro |
| Fluxo | Tempo Médio na Etapa (dias) | 4,3 | sem filtro |
| Fluxo | Tarefas Paradas na Etapa | 176 | sem filtro |
| Fluxo | Paradas há mais de 15 dias | 43 | sem filtro |
| Fluxo | Mudanças de Status | 1.252 | mês 09/2026 |
| Fluxo | Bloqueios no Período | 31 | mês 09/2026 |
| Referência | Data de Referência | 30/09/2026 | sem filtro |
| Referência | Texto Referência | Dados até 30/09/2026 | sem filtro |
| Contexto dos cartões | Contexto Projetos Ativos | de 122 no portfólio | sem filtro |
| Contexto dos cartões | Contexto Projetos Atrasados | 29% dos ativos | sem filtro |
| Contexto dos cartões | Contexto Atrasados de Ativos | 12 de 42 ativos | sem filtro |
| Contexto dos cartões | Contexto Entregues no Prazo | 21 de 63 concluídos | sem filtro |
| Contexto dos cartões | Contexto Tarefas Abertas | 6 impedidas agora | sem filtro |
| Contexto dos cartões | Contexto Tarefas Vencidas | 31% das abertas | sem filtro |
| Contexto dos cartões | Contexto Tarefas Concluídas | 91% de todas as tarefas | sem filtro |
| Contexto dos cartões | Contexto Horas Apontadas | +21% vs. o estimado | sem filtro |
| Contexto dos cartões | Contexto Orçamento Consumido | 103% das horas orçadas já usadas | sem filtro |
| Contexto dos cartões | Contexto Projetos de Ideias | 48 vieram de ideias | sem filtro |
| Contexto dos cartões | Contexto Orçamento | estourou em 1884 h | sem filtro |
