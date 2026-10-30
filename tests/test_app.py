import app
import pytest
import requests
from fastapi.testclient import TestClient

CLIENT = TestClient(app.APP)


@pytest.fixture(autouse=True)
def reset_tarefas():
    app.TAREFAS.clear()
    app.PROXIMO_ID = 0
    yield
    app.TAREFAS.clear()
    app.PROXIMO_ID = 0


def test_index():
    resposta = CLIENT.get("/")
    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "Olá, mundo!"}


def test_listar_tarefas():
    CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )

    resposta = CLIENT.get("/tarefas")

    assert resposta.status_code == 200
    assert resposta.json() == [{"0": "Estudar"}]


def test_criar_tarefa():
    resposta = CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "OK"}
    assert len(app.TAREFAS) == 1
    assert app.TAREFAS[0]["titulo"] == "Estudar"
    assert app.TAREFAS[0]["descricao"] == "Revisar testes"
    assert app.TAREFAS[0]["concluida"] is False
    assert app.TAREFAS[0]["concluida_em"] is None


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

    monkeypatch.setattr(app.requests, "post", enviar_notificacao)

    resposta = CLIENT.put("/tarefas/0")

    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "Tarefa atualizada"}
    assert app.TAREFAS[0]["concluida"] is True
    assert app.TAREFAS[0]["concluida_em"] is not None
    assert requisicao_notificacao == {
        "url": app.SERVICO_NOTIFICACAO_URL,
        "params": {"id": 0, "titulo": "Estudar"},
        "timeout": 10,
    }


def test_obter_tarefa():
    CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )

    resposta = CLIENT.get("/tarefas/0")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == 0
    assert resposta.json()["titulo"] == "Estudar"
    assert resposta.json()["descricao"] == "Revisar testes"
    assert resposta.json()["concluida"] is False
    assert resposta.json()["concluida_em"] is None


def test_excluir_tarefa():
    CLIENT.post(
        "/tarefas",
        params={"titulo": "Estudar", "descricao": "Revisar testes"},
    )

    resposta = CLIENT.delete("/tarefas/0")

    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "Tarefa apagada"}
    assert app.TAREFAS == []


def test_id_inexistente():
    assert CLIENT.get("/tarefas/999").status_code == 404
    assert CLIENT.put("/tarefas/999").status_code == 404
    assert CLIENT.delete("/tarefas/999").status_code == 404


def test_notificacao_fora_do_ar(monkeypatch):
    def falhar(*args, **kwargs):
        raise requests.ConnectionError("serviço fora do ar")

    monkeypatch.setattr(app.requests, "post", falhar)

    CLIENT.post(
        "/tarefas",
        params={"titulo": "Teste", "descricao": "x"},
    )

    resposta = CLIENT.put("/tarefas/0")

    assert resposta.status_code == 502
    assert app.TAREFAS[0]["concluida"] is False
    assert app.TAREFAS[0]["concluida_em"] is None