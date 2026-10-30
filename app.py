"""API de gerenciamento de tarefas e envio de notificações."""

from datetime import datetime

import requests
from fastapi import FastAPI, HTTPException, Path

APP = FastAPI(title="ServicoTarefa")
TAREFAS = []
APP.state.proximo_id = 0
SERVICO_NOTIFICACAO_URL = "http://localhost:8000/notificar"


def criar_tarefa(titulo: str, descricao: str) -> dict:
    """Cria uma tarefa com identificador e timestamps."""
    tarefa_id = APP.state.proximo_id

    tarefa = {
        "id": tarefa_id,
        "titulo": titulo,
        "descricao": descricao,
        "concluida": False,
        "criada_em": datetime.now(),
        "concluida_em": None,
    }
    APP.state.proximo_id += 1
    return tarefa


@APP.get("/tarefas")
async def tarefas() -> list[dict[int, str]]:
    """Lista as tarefas pelo identificador e título."""
    return [{tarefa["id"]: tarefa["titulo"]} for tarefa in TAREFAS]


@APP.post("/tarefas")
async def post_tarefa(titulo: str, descricao: str) -> dict[str, str]:
    """Cria uma tarefa."""
    TAREFAS.append(criar_tarefa(titulo, descricao))
    return {"mensagem": "OK"}


@APP.get("/tarefas/{id}")
async def tarefa_especifica(tarefa_id: int = Path(alias="id")) -> dict:
    """Retorna uma tarefa pelo identificador."""
    for tarefa in TAREFAS:
        if tarefa["id"] == tarefa_id:
            return tarefa
    raise HTTPException(status_code=404, detail="Tarefa não existe")


@APP.put("/tarefas/{id}")
def concluir_tarefa(tarefa_id: int = Path(alias="id")) -> dict[str, str]:
    """Conclui uma tarefa e solicita o envio de uma notificação."""
    tarefa_encontrada = next(
        (tarefa for tarefa in TAREFAS if tarefa["id"] == tarefa_id),
        None,
    )
    if tarefa_encontrada is None:
        raise HTTPException(status_code=404, detail="Tarefa não existe")

    if not tarefa_encontrada["concluida"]:
        try:
            resposta = requests.post(
                SERVICO_NOTIFICACAO_URL,
                params={
                    "id": tarefa_id,
                    "titulo": tarefa_encontrada["titulo"],
                },
                timeout=10,
            )
            resposta.raise_for_status()
        except requests.RequestException as erro:
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao comunicar com o ServiçoNotificacao: {erro}",
            ) from erro

        tarefa_encontrada["concluida"] = True
        tarefa_encontrada["concluida_em"] = datetime.now()

    return {"mensagem": "Tarefa atualizada"}


@APP.delete("/tarefas/{id}")
async def apagar_tarefa(tarefa_id: int = Path(alias="id")) -> dict[str, str]:
    """Exclui uma tarefa pelo identificador."""
    for indice, tarefa in enumerate(TAREFAS):
        if tarefa["id"] == tarefa_id:
            del TAREFAS[indice]
            return {"mensagem": "Tarefa apagada"}
    raise HTTPException(status_code=404, detail="Tarefa não existe")


@APP.get("/")
async def index() -> dict[str, str]:
    """Retorna a mensagem inicial da API."""
    return {"mensagem": "Olá, mundo!"}
