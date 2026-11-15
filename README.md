# API de Gerenciamento de Tarefas

Aplicação Python que disponibiliza operações HTTP para criar, consultar,
concluir e excluir tarefas. Os dados são armazenados em PostgreSQL, e a
conclusão de uma tarefa solicita uma notificação a um serviço separado.

## Arquitetura e stack

### Stack da aplicação

| Camada | Tecnologia | Papel neste projeto |
| --- | --- | --- |
| Linguagem | Python | Implementa a API, os serviços e o acesso a dados. |
| Framework web | FastAPI | Define as aplicações HTTP, rotas, dependências e respostas. |
| Runtime ASGI | Uvicorn | Executa as aplicações ASGI; o comando `fastapi run` inicia a aplicação usando esse runtime. |
| Banco de dados | PostgreSQL | Persiste as tarefas. |
| ORM e modelagem | SQLModel + SQLAlchemy | Representam as tabelas e executam consultas e transações. |
| Driver do banco | Psycopg 3 | Faz a comunicação entre Python e PostgreSQL. |
| Cliente HTTP | Requests | Chama o serviço de notificações quando uma tarefa é concluída. |
| Logs | `logging` da biblioteca padrão | Registra acessos, erros e eventos da aplicação. |
| Configuração | Variáveis de ambiente | Fornece as credenciais e o endereço do PostgreSQL ao processo. |
| Domínio | Modelo `Tarefa` | Representa uma tarefa e seus dados de conclusão. |

### Infraestrutura e execução

O repositório também contém:

- **Nginx**, configurado em `default.conf` como proxy reverso local na porta
  `8000`.
- **Docker**, com uma imagem definida em `Dockerfile` para executar o ServiçoTarefa
  na porta `8001`.
- **Kubernetes**, com `pod.yaml`, que descreve um Pod para o ServiçoTarefa e um
  Service de acesso. O manifesto espera que o serviço de banco chamado
  `svc-banco` exista no cluster.
- **GitHub Actions**, que instala dependências, executa Pylint e Pytest, publica
  a imagem no Docker Hub e aciona um deploy no Render por meio de um deploy hook.

O deploy hook do workflow não configura sozinho o serviço do Render: o serviço,
o hook e suas variáveis de ambiente precisam estar configurados na plataforma.
Não há um `render.yaml` neste repositório.

### Fluxo local com Nginx

```text
Cliente --HTTP--> Nginx :8000 --/tarefas--> ServiçoTarefa :8001
                         ^                         |
                         |                         +--SQL--> PostgreSQL
                         +--/notificar-- ServiçoNotificacao :8002
                              (chamada feita pelo ServiçoTarefa)
```

O Nginx encaminha `/tarefas` para o ServiçoTarefa e `/notificar` para o
ServiçoNotificacao. Ao concluir uma tarefa, o ServiçoTarefa faz um `POST` para
`http://localhost:8000/notificar`; no arranjo local, essa chamada passa pelo
Nginx e chega ao serviço de notificações.

Esse endereço `localhost` é específico dessa topologia local. Em containers ou
em um cluster, `localhost` se refere ao próprio container/Pod, não a outro
serviço. Nesses ambientes, o endereço do serviço de notificação precisa
corresponder à rede e à configuração do deploy. O `Dockerfile` deste repositório
inicia somente o ServiçoTarefa; ele não inicia Nginx nem o ServiçoNotificacao.

## Modelo de domínio

O modelo `Tarefa`, definido em `app/modelo.py`, representa a tabela de tarefas:

- `id`: identificador gerado pelo banco;
- `titulo`: título obrigatório;
- `descricao`: descrição opcional;
- `concluida`: indica se a tarefa foi concluída;
- `data_criacao`: data e hora de criação;
- `data_conclusao`: data e hora da conclusão, quando concluída.

Na inicialização da API, o ciclo de vida do FastAPI chama
`SQLModel.metadata.create_all(ENGINE)` para criar as tabelas dos modelos
registrados caso ainda não existam. Isso não substitui migrações para alterações
evolutivas de esquema em produção.

## Rotas da API

Os parâmetros escalares `titulo` e `descricao` da criação são enviados como
parâmetros de query, por exemplo `?titulo=Estudar`.

