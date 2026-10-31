from datetime import datetime, timezone

from app.modelo import Tarefa


def test_nova_tarefa():
    criada_em = datetime.now(timezone.utc)
    tarefa = Tarefa(id=0, titulo="Tarefa teste", data_criacao=criada_em)

    assert tarefa.id == 0
    assert tarefa.titulo == "Tarefa teste"
    assert tarefa.descricao is None
    assert tarefa.data_criacao == criada_em
    assert tarefa.data_conclusao is None
    assert tarefa.concluida is False


def test_finalizar_tarefa():
    tarefa = Tarefa(
        id=0,
        titulo="Tarefa teste",
        data_criacao=datetime.now(timezone.utc),
    )
    inicio = datetime.now(timezone.utc)

    tarefa.finalizar()

    fim = datetime.now(timezone.utc)
    assert tarefa.concluida is True
    assert tarefa.data_conclusao is not None
    assert inicio <= tarefa.data_conclusao <= fim
