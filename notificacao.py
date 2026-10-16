from fastapi import FastAPI


NOTIFICACAO = FastAPI(title="ServicoNotificacao")


@NOTIFICACAO.post("/notificar")
async def notificar(id: int, titulo: str) -> dict[str, str]:
    print(f"Tarefa '{titulo}' (id={id}) finalizada!", flush=True)
    return {"mensagem": "OK"}


@NOTIFICACAO.get("/")
async def index() -> dict[str, str]:
    return {"mensagem": "ServicoNotificacao ativo"}
