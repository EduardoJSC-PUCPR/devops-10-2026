import logging
from datetime import datetime

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import api
from app.log import LOGGER

CLIENT = TestClient(api.APP)


def test_timestamp_dos_logs_usa_utc_menos_tres():
    registro = logging.LogRecord(
        name="devops",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="teste",
        args=(),
        exc_info=None,
    )
    registro.created = 0
    formatador = LOGGER.handlers[0].formatter

    assert formatador is not None
    assert "1969-12-31 21:00:00 -03:00" in formatador.format(registro)


@pytest.fixture(autouse=True)
def reset_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_test_session():
        with Session(engine) as session:
            yield session

    api.APP.dependency_overrides[api.get_session] = get_test_session
    yield
    api.APP.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def test_index():
    resposta = CLIENT.get("/")
    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "Olá, mundo!"}


def test_engine_usa_postgresql_com_psycopg():
    assert api.ENGINE.url.drivername == "postgresql+psycopg"


def test_listar_tarefas():
    CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )

    resposta = CLIENT.get("/tarefas")

    assert resposta.status_code == 200
    assert resposta.json() == [{"1": "Estudar"}]


def test_listar_tarefas_vazia():
    resposta = CLIENT.get("/tarefas")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_criar_tarefa():
    resposta = CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )

    assert resposta.status_code == 201
    assert resposta.json() == {"mensagem": "OK"}
    tarefa = CLIENT.get("/tarefas/1").json()
    assert tarefa["titulo"] == "Estudar"
    assert tarefa["descricao"] == "Revisar testes"
    assert tarefa["concluida"] is False
    assert tarefa["data_conclusao"] is None
    assert datetime.fromisoformat(tarefa["data_criacao"]).microsecond == 0


def test_criar_tarefa_sem_descricao():
    resposta = CLIENT.post("/tarefas", params={"titulo": "Estudar"})

    assert resposta.status_code == 201
    assert CLIENT.get("/tarefas/1").json()["descricao"] is None


def test_criar_tarefa_registra_info_e_debug(caplog):
    with caplog.at_level(logging.DEBUG, logger="devops"):
        resposta = CLIENT.post(
            "/tarefas",
            params={"titulo": "Estudar", "descricao": "Revisar testes"},
        )

    assert resposta.status_code == 201
    mensagens = [registro.getMessage() for registro in caplog.records]
    assert "Tarefa criada: id=1" in mensagens
    assert "Acesso: POST /tarefas -> 201" in mensagens
    assert any(
        registro.levelno == logging.DEBUG
        and "Dados da tarefa criada: id=1 titulo='Estudar'" in registro.getMessage()
        for registro in caplog.records
    )


def test_registra_rota_inexistente_com_error_e_id_inexistente_com_info(caplog):
    with caplog.at_level(logging.DEBUG, logger="devops"):
        rota_inexistente = CLIENT.get("/nao-existe")
        tarefa_inexistente = CLIENT.get("/tarefas/999")

    assert rota_inexistente.status_code == 404
    assert tarefa_inexistente.status_code == 404
    assert any(
        registro.levelno == logging.ERROR
        and registro.getMessage() == "Rota inexistente: GET /nao-existe"
        for registro in caplog.records
    )
    assert any(
        registro.levelno == logging.INFO
        and registro.getMessage() == "Acesso: GET /tarefas/999 -> 404"
        for registro in caplog.records
    )


def test_obter_tarefa():
    CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )

    resposta = CLIENT.get("/tarefas/1")

    assert resposta.status_code == 200
    tarefa = resposta.json()
    assert tarefa["id"] == 1
    assert tarefa["titulo"] == "Estudar"
    assert tarefa["descricao"] == "Revisar testes"
    assert tarefa["concluida"] is False
    assert datetime.fromisoformat(tarefa["data_criacao"]).microsecond == 0
    assert tarefa["data_conclusao"] is None


def test_concluir_tarefa(monkeypatch):
    CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )
    requisicao_notificacao = {}

    class RespostaNotificacao:
        def raise_for_status(self):
            return None

    def enviar_notificacao(url, *, params, timeout):
        requisicao_notificacao["url"] = url
        requisicao_notificacao["params"] = params
        requisicao_notificacao["timeout"] = timeout
        return RespostaNotificacao()

    monkeypatch.setattr(api.requests, "post", enviar_notificacao)

    resposta = CLIENT.put("/tarefas/1")

    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "Tarefa atualizada"}
    resposta_tarefa = CLIENT.get("/tarefas/1")
    assert resposta_tarefa.json()["concluida"] is True
    assert isinstance(
        datetime.fromisoformat(resposta_tarefa.json()["data_conclusao"]),
        datetime,
    )
    assert requisicao_notificacao == {
        "url": api.SERVICO_NOTIFICACAO_URL,
        "params": {"id": 1, "titulo": "Estudar"},
        "timeout": 1,
    }


def test_excluir_tarefa():
    CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )

    resposta = CLIENT.delete("/tarefas/1")

    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "Tarefa apagada"}
    assert CLIENT.get("/tarefas").json() == []


def test_id_inexistente():
    obter = CLIENT.get("/tarefas/999")
    concluir = CLIENT.put("/tarefas/999")
    excluir = CLIENT.delete("/tarefas/999")

    assert obter.status_code == 404
    assert obter.json() == {"detail": "Tarefa não existe"}
    assert concluir.status_code == 404
    assert concluir.json() == {"detail": "Tarefa não existe"}
    assert excluir.status_code == 404
    assert excluir.json() == {"detail": "Tarefa não existe"}


def test_notificacao_fora_do_ar(monkeypatch):
    def falhar(*args, **kwargs):
        raise requests.ConnectionError("serviço fora do ar")

    monkeypatch.setattr(api.requests, "post", falhar)

    CLIENT.post(
        "/tarefas",
        params={"titulo": "Teste", "descricao": "x"},
    )

    resposta = CLIENT.put("/tarefas/1")

    assert resposta.status_code == 502
    tarefa = CLIENT.get("/tarefas/1").json()
    assert tarefa["concluida"] is False
    assert tarefa["data_conclusao"] is None


def test_autor():
    resposta = CLIENT.get("/autor")

    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "Eduardo José Skura Czerniak"}