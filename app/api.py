"""API de Gerenciamento de Tarefas e Envio de Notificações.""" 
# DocString para Documentação do Módulo

# ---------------------------------------------------------------------------
# IMPORTS / IMPORTAÇÕES
# ---------------------------------------------------------------------------

# — BIBLIOTECA PADRÃO DO PYTHON
import os
    # Sistema Operacional - Lê Variáveis de Ambiente
from contextlib import asynccontextmanager
    # Cria Gerenciador de Contexto para o Ciclo de Vida da Aplicação
from datetime import datetime, timedelta, timezone
    # Cria Fuso Horário e Data/Hora
from typing import Annotated
    # Permite Anotar Tipos de Variáveis e Parâmetros

# — BIBLIOTECAS DE TERCEIROS
import requests
    # Faz Requisições HTTP para Serviços Externos
from fastapi import Depends, FastAPI, HTTPException, Request
    # Cria a API e Define Rotas
        # Declara Dependências, Devolve Erros e Acessa Requisições HTTP
from sqlalchemy.engine import URL
    # Monta a URL Estruturada de Conexão com o Banco de Dados
from sqlmodel import Session, SQLModel, create_engine, select
    # Cria Sessões, Modelos, Conexões e Consultas ao Banco de Dados

# — MÓDULOS LOCAIS DO PROJETO
from .log import LOGGER # LOGGER = logging.getLogger("devops")
    # Configura o Log da Aplicação
from .modelo import Tarefa # class Tarefa(SQLModel, table=True)
    # Define o Modelo de Tarefa e seu Estado de Conclusão

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# ---------------------------------------------------------------------------

# Fuso Horário Utilizado na Criação das Tarefas
FUSO_HORARIO = timezone(timedelta(hours=-3)) # UTC-3 BRT

# Endereço do Serviço Externo Responsável pelo Envio de Notificações
SERVICO_NOTIFICACAO_URL = "http://localhost:8000/notificar"

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES DO BANCO DE DADOS
# ---------------------------------------------------------------------------

# Dados Buscados no Environment (Variáveis de Ambiente) do Render PostgreSQL
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME") # Usuário
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD") # Senha
DATABASE_ADDRESS = os.getenv("DATABASE_ADDRESS")   # Endereço
DATABASE = os.getenv("DATABASE")                   # Nome

# ---------------------------------------------------------------------------
# VALIDAÇÃO DAS CONFIGURAÇÕES DO BANCO DE DADOS
# ---------------------------------------------------------------------------

database_settings = {
    "DATABASE_USERNAME": DATABASE_USERNAME, # Usuário
    "DATABASE_PASSWORD": DATABASE_PASSWORD, # Senha
    "DATABASE_ADDRESS": DATABASE_ADDRESS,   # Endereço
    "DATABASE": DATABASE,                   # Nome
}

# Configurações Faltando/Vazias
missing_settings = [
    name
    for name, value in database_settings.items()
    if not value
]

# Loga Erro Crítico de Configuração em Falta
for name in missing_settings:
    LOGGER.critical("%s está faltando", name)

# Força Interrupção da Execução do Programa
if missing_settings:
    raise RuntimeError(
        "Variáveis de ambiente do PostgreSQL não configuradas: "
        + ", ".join(missing_settings)
    )

# ---------------------------------------------------------------------------
# CONEXÃO COM O BANCO DE DADOS
# ---------------------------------------------------------------------------

# Monta a URL de Conexão com PostgreSQL
DATABASE_URL = URL.create(
    "postgresql+psycopg",       # BD e Driver 
    username=DATABASE_USERNAME, # Usuário
    password=DATABASE_PASSWORD, # Senha
    host=DATABASE_ADDRESS,      # Endereço
    database=DATABASE,          # Nome
)

# Cria o Engine/Motor, Administrador de Conexões entre App e BD
# Infraestrutura Utilizada pelas Sessões/Sessions para Consultas e Transações
ENGINE = create_engine(DATABASE_URL)

# ---------------------------------------------------------------------------
# DEPENDÊNCIAS
# ---------------------------------------------------------------------------

# Define Dependência para Sessão do Banco de Dados, que será Injetado as Rotas
def get_session():
    """Fornece uma Sessão do Banco de Dados para uma Requisição."""
    # With Garante....
    with Session(ENGINE) as session: # Sessão é Aberta com o Engine
        yield session                # Entrega a Rota
# Declaração de Tipo Reutilizável de: Valor recebido da Sessão e Execução obtida pelo FastAPI
SessionDependency = Annotated[Session, Depends(get_session)] # Sessão Fechada após Fim da Requisição
# def <rota>(session: SessionDependency):

