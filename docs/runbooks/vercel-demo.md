# Demonstração na Vercel

O projeto `tavvo-demo` usa Vercel Services (beta) para publicar três serviços em
um Preview: painel Vite na raiz, Django em `/v1/` e Next.js em `/r/` e `/q/`.
O binding `API_INTERNAL_URL` permite que Next consulte o Django do mesmo deploy.
As rotas do navegador usam a mesma origem, preservando sessões e CSRF.

## Recursos

- Conta Vercel Hobby, projeto exclusivo `tavvo-demo`.
- Supabase Free exclusivo, região São Paulo, PostgreSQL e bucket privado
  `tavvo-images`. Não reutilizar um banco comercial neste procedimento.
- Dados fictícios e credenciais diferentes do desenvolvimento local.
- Recuperação de senha por e-mail indisponível nesta demonstração; o aviso
  aparece no login quando `VITE_DEMO_MODE=true`.
- Imagens limitadas a 4 MiB na demonstração para respeitar o limite de corpo
  das Functions. A configuração local continua permitindo 5 MiB.

## Preparação

1. Criar/vincular o projeto Vercel e conectar o recurso Supabase gratuito aos
   ambientes Preview e Development. Aceitar termos na conta do titular.
2. Executar `vercel env pull .local/vercel-supabase.env --environment development`.
   O arquivo e todo o diretório `.local/` são ignorados por Git e pelo deploy.
3. Com as dependências Python instaladas, executar:

   ```powershell
   python scripts/prepare_vercel_demo.py --project-ref REF_DO_PROJETO --dedicated-demo
   ```

   O script verifica o projeto, gera segredos próprios, provisiona `tavvo_app`
   sem superusuário/bypass RLS, migra o banco e fecha o acesso do Data API ao
   schema Django. Também testa upload/leitura/exclusão no bucket privado.
   Apenas a migração usa a conexão do proprietário. Reexecutar o provisionamento
   após futuras migrações para aplicar as permissões das tabelas novas.

4. Configurar em **Preview** os valores de `.local/vercel-demo.env`:

   | Tipo | Variáveis |
   | --- | --- |
   | Secret | `DATABASE_URL`, `DJANGO_SECRET_KEY`, `TAVVO_MFA_ENCRYPTION_KEY`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_SESSION_TOKEN` |
   | Config | `TAVVO_ENV`, `DATABASE_SSLMODE`, `DJANGO_ALLOWED_HOSTS`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_BUCKET`, `IMAGE_MAX_BYTES`, `VITE_DEMO_MODE` |

   **Não enviar** `MIGRATION_DATABASE_URL` nem `TAVVO_DB_PASSWORD` como variáveis
   adicionais. `VERCEL`, `VERCEL_URL` e o binding são fornecidos pela plataforma.
   A conexão `DATABASE_URL` já contém a senha do usuário restrito da aplicação.
   A chave de serviço de storage fica exclusivamente no servidor.
   Incluir em `DJANGO_ALLOWED_HOSTS` também o hostname exato do binding interno
   do serviço `api` deste projeto. A Vercel usa um host em
   `services.vercel-infra.com`; não liberar o domínio inteiro com wildcard.
   Os hosts públicos do deploy são adicionados pelas variáveis da plataforma.

5. Validar `npm run typecheck`, `npm run build` e os testes de backend locais.
   Executar `vercel deploy` no diretório vinculado, conferir o build remoto e
   guardar a URL efetivamente retornada. Não promover automaticamente a produção.
   Confirmar o ambiente efetivo retornado: a plataforma pode classificar o
   primeiro deploy de um projeto novo como Production. Manter os segredos de
   demonstração em Preview e usar um Preview confirmado para os testes.
   `apps/api/requirements.txt` deve repetir as versões de `requirements.lock`:
   o builder de Services requer um manifesto direto, sem a inclusão `-r`.
6. Criar um link compartilhável do Preview, com prazo, mantendo a proteção da
   Vercel. Credenciais de login são enviadas separadamente pelo titular.
7. Carregar as variáveis de demo no processo local e executar
   `python scripts/seed_demo.py --remote-demo https://HOST_DO_PREVIEW.vercel.app`.
   Se o Preview exigir link compartilhado, fornecer seu token ao processo em
   `TAVVO_DEMO_SHARE_TOKEN`. O script grava credenciais/IDs separados em
   `.local/vercel-demo-credentials.json` e `.local/vercel-demo-records.json`.
   A conta central mantém MFA obrigatório.
8. Verificar navegador → API → banco → resposta: login, alteração de produto,
   cardápio público, imagem, QR e isolamento A/B. Revogar a sessão administrativa
   criada para testes e remover o arquivo temporário de cookies após verificar.
   A suíte aceita `TAVVO_E2E_SHARE_TOKEN` e os três endereços `TAVVO_E2E_*_URL`
   apontando ao Preview. O teste de QR navega para o endereço realmente emitido
   pela API, sem substituir sua origem.

## Limites e operação

Este ambiente serve para apresentação. Não contém dados de clientes nem SMTP,
monitoramento operacional ou rotina de backup de produção. Não representa a
liberação comercial descrita no runbook de produção. Os planos gratuitos estão
sujeitos aos limites e políticas dos provedores; não habilitar upgrades pagos
automaticamente. Ao encerrar a demonstração, revogar o link compartilhado e
arquivar os recursos dedicados conforme autorização do titular.
