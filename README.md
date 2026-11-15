# Lista de Tarefas

## Descrição

API REST desenvolvida com FastAPI para criação, consulta, atualização e exclusão
de tarefas. O projeto utiliza PostgreSQL para persistência dos dados e possui
uma pipeline de CI/CD configurada com GitHub Actions.

## Tecnologias utilizadas

- Python
- FastAPI e Uvicorn
- SQLModel e SQLAlchemy
- PostgreSQL e Psycopg 3
- Requests
- pytest e pytest-cov
- Pylint, Ruff e Bandit
- Docker e Docker Hub
- GitHub Actions
- Render
- Nginx
- Kubernetes

## Execução local

Os comandos abaixo iniciam um PostgreSQL local em Docker e a API diretamente na
porta `8000`.

### 1. Inicie o PostgreSQL

```bash
docker run -d \
  --name postgres-tarefas \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=devops \
  -e POSTGRES_USER=devops \
  -p 5432:5432 \
  postgres:17
```

O container precisa estar em execução e pronto para aceitar conexões antes de
iniciar a API.

### 2. Configure as variáveis de ambiente

```bash
export DATABASE_ADDRESS=localhost
export DATABASE_PASSWORD=password
export DATABASE=devops
export DATABASE_USERNAME=devops
```

### 3. Instale as dependências e inicie a API

Na raiz do repositório:

```bash
python -m pip install -r requirements.txt
fastapi run app/api.py --port 8000
```

A documentação interativa da API estará disponível em
[http://localhost:8000/docs](http://localhost:8000/docs).

## Rotas principais

| Método | Caminho | Ação |
| --- | --- | --- |
| `GET` | `/tarefas` | Lista as tarefas. |
| `GET` | `/tarefas/{id_tarefa}` | Consulta uma tarefa. |
| `POST` | `/tarefas?titulo=...` | Cria uma tarefa; a descrição é opcional. |
| `PUT` | `/tarefas/{id_tarefa}` | Conclui uma tarefa. |
| `DELETE` | `/tarefas/{id_tarefa}` | Exclui uma tarefa. |

Também existem as rotas `GET /` e `GET /autor`.

## Notificações

Ao concluir uma tarefa, a API envia uma requisição para
`http://localhost:8000/notificar`. No fluxo completo usado no projeto, o Nginx
recebe essa chamada e a encaminha ao ServiçoNotificacao na porta `8002`, enquanto
encaminha as requisições de tarefas ao ServiçoTarefa na porta `8001`. Para
executar esse fluxo completo localmente, inicie os dois serviços e configure o
Nginx com `default.conf`; nesse arranjo, o proxy usa a porta `8000`.

Se estiver executando somente a API na porta `8000`, a documentação e as rotas
da API estarão disponíveis, mas a conclusão de uma tarefa não conseguirá
alcançar o ServiçoNotificacao. O `localhost` configurado no código é voltado
para o fluxo local com Nginx; em containers ou em outro ambiente, o endereço do
serviço deve corresponder à rede de deploy.

## Testes

Os testes usam um banco SQLite isolado e substituem a chamada ao serviço de
notificações. Para executá-los, defina valores de ambiente de teste porque a
configuração do banco é verificada quando a API é importada:

```bash
DATABASE_USERNAME=mock \
DATABASE_PASSWORD=mock \
DATABASE_ADDRESS=localhost \
DATABASE=mock \
pytest
```

## CI/CD

O workflow do GitHub Actions instala as dependências, executa Pylint e Pytest,
publica a imagem da aplicação no Docker Hub e aciona o deploy no Render. As
credenciais do Docker Hub e o deploy hook do Render são configurados como
variáveis e secrets do repositório GitHub.