# ---------------------------------------------------------------------------
# CICLO DE VIDA DA APLICAÇÃO
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Cria as Tabelas Antes de a Aplicação Atender Requisições."""

    SQLModel.metadata.create_all(ENGINE)

    yield # Tudo que Acontece ANTES do 'yield' é Executado na Inicialização


# ---------------------------------------------------------------------------
# CRIAÇÃO DA APLICAÇÃO FASTAPI
# ---------------------------------------------------------------------------

APP = FastAPI(
    title="ServicoTarefa", # Título
    lifespan=lifespan,     # Ciclo de Vida
)

# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------

@APP.middleware("http") # Participa de Todas Requisições HTTP
async def registrar_acessos(request: Request, call_next):
    """Registra no log os acessos e as tentativas de acessar rotas inexistentes."""

    resposta = await call_next(request)

    # Se Rota NÃO for Encontrada
    if resposta.status_code == 404 and request.scope.get("route") is None:
        LOGGER.error(
            "Rota inexistente: %s %s",
            request.method,
            request.url.path,
        )
    else:
        LOGGER.info(
            "Acesso: %s %s -> %s",
            request.method,
            request.url.path,
            resposta.status_code,
        )

    return resposta


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES — CHAMADAS EXTERNAS
# ---------------------------------------------------------------------------

def solicitar_notificacao(id_tarefa: int, titulo: str) -> None:
    """Solicita ao serviço de notificações o aviso de conclusão da tarefa."""

    try:
        resposta = requests.post(
            SERVICO_NOTIFICACAO_URL,
            params={
                "id": id_tarefa,
                "titulo": titulo,
            },
            timeout=1,
        )

        resposta.raise_for_status()

    except requests.RequestException as erro:
        raise HTTPException(
            status_code=502,
            detail=(
                "Falha ao comunicar com o ServiçoNotificacao: "
                f"{erro}"
            ),
        ) from erro

# ---------------------------------------------------------------------------
# ROTAS — INFORMAÇÕES GERAIS
# ---------------------------------------------------------------------------

@APP.get("/")
async def index() -> dict[str, str]:
    """Retorna a mensagem inicial da API."""

    return {"mensagem": "Olá, mundo!"}


@APP.get("/autor")
async def autor() -> dict[str, str]:
    """Retorna o nome completo do autor da API."""

    return {"mensagem": "Eduardo José Skura Czerniak"}


# ---------------------------------------------------------------------------
# ROTAS — CONSULTA DE TAREFAS
# ---------------------------------------------------------------------------

@APP.get("/tarefas")
def tarefas(
    session: SessionDependency,
) -> list[dict[str, str]]:
    """Lista os identificadores e títulos das tarefas."""

    lista_tarefas = session.exec(
        select(Tarefa)
    ).all()

    return [
        {str(tarefa.id): tarefa.titulo}
        for tarefa in lista_tarefas
    ]

@APP.get("/tarefas/{id_tarefa}")
def tarefa_especifica(
    id_tarefa: int,
    session: SessionDependency,
) -> Tarefa:
    """Retorna uma tarefa pelo identificador."""

    tarefa = session.get(Tarefa, id_tarefa)

    if tarefa is None:
        raise HTTPException(
            status_code=404,
            detail="Tarefa não existe",
        )

    return tarefa

# ---------------------------------------------------------------------------
# ROTAS — CRIAÇÃO DE TAREFAS
# ---------------------------------------------------------------------------

@APP.post("/tarefas", status_code=201)
def post_tarefa(
    session: SessionDependency,
    titulo: str,
    descricao: str | None = None,
) -> dict[str, str]:
    """Cria uma tarefa."""

    tarefa = Tarefa(
        titulo=titulo,
        descricao=descricao,
        data_criacao=datetime.now(FUSO_HORARIO).replace(
            microsecond=0
        ),
    )

    session.add(tarefa)
    session.commit()
    session.refresh(tarefa)

    LOGGER.info(
        "Tarefa criada: id=%s",
        tarefa.id,
    )

    LOGGER.debug(
        "Dados da tarefa criada: "
        "id=%s titulo=%r descricao=%r data_criacao=%s",
        tarefa.id,
        tarefa.titulo,
        tarefa.descricao,
        tarefa.data_criacao,
    )

    return {"mensagem": "OK"}


# ---------------------------------------------------------------------------
# ROTAS — ATUALIZAÇÃO DE TAREFAS
# ---------------------------------------------------------------------------

@APP.put("/tarefas/{id_tarefa}")
def concluir_tarefa(
    id_tarefa: int,
    session: SessionDependency,
) -> dict[str, str]:
    """Conclui uma tarefa e solicita o envio de uma notificação."""

    tarefa = session.get(Tarefa, id_tarefa)

    if tarefa is None:
        raise HTTPException(
            status_code=404,
            detail="Tarefa não existe",
        )

    if not tarefa.concluida:
        solicitar_notificacao(
            id_tarefa=id_tarefa,
            titulo=tarefa.titulo,
        )

        tarefa.finalizar()

        session.add(tarefa)
        session.commit()

    return {"mensagem": "Tarefa atualizada"}


# ---------------------------------------------------------------------------
# ROTAS — EXCLUSÃO DE TAREFAS
# ---------------------------------------------------------------------------

@APP.delete("/tarefas/{id_tarefa}")
def apagar_tarefa(
    id_tarefa: int,
    session: SessionDependency,
) -> dict[str, str]:
    """Exclui uma tarefa pelo identificador."""

    tarefa = session.get(Tarefa, id_tarefa)

    if tarefa is None:
        raise HTTPException(
            status_code=404,
            detail="Tarefa não existe",
        )

    session.delete(tarefa)
    session.commit()

    return {"mensagem": "Tarefa apagada"}
