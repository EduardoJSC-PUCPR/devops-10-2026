"""API de gerenciamento de tarefas e envio de notificações."""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated

import requests
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.engine import URL
from sqlmodel import Session, SQLModel, create_engine, select

from .log import LOGGER
from .modelo import Tarefa

# ---------------------------------------------------------------- banco

DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_ADDRESS = os.getenv("DATABASE_ADDRESS")
DATABASE = os.getenv("DATABASE")

database_settings = {
    "DATABASE_USERNAME": DATABASE_USERNAME,
    "DATABASE_PASSWORD": DATABASE_PASSWORD,
    "DATABASE_ADDRESS": DATABASE_ADDRESS,
    "DATABASE": DATABASE,
}
missing_settings = [
    name for name, value in database_settings.items() if not value
]
for name in missing_settings:
    LOGGER.critical("%s está faltando", name)
if missing_settings:
    raise RuntimeError(
        "Variáveis de ambiente do PostgreSQL não configuradas: "
        + ", ".join(missing_settings)
    )

ENGINE = create_engine(
    URL.create(
        "postgresql+psycopg",
        username=DATABASE_USERNAME,
        password=DATABASE_PASSWORD,
        host=DATABASE_ADDRESS,
        database=DATABASE,
    )
)
SERVICO_NOTIFICACAO_URL = "http://localhost:8000/notificar"


def get_session():
    """Fornece uma sessão do banco para uma requisição."""
    with Session(ENGINE) as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Cria as tabelas antes de atender requisições."""
    SQLModel.metadata.create_all(ENGINE)
    yield


APP = FastAPI(title="ServicoTarefa", lifespan=lifespan)


@APP.middleware("http")
async def registrar_acessos(request: Request, call_next):
    """Registra acessos às rotas e erros de caminhos inexistentes."""
    resposta = await call_next(request)

    if resposta.status_code == 404 and request.scope.get("route") is None:
        LOGGER.error(
            "Rota inexistente: %s %s", request.method, request.url.path
        )
    else:
        LOGGER.info(
            "Acesso: %s %s -> %s",
            request.method,
            request.url.path,
            resposta.status_code,
        )
    return resposta


# GET /tarefas: lista todas as tarefas (objeto completo)
@APP.get("/tarefas")
def tarefas(session: SessionDependency) -> list[dict[str, str]]:
    """Lista todas as tarefas."""
    lista_tarefas = session.exec(select(Tarefa)).all()

    return [{str(tarefa.id): tarefa.titulo} for tarefa in lista_tarefas]


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
        data_criacao=datetime.now(timezone(timedelta(hours=-3))).replace(microsecond=0),
    )
    session.add(tarefa)
    session.commit()
    session.refresh(tarefa)

    LOGGER.info("Tarefa criada: id=%s", tarefa.id)
    LOGGER.debug(
        "Dados da tarefa criada: id=%s titulo=%r descricao=%r data_criacao=%s",
        tarefa.id,
        tarefa.titulo,
        tarefa.descricao,
        tarefa.data_criacao,
    )
    return {"mensagem": "OK"}


@APP.get("/tarefas/{id_tarefa}")
def tarefa_especifica(id_tarefa: int, session: SessionDependency) -> Tarefa:
    """Retorna uma tarefa pelo identificador."""
    tarefa = session.get(Tarefa, id_tarefa)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Tarefa não existe")
    return tarefa


@APP.put("/tarefas/{id_tarefa}")
def concluir_tarefa(
    id_tarefa: int,
    session: SessionDependency,
) -> dict[str, str]:
    """Conclui uma tarefa e solicita o envio de uma notificação."""
    tarefa = session.get(Tarefa, id_tarefa)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Tarefa não existe")

    if not tarefa.concluida:
        try:
            resposta = requests.post(
                SERVICO_NOTIFICACAO_URL,
                params={
                    "id": id_tarefa,
                    "titulo": tarefa.titulo,
                },
                timeout=1,
            )
            resposta.raise_for_status()
        except requests.RequestException as erro:
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao comunicar com o ServiçoNotificacao: {erro}",
            ) from erro

        tarefa.finalizar()
        session.add(tarefa)
        session.commit()

    return {"mensagem": "Tarefa atualizada"}


@APP.delete("/tarefas/{id_tarefa}")
def apagar_tarefa(
    id_tarefa: int,
    session: SessionDependency,
) -> dict[str, str]:
    """Exclui uma tarefa pelo identificador."""
    tarefa = session.get(Tarefa, id_tarefa)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Tarefa não existe")
    session.delete(tarefa)
    session.commit()
    return {"mensagem": "Tarefa apagada"}


@APP.get("/")
async def index() -> dict[str, str]:
    """Retorna a mensagem inicial da API."""
    return {"mensagem": "Olá, mundo!"}


@APP.get("/autor")
async def autor() -> dict[str, str]:
    """Retorna o nome completo do autor da API."""
    return {"mensagem": "Eduardo José Skura Czerniak"}
