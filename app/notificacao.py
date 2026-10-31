"""Serviço de notificações de tarefas."""

from fastapi import FastAPI, Query

NOTIFICACAO = FastAPI(title="ServicoNotificacao")

@NOTIFICACAO.post("/notificar")
async def notificar(titulo: str, id_tarefa: int = Query(alias="id")) -> dict[str, str]:
    """Registra a conclusão de uma tarefa."""
    print(f"Tarefa '{titulo}' (id={id_tarefa}) finalizada!", flush=True)
    return {"mensagem": "OK"}


@NOTIFICACAO.get("/")
async def index() -> dict[str, str]:
    """Informa que o serviço está ativo."""
    return {"mensagem": "ServicoNotificacao ativo"}
