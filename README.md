# devops-10-2026

## Arquitetura

- O cliente cURL acessa o Nginx na porta `8000`.
- O Nginx encaminha `/tarefas` para o ServiçoTarefa (`app.py`) na porta `8001`.
- O Nginx encaminha `/notificar` para o ServiçoNotificacao (`notificacao.py`) na porta `8002`.
- Ao concluir uma tarefa, o ServiçoTarefa chama `http://localhost:8000/notificar`; o Nginx encaminha essa chamada para a porta `8002`. A mensagem aparece no terminal do ServiçoNotificacao.

## Executar localmente

Instale as dependências:

```bash
pip install -r requirements.txt
```

Inicie cada serviço em um terminal separado:

```bash
fastapi dev --port 8001 app.py
```

```bash
fastapi dev --port 8002 notificacao.py
```

Copie a configuração do Nginx, valide-a e reinicie o serviço:

```bash
sudo cp default.conf /etc/nginx/conf.d/default.conf
sudo nginx -t
sudo service nginx restart
service nginx status
```

O Nginx fica disponível em `http://localhost:8000`. Confirme o proxy para os dois serviços:

```bash
curl "http://localhost:8000/tarefas"
curl -X POST "http://localhost:8000/notificar?id=1&titulo=Teste"
```

Se `/tarefas` retornar `502 Bad Gateway`, verifique se o ServiçoTarefa está rodando na porta `8001`. Para conferir os processos nas portas usadas:

```bash
sudo ss -ltnp | grep -E ':(8000|8001|8002)\b'
```

O Nginx precisa estar na porta `8000`, o ServiçoTarefa na `8001` e o ServiçoNotificacao na `8002`.

## Exemplos cURL

```bash
# Criar tarefa
curl -X POST "http://localhost:8000/tarefas?titulo=Estudar&descricao=Revisar%20microservicos"

# Listar tarefas
curl "http://localhost:8000/tarefas"

# Consultar tarefa
curl "http://localhost:8000/tarefas/0"

# Concluir tarefa; a notificação aparece no terminal do ServiçoNotificacao
curl -X PUT "http://localhost:8000/tarefas/0"

# Excluir tarefa
curl -X DELETE "http://localhost:8000/tarefas/0"
```
