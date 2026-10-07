# Valores esperados das medidas

Calculados em SQL direto na gold, sem passar pelo DAX (`tools/valores_esperados.py`).
No Power BI, cada medida em um cartão tem que mostrar o mesmo valor.
As medidas de período usam o mês **09/2026** num filtro de `dim_data[mes_ano]`; as demais, nenhum filtro.

| Pasta | Medida | Valor esperado | Contexto |
|---|---|---:|---|
| Portfólio | Projetos | 45 | sem filtro |
| Portfólio | Projetos Ativos | 26 | sem filtro |
| Portfólio | Projetos em Andamento | 25 | sem filtro |
| Portfólio | Projetos Concluídos | 14 | sem filtro |
| Prazo | Projetos Atrasados | 7 | sem filtro |
| Prazo | % Projetos Atrasados | 26,9% | sem filtro |
| Prazo | % Projetos Entregues no Prazo | 21,4% | sem filtro |
| Prazo | Atraso Médio dos Projetos (dias) | 89,2 | sem filtro |
| Esforço | Horas Orçadas | 22.750 | sem filtro |
| Esforço | % Orçamento Consumido | 96,3% | sem filtro |
| Tarefas | Tarefas | 1.435 | sem filtro |
| Tarefas | Tarefas Abertas | 140 | sem filtro |
| Tarefas | Tarefas Concluídas | 1.235 | sem filtro |
| Tarefas | Tarefas Bloqueadas | 7 | sem filtro |
| Prazo | Tarefas Vencidas | 39 | sem filtro |
| Prazo | % Abertas Vencidas | 30,7% | sem filtro |
| Prazo | % Entregues no Prazo | 76,2% | sem filtro |
| Prazo | Atraso Médio das Tarefas (dias) | 20,8 | sem filtro |
| Tempo | Lead Time Médio (dias) | 20,6 | sem filtro |
| Tempo | Ciclo Médio (dias) | 9,1 | sem filtro |
| Tempo | Ciclo Mediano (dias) | 6,8 | sem filtro |
| Tempo | Idade Média das Abertas (dias) | 42,4 | sem filtro |
| Tempo | Dias Bloqueada | 1.385,5 | sem filtro |
| Tempo | % Concluídas com Retrabalho | 18,0% | sem filtro |
| Esforço | Horas Estimadas | 18.630 | sem filtro |
| Esforço | Horas Apontadas | 21.919 | sem filtro |
| Esforço | Desvio de Esforço % | +33,6% | sem filtro |
| Período | Tarefas Criadas | 167 | mês 09/2026 |
| Período | Tarefas Entregues | 175 | mês 09/2026 |
| Período | Saldo do Período | -8 | mês 09/2026 |
| Fluxo | Tempo Médio na Etapa (dias) | 4,4 | sem filtro |
| Fluxo | Tarefas Paradas na Etapa | 140 | sem filtro |
| Fluxo | Paradas há mais de 15 dias | 27 | sem filtro |
| Fluxo | Mudanças de Status | 1.019 | mês 09/2026 |
| Fluxo | Bloqueios no Período | 26 | mês 09/2026 |
| Referência | Data de Referência | 30/09/2026 | sem filtro |
| Referência | Texto Referência | Dados até 30/09/2026 | sem filtro |
| Contexto dos cartões | Contexto Projetos Ativos | de 45 no portfólio | sem filtro |
| Contexto dos cartões | Contexto Projetos Atrasados | 27% dos ativos | sem filtro |
| Contexto dos cartões | Contexto Atrasados de Ativos | 7 de 26 ativos | sem filtro |
| Contexto dos cartões | Contexto Entregues no Prazo | 3 de 14 concluídos | sem filtro |
| Contexto dos cartões | Contexto Tarefas Abertas | 7 bloqueadas agora | sem filtro |
| Contexto dos cartões | Contexto Tarefas Vencidas | 31% das abertas | sem filtro |
| Contexto dos cartões | Contexto Tarefas Concluídas | 86% de todas as tarefas | sem filtro |
| Contexto dos cartões | Contexto Horas Apontadas | +18% vs. o estimado | sem filtro |
| Contexto dos cartões | Contexto Orçamento | restam 831 h | sem filtro |
