# Tavvo Restaurants

SaaS multi-tenant de cardápios digitais, com backend central Django REST Framework, PostgreSQL, painéis React e site público Next.js.

## Executar localmente

Pré-requisitos: Python 3.12, Node.js 22.12+ e Docker Compose v2. Na raiz:

```sh
python scripts/configure_local.py
docker compose up --build -d
docker compose exec api python scripts/manage.py createsuperuser
npm ci
```

Execute `npm run dev:admin` e `npm run dev:public` em terminais separados. Abra o painel em `http://localhost:5173` e o site público em `http://localhost:3000`. O primeiro administrador é criado interativamente, sem senha padrão; o login exige cadastrar MFA. Detalhes, portas, worker de email e solução de problemas: [execução local](docs/runbooks/local-development.md).

O PostgreSQL e o S3 local têm volumes persistentes. A API usa uma role sem propriedade de tabelas ou bypass de RLS; migrações usam credencial separada. `python scripts/configure_local.py` gera segredos aleatórios e não sobrescreve `.env` existente. Não versione segredos.

## Estrutura

- `apps/api`: identidade/MFA, restaurantes, catálogo, publicação, mesas/QR e auditoria.
- `apps/admin`: painéis Tavvo e restaurante em React/Vite.
- `apps/public-reference`: site Next.js alimentado pela API pública.
- `packages/api-client`: contrato compartilhado pelos frontends.
- `infra`: bootstrap de banco, runtime, armazenamento local e worker de recuperação.
- `docs`: decisões e procedimentos operacionais.

## Verificar

Com `.env`, PostgreSQL e o ambiente Python configurados:

```sh
python -m pip install -r apps/api/requirements-dev.lock
python -m ruff check apps/api scripts infra
python scripts/manage.py makemigrations --check --dry-run
python scripts/test_backend.py -q
python scripts/manage.py spectacular --file docs/api/openapi.yaml --validate --fail-on-warn
npm run generate:api
npm run typecheck
npm run build
```

O helper de testes usa banco isolado `test_tavvo`; não configure conexão de produção para executar pytest. A CI repete a verificação em PostgreSQL 18 real, com role runtime separada, e verifica os builds dos frontends. O workflow não realiza deploy.

Com API, S3, painel e site rodando, a demonstração completa usa:

```sh
python scripts/seed_demo.py
python scripts/test_e2e.py
python scripts/verify_persistence.py snapshot
```

Reinicie os serviços preservando seus dados e execute `python scripts/verify_persistence.py verify`, sem repetir o seed. As credenciais geradas ficam somente em `.local/`, ignorado pelo Git. Consulte [testes de navegador](tests/e2e/README.md).

## Estado e operação

O fluxo local integrado passou em PostgreSQL real: 40 testes de backend e três testes de navegador, além de comparação dos dados após reiniciar aplicações e banco. O contrato OpenAPI validado gera os tipos compartilhados dos frontends. Consulte [evidências e limites da validação](docs/verification/2026-10-20.md).

Não há deploy de produção, infraestrutura contratada nem credenciais de produção. Docker não está instalado nesta estação: o Compose completo tem um job de CI dedicado, cujo resultado precisa ser conferido no GitHub. Os testes locais de imagens usaram Moto como emulador S3; não comprovam a operação de um provedor de produção.

- [Publicação manual e observabilidade](docs/runbooks/production.md)
- [Backup e restauração](docs/runbooks/backup-restore.md)
- [Decisão arquitetural](docs/adr/0001-foundation.md)

## Decisões

A stack foi aprovada na conversa de desenvolvimento de 19/10/2026, quando o responsável informou este repositório e autorizou iniciar a implementação. O repositório remoto estava vazio; não havia implementação ou documentação v1.0 para preservar.

Consulte `docs/adr/0001-foundation.md` para os limites arquiteturais. Commits seguem Conventional Commits: `feat`, `fix`, `test`, `docs`, `chore` e `ci`, com escopo quando útil.