| Método | Caminho | Comportamento |
| --- | --- | --- |
| `GET` | `/` | Retorna uma mensagem inicial. |
| `GET` | `/autor` | Retorna o nome do autor. |
| `GET` | `/tarefas` | Lista os identificadores e títulos das tarefas. |
| `GET` | `/tarefas/{id_tarefa}` | Consulta uma tarefa pelo identificador. |
| `POST` | `/tarefas?titulo=...` | Cria uma tarefa; `descricao` é opcional. |
| `PUT` | `/tarefas/{id_tarefa}` | Conclui a tarefa e solicita uma notificação. |
| `DELETE` | `/tarefas/{id_tarefa}` | Exclui a tarefa. |
| `POST` | `/notificar?id=...&titulo=...` | Rota do ServiçoNotificacao. |

As aplicações FastAPI disponibilizam documentação OpenAPI interativa em
`/docs` quando acessadas diretamente. A configuração atual do Nginx encaminha
somente `/tarefas` e `/notificar`; portanto, as outras rotas e a documentação
devem ser acessadas diretamente nas portas dos serviços ou por um proxy
configurado para encaminhá-las.

## Executar localmente

### 1. Instalar dependências

Use Python 3.14, conforme a imagem Docker e o workflow de CI:

```bash
python -m pip install -r requirements.txt
```

### 2. Configurar o PostgreSQL

Defina as variáveis de ambiente no mesmo ambiente em que a API será executada:

```bash
export DATABASE_USERNAME="seu_usuario"
export DATABASE_PASSWORD="sua_senha"
export DATABASE_ADDRESS="localhost"
export DATABASE="nome_do_banco"
```

`DATABASE_ADDRESS` é o host do PostgreSQL; o código usa a porta padrão do
PostgreSQL (`5432`). O banco precisa existir e estar acessível. A aplicação
encerra a inicialização se alguma dessas variáveis estiver ausente.

No Render, configure essas variáveis nas configurações do serviço. Em Docker,
Kubernetes ou outra plataforma, forneça-as ao container/Pod por meio do
mecanismo de configuração correspondente. Não coloque credenciais reais no
código nem em arquivos versionados.

### 3. Iniciar os serviços

Inicie cada serviço em um terminal separado:

```bash
fastapi dev --port 8001 app/api.py
```

```bash
fastapi dev --port 8002 app/notificacao.py
```

### 4. Iniciar o Nginx local

Instale ou disponibilize o Nginx e configure o arquivo do projeto:

```bash
sudo cp default.conf /etc/nginx/conf.d/default.conf
sudo nginx -t
sudo service nginx restart
service nginx status
```

O proxy local atende em `http://localhost:8000`. Teste os encaminhamentos:

```bash
curl "http://localhost:8000/tarefas"
curl -X POST "http://localhost:8000/notificar?id=1&titulo=Teste"
```

O Nginx deve estar na porta `8000`, o ServiçoTarefa na `8001` e o
ServiçoNotificacao na `8002`.

## Exemplos cURL

Os exemplos abaixo usam o Nginx local em `http://localhost:8000`:

```bash
# Criar tarefa
curl -X POST "http://localhost:8000/tarefas?titulo=Estudar&descricao=Revisar%20microservicos"

# Listar tarefas
curl "http://localhost:8000/tarefas"

# Consultar tarefa
curl "http://localhost:8000/tarefas/1"

# Concluir tarefa; a notificação aparece no terminal do ServiçoNotificacao
curl -X PUT "http://localhost:8000/tarefas/1"

# Excluir tarefa
curl -X DELETE "http://localhost:8000/tarefas/1"
```

## Testes e qualidade

Os testes usam um banco SQLite isolado e substituem a chamada HTTP de
notificação; não precisam de um PostgreSQL nem do ServiçoNotificacao em
execução. Como a API valida as variáveis de banco ao ser importada, informe
valores de teste ao executar Pytest:

```bash
DATABASE_USERNAME=mock \
DATABASE_PASSWORD=mock \
DATABASE_ADDRESS=localhost \
DATABASE=mock \
pytest
```

Para executar o mesmo lint usado no workflow de CI:

```bash
pylint --source-roots=. app
```

O workflow do GitHub Actions também executa os testes e o lint em pushes e
pull requests para `main`.

Se uma rota retornar `502 Bad Gateway`, confira se o serviço de destino está
rodando na porta esperada. Para verificar as portas locais:

```bash
sudo ss -ltnp | grep -E ':(8000|8001|8002)\b'
```
