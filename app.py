from fastapi import FastAPI
from datetime import datetime

APP = FastAPI()
TAREFAS = []

# Estrutura da tarefa
"""
{
    "id" -> int,
    "titulo" -> str,
    "descricao" -> str,
    "concluida" -> bool,
    "criada_em" -> datetime
}
"""

def criar_tarefa(titulo, descricao):
    return {
        "id": len(TAREFAS),
        "titulo": titulo,
        "descricao": descricao,
        "concluida": False,
        "criada_em": datetime.now()
    }

@APP.get("/tarefas")
async def tarefas():
    return TAREFAS

@APP.post("/tarefas")
async def post_tarefa(titulo: str, descricao: str):
    global TAREFAS

    tarefa_nova = criar_tarefa(titulo, descricao)

    TAREFAS.append(tarefa_nova)

    return {"mensagem": "OK"}

@APP.get("/")
async def index():
    return {"mensagem": "Olá, mundo!"}