# Importações:
from datetime import datetime
import requests # HTTP API REST
from fastapi import FastAPI, HTTPException

# ============================================================

# Configuração e Memória do Programa:
# MAIUSCULO, Global, Fixo
APP = FastAPI(title="ServicoTarefa")
TAREFAS = []
PROXIMO_ID = 0
# Serviço Separado para Notificações
SERVICO_NOTIFICACAO_URL = "http://localhost:8000/notificar"

# ============================================================

# Funções Auxiliares:
# Define Função para ser Chamado
# Pega Parâmetros (Título, Descrição)
# Retorna Dicionário (Conjunto de Chave: Valor)
def criar_tarefa(titulo: str, descricao: str) -> dict:
    global PROXIMO_ID # Chama ID Global

    # Dicionário/Estrutura da Tarefa da Array TAREFAS
    tarefa = {
        "id": PROXIMO_ID,            # ID Global
        "titulo": titulo,            # Parâmetro
        "descricao": descricao,      # Parâmetro
        "concluida": False,          # Flag
        "criada_em": datetime.now(), # Timestamp 
        "concluida_em": None,        # Timestamp 
    }
    PROXIMO_ID += 1 # Incrementa ID Global para Próxima Tarefa
    return tarefa   # Envia Estrutura para Função Chamadora

# ============================================================

# Rotas
# @ - Decorador para Endereço URL, Verbo HTTP, ID Endpoint, Parâmetros Padrão
# async - ASSÍNCRONO, Resposta Rápida, Não Bloqueia Servidor, Conexões Simultâneas
# list[dict[,]] - Lista de Dicionários, Chave: Valor
# return [{:} for in] - Retorna Lista de Dicionários, Cada Tarefa com ID e Título

@APP.get("/tarefas")
async def tarefas() -> list[dict[int, str]]:
    return [{tarefa["id"]: tarefa["titulo"]} for tarefa in TAREFAS]


@APP.post("/tarefas")
async def post_tarefa(titulo: str, descricao: str) -> dict[str, str]:
    TAREFAS.append(criar_tarefa(titulo, descricao))
    return {"mensagem": "OK"}


@APP.get("/tarefas/{id}")
async def tarefa_especifica(id: int) -> dict:
    for tarefa in TAREFAS:
        if tarefa["id"] == id:
            return tarefa
    raise HTTPException(status_code=404, detail="Tarefa não existe")


@APP.put("/tarefas/{id}")
def concluir_tarefa(id: int) -> dict[str, str]:
    tarefa_encontrada = next(
        (tarefa for tarefa in TAREFAS if tarefa["id"] == id),
        None,
    )
    if tarefa_encontrada is None:
        raise HTTPException(status_code=404, detail="Tarefa não existe")

    if not tarefa_encontrada["concluida"]:
        try:
            resposta = requests.post(
                SERVICO_NOTIFICACAO_URL,
                params={
                    "id": id,
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
async def apagar_tarefa(id: int) -> dict[str, str]:
    for indice, tarefa in enumerate(TAREFAS):
        if tarefa["id"] == id:
            del TAREFAS[indice]
            return {"mensagem": "Tarefa apagada"}
    raise HTTPException(status_code=404, detail="Tarefa não existe")


@APP.get("/")
async def index() -> dict[str, str]:
    return {"mensagem": "Olá, mundo!"}
