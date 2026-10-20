# Execução local

## Requisitos

Docker Engine/Desktop com Compose v2, Python 3.12 e Node.js 22.12 ou superior. Comandos partem da raiz do repositório. Os serviços são acessíveis apenas em loopback; não use este Compose como configuração de produção.

## Primeiro início

```sh
python scripts/configure_local.py
docker compose config --quiet
docker compose up --build -d
docker compose ps -a
docker compose logs --tail 100 api migrate db-bootstrap storage-init auth-mail
docker compose exec api python scripts/manage.py createsuperuser
npm ci
```

O configurador cria `.env` com valores aleatórios e não sobrescreve arquivo existente. As senhas geradas são seguras para interpolação em URLs. Ao usar senhas próprias, codifique caracteres reservados na URL. Não copie os placeholders de `.env.example` como segredos reais.

O primeiro build de MinIO compila a release oficial fixada em `infra/minio.Dockerfile` e pode levar alguns minutos. A distribuição comunitária passou a ser somente código-fonte; não dependemos de uma imagem antiga do Docker Hub. Este componente é somente o S3 de desenvolvimento. [Release e instruções oficiais](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z).

O bootstrap espera o PostgreSQL responder e cria `tavvo_app` sem `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION`, `BYPASSRLS` ou propriedade das tabelas. `migrate` usa o owner em um processo separado. A API e o worker recebem apenas a conexão de runtime. O bucket S3 permanece privado e imagens são servidas pela API. A ordem usa as condições de saúde e conclusão do Compose. [Documentação do Compose](https://docs.docker.com/compose/how-tos/startup-order).

`createsuperuser` solicita email, nome e senha no terminal; não há credencial administrativa padrão. Depois do login, configure TOTP e salve os códigos de recuperação antes de administrar restaurantes.

Em dois terminais separados:

```sh
npm run dev:admin
```

```sh
npm run dev:public
```

| Serviço | Endereço local |
| --- | --- |
| Painéis Tavvo/restaurante | http://localhost:5173 |
| Site público de referência | http://localhost:3000 |
| OpenAPI | http://localhost:8000/v1/schema/ |
| Documentação interativa | http://localhost:8000/v1/docs/ |
| Liveness / readiness do banco | http://localhost:8000/health/ e http://localhost:8000/ready/ |
| Mensagens de recuperação no Mailpit | http://localhost:8025 |
| Console local de armazenamento | http://localhost:9001 |

O Vite encaminha `/v1` para a API; o site público faz as leituras no servidor. Use o mesmo hostname (`localhost`) durante login, MFA e operações para manter cookies e CSRF consistentes. Credenciais de S3 e banco nunca são variáveis públicas do frontend. `API_INTERNAL_URL` pode alterar o destino interno da API no desenvolvimento dos frontends.

## Editar e reiniciar

```sh
docker compose up --build -d
```

As imagens contêm o código; mudanças Python exigem rebuild. Migrações são reaplicadas de forma idempotente. O frontend usa recarga de desenvolvimento. Para parar mantendo dados:

```sh
docker compose stop
```

Os volumes `postgres_data`, `storage_data` e `mailpit_data` preservam banco, imagens e email entre recriações. Não remova volumes para resolver erros. Trocar `POSTGRES_PASSWORD` em `.env` não altera a senha de um banco já inicializado: rotação exige alteração coordenada no banco e nos clientes. O PostgreSQL 18 monta o volume em `/var/lib/postgresql`, conforme sua [imagem oficial](https://hub.docker.com/_/postgres).

## API fora do Docker

É possível manter os serviços locais no Compose e executar a API no host:

```sh
docker compose up -d db storage mailpit
python -m venv .venv
```

Ative `.venv` (`.venv\Scripts\Activate.ps1` no PowerShell ou `source .venv/bin/activate` em POSIX). Em seguida:

```sh
python -m pip install -r apps/api/requirements-dev.lock
python scripts/manage.py check
```

Se o banco ainda não foi provisionado, use `docker compose run --rm db-bootstrap`, depois `python scripts/manage.py migrate`. Inicialize o bucket com `docker compose run --rm storage-init`. Pare `api` do Compose caso esteja rodando; então execute `python scripts/manage.py runserver 127.0.0.1:8000`. Execute `python infra/mail_worker.py` em outro terminal para processar a fila de recuperação. O helper `scripts/manage.py` carrega `.env`; comandos de migração selecionam `MIGRATION_DATABASE_URL` explicitamente.

## Verificação

Com o ambiente Python ativado, o PostgreSQL acessível e a role provisionada:

```sh
python -m ruff check apps/api scripts infra
python scripts/manage.py makemigrations --check --dry-run
python scripts/manage.py check
python scripts/test_backend.py -q
python scripts/manage.py spectacular --file docs/api/openapi.yaml --validate --fail-on-warn
npm run generate:api
npm run typecheck
npm run build
```

O pytest cria `test_tavvo` separado por meio do owner e testa também `SET LOCAL ROLE tavvo_app`; não faça testes apontando para banco de produção. Os testes de storage podem usar Moto como emulador do contrato S3. Isso não substitui o ensaio do provedor S3 escolhido para produção. Versione o schema e os tipos gerados juntos quando o contrato mudar; a CI rejeita divergências.

Para demonstrar os dois restaurantes, use `python scripts/seed_demo.py` com os serviços rodando. Contas, categorias, produtos e mesa são criados pela API; as credenciais aleatórias ficam em `.local/demo-credentials.json`, sem impressão no terminal. Execute `python scripts/test_e2e.py` para conferir os fluxos reais. O seed é restrito a desenvolvimento local; não é um mecanismo de provisionamento de contas de produção.

O lock de runtime exclui pytest, Ruff e Moto. `requirements-dev.lock` inclui o runtime e os testes. Dependências exclusivas do Windows usam markers; Linux é exercitado no workflow. Atualize ambos os locks juntos e teste resolução, migrações e regressões antes de alterar versões.

## Diagnóstico

- `db-bootstrap` ou `migrate` com falha: veja logs, conexão owner e versão do banco. Não use owner na API para contornar RLS.
- Imagem retorna 503: confira `storage-init`, bucket e credenciais. `/ready/` testa o banco, não a disponibilidade de S3/SMTP.
- Recuperação sem email: confira `auth-mail` e Mailpit. O worker processa lotes a cada 10 segundos; solicitações expiram após 15 minutos e falhas são limitadas a cinco tentativas.
- Porta ocupada: pare a instância local conflitante antes de iniciar outra. As portas padrão são 55432, 8000, 9000, 9001, 1025 e 8025.
- Erro de CSRF: confirme o hostname, o proxy do Vite e `CSRF_TRUSTED_ORIGINS`; não desative a proteção.

Docker não está instalado nesta estação Windows. O Compose completo foi compilado e executado em Ubuntu no [GitHub Actions](https://github.com/Eduuh1227/Tavvo-Project/actions/runs/39478968836), com os três testes de navegador aprovados usando MinIO real e comparação dos dados após reiniciar os serviços. Consulte a [evidência de execução](../verification/2026-10-20.md) para os limites do ensaio.
