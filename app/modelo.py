"""Modelos da aplicação de tarefas."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Tarefa(SQLModel, table=True):
    """Representa uma tarefa e seu estado de conclusão."""

    id: int | None = Field(default=None, primary_key=True)
    titulo: str
    descricao: str | None = None
    concluida: bool = False
    data_criacao: datetime
    data_conclusao: datetime | None = None

    def finalizar(self):
        """Marca a tarefa como concluída."""
        self.concluida = True
        self.data_conclusao = datetime.now(timezone.utc)
