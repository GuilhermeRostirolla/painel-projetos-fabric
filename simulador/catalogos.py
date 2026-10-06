"""Catálogos fixos do cenário: equipes, status, tipos de tarefa e nomes de projetos."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Equipe:
    id: int
    nome: str
    sigla: str


@dataclass(frozen=True)
class Status:
    id: int
    nome: str
    categoria: str
    ordem: int


@dataclass(frozen=True)
class TipoTarefa:
    nome: str
    peso: float                  # chance relativa de sorteio
    estimativas: tuple[int, ...]  # horas possíveis
    estouro: float               # mediana de horas reais / estimadas


EQUIPES = (
    Equipe(1, "Tecnologia", "TEC"),
    Equipe(2, "Dados & BI", "DAT"),
    Equipe(3, "Operações", "OPE"),
    Equipe(4, "Comercial", "COM"),
    Equipe(5, "Pessoas & Cultura", "PES"),
)

BACKLOG, A_FAZER, EM_ANDAMENTO, BLOQUEADA, EM_REVISAO, CONCLUIDA, CANCELADA = (
    "Backlog", "A Fazer", "Em Andamento", "Bloqueada", "Em Revisão", "Concluída", "Cancelada")

STATUS = (
    Status(1, BACKLOG, "Não iniciada", 1),
    Status(2, A_FAZER, "Não iniciada", 2),
    Status(3, EM_ANDAMENTO, "Em execução", 3),
    Status(4, BLOQUEADA, "Em execução", 4),
    Status(5, EM_REVISAO, "Em execução", 5),
    Status(6, CONCLUIDA, "Concluída", 6),
    Status(7, CANCELADA, "Cancelada", 7),
)
STATUS_FINAIS = frozenset({CONCLUIDA, CANCELADA})

TIPOS = (
    TipoTarefa("Funcionalidade", 0.38, (8, 16, 24, 40), 1.25),
    TipoTarefa("Correção", 0.18, (2, 4, 8), 1.40),
    TipoTarefa("Análise", 0.16, (4, 8, 16), 1.10),
    TipoTarefa("Documentação", 0.10, (2, 4, 8), 0.95),
    TipoTarefa("Infraestrutura", 0.10, (8, 16, 24), 1.30),
    TipoTarefa("Treinamento", 0.08, (4, 8), 1.00),
)

PRIORIDADES = ("Baixa", "Média", "Alta", "Crítica")
PESO_PRIORIDADES = (0.20, 0.45, 0.27, 0.08)

CARGOS = {
    "gestor": "Coordenador(a)",
    "membro": ("Analista Júnior", "Analista Pleno", "Analista Sênior", "Especialista"),
}

# (equipe_id, nome do projeto)
PROJETOS = (
    (1, "Migração do ERP para nuvem"), (1, "Portal do Cliente 2.0"),
    (1, "Autenticação única (SSO)"), (1, "App de vistoria em campo"),
    (1, "Modernização da rede das filiais"), (1, "Integração com transportadoras"),
    (1, "Backup e recuperação de desastres"), (1, "Central de chamados de TI"),
    (1, "API de rastreamento de pedidos"), (1, "Atualização do parque de notebooks"),
    (2, "Data Lake corporativo"), (2, "Painel de indicadores comerciais"),
    (2, "Previsão de demanda"), (2, "Governança e catálogo de dados"),
    (2, "Painel de custos logísticos"), (2, "Automação de relatórios financeiros"),
    (2, "Qualidade de dados de cadastro"), (2, "Migração de relatórios para Power BI"),
    (3, "Roteirização de entregas"), (3, "Redução de perdas no armazém"),
    (3, "Manutenção preditiva da frota"), (3, "Padronização de processos de expedição"),
    (3, "Inventário com coletor"), (3, "Gestão de pátio"),
    (3, "Indicadores de nível de serviço"), (3, "Novo layout do centro de distribuição"),
    (4, "CRM para equipe de vendas"), (4, "Reestruturação da tabela de preços"),
    (4, "Programa de fidelidade"), (4, "Portal de cotações online"),
    (4, "Prospecção no agronegócio"), (4, "Treinamento de vendas consultivas"),
    (4, "Pesquisa de satisfação de clientes"),
    (5, "Novo processo de onboarding"), (5, "Plataforma de treinamentos"),
    (5, "Avaliação de desempenho 360"), (5, "Programa de ideias"),
    (5, "Pesquisa de clima"), (5, "Trilha de lideranças"),
    (5, "Ponto eletrônico digital"), (5, "Plano de cargos e salários"),
    (2, "Monitoramento de pipelines de dados"), (1, "Assinatura eletrônica de contratos"),
    (3, "Controle de combustível"), (4, "Expansão para o Nordeste"),
)

# Modelos de título por tipo de tarefa; {obj} vem de OBJETOS
TITULOS = {
    "Funcionalidade": ("Criar tela de {obj}", "Implementar cadastro de {obj}",
                       "Desenvolver relatório de {obj}", "Integrar {obj} com o ERP",
                       "Automatizar envio de {obj}", "Adicionar filtro de {obj}"),
    "Correção": ("Corrigir erro em {obj}", "Ajustar cálculo de {obj}",
                 "Resolver lentidão em {obj}", "Corrigir duplicidade em {obj}"),
    "Análise": ("Levantar requisitos de {obj}", "Mapear processo de {obj}",
                "Analisar dados de {obj}", "Definir regras de {obj}"),
    "Documentação": ("Documentar fluxo de {obj}", "Escrever manual de {obj}",
                     "Atualizar procedimento de {obj}"),
    "Infraestrutura": ("Configurar ambiente de {obj}", "Provisionar servidor de {obj}",
                       "Configurar monitoramento de {obj}", "Revisar acessos de {obj}"),
    "Treinamento": ("Treinar usuários em {obj}", "Preparar material sobre {obj}",
                    "Realizar workshop de {obj}"),
}
OBJETOS = ("pedidos", "clientes", "fornecedores", "notas fiscais", "contratos",
           "rotas", "estoque", "frota", "colaboradores", "metas", "orçamentos",
           "cotações", "chamados", "indicadores", "faturamento", "cadastros",
           "entregas", "pagamentos", "acessos", "relatórios gerenciais")
