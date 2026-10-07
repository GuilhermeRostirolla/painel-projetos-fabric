"""Catálogos do cenário no vocabulário da AEVO (Central de Iniciativas): portfólios, etapas, tipos e projetos."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Portfolio:
    id: int
    nome: str
    sigla: str
    custo_hora: int


@dataclass(frozen=True)
class Status:
    id: int
    nome: str
    categoria: str
    ordem: int


@dataclass(frozen=True)
class TipoTarefa:
    nome: str
    peso: float
    estimativas: tuple[int, ...]
    estouro: float


PORTFOLIOS = (
    Portfolio(1, "Transformação Digital", "TD", 160),
    Portfolio(2, "Dados & Analytics", "DA", 170),
    Portfolio(3, "Excelência Operacional", "EO", 130),
    Portfolio(4, "Crescimento Comercial", "CC", 140),
    Portfolio(5, "Pessoas & Cultura", "PC", 120),
    Portfolio(6, "Experiência do Cliente", "EC", 150),
    Portfolio(7, "Sustentabilidade & ESG", "SE", 140),
    Portfolio(8, "Inovação Aberta", "IA", 180),
)

ETAPAS_PORTFOLIO = ("Planejamento", "Execução", "Implantação", "Concluído")

BACKLOG, A_FAZER, EM_ANDAMENTO, BLOQUEADA, EM_REVISAO, CONCLUIDA, CANCELADA = (
    "Backlog", "A fazer", "Fazendo", "Impedido", "Em revisão", "Concluído", "Arquivada")

STATUS = (
    Status(1, BACKLOG, "Não iniciada", 1),
    Status(2, A_FAZER, "Não iniciada", 2),
    Status(3, EM_ANDAMENTO, "Em andamento", 3),
    Status(4, BLOQUEADA, "Em andamento", 4),
    Status(5, EM_REVISAO, "Em andamento", 5),
    Status(6, CONCLUIDA, "Concluída", 6),
    Status(7, CANCELADA, "Arquivada", 7),
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
    (1, "Migração de e-mail corporativo"), (1, "Segurança de endpoints"), (1, "Rede Wi-Fi nas lojas"),
    (1, "Automação de folha com RPA"), (1, "Portal do fornecedor"), (1, "Gestão de identidades"),
    (2, "Modelo de churn de clientes"), (2, "Precificação dinâmica"), (2, "Painel executivo de vendas"),
    (2, "Lakehouse no Microsoft Fabric"), (2, "Detecção de fraudes em reembolsos"), (2, "Segmentação de clientes"),
    (2, "Previsão de inadimplência"),
    (3, "Lean no centro de distribuição"), (3, "Rastreamento de frota por GPS"), (3, "Redução de avarias no transporte"),
    (3, "Cross docking regional"), (3, "Sistema de gestão de armazém"), (3, "Inspeção de qualidade com visão"),
    (3, "Programa 5S nas filiais"),
    (4, "Força de vendas no campo"), (4, "Canal de vendas B2B online"), (4, "Programa de parceiros"),
    (4, "Revisão de comissionamento"), (4, "Inteligência de mercado"), (4, "Abertura de filial em Goiânia"),
    (4, "Key account management"),
    (5, "Programa de estágio"), (5, "Saúde mental e bem-estar"), (5, "Universidade corporativa"),
    (5, "Diversidade e inclusão"), (5, "Benefícios flexíveis"), (5, "Gestão de talentos"),
    (5, "Recrutamento com triagem digital"),
    (6, "Jornada do cliente omnichannel"), (6, "Chatbot de atendimento"), (6, "NPS em tempo real"),
    (6, "Central de relacionamento"), (6, "App do cliente"), (6, "Programa de recompra"),
    (6, "Autoatendimento de segunda via"), (6, "Pesquisa pós-entrega"), (6, "Redesenho do site"),
    (6, "Atendimento por WhatsApp"), (6, "Tratamento de reclamações"), (6, "Base de conhecimento"),
    (6, "Personalização de ofertas"), (6, "Entrega agendada"), (6, "Clube de vantagens"),
    (7, "Inventário de emissões"), (7, "Energia solar nos CDs"), (7, "Logística reversa de embalagens"),
    (7, "Frota elétrica urbana"), (7, "Relatório de sustentabilidade"), (7, "Redução de consumo de água"),
    (7, "Compras sustentáveis"), (7, "Gestão de resíduos"), (7, "Certificação ISO 14001"),
    (7, "Programa de voluntariado"), (7, "Neutralização de carbono"), (7, "Embalagem reciclável"),
    (7, "Eficiência energética nas lojas"), (7, "Diagnóstico ESG de fornecedores"),
    (8, "POC de roteirização com IA"), (8, "Piloto de drones no inventário"), (8, "Hackathon de logística"),
    (8, "Programa de intraempreendedorismo"), (8, "POC de visão computacional"), (8, "Desafio de startups 2025"),
    (8, "Piloto de IoT em câmaras frias"), (8, "Assistente de IA para vendedores"), (8, "Marketplace de serviços"),
    (8, "Gêmeo digital do CD"), (8, "Desafio de startups 2026"), (8, "POC de manutenção com sensores"),
    (8, "Laboratório de inovação"), (8, "Piloto de pagamentos por aproximação"),
)

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
